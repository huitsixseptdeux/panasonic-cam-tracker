"""Links faces to tracked bodies and names them against the library.

Two halves, split by thread:
- `observe()` runs on the face worker thread (`executor`): the only code that
  touches the face models. Pure function of (frame, tracks).
- `apply()` / `current()` run on the pipeline thread: they keep the per-track
  memory and project each remembered face onto the body's current position,
  so names and face boxes stay put between (rare) face checks.

Deciding *when* to observe is `scheduler.py`'s job, not this module's.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..tracker import Track
from .base import BBox, FaceStack
from .library import FaceLibrary


@dataclass
class Identity:
    face_bbox: Optional[BBox] = None
    person_id: Optional[str] = None
    name: Optional[str] = None
    score: float = 0.0


@dataclass
class FaceObservation:
    track_id: int
    body: BBox
    face: Optional[BBox]
    person_id: Optional[str]
    score: float


@dataclass
class FaceCandidate:
    bbox: BBox
    crop: np.ndarray
    embedding: np.ndarray


@dataclass
class _Memory:
    person_id: Optional[str]
    score: float
    rel_face: Optional[BBox]  # face box as fractions of the body box
    checked_at: float


def _face_in_body(face: BBox, body: BBox) -> bool:
    fx = (face[0] + face[2]) / 2.0
    fy = (face[1] + face[3]) / 2.0
    x1, y1, x2, y2 = body
    return x1 <= fx <= x2 and y1 <= fy <= y1 + (y2 - y1) * 0.5


def _to_rel(face: BBox, body: BBox) -> BBox:
    bw, bh = max(1.0, body[2] - body[0]), max(1.0, body[3] - body[1])
    return ((face[0] - body[0]) / bw, (face[1] - body[1]) / bh, (face[2] - body[0]) / bw, (face[3] - body[1]) / bh)


def _from_rel(rel: BBox, body: BBox) -> BBox:
    bw, bh = body[2] - body[0], body[3] - body[1]
    return (body[0] + rel[0] * bw, body[1] + rel[1] * bh, body[0] + rel[2] * bw, body[1] + rel[3] * bh)


def crop_with_margin(frame: np.ndarray, bbox: BBox, margin: float = 0.35) -> np.ndarray:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    xa, ya = max(0, int(x1 - mx)), max(0, int(y1 - my))
    xb, yb = min(w, int(x2 + mx)), min(h, int(y2 + my))
    return frame[ya:yb, xa:xb].copy()


class IdentityResolver:
    def __init__(self, stack: FaceStack, library: FaceLibrary):
        self.stack = stack
        self.library = library
        # Single thread owns the face models; every model call goes through it.
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="faces")
        self._mem: dict[int, _Memory] = {}

    # ---- pipeline thread ------------------------------------------------

    def reset(self) -> None:
        self._mem.clear()

    def last_checked(self, track_id: int) -> Optional[float]:
        m = self._mem.get(track_id)
        return m.checked_at if m else None

    def person_of(self, track_id: Optional[int]) -> Optional[str]:
        if track_id is None:
            return None
        m = self._mem.get(track_id)
        return m.person_id if m else None

    def apply(self, observations: list[FaceObservation], live_ids: set[int]) -> None:
        now = time.monotonic()
        for o in observations:
            if o.track_id not in live_ids:
                continue
            prev = self._mem.get(o.track_id)
            if o.face is None:
                # Face turned away or hidden: keep who we think it is.
                if prev:
                    prev.checked_at = now
                else:
                    self._mem[o.track_id] = _Memory(None, 0.0, None, now)
                continue
            self._mem[o.track_id] = _Memory(o.person_id, o.score, _to_rel(o.face, o.body), now)
            if o.person_id:
                # A person can only be in one place: the newest sighting wins.
                for tid, m in self._mem.items():
                    if tid != o.track_id and m.person_id == o.person_id:
                        m.person_id, m.score = None, 0.0

    def current(self, tracks: list[Track]) -> dict[int, Identity]:
        live = {t.track_id for t in tracks}
        self._mem = {k: v for k, v in self._mem.items() if k in live}
        out: dict[int, Identity] = {}
        for t in tracks:
            m = self._mem.get(t.track_id)
            if m is None:
                continue
            person = self.library.get(m.person_id) if m.person_id else None
            out[t.track_id] = Identity(
                face_bbox=_from_rel(m.rel_face, t.bbox) if m.rel_face else None,
                person_id=m.person_id if person else None,
                name=person.name if person else None,
                score=m.score,
            )
        return out

    def match(self, embedding: np.ndarray) -> tuple[Optional[str], float]:
        best_id, best = None, -1.0
        for person in self.library.usable():
            for ref in person.vectors():
                s = self.stack.embedder.similarity(embedding, ref)
                if s > best:
                    best_id, best = person.id, s
        if best >= self.stack.embedder.match_threshold:
            return best_id, best
        return None, best

    # ---- face worker thread ---------------------------------------------

    def observe(self, frame: np.ndarray, tracks: list[Track]) -> list[FaceObservation]:
        faces = self.stack.detector.detect(frame)
        out = []
        for t in tracks:
            inside = [f for f in faces if _face_in_body(f.bbox, t.bbox)]
            if not inside:
                out.append(FaceObservation(t.track_id, t.bbox, None, None, 0.0))
                continue
            face = max(inside, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            pid, score = self.match(self.stack.embedder.embed(frame, face))
            out.append(FaceObservation(t.track_id, t.bbox, face.bbox, pid, score))
        return out

    def candidates(self, image: np.ndarray) -> list[FaceCandidate]:
        out = []
        for face in self.stack.detector.detect(image)[:10]:
            out.append(
                FaceCandidate(
                    bbox=face.bbox,
                    crop=crop_with_margin(image, face.bbox),
                    embedding=self.stack.embedder.embed(image, face),
                )
            )
        return out
