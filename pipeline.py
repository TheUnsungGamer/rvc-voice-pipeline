"""
Pipeline orchestrator — runs under envs/tts (Python 3.10).
Bridges TTS and RVC across the venv boundary via HTTP + subprocess.

Modes:
  tts   — synthesize text to wav only
  rvc   — convert an existing wav through RVC only
  chain — tts → temp wav → rvc → final wav
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).parent
RVC_PYTHON = REPO_ROOT / "envs" / "rvc" / "Scripts" / "python.exe"  # Windows
RVC_PYTHON_UNIX = REPO_ROOT / "envs" / "rvc" / "bin" / "python"
RVC_INFER_SCRIPT = REPO_ROOT / "rvc_infer.py"
OUTPUT_DIR = REPO_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TTS_BASE_URL = f"http://{os.getenv('TTS_HOST', '127.0.0.1')}:{os.getenv('TTS_PORT', '5050')}"


def _resolve_rvc_python() -> Path:
    """Return the correct RVC venv python path for the current OS."""
    if RVC_PYTHON.exists():
        return RVC_PYTHON
    if RVC_PYTHON_UNIX.exists():
        return RVC_PYTHON_UNIX
    raise FileNotFoundError(
        "RVC python not found. Run setup.bat (Windows) or setup.sh (Linux/Mac) first."
    )


def _wait_for_tts_server(timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            httpx.get(f"{TTS_BASE_URL}/health", timeout=2).raise_for_status()
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"TTS server did not respond within {timeout_seconds}s")


def synthesize_text_to_wav(
    text: str,
    voice: str,
    output_filename: str,
) -> Path:
    """POST to the TTS server and save the result to output/."""
    _wait_for_tts_server()
    response = httpx.post(
        f"{TTS_BASE_URL}/synthesize",
        json={"text": text, "voice": voice, "output_filename": output_filename},
        timeout=60,
    )
    response.raise_for_status()
    saved_path = Path(response.json()["path"])
    return saved_path


def run_rvc_on_wav(
    input_wav_path: Path,
    output_wav_path: Path,
    model_pth_path: Path,
    index_path: Path | None = None,
    pitch_shift_semitones: int = 0,
    index_influence_ratio: float = 0.75,
    device: str = "cuda:0",
) -> Path:
    """
    Invoke rvc_infer.py inside the RVC venv as a subprocess.
    This is how we cross the Python 3.10 / 3.12 venv boundary cleanly.
    """
    rvc_python_path = _resolve_rvc_python()

    subprocess_command = [
        str(rvc_python_path),
        str(RVC_INFER_SCRIPT),
        "--input",  str(input_wav_path),
        "--output", str(output_wav_path),
        "--model",  str(model_pth_path),
        "--pitch",  str(pitch_shift_semitones),
        "--index-ratio", str(index_influence_ratio),
        "--device", device,
    ]

    if index_path and index_path.exists():
        subprocess_command += ["--index", str(index_path)]

    result = subprocess.run(
        subprocess_command,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"RVC inference failed (exit {result.returncode}):\n{result.stderr}"
        )

    return output_wav_path


def run_chain(
    text: str,
    voice: str,
    model_pth_path: Path,
    index_path: Path | None,
    pitch_shift_semitones: int,
    output_stem: str,
    device: str = "cuda:0",
) -> Path:
    """Full TTS → RVC chain. Returns path to the final converted wav."""
    tts_wav_path = synthesize_text_to_wav(
        text=text,
        voice=voice,
        output_filename=f"{output_stem}_tts.wav",
    )

    final_wav_path = OUTPUT_DIR / f"{output_stem}_rvc.wav"

    run_rvc_on_wav(
        input_wav_path=tts_wav_path,
        output_wav_path=final_wav_path,
        model_pth_path=model_pth_path,
        index_path=index_path,
        pitch_shift_semitones=pitch_shift_semitones,
        device=device,
    )

    return final_wav_path
