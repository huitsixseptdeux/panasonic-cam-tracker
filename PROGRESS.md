# PROGRESS.md

## 2026-11-09

- Audited repo (empty except `START.md`) and environment: Python 3.10.11, Node v24.14.0,
  git 2.45.2, ffmpeg present; NVIDIA GPU with CUDA 13.3 driver; `cv2` not yet installed.
  A real UVC webcam ("USB2.0 FHD UVC WebCam") plus NDI Webcam virtual devices and OBS
  Virtual Camera are available via DirectShow — good for both input and output testing.
  No Panasonic software/manuals/screenshots and no Craft Anything install found locally.
- `git init`'d the repo.
- **Phase 0 investigation** (timeboxed, doc-only — no live Panasonic software or
  hardware available to observe): researched Panasonic's built-in auto tracking (AW-UE150A/
  UE80/UE50/UE40/UE30) and the Auto Tracking Plug-in for Media Production Suite
  (AW-SF100/SF200). Wrote `REFERENCE.md` with verified features, a confidence-rated
  (low-confidence, reconstructed) screen inventory, source links, and a prioritized
  feature checklist mapped to START.md's phases.
- Evaluated Craft Anything (storytold/craft-anything): confirmed it's a clean-room
  reverse-engineering tool that needs a *live* running target (site/app) to observe.
  Decided **not to install/use it** — there is no live Panasonic UI anywhere reachable
  from this machine, only static marketing pages and PDFs, which it isn't built to
  reverse-engineer. Documented the decision in `REFERENCE.md` §4.
- Wrote `ARCHITECTURE.md`: module boundaries (`VideoSource`, `Detector`, `Tracker`,
  `AutoFramer`, `PTZController`, `VideoOutput`), the REST/WebSocket contract, frontend
  structure, and explicit tracking/identity-switching limitations.
- Scaffolding Phase 1 MVP: FastAPI + OpenCV + Ultralytics YOLOv8n backend, React+TS+Vite
  frontend. In progress — see below for current status; this section will be updated as
  each piece lands.

## 2026-11-09 (cont'd)

- Finished the Phase 1 backend (FastAPI, OpenCV, Ultralytics YOLOv8n, centroid/IOU
  tracker, `AutoFramer`) and frontend (React/TS/Vite, canvas overlay, controls, status).
  Fixed the WebSocket transport to send binary JPEG frames + a separate JSON metadata
  message instead of base64-in-JSON, after a user question about performance.
- Got CUDA working: initial `pip install ultralytics` pulled a CPU-only torch wheel
  despite the machine's RTX 4090 (laptop) GPU; reinstalled `torch`/`torchvision` from the
  `cu124` index and explicitly `.to("cuda:0")` the YOLO model (ultralytics doesn't do this
  automatically on Windows here). **Verified against the real attached webcam**: CUDA
  detection running, person detected, ~19.8 FPS at 640×480 — not a guess.
- Backend crashed once in the background with exit code 4 and no Python traceback (looks
  native/CUDA-level) after running un-polled for a while. Restarted cleanly; root cause
  not yet confirmed. Later got independent evidence this machine's GPU/driver may be the
  common factor (see below), not necessarily our code.
- User provided the official AW-SF100 90-day trial installer locally
  (`Downloads/DV91000377S/AutoTrackingSoftware`). Installed it (with user confirmation,
  since it modifies the system). Its own `torch_cuda.dll`/`cudnn_*64_8.dll` confirmed
  LibTorch + CUDA 11/cuDNN 8 under the hood, a bundled Node.js web server, and an
  MjpegProcessor — matching the manual's stated architecture.
