# START.md — Camera-Agnostic Auto-Tracking Application

## Goal
Build an independent, camera-agnostic application for detecting, tracking, and automatically framing people in video. Panasonic's auto-tracking software is a **reference for UI, workflows, and feature discovery only**; do not assume Panasonic hardware is required or attempt to reproduce proprietary code.

## Instructions for the VS Code coding agent
You are the lead engineer. Work incrementally, maintain a running progress log in `PROGRESS.md`, and deliver a working application at the end of each phase. Do not assume that any particular software or device is installed: inspect the repository and environment first. Do not silently invent features based on screenshots.

### Phase 0 — Investigate before building
1. Identify the exact Panasonic tracking application/version intended as a UI/feature reference (e.g. Auto Tracking / Media Production Suite). Record confirmed links to official documentation, screenshots, manuals and any available demo.
2. Inspect the current machine/repository to determine whether Panasonic software, screenshots, or documentation are already available. Never download or install software without checking first.
3. **Evaluate Craft Anything** (https://github.com/storytold/craft-anything) as a helpful reverse-engineering tool. Check its current installation instructions, supported platforms, capabilities and limitations. If available and useful, use it to inspect the reference UI and observable workflows. If it is unavailable or unsuitable, proceed with official manuals, screenshots, and hands-on observations. It is **optional**, not a hard dependency.
4. Create `REFERENCE.md`: verified features, screen inventory, interaction flows, parameters, source links, confidence/unknowns, and a prioritized feature checklist. Distinguish observed behavior from assumptions.
5. Don't spend the whole project on reverse engineering: timebox this investigation and identify the smallest useful feature set.

### Product requirements
- **Camera-agnostic sources**: start with webcam (UVC), video files, and RTSP/IP feeds; design interfaces for future NDI, ONVIF, and manufacturer SDK sources.
- **Vision pipeline**: detect people, assign stable IDs when possible, select/lock a subject, and track its position over time. Be explicit about identity-switching and occlusion limitations.
- **Auto-framing**: smooth virtual pan/tilt/zoom by cropping/rescaling a high-resolution video source. Include target framing, dead zone, damping, maximum speed, and reacquisition behavior.
- **Optional physical PTZ**: a separate adapter interface. Only implement hardware control after confirming the camera's documented protocol and testing safely. No vendor lock-in.
- **UI**: live preview with bounding boxes, target selection, tracking start/stop, source selection, tracking settings, and status/debug view. Use Panasonic only as a UX/feature reference, not as code to copy.
- **Output**: show the processed/auto-framed preview; plan a modular output interface for future virtual camera, NDI, streaming, or recording.
- All features must run with **no Panasonic camera connected**.

### Suggested architecture (adapt based on findings)
- UI: local browser app (React + TypeScript or comparable stack).
- Processing backend: Python with OpenCV plus a maintained people-detection/tracking model, or a better-supported alternative justified in `ARCHITECTURE.md`.
- Clear modules/interfaces: `VideoSource`, `Detector`, `Tracker`, `AutoFramer`, `PTZController` (optional), `VideoOutput`.
- Local API/WebSocket for preview metadata, controls and status; avoid unnecessary cloud services.
- Configurations persisted locally; sensible defaults; reliable start/stop and cleanup.

### Phase 1 — Working MVP
Deliver an application that:
1. Opens a webcam or test video.
2. Displays a live preview.
3. Detects people and draws bounding boxes.
4. Lets the user choose a target and start/stop tracking.
5. Produces a smoothly auto-framed crop following that target, even with a fixed webcam.
6. Exposes a few useful framing/smoothing controls.
7. Handles source loss and no-person-detected states gracefully.

Provide exact install/run commands and a reproducible demo using a sample video if no camera is attached.

### Phase 2 — Reference-driven improvement
Use the `REFERENCE.md` feature checklist and, if useful, Craft Anything observations to refine UI structure and interactions. Implement high-value missing features one by one. Compare visible behavior, not just visual similarity. Keep the original Panasonic implementation separate and do not copy proprietary assets or code.

### Phase 3 — Broader inputs, output and hardware
Add RTSP/IP camera support, configurable video output/recording, performance tuning, diagnostics and optional physical PTZ adapters (such as ONVIF where supported). Test each hardware integration only against confirmed device capabilities.

## Engineering guardrails
- No Ollama/local LLM configuration is part of this project scope.
- Do not make Craft Anything mandatory for building or running the application.
- Use documented APIs and authorized inspection; avoid license bypassing or proprietary code extraction.
- Prefer a small, testable implementation over a speculative full clone.
- Track latency, resolution, frame rate, CPU/GPU utilization and dropped frames.
- Explain architectural decisions and surface blockers instead of hiding them.

## First tasks — execute now
1. Audit the repository and environment and report what already exists.
2. Research and verify the exact Panasonic reference software and Craft Anything workflow.
3. Write `REFERENCE.md`, `ARCHITECTURE.md` and `PROGRESS.md`.
4. Scaffold the application and implement the Phase 1 MVP.
5. Run tests and provide a short demo/runbook in the main `README.md`.

**Definition of success:** A user can run the app locally with an ordinary webcam or video file, select a detected person, and see smooth autonomous digital framing, without any Panasonic hardware.
