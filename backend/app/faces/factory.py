"""Single switch point for the face model implementation."""
from __future__ import annotations

import os

from .base import FaceStack

MODELS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))


def build_face_stack(backend: str = "opencv") -> FaceStack:
    if backend == "opencv":
        from .opencv_backend import SFaceEmbedder, YuNetDetector

        return FaceStack(
            detector=YuNetDetector(os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")),
            embedder=SFaceEmbedder(os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")),
            name="opencv-yunet-sface",
        )
    raise ValueError(f"Unknown face backend: {backend}")
