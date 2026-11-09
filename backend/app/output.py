from __future__ import annotations

import abc
import json

import cv2
import numpy as np
from fastapi import WebSocket


class VideoOutput(abc.ABC):
    """Where processed frames go. Phase 1 only implements the live browser
    preview; VirtualCameraOutput / NDIOutput / RecordingOutput are future
    additions behind this same interface (Phase 3 in START.md).
    """

    @abc.abstractmethod
    async def publish(self, frame: np.ndarray, metadata: dict) -> None:
        ...


class WebSocketPreview(VideoOutput):
    """Streams raw binary JPEG frames plus a sidecar JSON metadata message.

    Deliberately avoids base64-in-JSON (that was ~33% more bytes plus JSON
    parse/stringify overhead on every frame): each frame goes out as one
    binary WebSocket message (`send_bytes`), immediately followed by one text
    message carrying the detections/crop/status for that same frame. Message
    order is preserved per-connection, so the client just pairs "latest binary
    blob" with "the metadata message that follows it" — no explicit frame IDs
    needed.
    """

    def __init__(self, jpeg_quality: int = 80):
        self._clients: set[WebSocket] = set()
        self.jpeg_quality = jpeg_quality

    def add_client(self, ws: WebSocket) -> None:
        self._clients.add(ws)

    def remove_client(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def publish(self, frame: np.ndarray, metadata: dict) -> None:
        if not self._clients:
            return
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            return
        frame_bytes = buf.tobytes()
        message = json.dumps(metadata)
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_bytes(frame_bytes)
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_client(ws)

    async def publish_status(self, status: dict) -> None:
        if not self._clients:
            return
        message = json.dumps({"status": status})
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_client(ws)
