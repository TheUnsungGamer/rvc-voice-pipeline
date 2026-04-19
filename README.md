# RVC Voice Pipeline

A barebones, redistributable shell for RVC voice conversion with three operating modes:

| Mode | What it does |
|------|-------------|
| **TTS only** | Text → WAV via edge-tts |
| **RVC only** | WAV → converted WAV via your RVC model |
| **Chain** | Text → TTS WAV → RVC WAV in one click |

Runs a Gradio Web UI at `http://localhost:7860`. No coding required after setup.

---

## Why this exists

Every RVC tutorial assumes you already know what you're doing. You clone the repo, stare at a wall of dependency errors, realize your Python version is wrong, install another version, break your first one, and eventually give up or spend a weekend debugging import paths.

This repo is the thing I wished existed when I started. It is a clean, working shell — not a fork of RVC, not a GUI wrapper, not a cloud service. It is a local pipeline you download, unzip, run one setup script, and use. That's it.

There is no hosted version. No subscription. No account. It runs entirely on your machine.

The three modes (TTS only, RVC only, and the full TTS → RVC chain) cover every real use case I've seen. The Gradio UI means non-developers can use it without touching a terminal after setup.

This took significant time to get right — specifically the dual Python environment problem described below, which is the part nobody talks about and the reason most DIY setups silently break.

---

## The dual-environment problem (and why it matters)

This is the part that trips everyone up.

RVC requires **Python 3.12**. The best TTS libraries (edge-tts, Coqui, Piper) run cleanest on **Python 3.10**. These two environments have conflicting dependency trees — you cannot install them into the same venv without breaking one or both.

Most people either don't know this, or they force everything into one environment and end up with a broken install they can't diagnose.

This pipeline solves it with a clean split-venv architecture:

```
envs/tts/   ← Python 3.10 venv
            runs: tts_server.py, pipeline.py, ui.py

envs/rvc/   ← Python 3.12 venv
            runs: rvc_infer.py + RVC internals
```

The two environments never share a Python process. `pipeline.py` (running in the 3.10 venv) calls `rvc_infer.py` as a **subprocess**, passing the explicit path to the 3.12 Python binary. The venv boundary is crossed at the OS level — no hacks, no `sys.path` manipulation, no monkey-patching.

```
pipeline.py (3.10)
    │
    └── subprocess: envs/rvc/bin/python rvc_infer.py --input ... --output ...
                         (3.12)
```

The TTS server runs as a local FastAPI service on port 5050. The Gradio UI and pipeline orchestrator talk to it over HTTP. This also means you can swap out the TTS backend entirely — Coqui, Piper, Bark, anything — by replacing one function in `tts_server.py` without touching the rest of the stack.

---

## Download

**Do not clone this repo directly.** The repo contains a single release zip with the full pipeline structure inside.

1. Download `rvc-voice-pipeline.zip` from this repo
2. Unzip it wherever you want to run it from
3. Follow the setup steps below

---

## Requirements

- Python **3.10** and **3.12** both installed and available on your PATH
- CUDA-capable GPU recommended (CPU inference works but is significantly slower)
- [FFmpeg](https://ffmpeg.org/download.html) on your system PATH (required for mp3 → wav conversion)
- [rvc-beta0717](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) cloned into the unzipped folder root (see step 1 below)

---

## Setup

### 1. Clone RVC into the pipeline folder

RVC cannot be pip-installed as a clean package. Clone it directly into the root of the unzipped folder:

```bash
git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git .
```

> The `.` at the end is important — clone into the current directory, not a subdirectory.
> `rvc_infer.py` imports from `configs/` and `infer/` which must exist at the root level.

### 2. Bootstrap both venvs

**Windows:**
```bat
setup.bat
```

**Linux / Mac:**
```bash
chmod +x setup.sh run.sh
./setup.sh
```

This creates `envs/tts` (Python 3.10) and `envs/rvc` (Python 3.12) and installs all dependencies into each independently. The two environments do not interact.

### 3. Drop in your model files

Place your `.pth` and `.index` files into the `models/` folder:

```
models/
  my_voice.pth
  my_voice.index   ← optional but improves similarity
```

Subdirectories are supported — the UI will find them recursively.

---

## Running

**Windows:**
```bat
run.bat
```

**Linux / Mac:**
```bash
./run.sh
```

Open `http://localhost:7860` in your browser. Hit Ctrl+C (or any key on Windows) to shut both services down cleanly.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_HOST` | `127.0.0.1` | TTS server bind address |
| `TTS_PORT` | `5050` | TTS server port |
| `UI_PORT` | `7860` | Gradio UI port |

---

## Swapping the TTS backend

All TTS logic is isolated in `_synthesize_to_wav()` inside `tts_server.py`. Replace that single function to use Coqui, Piper, Bark, or any other backend. The pipeline, UI, and RVC layer are completely unaffected.

---

## Known issues

- **RVC import path** — `rvc_infer.py` imports from `configs.config` and `infer.modules.vc.modules`. If your rvc-beta0717 checkout has a different internal layout, update those import paths at the top of `rvc_infer.py`.
- **mp3 → wav fallback** — if ffmpeg is missing, edge-tts output is saved as `.mp3` with a `.wav` extension. Install ffmpeg and this resolves automatically.
- **CPU inference** — select `cpu` in the device dropdown before running if you don't have a CUDA GPU. It works, it's just slow.
