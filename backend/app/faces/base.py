"""Model-agnostic face interfaces.

Everything outside `faces/` depends only on these types. Swapping the model
(InsightFace, a TensorRT engine, a C++ service over IPC...) means writing a new
FaceDetector/FaceEmbedder pair and registering it in `factory.py`.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

import numpy as np

BBox = tuple[float, float, float, float]  # x1, y1, x2, y2 in frame pixels


@dataclass
class FaceDetection:
    bbox: BBox
    score: float
    # Backend-specific payload (e.g. landmarks) the matching embedder needs to
    # align the face. Opaque to everything else.
    raw: object = None


class FaceDetector(abc.ABC):
    @abc.abstractmethod
    def detect(self, frame: np.ndarray) -> list[FaceDetection]:
        ...


class FaceEmbedder(abc.ABC):
    # Cosine similarity at or above which two embeddings are the same person.
    match_threshold: float

    @abc.abstractmethod
    def embed(self, frame: np.ndarray, face: FaceDetection) -> np.ndarray:
        """Return an L2-normalised 1-D float32 embedding."""

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))


@dataclass
class FaceStack:
    detector: FaceDetector
    embedder: FaceEmbedder
    name: str
