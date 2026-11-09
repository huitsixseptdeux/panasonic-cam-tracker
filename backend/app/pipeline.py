from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from .autoframer import AutoFramer, FramingSettings
from .detector import Detector, YoloPersonDetector
from .faces.identity import Identity, IdentityResolver
from .faces.scheduler import FaceScheduler
from .output import WebSocketPreview
from .sources import VideoSource, make_source
from .tracker import CentroidTracker, Track

logger = logging.getLogger("pipeline")

FACE_MODES = ("off", "select", "auto")


def _timed_observe(identity: IdentityResolver, frame, tracks: list[Track]):
    t0 = time.perf_counter()
    obs = identity.observe(frame, tracks)
    return obs, (time.perf_counter() - t0) * 1000.0


def _area(t: Track) -> float:
    return (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1])


class Pipeline:
    def __init__(self, output: WebSocketPreview, identity: Optional[IdentityResolver] = None):
        self.output = output
        # Optional: the pipeline works without faces; None when models are missing.
        self.identity = identity
        # "off": body tracking only. "select": follow face_person_id.
        # "auto": follow any registered person, highest priority first.
        self.face_mode = "off"
        self.face_person_id: Optional[str] = None
        self.face_scheduler = FaceScheduler()
        # In-flight face job: (generation, future). The generation guards against
        # applying results computed for a previous source's track IDs.
        self._face_job = None
        self._face_gen = 0
        self.face_checks_last_job = 0
        self.face_job_ms = 0.0
        self.last_frame = None
        self.source: Optional[VideoSource] = None
        self.source_type: Optional[str] = None
        self.source_id: Optional[str] = None

        self.detector: Optional[Detector] = None
        self.tracker = CentroidTracker()
        self.autoframer: Optional[AutoFramer] = None
        self.framing = FramingSettings()
        self.confidence = 0.4

        # `running`: frames are being captured and detected (live preview).
        # `tracking`: the crop follows the selected target. Kept separate so the
        # preview is always live and the operator picks a target before engaging.
        self.running = False
        self.tracking = False
        self.selected_track_id: Optional[int] = None
        self.dropped_frames = 0
        self.fps = 0.0
        self.last_error: Optional[str] = None
        self.person_detected = False

        self._task: Optional[asyncio.Task] = None
        self._frame_times: list[float] = []

    def _ensure_detector(self) -> Detector:
        if self.detector is None:
            logger.info("Loading YOLO person detector (first use may download weights)...")
            self.detector = YoloPersonDetector(confidence=self.confidence)
        return self.detector

    async def set_source(self, source_type: str, source_id: str) -> None:
        await self.stop()
        if self.source is not None:
            self.source.close()
        self.source = make_source(source_type, source_id)
        ok = self.source.open()
        self.source_type, self.source_id = source_type, source_id
        self.tracker = CentroidTracker()
        self.selected_track_id = None
        self.autoframer = None
        if self.identity is not None:
            self.identity.reset()
        self.face_scheduler.reset()
        self._face_gen += 1
        self._face_job = None
        if not ok:
            self.last_error = f"Failed to open source {source_type}:{source_id}"
            logger.error(self.last_error)
            return
        self.last_error = None
        await self.start()

    async def start(self) -> None:
        if self.running or self.source is None:
            return
        self._ensure_detector()
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    def set_tracking(self, enabled: bool) -> None:
        self.tracking = enabled

    async def stop(self) -> None:
        self.running = False
        self.tracking = False
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except Exception:
                pass
            self._task = None

    def select_target(self, track_id: Optional[int]) -> None:
        self.selected_track_id = track_id

    def set_recognition(self, mode: str, person_id: Optional[str]) -> None:
        if mode not in FACE_MODES:
            raise ValueError(f"mode must be one of {FACE_MODES}")
        self.face_mode = mode
        self.face_person_id = person_id

    def _choose_target(self, tracks: list[Track], ids: dict[int, Identity]) -> None:
        """Update selected_track_id. Face identity wins over the body ID, which is
        how a person who came back with a new body ID gets picked up again."""
        if not self.tracking or not tracks:
            return

        if self.face_mode == "select" and self.face_person_id:
            match = next((t for t in tracks if ids.get(t.track_id, Identity()).person_id == self.face_person_id), None)
            if match is not None:
                self.selected_track_id = match.track_id
            return  # wait for that face; never fall back to someone else

        if self.face_mode == "auto" and self.identity is not None:
            current = ids.get(self.selected_track_id, Identity()) if self.selected_track_id is not None else Identity()
            if current.person_id is None:
                order = {p.id: p.order for p in self.identity.library.list()}
                known = [t for t in tracks if ids.get(t.track_id, Identity()).person_id in order]
                if known:
                    best = min(known, key=lambda t: order[ids[t.track_id].person_id])
                    self.selected_track_id = best.track_id
                    return

        if self.selected_track_id is None:
            self.selected_track_id = max(tracks, key=_area).track_id

    def update_settings(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if value is not None and hasattr(self.framing, key):
                setattr(self.framing, key, value)
        confidence = kwargs.get("confidence")
        if confidence is not None:
            self.confidence = confidence
            if self.detector is not None:
                self.detector.confidence = confidence

    async def _run_loop(self) -> None:
        loop = asyncio.get_event_loop()
        assert self.source is not None
        assert self.detector is not None

        while self.running:
            frame = await loop.run_in_executor(None, self.source.read)
            if frame is None:
                self.dropped_frames += 1
                if not self.source.is_open:
                    self.last_error = "Video source disconnected"
                    self.running = False
                    await self._publish_status_only()
                    break
                await asyncio.sleep(0.05)
                continue

            h, w = frame.shape[:2]
            if self.autoframer is None:
                self.autoframer = AutoFramer(w, h, self.framing)
            else:
                self.autoframer.resize(w, h)

            self.last_frame = frame
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)
            self.person_detected = len(tracks) > 0
            ids = self._pump_faces(frame, tracks)

            self._choose_target(tracks, ids)

            target: Optional[Track] = None
            if self.tracking and self.selected_track_id is not None:
                target = next((t for t in tracks if t.track_id == self.selected_track_id), None)

            crop = self.autoframer.update(target)
            self._tick_fps()

            metadata = {
                "w": w,
                "h": h,
                "detections": [self._detection_dict(t, ids.get(t.track_id)) for t in tracks],
                "selected_track_id": self.selected_track_id,
                "crop": {"x": crop.x, "y": crop.y, "w": crop.w, "h": crop.h},
                "status": self.status_dict(),
            }
            await self.output.publish(frame, metadata)

    def _pump_faces(self, frame, tracks: list[Track]) -> dict[int, Identity]:
        """Collect a finished face job, start a new one if the scheduler asks.
        Never waits on the face worker."""
        if self.identity is None:
            return {}

        if self._face_job is not None:
            gen, fut = self._face_job
            if fut.done():
                self._face_job = None
                try:
                    observations, ms = fut.result()
                    if gen == self._face_gen:
                        self.identity.apply(observations, {t.track_id for t in tracks})
                        self.face_checks_last_job = len(observations)
                        self.face_job_ms = ms
                except Exception:
                    logger.exception("Face job failed")

        if self._face_job is None:
            due = self.face_scheduler.due(
                tracks, self.identity, self.face_mode, self.selected_track_id, self.face_person_id
            )
            if due:
                fut = self.identity.executor.submit(_timed_observe, self.identity, frame.copy(), due)
                self._face_job = (self._face_gen, fut)

        return self.identity.current(tracks)

    @staticmethod
    def _detection_dict(t: Track, ident: Optional[Identity]) -> dict:
        d = {"id": t.track_id, "bbox": list(t.bbox), "conf": round(t.confidence, 3)}
        if ident is not None:
            d["face_bbox"] = list(ident.face_bbox) if ident.face_bbox else None
            d["person_id"] = ident.person_id
            d["person_name"] = ident.name
        return d

    async def _publish_status_only(self) -> None:
        await self.output.publish_status(self.status_dict())

    def _tick_fps(self) -> None:
        now = time.monotonic()
        self._frame_times.append(now)
        cutoff = now - 2.0
        self._frame_times = [t for t in self._frame_times if t >= cutoff]
        if len(self._frame_times) >= 2:
            self.fps = (len(self._frame_times) - 1) / (self._frame_times[-1] - self._frame_times[0])

    def status_dict(self) -> dict:
        return {
            "running": self.running,
            "tracking": self.tracking,
            "source_open": bool(self.source and self.source.is_open),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "fps": round(self.fps, 1),
            "dropped_frames": self.dropped_frames,
            "device": self.detector.device if self.detector else "none",
            "selected_track_id": self.selected_track_id,
            "person_detected": self.person_detected,
            "error": self.last_error,
            "face_mode": self.face_mode,
            "face_person_id": self.face_person_id,
            "faces_available": self.identity is not None,
            "face_busy": self._face_job is not None,
            "face_checks_last_job": self.face_checks_last_job,
            "face_job_ms": round(self.face_job_ms),
        }
