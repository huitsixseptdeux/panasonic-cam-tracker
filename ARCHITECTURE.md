# ARCHITECTURE.md

## Stack

- **Backend**: Python 3.10, FastAPI + Uvicorn (ASGI), OpenCV for capture/encode,
  [Ultralytics YOLOv8n](https://github.com/ultralytics/ultralytics) for person detection
  (COCO class 0 only). Chosen over writing a detector from scratch because it's
  maintained, has permissive AGPL/commercial dual licensing fine for local/internal use,
  runs on CPU or CUDA transparently, and a nano model is fast enough for real-time on
  modest hardware. This machine has an NVIDIA GPU (CUDA 13.3 driver present), so
  detection can use it automatically if a CUDA-enabled torch build is installed; CPU
  fallback works for the MVP.
- **Frontend**: React + TypeScript + Vite. A local browser app, per START.md's suggested
  architecture. No framework-level state library — the app is small enough for plain
  hooks.
- **Transport**: a single WebSocket (`/ws/stream`) carries both video frames (base64 JPEG)
  and per-frame metadata (detections, track IDs, selected target, current crop/framing
  state, pipeline status) as JSON messages. A REST API handles control actions (switch
  source, select target, start/stop, change settings). This is simpler than a binary
  frame channel + separate metadata channel for an MVP; revisit if frame rate suffers.

## Modules (backend/app/)

Each stage is an abstract interface with one concrete implementation today, so sources,
detectors, trackers, and outputs can be swapped without touching the pipeline.

- **`sources.py` — `VideoSource`**: `open()`, `read() -> Frame | None`, `close()`,
  `is_open`. Implementations: `WebcamSource` (OpenCV `VideoCapture(index)`),
  `FileSource` (OpenCV `VideoCapture(path)`, loops at EOF). Stubbed for later:
  `RTSPSource`, and NDI/ONVIF would be added here as new classes implementing the same
  interface — no pipeline changes needed.
- **`detector.py` — `Detector`**: `detect(frame) -> list[Detection]` where `Detection`
  is `(bbox_xyxy, confidence, class_id)`. Implementation: `YoloPersonDetector`, filters
  to person class, configurable confidence threshold.
- **`tracker.py` — `Tracker`**: `update(detections) -> list[Track]` where `Track` adds a
  persistent `track_id` to a detection. Implementation: `CentroidTracker`, a lightweight
  IOU + centroid-distance matcher with a disappearance grace period (no Kalman filter,
  no re-ID embeddings). **Limitation, stated explicitly**: this tracker *will* swap IDs
  under crossing/occlusion between visually similar people, and does not re-identify a
  person who leaves and re-enters frame — it assigns a new ID. This matches the
  "identity-switching and occlusion limitations" START.md asks us to be explicit about.
  A re-ID-capable tracker (e.g. ByteTrack/BoT-SORT via Ultralytics' built-in `.track()`)
  is a documented upgrade path, not implemented now, to keep the module boundary clean
  and dependency-light for the MVP.
- **`autoframer.py` — `AutoFramer`**: given the current frame size, the selected track's
  bbox (or `None` if lost), and settings, maintains a smoothed crop window and returns
  it. Behavior:
  - **Target framing**: crop centered on the subject, sized so the subject occupies a
    configurable target fraction of frame height.
  - **Dead zone**: if the subject's center is within N% of frame center from the current
    crop center, don't move (avoids micro-jitter).
  - **Damping**: crop center/size move toward the target via exponential smoothing
    (`current += (target - current) * alpha`), not instantly.
  - **Max speed**: per-frame crop movement is clamped (pixels/frame), so fast subject
    motion causes a bounded pan rate, not a snap.
  - **Reacquisition**: on track loss, hold the last crop for a grace period, then ease
    back out toward the full frame; resumes framing immediately if the same or a new
    target is selected.
- **`ptz.py` — `PTZController`** (interface only, not implemented): `pan(dx)`,
  `tilt(dy)`, `zoom(dz)`, `get_capabilities()`. No physical PTZ hardware is available to
  test against, so per the engineering guardrails this stays an unimplemented adapter
  point (e.g. for ONVIF) until a real device and documented protocol are available.
- **`output.py` — `VideoOutput`** (interface, one implementation): `WebSocketPreview`
  writes JPEG+metadata to connected clients. Stub classes documented for future
  `VirtualCameraOutput`, `NDIOutput`, `RecordingOutput` — not implemented in Phase 1.
- **`pipeline.py`**: owns the capture→detect→track→autoframe→encode→broadcast loop,
  runs as an asyncio task with blocking capture offloaded to a thread executor. Tracks
  fps, dropped frames, and per-stage timing for the status endpoint.
- **`server.py`**: FastAPI app wiring REST endpoints and the `/ws/stream` WebSocket to a
  single `Pipeline` instance.

## Face recognition (`backend/app/faces/`)

Split so the model, the policy and the storage can each change alone:

| Module | Responsibility | Changes when… |
|---|---|---|
| `base.py` | `FaceDetector`, `FaceEmbedder` interfaces | never, ideally |
| `opencv_backend.py` | YuNet detection + SFace embedding | the model changes |
| `factory.py` | picks the backend (`FACE_BACKEND` env var) | a backend is added |
| `library.py` | registered people, priority order, embeddings tagged with the backend that made them | storage changes |
| `identity.py` | links faces to body tracks, per-track memory, projects the face box onto the moving body | association logic changes |
| `scheduler.py` | decides which tracks need a face check now | the policy changes |

Threading: one face-worker thread owns the models (`IdentityResolver.executor`).
The pipeline submits a job only when the scheduler asks and never waits for it;
results are applied on the next frame. Registration requests from the API go
through the same worker.

Scheduling is event-based, matching Panasonic's behaviour (recognition is a mode,
tracking starts when the face appears, faces matter again on loss):
recognition off → no work; new body → one check; searching → unknown bodies a few
times a second; target locked → confirm every ~2 s; target box overlapping
another → re-check both.

Moving to C++ or another model: implement `FaceDetector`/`FaceEmbedder` (in
process, or as a thin client to a C++ service) and register it in `factory.py`.
Stored embeddings from another backend are marked stale rather than mismatched.

## REST/WebSocket contract (current)

- `GET /api/sources` — enumerate available sources (webcam indices found via probing,
  plus any configured sample files).
- `POST /api/source` `{type: "webcam"|"file", id}` — switch active source.
- `POST /api/target` `{track_id: number | null}` — select/clear tracked subject.
- `POST /api/tracking` `{action: "start"|"stop"}`
- `POST /api/settings` `{dead_zone_pct?, damping?, max_speed_px?, target_fill_pct?,
  confidence?}` — partial updates, applied live.
- `GET /api/status` — fps, resolution, dropped frame count, source state, CUDA/CPU in
  use, selected target, pipeline running flag.
- `WS /ws/stream` — server pushes `{frame: base64 jpeg, w, h, detections: [{id, bbox,
  conf}], selected_track_id, crop: {x,y,w,h}, status: {...}}` at the pipeline's frame
  rate; client sends `{type: "select", track_id}` for click-to-select target directly
  over the socket as a convenience (mirrors the REST endpoint).

## Frontend structure (frontend/src/)

- `api.ts` — typed REST calls + WebSocket client wrapper.
- `components/PreviewCanvas.tsx` — draws the decoded frame + bbox overlays on a
  `<canvas>`, maps click coordinates back to frame space to select a target.
- `components/ControlsPanel.tsx` — source selector, start/stop, sliders for dead zone /
  damping / max speed / target fill, confidence.
- `components/StatusBar.tsx` — fps, resolution, dropped frames, "no person detected" /
  "source lost" banners.
- `App.tsx` — wires WebSocket state into the above.

## Tracking & identity limitations (explicit, per START.md requirement)

- Single-camera 2D tracking only; no depth, no re-identification across camera cuts.
- The MVP centroid tracker can and will swap IDs when two people's boxes overlap
  significantly or cross paths; this is a known limitation, not a bug to silently hide —
  surfaced via the UI by showing raw track IDs so a user can notice and re-select.
- A person who leaves the frame and returns gets a **new** ID; there is no long-term
  re-identification. Upgrading to an embedding-based re-ID tracker is a Phase 2+ option,
  not required for Phase 1's definition of success.
- Occlusion (subject fully hidden behind another object/person) triggers the
  reacquisition behavior in `AutoFramer` (hold last crop, then ease out) rather than
  guessing a position.

## Performance tracking

The pipeline records, exposed via `/api/status`: effective FPS, frame resolution,
dropped-frame count (frames the capture thread couldn't keep up with), and whether
detection is running on CPU or CUDA. CPU/GPU utilization percentages are OS-level metrics
and are deliberately left as a documented follow-up (`psutil`/`pynvml` integration) rather
than guessed at in Phase 1.
