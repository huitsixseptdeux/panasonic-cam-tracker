"""Event-based policy: which tracks need a face check right now.

Faces are not checked every frame. Work happens only on events:
- recognition is OFF                -> nothing
- a new body appears                -> check it once
- searching (target not found/lost) -> check unknown bodies a few times a second
- target locked                     -> re-confirm its face every couple of seconds
- target box overlaps someone       -> re-check both (an ID swap is likely)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from ..tracker import Track, iou
from .identity import IdentityResolver


@dataclass
class SchedulerConfig:
    search_interval_s: float = 0.25
    confirm_interval_s: float = 2.0
    overlap_interval_s: float = 0.5
    overlap_iou: float = 0.05
    max_per_job: int = 8


class FaceScheduler:
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.cfg = config or SchedulerConfig()
        self._seen: set[int] = set()

    def reset(self) -> None:
        self._seen.clear()

    def due(
        self,
        tracks: list[Track],
        resolver: IdentityResolver,
        mode: str,
        target_track_id: Optional[int],
        target_person_id: Optional[str],
    ) -> list[Track]:
        live = {t.track_id: t for t in tracks}
        new_ids = set(live) - self._seen
        self._seen = set(live)
        if mode == "off" or not tracks:
            return []

        now = time.monotonic()

        def older_than(tid: int, interval: float) -> bool:
            last = resolver.last_checked(tid)
            return last is None or now - last >= interval

        due: dict[int, Track] = {tid: live[tid] for tid in new_ids}

        if mode == "select":
            searching = not any(resolver.person_of(tid) == target_person_id for tid in live)
        else:
            searching = target_track_id not in live or resolver.person_of(target_track_id) is None

        if searching:
            for tid, t in live.items():
                if resolver.person_of(tid) is None and older_than(tid, self.cfg.search_interval_s):
                    due[tid] = t

        target = live.get(target_track_id) if target_track_id is not None else None
        if target is not None:
            if older_than(target.track_id, self.cfg.confirm_interval_s):
                due[target.track_id] = target
            for t in tracks:
                if t is not target and iou(t.bbox, target.bbox) > self.cfg.overlap_iou:
                    if older_than(target.track_id, self.cfg.overlap_interval_s):
                        due[target.track_id] = target
                        due[t.track_id] = t

        return list(due.values())[: self.cfg.max_per_job]
