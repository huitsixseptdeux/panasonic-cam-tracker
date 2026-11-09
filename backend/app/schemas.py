from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class SourceSpec(BaseModel):
    type: Literal["webcam", "file"]
    id: str


class TargetSpec(BaseModel):
    track_id: Optional[int] = None


class TrackingAction(BaseModel):
    action: Literal["start", "stop"]


class SettingsUpdate(BaseModel):
    dead_zone_pct: Optional[float] = None
    damping: Optional[float] = None
    max_speed_px: Optional[float] = None
    target_fill_pct: Optional[float] = None
    subject_portion: Optional[float] = None
    confidence: Optional[float] = None

