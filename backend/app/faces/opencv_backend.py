"""OpenCV Zoo face models: YuNet (detection) + SFace (recognition).

Chosen for the proof of concept because they ship with OpenCV (no extra
dependency) and are Apache-2.0 licensed. Less accurate than ArcFace-class
models; replace via `factory.py` if that becomes a problem.
"""
from __future__ import annotations

import cv2
import numpy as np

from .base import FaceDetection, FaceDetector, FaceEmbedder


class YuNetDetector(FaceDetector):
    def __init__(self, model_path: str, score_threshold: float = 0.7):
        self._det = cv2.FaceDetectorYN.create(model_path, "", (320, 320), score_threshold, 0.3, 5000)
        self._size: tuple[int, int] | None = None

    def detect(self, frame: np.ndarray) -> list[FaceDetection]:
        h, w = frame.shape[:2]
        if self._size != (w, h):
            self._det.setInputSize((w, h))
            self._size = (w, h)
        _, faces = self._det.detect(frame)
        if faces is None:
            return []
        out = []
        for row in faces:
            x, y, fw, fh = row[:4]
            out.append(FaceDetection(bbox=(float(x), float(y), float(x + fw), float(y + fh)), score=float(row[14]), raw=row))
        return out


class SFaceEmbedder(FaceEmbedder):
    # OpenCV's published cosine threshold for SFace on LFW.
    match_threshold = 0.363

    def __init__(self, model_path: str):
        self._rec = cv2.FaceRecognizerSF.create(model_path, "")

    def embed(self, frame: np.ndarray, face: FaceDetection) -> np.ndarray:
        aligned = self._rec.alignCrop(frame, face.raw)
        feat = self._rec.feature(aligned).flatten().astype(np.float32)
        norm = np.linalg.norm(feat)
        return feat / norm if norm > 0 else feat
