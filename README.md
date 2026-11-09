# Auto-Tracker

Camera-agnostic person tracking with automatic digital framing. Point it at a
webcam or a video file, click a person (or let it pick one, or register faces),
and it outputs a smoothly panned/zoomed crop that keeps that person framed.

Panasonic's AW-SF100 Auto Tracking Software is the feature and UX reference
(see `REFERENCE.md`); no Panasonic hardware or code is needed or used.

## Requirements

- Windows 10/11 (developed on Windows 11; Linux/macOS untested)
- Python 3.10, Node.js 18+
- Optional: NVIDIA GPU. Person detection uses CUDA when available and falls
  back to CPU otherwise.

## Install

**New to the project? Follow [SETUP.md](SETUP.md)**: a step-by-step from a fresh
PC (Git, VS Code, Python, Node) to the app running. The short version:

```bash
# backend
cd backend
python -m venv .venv
source .venv/Scripts/activate          # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# GPU build of PyTorch (plain pip gives a CPU-only build):
pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu124

# face models + test videos (not in git)
python scripts/fetch_assets.py

# frontend
cd ../frontend
npm install
```

The YOLO person model (`yolov8n.pt`) downloads automatically on first start.
Without the face models the app still runs; face recognition is just disabled.

## Run

Two terminals:

```bash
# 1. backend  (http://127.0.0.1:8000)
cd backend && source .venv/Scripts/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. frontend (http://localhost:5173)
cd frontend && npm run dev
```

Open http://localhost:5173.

## Test videos

Put any `.mp4 / .avi / .mov / .mkv` in `backend/samples/` and it appears in the
source list (files loop). Clips used during development, all free:

| File | Source | Good for |
|---|---|---|
| `speaker_on_stage.mp4` | Mixkit #13194 | one presenter on stage |
| `conference_room_group.mp4` | Mixkit #23116 | 6 faces around a table, face recognition |
| `team_meeting.mp4` | Mixkit #15798 | 5 people meeting |
| `conference_audience.mp4` | Mixkit #23035 | 5–8 seated people |
| `talk_with_audience.mp4` | Mixkit #23292 | speaker, audience enters frame |
| `pedestrians_opencv.avi` | OpenCV `samples/data/vtest.avi` | crossing people, ID switches |

Mixkit clips: `https://assets.mixkit.co/videos/<id>/<id>-720.mp4`, Mixkit License.

## Using it

1. **Pick a source** on the left. The image goes live immediately.
2. **Click a person** in the image to follow them, or press **Start** to
   follow the biggest person automatically.
3. **Framing presets**: Upper body / Full body / Wide.
4. **Tracking settings** (sliders icon, top right): dead zone, smoothing, max
   pan speed, detection confidence.
5. The right column shows the **program output** (the framed crop) and
   diagnostics (input resolution, fps, dropped frames, detector device).
   `cuda:0` means detection runs on the first GPU.

### Face recognition (backend done, UI in progress)

Register people once, then either follow one specific person or let it follow
whoever registered is in shot, by priority order. Faces are checked on events
(new person, target lost, boxes crossing, a periodic confirm), not every frame,
in a background worker, so video is never slowed down.

API (until the UI lands):

| Call | Purpose |
|---|---|
| `POST /api/faces/candidates {image?}` | detect faces in an uploaded image (data URL) or the current frame |
| `POST /api/faces {token, name}` | register a detected face |
| `GET /api/faces` / `PATCH /api/faces/{id}` / `DELETE /api/faces/{id}` | list / rename / delete |
| `PUT /api/faces/order {ids}` | set priority order |
| `POST /api/recognition {mode: off\|select\|auto, person_id?}` | recognition mode |

Face data is stored locally in `backend/data/faces/` (git-ignored).

## Project layout

```
backend/app/
  main.py            composition root: builds pipeline + face stack, REST + WebSocket
  api_faces.py       face library / recognition endpoints
  pipeline.py        capture -> detect -> track -> faces -> choose target -> frame -> publish
  sources.py         VideoSource: webcam, file (RTSP/NDI later)
  detector.py        Detector: YOLOv8n person detector
  tracker.py         Tracker: body tracking + IDs
  autoframer.py      AutoFramer: smoothed digital pan/zoom crop
  faces/
    base.py          FaceDetector / FaceEmbedder interfaces (model-agnostic)
    opencv_backend.py  YuNet + SFace implementation
    factory.py       the single place that picks the face backend (FACE_BACKEND env var)
    library.py       registered people storage
    identity.py      faces <-> bodies, per-track memory (worker thread does model calls)
    scheduler.py     event-based policy: when to check faces
  ptz.py, output.py  PTZ and output interfaces (stubs for hardware / NDI / recording)
frontend/src/        React + TypeScript UI
```

Every stage sits behind an interface, so a model swap (e.g. InsightFace,
TensorRT) or moving a stage to C++ means replacing one implementation, not the
pipeline. Details in `ARCHITECTURE.md`.

## Troubleshooting

- **"address already in use" on port 8000**: an old backend is still running.
  PowerShell: `Get-NetTCPConnection -LocalPort 8000 | % { Stop-Process -Id $_.OwningProcess }`
- **Webcam shows nothing / "Failed to open source"**: another app (Teams, OBS,
  browser) may hold the camera. Close it and pick the source again.
- **`cpu` instead of `cuda:0`**: reinstall the CUDA build of torch (see Install).
- **Backend exits with no error**: a native crash seen a few times on this
  machine, cause not yet found. The run command above can be prefixed with
  `PYTHONFAULTHANDLER=1` to print where it dies; please share that output.

## Status

Proof of concept. See `PROGRESS.md` for what's done and the roadmap.
