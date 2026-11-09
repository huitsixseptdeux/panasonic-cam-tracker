# REFERENCE.md — Panasonic Auto Tracking: UI/Feature Reference

Investigation timeboxed to ~1 hour of documentation research (Phase 0). No Panasonic
hardware, software installer, or screenshots were available on this machine or in this
repository, so everything below is derived from Panasonic's public product pages,
announcements, and spec sheets, not hands-on use or screen captures. Confidence is marked
per section. **Nothing here is copied code or proprietary assets — feature descriptions
only, used to decide what our app should do, not how Panasonic implemented it.**

## 1. Which Panasonic product is the actual reference

Panasonic ships *two different* auto-tracking implementations. Both are legitimate
references for feature discovery; we treat the software plug-in as primary because it is
camera-agnostic-ish (runs on a PC) and far better documented.

| | Built-in auto tracking | Auto Tracking Plug-in for Media Production Suite (AW-SF100 / AW-SF200) |
|---|---|---|
| Where it runs | Inside the camera firmware | External PC/server, or web app, driving the camera over the network |
| Cameras | AW-UE150A, AW-UE80, AW-UE50, AW-UE40, AW-UE30 | AW-UE160, AW-UE150, AW-HE130, AW-UE70, AW-HE42/40/38, AG-CX10/CX350, AJ-CX4000, AW-HE145, AW-UE40/50/80/100 (list per Panasonic's compatibility page) |
| Detection | Unspecified ("simple setup", no wiring); likely face/body detection reused from the plug-in | Explicit: body template matching + facial detection + deep learning |
| Multi-subject | Single subject only | Single tracked subject per instance; AW-UE150 can 4K-crop-track up to 3 people simultaneously |
| Licensing | Included with camera | 30/90-day free trial, then paid; AW-SF200 adds a floating license for many cameras |

**Confidence: high** that these are the two distinct products and their rough feature
split; **low** on exact parameter names, since no manual/UI screenshot was accessible —
all UI-level detail below is reconstructed from marketing copy, not a verified screen
inventory.

Sources:
- [AI-powered Automated Shooting Solution (built-in)](https://pro-av.panasonic.net/en/support/auto_tracking/)
- [PTZ Camera Auto Tracking Software (plug-in, NA)](https://connect.na.panasonic.com/av/video/software/ptz-auto-tracking)
- [Panasonic Announces New Free And Advanced Auto Tracking Software For PTZ Cameras](https://eu.connect.panasonic.com/gb/en/news/panasonic-announces-new-free-and-advanced-auto-tracking-software-ptz-cameras)
- [Auto Tracking Plug-in product page](https://shop.panasonic.com/fr/products/auto-tracking-plug-in-for-media-production-suite)

Primary documents linked from the NA plug-in page but **not fetched** (PDFs, out of
timebox — flagged as unknowns, not read): AW-SF100 API Documentation, AW-SF100/SF200
Brochure, AW-SF100 Operating Instructions, AW-SF100 Installation Instructions, AW-SF100
Keyboard Shortcuts, CUDA Toolkit install procedures, a Cisco Live case study.

## 2. Verified features (confidence: HIGH — read directly from Panasonic's own
AW-SF100 "Auto Tracking Software Operation Manual" PDF, downloaded from their official
site and parsed; not marketing copy, not an inference)

- **Three selectable tracking methods** (Settings → Tracking tab): **Template matching**
  (low CPU, no GPU needed), **Deep Learning (CPU)**, **Deep Learning (GPU)**. GPU mode
  requires an NVIDIA Pascal (GTX 1050 Ti+/Quadro P2000+) or Turing (RTX 2060+) card, a
  64-bit OS and app, and a matching CUDA Toolkit (8.0 for Pascal, 10.1 for Turing) — this
  is exactly the CUDA/cuDNN dependency we found in the installer's DLLs.
  - A second display rectangle convention: blue = tracked target, yellow = recognized
    face, red = any detected human (deep-learning modes only, to distinguish "a person"
    from "the" tracked person).
- **Face recognition** is a separate, optional layer on top of detection: you register
  face data (from a file or captured live from the camera feed, auto-detected with a
  frame, named, added to a library), then toggle face recognition on/off; "Auto Face
  Search" auto-assigns the tracking target to any registered face seen in frame.
- **Target acquisition is click-based**, exactly as we assumed: a "Target Position Set"
  toggle decides whether left-clicking the camera image **moves the framing target** to
  that point, or **selects whatever object is at that point as the new tracking target**.
- **Tracking Setting window** (per camera) exposes exactly these parameters:
  - Auto Tracking Start (auto-engage on detection) / Stop Tracking with manual preset
    recall.
  - **Lost-state trigger**: Body-only, or Body+Face with a configurable 1–30s grace
    period before declaring the subject lost.
  - **Home position**: on loss, hold position, or recall one of 9 presets after a
    configurable 1–30s delay — our `AutoFramer`'s "ease back to full frame after a hold
    period" is the digital-crop equivalent of this.
  - **Sensitivity Level**, 1–10.
  - **Tracking Disable Area**: a rectangle (max 640×360) drawn directly on the preview
    (right-click + drag) inside which tracking is ignored — confirms "masking" is a
    draw-a-box-on-the-preview interaction, not a separate menu.
  - A **mask area slider** (separate from Tracking Disable Area) trims detection to a
    vertical band of the frame (top/bottom masked).
- **Angle specification** presets: Upper Body / Full Body / Full / OFF — each maps to a
  stored zoom magnification that is either entered manually per camera or auto-computed
  from that camera's installed **Height** and **Distance** (set once per registered
  camera). This is their "Auto Zoom" — it's per-preset framing tightness, not a single
  continuous target-fill slider like ours; good Phase 2 UX option to offer both.
  - **Pan/Tilt Limitation**: independent Top/Bottom/Left/Right ON/OFF toggles.
- **Multi-camera**: a registered camera list (ID, name, IP, port, connection status,
  search-by-name) with Add/Edit/Delete; "Auto Search" discovers cameras on the network
  and pre-fills fields. Per-camera config includes login/password, install height/
  distance, per-angle zoom, and **Image Capture Type: JPEG or H.264** (their doc
  explicitly recommends JPEG over H.264 for tracking performance on most models — notable
  given everyone defaults to H.264 for bandwidth; worth keeping in mind for our own
  source handling).
- **Two deployment modes**: standalone (one PC) or a web-application version (server PC +
  browser clients, Chrome only) — matches the Node.js web server we found in the
  installer.
- **Licensing**: 30-day trial (their manual's number; marketing pages say 30 or 90
  depending on region/date), paid key-code activation after.
- **Explicit, stated caution** (direct quote, condensed): tracks **one** target and is
  **not** meant for scenes with several moving subjects; detection can misfire; loss of
  tracking is expected; "use this software in an environment in which the correction task
  can be performed by the operator." This is their own documentation, not us inferring an
  operator-in-the-loop requirement.
- **Minimum hardware**, confirmed: Core i5-3320M/4GB RAM/1600×900 minimum; Core
  i7-4710MQ/8GB/1920×1080 recommended — modest by today's standards, consistent with a
  single-camera, single-subject tool rather than a heavy multi-stream system.

## 3. Screen inventory (confidence: HIGH — read directly from the manual, not
reconstructed)

1. **View screen** (shown on launch): camera list with thumbnails, per-camera status
   (**Lost / Tracking / Stop / Disconnect**), tracking-target face thumbnail + name,
   Connect/Disconnect per camera, an optional collapsible "camera controller" (PTZ,
   focus, preset, image-adjust, a link to the camera's own web admin page).
2. **Main screen**: camera list (narrower) + a large tracking operation area per camera —
   live image with the blue/yellow/red overlay rectangles described above, the mask-area
   slider, Tracking Start/Stop, Tracking Setting button, Face Recognition on/off +
   face-select, Target Position Set toggle, Angle preset buttons, Pan/Tilt Limitation
   toggles — plus the same camera controller as the View screen.
3. **Tracking Setting window** (modal, opened from Main): all the per-camera tracking
   parameters listed in §2.
4. **Select Face window** (modal): pick which registered face is the active recognition
   target.
5. **Settings → Camera tab**: the registered-camera list + Add/Edit/Delete, feeding a
   **Register/Edit Camera screen** (name, IP, port, login, password, height, distance,
   max zoom, per-angle zoom with an Auto checkbox, Auto Search, Image Capture Type).
6. **Settings → Face Recognition tab**: registered face-data list + Add/Edit/Delete,
   feeding a **Register/Edit Face Data screen** (import from file or live camera capture,
   click-to-pick the detected face, name it).
7. **Settings → Tracking tab**: global tracking-method selector (Template matching / Deep
   Learning CPU / Deep Learning GPU).

Every one of these maps cleanly onto a feature we either already built (target click-
select, start/stop, dead-zone-style masking) or should plan for in Phase 2 (per-camera
registration list, face-recognition layer, lost-state grace period + "home" behavior,
draw-a-rectangle disable zones, pan/tilt-limit equivalents for our crop).

## 4. Craft Anything evaluation

Installed/evaluated: **cloned and inspected the actual repo** (`git clone --depth 1
https://github.com/storytold/craft-anything`, read `README.md`, `docs/tools.md`,
`docs/file-formats.md`) — not just the GitHub page summary. Did not run it (no suitable
target — see below).

[storytold/craft-anything](https://github.com/storytold/craft-anything) is a Rust CLI/desktop
tool, early alpha, built around four steps: **Study → Build → Check → Ready**. It drives a
coding agent (Claude Code first-class) to rebuild a target and checks the result against it.

**What it can study, confirmed from the repo, not just marketing copy:**
- **Deep mode**: a *live* website (reads page source/JS), a running local app/game (reads its
  code and files, optionally via Ghidra), i.e. black-box access to something actually running
  or installed on disk.
- **Clean-room mode** (default): works only from *pictures you manually add* plus what a
  visitor/user can see (screenshots, visible text, measured layout, a captured window image) —
  it never reads the target's own code/files in this mode.
- Checked its full tool list (`docs/tools.md`, ~320 tools): there is **no PDF or document
  ingestion tool** — no parser for manuals/brochures/API-doc PDFs. The only "file"-type targets
  are things like ROM/save/firmware formats to reverse-engineer as a format, not documentation
  to read as reference material. (`PdfCraft` is a separate, unrelated ArtCraft app for PDF
  editing, not a Craft Anything input source.)

**Why unsuitable here, concretely**: this project's only material is text marketing pages and
linked PDFs (brochures, operating instructions) — no running Panasonic software, no
AW-SF100/SF200 instance, no AW-UE150A-class camera, and no screenshots of the real UI saved
anywhere. That rules out Deep mode (nothing live to point it at) *and* clean-room mode (no
screenshots/pictures exist to feed it, and it has no PDF reader to pull them from the linked
manuals itself). Re-evaluate if a trial install, demo instance, or actual screenshots/screen
recording of the real software become available — at that point clean-room mode with manually
captured screenshots would be directly usable.

Per START.md, Craft Anything is optional and not a hard dependency — proceeding without it.

**Addendum — what actually happened instead**: we later got the real AW-SF100 90-day
trial installer (user-provided download) and installed it. Confirmed from its own files
before running anything: it ships `torch_cpu.dll`/`torch_cuda.dll`/`cudnn_*64_8.dll`
(LibTorch + CUDA 11/cuDNN 8), a bundled Node.js runtime, and an `MjpegProcessor` —
independent confirmation of the manual's stated architecture. On launch, its own
`TrackingControl` (the CUDA inference engine) crashed immediately with "Tracking Control
process stopped. Start again." This happened with no camera connected and on a GPU/driver
combination far newer than the software's 2019-era CUDA 11/cuDNN 8 target, which is the
likely cause — not pursued further since Craft Anything also couldn't help here (no
window ever rendered past the crash dialog). **We got a verified screen inventory a
different, simpler way**: downloading Panasonic's own official Operating Instructions PDF
and Keyboard Shortcuts PDF and reading them directly (text-extracted with PyMuPDF) —
every screen, button, and parameter in §2/§3 below comes from that manual, not from
running the software or from Craft Anything. This is squarely "official manuals" per
START.md Phase 0 step 1, just executed after the live-software route turned out to be a
dead end on this machine.

## 5. Confidence / unknowns summary

| Confirmed (from the official manual, high confidence) | Still unconfirmed |
|---|---|
| Full screen inventory: View, Main, Tracking Setting, Select Face, Settings×3 tabs, their sub-screens | Exact pixel layout/visual design (manual describes function, not pixel-perfect mockups — we didn't render manual screenshots to images) |
| All Main-screen and Tracking-Setting parameters (sensitivity 1-10, lost-state trigger/duration, home position, disable-area, angle presets, pan/tilt limits) | Exact tracking algorithm internals (template matching method, deep learning model architecture) |
| Three tracking methods (Template / Deep Learning CPU / Deep Learning GPU) and their CUDA/GPU requirements | Built-in (in-camera) auto tracking's UI — the manual we read covers the AW-SF100 plug-in only, not the in-camera feature |
| Target-select-by-click behavior (two modes: reposition vs. reselect) | AW-SF200's multi-camera/floating-license UI differences (not covered in the AW-SF100 single-PC manual) |
| Operator-in-the-loop is explicit, direct-quoted guidance from Panasonic | — |

## 6. Prioritized feature checklist for our app

Ordered by value for a camera-agnostic MVP; Phase numbers map to START.md phases.

1. **[Phase 1]** Live preview with detection bounding boxes — table stakes.
2. **[Phase 1]** Manual target selection among multiple detected people.
3. **[Phase 1]** Start/stop tracking.
4. **[Phase 1]** Smooth auto-framing (pan/tilt/zoom via crop) with dead zone, damping,
   max speed — mirrors Panasonic's "smooth, not jumpy" framing goal.
5. **[Phase 1]** Graceful handling of source loss / no-person-detected — mirrors
   Panasonic's operator-in-the-loop philosophy.
6. **[Phase 2]** Angle/zoom presets (Upper Body / Full Body / Full) as an alternative to
   (or alongside) our continuous target-fill slider — confirmed this is how Panasonic
   actually exposes "Auto Zoom", not a single slider.
7. **[Phase 2]** Draw-a-rectangle tracking-disable area on the live preview (right-click +
   drag, per their manual) — more concrete than our original vague "masking" item.
8. **[Phase 2]** Sensitivity control (confirmed as a single 1–10 value, not multiple
   knobs).
9. **[Phase 2]** Lost-state handling as two explicit, separate settings: a grace period
   before declaring "lost" (confirmed 1–30s, triggerable by body-only or body+face), and
   a configurable "home" behavior after loss (hold vs. recall a saved preset after a
   second configurable delay) — richer than our current single `reacquire_hold_frames`.
10. **[Phase 2]** Optional face-recognition layer on top of detection: register named
    faces (from file or live capture), toggle on/off, auto-assign target to a recognized
    face — confirmed as a distinct, optional feature, not baked into base detection.
11. **[Phase 2]** Multi-source registration + quick switching (their per-camera list with
    Add/Edit/Delete/Auto-Search), generalized to any configured source.
12. **[Phase 3]** Re-acquisition aid equivalent (e.g. widen search radius / use a
    secondary wide source) after track loss.
13. **[Phase 3]** RTSP/ONVIF sources; optional physical PTZ adapter; independent pan/tilt
    directional limit toggles (confirmed as 4 separate Top/Bottom/Left/Right switches).
14. **[Phase 3]** Recording / NDI-style output module.

Identity-switching and occlusion are explicitly **not** solved by Panasonic's marketing
copy either (hence their "operator must be ready to adjust" caveat) — our implementation
will document the same limitation rather than overclaim robustness (see ARCHITECTURE.md
§ Tracking limitations).
