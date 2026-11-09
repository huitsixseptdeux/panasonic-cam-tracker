from __future__ import annotations

import abc
import glob
import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class SourceInfo:
    type: str
    id: str
    label: str


class VideoSource(abc.ABC):
    """Common interface for anything that can hand us frames.

    Concrete sources today: webcam (UVC via OpenCV) and local video files.
    RTSP/NDI/ONVIF sources plug in here later as new subclasses — the pipeline
    never needs to change.
    """

    @abc.abstractmethod
    def open(self) -> bool:
        ...

    @abc.abstractmethod
    def read(self) -> Optional[np.ndarray]:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...

    @property
    @abc.abstractmethod
    def is_open(self) -> bool:
        ...


class WebcamSource(VideoSource):
    def __init__(self, index: int):
        self.index = index
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.index)
        if self._cap.isOpened():
            # Drivers default to 640x480; digital framing needs resolution headroom
            # to crop into. MJPG is needed for most UVC cams to reach 1080p30.
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        return self._cap.isOpened()

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        return frame if ok else None

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()


class FileSource(VideoSource):
    """Plays a local video file, looping at EOF so a demo never just stops."""

    def __init__(self, path: str):
        self.path = path
        self._cap: Optional[cv2.VideoCapture] = None
        self._last_read = 0.0
        self._frame_interval = 1.0 / 30.0

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.path)
        if self._cap.isOpened():
            fps = self._cap.get(cv2.CAP_PROP_FPS)
            if fps and fps > 1:
                self._frame_interval = 1.0 / fps
        return self._cap.isOpened()

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None:
            return None
        # Pace file playback to its native fps so detection isn't fed frames
        # faster than real time.
        elapsed = time.monotonic() - self._last_read
        if elapsed < self._frame_interval:
            time.sleep(self._frame_interval - elapsed)
        self._last_read = time.monotonic()

        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        return frame if ok else None

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()


def probe_webcams(max_index: int = 4) -> list[SourceInfo]:
    found: list[SourceInfo] = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                found.append(SourceInfo(type="webcam", id=str(i), label=f"Webcam {i}"))
        cap.release()
    return found


def list_sample_files(samples_dir: str) -> list[SourceInfo]:
    samples_dir = os.path.normpath(samples_dir)
    files = sorted(
        f for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv") for f in glob.glob(os.path.join(samples_dir, ext))
    )
    return [SourceInfo(type="file", id=f, label=os.path.basename(f)) for f in files]


def make_source(spec_type: str, spec_id: str) -> VideoSource:
    if spec_type == "webcam":
        return WebcamSource(int(spec_id))
    if spec_type == "file":
        return FileSource(spec_id)
    raise ValueError(f"Unknown source type: {spec_type}")
