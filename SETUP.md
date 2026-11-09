# Getting set up

Step by step, from a fresh Windows PC to the app running in your browser.
Takes about 30 minutes, most of it downloads. macOS/Linux notes are at the end.

You'll end up with two things running at once: a **backend** (Python, does the
video and AI work) and a **frontend** (the web page you click on). You open the
frontend in your browser at http://localhost:5173.

---

## 1. Get access to the repo

The repo is private. Send your GitHub username to the owner; they add you under
the repo's **Settings → Collaborators → Add people**. Accept the invite from the
email GitHub sends you (or from https://github.com/notifications).

No GitHub account yet? Create one at https://github.com/signup first.

## 2. Install the tools

Install these four, in any order. Accept the defaults unless noted.

| Tool | Download | Note |
|---|---|---|
| Git | https://git-scm.com/download/win | defaults are fine |
| VS Code | https://code.visualstudio.com/ | tick **"Add to PATH"** and **"Open with Code"** |
| Python **3.10** | https://www.python.org/downloads/release/python-31011/ (Windows installer 64-bit) | tick **"Add python.exe to PATH"** on the first screen. Use 3.10: newer versions are untested here |
| Node.js **LTS** | https://nodejs.org/ | defaults are fine |

Have an NVIDIA graphics card? Also update its driver from
https://www.nvidia.com/Download/index.aspx. It's optional: the app also runs on
the CPU, just slower.

**Restart your PC** after installing, so every tool is found.

Check it worked: open **PowerShell** (Start menu, type "PowerShell") and run:

```powershell
git --version
py -3.10 --version
node --version
```

Each should print a version number. If one says "not recognized", reinstall it
and make sure the PATH option was ticked.

## 3. Get the code into VS Code

1. Open VS Code.
2. Press `Ctrl+Shift+P`, type **Git: Clone**, press Enter.
3. Choose **Clone from GitHub**, sign in to GitHub when the browser asks, then pick
   **huitsixseptdeux/panasonic-cam-tracker**.
4. Choose a folder to put it in (for example `Documents\dev`), then click
   **Open** when VS Code asks whether to open the cloned repo.
5. VS Code asks whether you trust the authors: click **Yes**.
6. A popup offers to install the **recommended extensions**: click **Install**
   (Python, Pylance, ESLint, Prettier).

## Quick way (Windows): two double-clicks

After steps 1–3, open the project folder in File Explorer and:

1. Double-click **`setup.bat`**: installs everything (once, a few minutes).
2. Double-click **`start.bat`**: opens two windows (backend and frontend) and
   your browser on the app. Close those two windows to stop it.

That's all you need to try the app. Steps 4–6 below do the same by hand, which
you'll want once you start changing code.

## 4. Set up the backend

Open a terminal inside VS Code: menu **Terminal → New Terminal**. It opens in
the project folder. Run these one at a time:

```powershell
cd backend
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt now starts with `(.venv)`. That means the project's own Python is
active.

> **Error "running scripts is disabled on this system"?** Run this once, then
> run the `Activate.ps1` line again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Then install the Python packages (a few minutes, it's a big download):

```powershell
pip install -r requirements.txt
```

**Only if you have an NVIDIA card**, also run this. Without it, detection runs on
the CPU:

```powershell
pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Download the face models and the test videos (they're too big for git):

```powershell
python scripts/fetch_assets.py
```

Finally, tell VS Code to use this Python: press `Ctrl+Shift+P`, type
**Python: Select Interpreter**, and pick the one whose path contains
`backend\.venv`.

## 5. Set up the frontend

Open a **second** terminal: click the **+** at the top right of the terminal
panel. Then:

```powershell
cd frontend
npm install
```

## 6. Run it

You need both terminals running at the same time.

**Terminal 1, backend** (in `backend`, with `(.venv)` showing):

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete`.

**Terminal 2, frontend** (in `frontend`):

```powershell
npm run dev
```

Open **http://localhost:5173** in your browser.

Try it: pick **speaker_on_stage.mp4** on the left, click the person in the
image, and watch the right-hand panel follow her. The first start takes a few
extra seconds while the detection model downloads.

To stop either one: click its terminal and press `Ctrl+C`.

**Next time** you only need step 6, plus `.venv\Scripts\Activate.ps1` in the
backend terminal first.

## 7. Day-to-day with Git

In VS Code's terminal:

```powershell
git pull                          # get the latest changes before you start
git checkout -b my-change         # work on your own branch
# ... edit files ...
git add -A
git commit -m "Describe what you changed"
git push -u origin my-change      # then open a Pull Request on GitHub
```

The **Source Control** icon in VS Code's left sidebar does the same with
buttons.

If someone added Python or npm packages, rerun `pip install -r requirements.txt`
(backend, with the venv active) or `npm install` (frontend).

## 8. Where things are

- `README.md`: what the app does and how it's organised
- `ARCHITECTURE.md`: how the pieces fit together
- `PROGRESS.md`: what's done and the roadmap
- `backend/app/`: the Python code. `frontend/src/`: the web page

## When something goes wrong

| Problem | Fix |
|---|---|
| `py` or `node` "not recognized" | Reinstall with the PATH option ticked, then restart the PC |
| `Activate.ps1` blocked | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry |
| Backend: "address already in use" / port 8000 | A backend is already running. Close the other terminal, or run `Get-NetTCPConnection -LocalPort 8000 \| % { Stop-Process -Id $_.OwningProcess }` |
| Page loads but "connecting…" forever | The backend isn't running. Start terminal 1 |
| Webcam shows nothing | Another app (Teams, Zoom, OBS) is using the camera. Close it and pick the source again |
| Top bar shows `cpu`, you have an NVIDIA card | Run the NVIDIA `pip install` line from step 4 again |
| Backend window closes with no error | Known issue. Start it with `$env:PYTHONFAULTHANDLER=1; python -X faulthandler -m uvicorn app.main:app --port 8000` and send the output to the team |

## macOS / Linux

Same steps, with these differences:
- Install Python 3.10 with your package manager or pyenv. Use `python3.10`
  instead of `py -3.10`.
- Activate the venv with `source .venv/bin/activate`.
- Skip the NVIDIA line on a Mac (no CUDA). On Linux with an NVIDIA card it applies.
- Webcam support has only been tested on Windows.
