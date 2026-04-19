@echo off
setlocal

echo [setup] Creating TTS venv (Python 3.10)...
py -3.10 -m venv envs\tts
if errorlevel 1 (
    echo [setup] ERROR: Python 3.10 not found. Install from python.org and retry.
    exit /b 1
)

echo [setup] Installing TTS dependencies...
envs\tts\Scripts\pip install --upgrade pip
envs\tts\Scripts\pip install ^
    fastapi ^
    uvicorn[standard] ^
    httpx ^
    edge-tts ^
    pydub ^
    gradio

echo.
echo [setup] Creating RVC venv (Python 3.12)...
py -3.12 -m venv envs\rvc
if errorlevel 1 (
    echo [setup] ERROR: Python 3.12 not found. Install from python.org and retry.
    exit /b 1
)

echo [setup] Installing RVC dependencies...
envs\rvc\Scripts\pip install --upgrade pip
envs\rvc\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
envs\rvc\Scripts\pip install ^
    scipy ^
    numpy ^
    librosa ^
    soundfile ^
    praat-parselmouth ^
    pyworld ^
    faiss-gpu

echo.
echo [setup] NOTE: RVC core (rvc-beta0717) must be cloned manually into this repo root.
echo         See README.md for instructions.
echo.
echo [setup] Done. Run run.bat to start the pipeline.
endlocal