- On launch, Panasonic's own `TrackingControl` engine crashed immediately ("Tracking
  Control process stopped. Start again.") — verified via screenshot. Given our own
  pipeline also crashed once, and both are CUDA inference processes on the same
  GPU/driver, this looks like an environment-level incompatibility (the software targets
  2019-era CUDA 11/cuDNN 8; this machine's driver reports a much newer CUDA 13.3), not
  something worth chasing further. Decided to stop pursuing the live install.
- Instead, downloaded Panasonic's official **Operating Instructions** and **Keyboard
  Shortcuts** PDFs directly and text-extracted them (PyMuPDF, in a throwaway venv under
  the scratchpad — not added to project dependencies). This gave a **verified** (not
  reconstructed) full screen inventory and parameter list, now written into
  `REFERENCE.md` §2/§3/§5/§6: three tracking methods (Template/Deep-Learning-CPU/
  Deep-Learning-GPU), full Tracking Setting window parameters (sensitivity 1–10,
  lost-state trigger+duration, home-position preset recall, disable-area rectangle,
  angle/zoom presets), face-recognition registration flow, multi-camera registration
  flow. This made Craft Anything moot — the official manual gave us everything a
  screenshot-driven clean-room study would have, without needing to get the (now proven
  unreliable on this machine) software running.

## 2026-11-09 (afternoon)

- Rendered the real screenshots from Panasonic's manual (earlier work had only used its
  text) and rebuilt the UI on their actual layout: three columns (sources | tracking |
  output), round icon toggles, framing presets, tuning moved to a settings popup.
  Design canvas: https://claude.ai/artifact/Q6LhbH1Xg5zkop2p9xT2Kx
- Preview is live as soon as a source is picked; Start/Stop only controls following
  (matches Panasonic). Start with no target picks the largest person; clicking a person
  or a preset starts following.
- Framing fixes: webcams now open at 1080p (were 640x480, leaving nothing to crop);
  presets frame a portion of the body (Upper body = head and shoulders).
- Settings changed before Start were dropped; fixed.
- Test clips added (see README).
- Face recognition backend (proof of concept): pluggable `faces/` package
  (interfaces, OpenCV YuNet+SFace backend, factory, library, identity, scheduler),
  REST API, Select-face and Auto-face-search modes. Event-based scheduling on a
  background worker: measured 0.05 ms median added to the video loop (was 240 ms when
  run per frame), ~2 face jobs/s, registered target found within 5 frames.
- Known: backend sometimes exits with no Python traceback (native crash). Not yet
  root-caused; run with `PYTHONFAULTHANDLER=1` to locate it.

## Roadmap

Now / next:
- [x] Face UI: People page (grid, add from photo or live frame, rename, delete, drag to
      reorder), Face Recognition ON/OFF + Select Face + Auto Face Search on the main screen.
- [x] `setup.bat` / `start.bat` for one-click install and launch on Windows.
- [ ] Crash fix: native access violations when the video source is closed while being
      read (fast source switching) and when webcams are probed concurrently. Cause
      found with faulthandler; fix proposed (single capture owner, locked + cached
      webcam probing). Awaiting go.
- [ ] "People in shot" strip under the image: click a face chip to follow, name unknown
      faces in place, registered-but-absent people dimmed for pre-selection. Proposed.
- [ ] Settings the Panasonic way: Setting button under Start/Stop; operator-level
      Sensitivity 1–10 and lost behaviour first, current sliders under "Advanced". Proposed.
- [ ] Overlapping boxes: click picks the face first, then nearest box centre; click again
      cycles. (Proposed, awaiting go.)
- [ ] Better body tracker: ByteTrack-style (motion prediction, two-stage matching) behind
      the `Tracker` interface, to stop IDs climbing. (Proposed, awaiting go.)
- [ ] Re-identification of unregistered people: keep a lost person's face signature for a
      while, give the old ID back when they reappear. (Proposed, awaiting go.)
- [ ] Root-cause the native backend crash.

Phase 2 (from the Panasonic manual, REFERENCE.md §6):
- [ ] VIEW screen (grid of all sources).
- [ ] After-lost behaviour: hold vs ease to wide; "declare lost after N s"; lost by face.
- [ ] Click-to-place the subject in frame (Target Position Set).
- [ ] Detection mask handles and draw-a-rectangle tracking-disable area.
- [ ] Sensitivity 1–10.
- [ ] Settings pages: sources/cameras, tracking method.
- [ ] Focus: webcam focus/autofocus where the UVC driver exposes it; for PTZ cameras,
      near/far/auto and face-priority autofocus via the PTZ adapter.

Phase 3:
- [ ] RTSP / ONVIF / NDI sources.
- [ ] Physical PTZ adapter (pan/tilt/zoom/focus) once a camera is available to test.
- [ ] Output: virtual camera, NDI, recording.
- [ ] Face models on GPU (onnxruntime-gpu backend) if CPU face checks become a bottleneck.
- [ ] Performance: TensorRT person detector, frame skipping between detections.
