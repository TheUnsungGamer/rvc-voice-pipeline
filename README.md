# RVC Voice Pipeline

A barebones, redistributable shell for RVC voice conversion with three operating modes:

| Mode | What it does |
|------|-------------|
| **TTS only** | Text → WAV via edge-tts |
| **RVC only** | WAV → converted WAV via your RVC model |
| **Chain** | Text → TTS WAV → RVC WAV in one click |

Runs a Gradio Web UI at `http://localhost:7860`. No coding required after setup.

---

## Requirements

- Python **3.10** and **3.12** both installed (the split-venv architecture requires both)
- CUDA-capable GPU recommended (CPU inference works but is slow)
- [FFmpeg](https://ffmpeg.org/download.html) on your system PATH (required by pydub for mp3→wav conversion)
- [rvc-beta0717](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) cloned into this repo root (see below)

---

## Setup

### 1. Clone RVC into this repo

RVC cannot be pip-installed as a clean package — you need to clone it directly:

```bash
git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git .
```

> Clone into `.` (the repo root), not a subdirectory. `rvc_infer.py` imports
> from `configs/` and `infer/` which must exist at the root level.

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

This creates `envs/tts` (Python 3.10) and `envs/rvc` (Python 3.12) and installs all dependencies into each.

### 3. Drop in your model files

Place your `.pth` and `.index` files into the `models/` folder:

```
models/
  my_voice.pth
  my_voice.index   ← optional but improves similarity
```

Subdirectories are fine — the UI will find them recursively.

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

Open `http://localhost:7860` in your browser.

---

## Architecture

```
envs/tts (Python 3.10)          envs/rvc (Python 3.12)
├── tts_server.py (FastAPI)      ├── rvc_infer.py
├── pipeline.py (orchestrator)   └── [rvc-beta0717 internals]
└── ui.py (Gradio)
         │
         └── subprocess call crosses the venv boundary
```

`pipeline.py` runs in the 3.10 venv and spawns `rvc_infer.py` as a subprocess using the 3.12 python binary. This is the same pattern used in the Ash stack — it's the cleanest way to satisfy RVC's hard 3.12 dependency without breaking TTS.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_HOST` | `127.0.0.1` | TTS server bind address |
| `TTS_PORT` | `5050` | TTS server port |
| `UI_PORT` | `7860` | Gradio UI port |

---

## Swapping the TTS backend

All TTS logic lives in `_synthesize_to_wav()` in `tts_server.py`. Replace that function to use Coqui, Piper, Bark, or any other backend — the pipeline and UI are unaffected.

---

## Known issues

- **Hardcoded `cuda:0`** — the device dropdown in the UI passes the value through, but if you only have CPU, select `cpu` before running.
- **RVC import path** — `rvc_infer.py` imports from `configs.config` and `infer.modules.vc.modules`. If your rvc-beta0717 checkout has a different layout, update those import paths at the top of `rvc_infer.py`.
- **mp3 → wav fallback** — if `pydub` is not installed or ffmpeg is missing, edge-tts output is saved as `.mp3` with a `.wav` extension. Install ffmpeg to fix this.
