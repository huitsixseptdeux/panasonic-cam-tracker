from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .tracker import Track


@dataclass
class Crop:
    x: float
    y: float
    w: float
    h: float


@dataclass
class FramingSettings:
    dead_zone_pct: float = 0.08  # fraction of crop size the target can drift before we move
    damping: float = 0.12  # exponential smoothing factor per frame, 0..1 (higher = snappier)
    max_speed_px: float = 40.0  # max crop-center movement per frame, in source pixels
    target_fill_pct: float = 0.8  # desired subject height as a fraction of crop height
    subject_portion: float = 1.0  # top fraction of the body to frame (0.45 = head and shoulders)
    reacquire_hold_frames: int = 20  # frames to hold last crop after losing the subject
    reacquire_ease: float = 0.03  # how fast the crop eases back to full frame once lost


class AutoFramer:
    """Smoothly pans/zooms a crop window to keep the selected subject framed.

    This is the digital equivalent of PTZ: instead of moving a physical camera,
    we move/resize a crop rectangle over a high-resolution source frame.
    """

    def __init__(self, frame_w: int, frame_h: int, settings: Optional[FramingSettings] = None):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.settings = settings or FramingSettings()
        self._crop = Crop(x=0, y=0, w=float(frame_w), h=float(frame_h))
        self._missing_frames = 0

    def resize(self, frame_w: int, frame_h: int) -> None:
        self.frame_w, self.frame_h = frame_w, frame_h

    def update(self, target: Optional[Track]) -> Crop:
        s = self.settings
        full_aspect = self.frame_w / self.frame_h

        if target is None:
            self._missing_frames += 1
            if self._missing_frames > s.reacquire_hold_frames:
                # Ease back out toward the full frame rather than snapping.
                self._move_toward(
                    Crop(x=0, y=0, w=float(self.frame_w), h=float(self.frame_h)),
                    alpha=s.reacquire_ease,
                )
            return self._clamped_crop()

        self._missing_frames = 0
        tx1, ty1, tx2, ty2 = target.bbox
        portion = min(1.0, max(0.2, s.subject_portion))
        subj_h = max(1.0, (ty2 - ty1) * portion)
        subj_cx = (tx1 + tx2) / 2.0
        subj_cy = ty1 + subj_h / 2.0

        desired_crop_h = subj_h / s.target_fill_pct
        desired_crop_w = desired_crop_h * full_aspect
        desired_crop_h = min(desired_crop_h, self.frame_h)
        desired_crop_w = min(desired_crop_w, self.frame_w)

        desired = Crop(
            x=subj_cx - desired_crop_w / 2.0,
            y=subj_cy - desired_crop_h / 2.0,
            w=desired_crop_w,
            h=desired_crop_h,
        )

        cur_cx = self._crop.x + self._crop.w / 2.0
        cur_cy = self._crop.y + self._crop.h / 2.0
        des_cx = desired.x + desired.w / 2.0
        des_cy = desired.y + desired.h / 2.0

        dead_zone_px = s.dead_zone_pct * self._crop.w
        if abs(des_cx - cur_cx) < dead_zone_px and abs(des_cy - cur_cy) < dead_zone_px:
            # Still smooth size changes (zoom) even when we don't pan.
            self._crop.w += (desired.w - self._crop.w) * s.damping
            self._crop.h += (desired.h - self._crop.h) * s.damping
            self._crop.x = cur_cx - self._crop.w / 2.0
            self._crop.y = cur_cy - self._crop.h / 2.0
            return self._clamped_crop()

        self._move_toward(desired, alpha=s.damping, max_speed_px=s.max_speed_px)
        return self._clamped_crop()

    def _move_toward(self, desired: Crop, alpha: float, max_speed_px: Optional[float] = None) -> None:
        cur_cx = self._crop.x + self._crop.w / 2.0
        cur_cy = self._crop.y + self._crop.h / 2.0
        des_cx = desired.x + desired.w / 2.0
        des_cy = desired.y + desired.h / 2.0

        dx = (des_cx - cur_cx) * alpha
        dy = (des_cy - cur_cy) * alpha
        if max_speed_px is not None:
            dx = max(-max_speed_px, min(max_speed_px, dx))
            dy = max(-max_speed_px, min(max_speed_px, dy))

        self._crop.w += (desired.w - self._crop.w) * alpha
        self._crop.h += (desired.h - self._crop.h) * alpha
        new_cx = cur_cx + dx
        new_cy = cur_cy + dy
        self._crop.x = new_cx - self._crop.w / 2.0
        self._crop.y = new_cy - self._crop.h / 2.0

    def _clamped_crop(self) -> Crop:
        w = max(10.0, min(self._crop.w, self.frame_w))
        h = max(10.0, min(self._crop.h, self.frame_h))
        x = max(0.0, min(self._crop.x, self.frame_w - w))
        y = max(0.0, min(self._crop.y, self.frame_h - h))
        self._crop = Crop(x=x, y=y, w=w, h=h)
        return self._crop
