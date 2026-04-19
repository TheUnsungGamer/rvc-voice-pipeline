#!/usr/bin/env bash
set -e

echo "[setup] Creating TTS venv (Python 3.10)..."
python3.10 -m venv envs/tts || { echo "[setup] ERROR: Python 3.10 not found."; exit 1; }

echo "[setup] Installing TTS dependencies..."
envs/tts/bin/pip install --upgrade pip
envs/tts/bin/pip install \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    edge-tts \
    pydub \
    gradio

echo
echo "[setup] Creating RVC venv (Python 3.12)..."
python3.12 -m venv envs/rvc || { echo "[setup] ERROR: Python 3.12 not found."; exit 1; }

echo "[setup] Installing RVC dependencies..."
envs/rvc/bin/pip install --upgrade pip
envs/rvc/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
envs/rvc/bin/pip install \
    scipy \
    numpy \
    librosa \
    soundfile \
    praat-parselmouth \
    pyworld \
    faiss-gpu

echo
echo "[setup] NOTE: RVC core (rvc-beta0717) must be cloned manually into this repo root."
echo "        See README.md for instructions."
echo
echo "[setup] Done. Run ./run.sh to start the pipeline."
