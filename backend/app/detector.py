from __future__ import annotations

import abc
from dataclasses import dataclass

import numpy as np

PERSON_CLASS_ID = 0  # COCO class index for "person"


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixel coords
    confidence: float


class Detector(abc.ABC):
    @abc.abstractmethod
    def detect(self, frame: np.ndarray) -> list[Detection]:
        ...

    @property
    @abc.abstractmethod
    def device(self) -> str:
        ...


class YoloPersonDetector(Detector):
    """Ultralytics YOLOv8n, filtered to the 'person' class only.

    Chosen for Phase 1 because it's maintained, fast enough on CPU for a
    single-camera demo, and transparently uses CUDA if a GPU-enabled torch
    build is present — no code branching needed here.
    """

    def __init__(self, confidence: float = 0.4, model_name: str = "yolov8n.pt"):
        import torch
        from ultralytics import YOLO  # deferred import: heavy, and optional until used

        self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self._model = YOLO(model_name)
        self._model.to(self._device)
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame,
            classes=[PERSON_CLASS_ID],
            conf=self.confidence,
            device=self._device,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(Detection(bbox=(x1, y1, x2, y2), confidence=conf))
        return detections

    @property
    def device(self) -> str:
        return self._device
