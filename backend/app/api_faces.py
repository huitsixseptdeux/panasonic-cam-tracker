"""HTTP API for the face library and recognition modes.

Model calls go through the resolver's single face-worker thread, so the face
models are never used concurrently with the pipeline's face jobs.
"""
from __future__ import annotations

import asyncio
import base64
import time
import uuid
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .faces.identity import FaceCandidate
from .pipeline import FACE_MODES, Pipeline

CANDIDATE_TTL_S = 600


class CandidateRequest(BaseModel):
    # data URL or bare base64 JPEG/PNG; omitted = use the current camera frame
    image: Optional[str] = None


class RegisterRequest(BaseModel):
    token: str
    name: str


class RenameRequest(BaseModel):
    name: str


class OrderRequest(BaseModel):
    ids: list[str]


class RecognitionRequest(BaseModel):
    mode: str
    person_id: Optional[str] = None


def _jpeg_b64(img: np.ndarray, max_side: int = 0) -> str:
    if max_side and max(img.shape[:2]) > max_side:
        s = max_side / max(img.shape[:2])
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _decode_image(data: str) -> np.ndarray:
    if "," in data and data.startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        arr = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
    except ValueError as exc:
        raise HTTPException(400, "Image is not valid base64") from exc
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not read the image. Use a JPEG or PNG.")
    return img


def build_router(pipeline: Pipeline) -> APIRouter:
    router = APIRouter(prefix="/api")
    candidates: dict[str, tuple[float, FaceCandidate]] = {}

    def resolver():
        if pipeline.identity is None:
            raise HTTPException(503, "Face models are not loaded. Check backend/models/.")
        return pipeline.identity

    def person_json(p) -> dict:
        return {"id": p.id, "name": p.name, "order": p.order, "stale": p.backend != resolver().library.backend}

    @router.get("/faces")
    async def list_faces():
        return {"people": [person_json(p) for p in resolver().library.list()]}

    @router.get("/faces/{person_id}/image")
    async def face_image(person_id: str):
        lib = resolver().library
        if lib.get(person_id) is None:
            raise HTTPException(404, "Unknown person")
        return FileResponse(lib.image_path(person_id), media_type="image/jpeg")

    @router.post("/faces/candidates")
    async def find_candidates(req: CandidateRequest):
        if req.image:
            img = _decode_image(req.image)
        elif pipeline.last_frame is not None:
            img = pipeline.last_frame.copy()
        else:
            raise HTTPException(409, "No camera frame yet. Start a source first, or upload a photo.")

        now = time.time()
        for tok in [t for t, (ts, _) in candidates.items() if now - ts > CANDIDATE_TTL_S]:
            del candidates[tok]

        res = resolver()
        detected = await asyncio.get_running_loop().run_in_executor(res.executor, res.candidates, img)
        found = []
        for cand in detected:
            tok = uuid.uuid4().hex
            candidates[tok] = (now, cand)
            pid, score = resolver().match(cand.embedding)
            existing = resolver().library.get(pid) if pid else None
            found.append(
                {
                    "token": tok,
                    "bbox": list(cand.bbox),
                    "thumb": _jpeg_b64(cand.crop, 160),
                    "matches": existing.name if existing else None,
                }
            )
        return {"width": img.shape[1], "height": img.shape[0], "image": _jpeg_b64(img, 960), "faces": found}

    @router.post("/faces")
    async def register(req: RegisterRequest):
        name = req.name.strip()
        if not name:
            raise HTTPException(400, "Enter a name.")
        entry = candidates.pop(req.token, None)
        if entry is None:
            raise HTTPException(410, "That face expired. Detect faces again.")
        cand = entry[1]
        person = resolver().library.add(name, cand.crop, cand.embedding)
        return person_json(person)

    @router.patch("/faces/{person_id}")
    async def rename(person_id: str, req: RenameRequest):
        if resolver().library.get(person_id) is None:
            raise HTTPException(404, "Unknown person")
        name = req.name.strip()
        if not name:
            raise HTTPException(400, "Enter a name.")
        return person_json(resolver().library.rename(person_id, name))

    @router.delete("/faces/{person_id}")
    async def delete(person_id: str):
        if resolver().library.get(person_id) is None:
            raise HTTPException(404, "Unknown person")
        if pipeline.face_person_id == person_id and pipeline.face_mode == "select":
            raise HTTPException(409, "This person is the current tracking target. Pick someone else first.")
        resolver().library.delete(person_id)
        return {"ok": True}

    @router.put("/faces/order")
    async def reorder(req: OrderRequest):
        resolver().library.reorder(req.ids)
        return {"people": [person_json(p) for p in resolver().library.list()]}

    @router.post("/recognition")
    async def recognition(req: RecognitionRequest):
        if req.mode not in FACE_MODES:
            raise HTTPException(400, f"mode must be one of {FACE_MODES}")
        if req.mode == "select":
            if not req.person_id or resolver().library.get(req.person_id) is None:
                raise HTTPException(400, "Pick a registered person.")
        pipeline.set_recognition(req.mode, req.person_id)
        return pipeline.status_dict()

    return router
