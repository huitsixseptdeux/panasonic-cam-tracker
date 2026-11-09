from __future__ import annotations

import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api_faces import build_router as build_faces_router
from .faces.factory import build_face_stack
from .faces.identity import IdentityResolver
from .faces.library import FaceLibrary
from .output import WebSocketPreview
from .pipeline import Pipeline
from .schemas import SettingsUpdate, SourceSpec, TargetSpec, TrackingAction
from .sources import list_sample_files, probe_webcams

logging.basicConfig(level=logging.INFO)

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")
FACES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "faces"))
FACE_BACKEND = os.environ.get("FACE_BACKEND", "opencv")

logger = logging.getLogger("main")


def _build_identity() -> IdentityResolver | None:
    try:
        stack = build_face_stack(FACE_BACKEND)
    except Exception as exc:  # missing model files, unsupported OpenCV build...
        logger.warning("Face recognition disabled: %s", exc)
        return None
    return IdentityResolver(stack, FaceLibrary(FACES_DIR, backend=stack.name))

app = FastAPI(title="Camera-Agnostic Auto-Tracking API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

output = WebSocketPreview()
pipeline = Pipeline(output, identity=_build_identity())
app.include_router(build_faces_router(pipeline))


@app.get("/api/sources")
def get_sources():
    webcams = probe_webcams()
    files = list_sample_files(SAMPLES_DIR)
    return {"sources": [s.__dict__ for s in webcams + files]}


@app.post("/api/source")
async def set_source(spec: SourceSpec):
    await pipeline.set_source(spec.type, spec.id)
    return pipeline.status_dict()


@app.post("/api/target")
def set_target(spec: TargetSpec):
    pipeline.select_target(spec.track_id)
    return {"selected_track_id": pipeline.selected_track_id}


@app.post("/api/tracking")
async def tracking_action(action: TrackingAction):
    if action.action == "start":
        await pipeline.start()
        pipeline.set_tracking(True)
    else:
        pipeline.set_tracking(False)
    return pipeline.status_dict()


@app.post("/api/settings")
def update_settings(settings: SettingsUpdate):
    pipeline.update_settings(**settings.model_dump())
    return {"ok": True}


@app.get("/api/status")
def get_status():
    return {
        **pipeline.status_dict(),
        "width": pipeline.autoframer.frame_w if pipeline.autoframer else 0,
        "height": pipeline.autoframer.frame_h if pipeline.autoframer else 0,
    }


@app.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    output.add_client(ws)
    # Push a status snapshot immediately: otherwise a client that connects while the
    # pipeline is idle (nothing publishing yet) sees no message and stays stuck on
    # a "Connecting..." state indefinitely.
    await output.publish_status(pipeline.status_dict())
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "select":
                pipeline.select_target(data.get("track_id"))
    except WebSocketDisconnect:
        pass
    finally:
        output.remove_client(ws)
