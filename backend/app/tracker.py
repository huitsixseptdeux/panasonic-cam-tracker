from __future__ import annotations

import abc
from dataclasses import dataclass

from .detector import Detection


@dataclass
class Track:
    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class Tracker(abc.ABC):
    @abc.abstractmethod
    def update(self, detections: list[Detection]) -> list[Track]:
        ...


class CentroidTracker(Tracker):
    """Minimal IOU-assisted centroid tracker.

    Deliberately simple for Phase 1: greedy-matches new detections to existing
    tracks by IOU (falling back to nearest centroid), keeps a track alive for
    `max_missed` frames after it stops matching, then drops it.

    Known, documented limitations (see ARCHITECTURE.md):
    - No motion model / Kalman filter, so fast motion can break IOU matching.
    - No appearance re-identification: two people crossing paths can swap IDs,
      and a person who leaves and re-enters frame gets a brand new ID.
    This is an intentional scope cut for the MVP, not an oversight.
    """

    def __init__(self, max_missed: int = 15, iou_threshold: float = 0.2):
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self._next_id = 1
        self._tracks: dict[int, Track] = {}
        self._missed: dict[int, int] = {}

    def update(self, detections: list[Detection]) -> list[Track]:
        unmatched_dets = list(range(len(detections)))
        matched_ids: set[int] = set()

        # Greedy best-IOU matching, highest IOU first.
        pairs: list[tuple[float, int, int]] = []
        for tid, track in self._tracks.items():
            for di in unmatched_dets:
                score = iou(track.bbox, detections[di].bbox)
                if score >= self.iou_threshold:
                    pairs.append((score, tid, di))
        pairs.sort(key=lambda p: p[0], reverse=True)

        used_dets: set[int] = set()
        used_tracks: set[int] = set()
        for score, tid, di in pairs:
            if tid in used_tracks or di in used_dets:
                continue
            det = detections[di]
            self._tracks[tid] = Track(track_id=tid, bbox=det.bbox, confidence=det.confidence)
            self._missed[tid] = 0
            used_tracks.add(tid)
            used_dets.add(di)
            matched_ids.add(tid)

        # Unmatched existing tracks age out.
        for tid in list(self._tracks.keys()):
            if tid not in matched_ids:
                self._missed[tid] = self._missed.get(tid, 0) + 1
                if self._missed[tid] > self.max_missed:
                    del self._tracks[tid]
                    del self._missed[tid]

        # Unmatched detections spawn new tracks.
        for di in unmatched_dets:
            if di in used_dets:
                continue
            det = detections[di]
            tid = self._next_id
            self._next_id += 1
            self._tracks[tid] = Track(track_id=tid, bbox=det.bbox, confidence=det.confidence)
            self._missed[tid] = 0

        return list(self._tracks.values())
