"""
TTS server — runs under envs/tts (Python 3.10).
Exposes POST /synthesize → streams wav audio back.
Swap out the synthesis backend by replacing _synthesize_to_wav().
"""

import asyncio
import io
import os
import tempfile
from pathlib import Path

import edge_tts
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

TTS_HOST = os.getenv("TTS_HOST", "127.0.0.1")
TTS_PORT = int(os.getenv("TTS_PORT", "5050"))
DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


app = FastAPI(title="TTS Server")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    # output_filename is optional — omit to get streaming bytes back
    output_filename: str | None = None


async def _synthesize_to_wav(text: str, voice: str, destination_path: Path) -> None:
    """Synthesize text to wav via edge-tts. Swap this function to change TTS backends."""
    communicator = edge_tts.Communicate(text, voice)
    mp3_buffer = io.BytesIO()

    async for audio_chunk in communicator.stream():
        if audio_chunk["type"] == "audio":
            mp3_buffer.write(audio_chunk["data"])

    mp3_buffer.seek(0)

    # edge-tts outputs mp3 — convert to wav so RVC can consume it directly
    try:
        import pydub
        audio_segment = pydub.AudioSegment.from_mp3(mp3_buffer)
        audio_segment.export(str(destination_path), format="wav")
    except ImportError:
        # Fallback: write mp3 and rename — RVC can handle it with ffmpeg
        mp3_path = destination_path.with_suffix(".mp3")
        with open(mp3_path, "wb") as mp3_file:
            mp3_file.write(mp3_buffer.getvalue())
        os.rename(mp3_path, destination_path)


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    if request.output_filename:
        wav_output_path = OUTPUT_DIR / request.output_filename
    else:
        wav_output_path = OUTPUT_DIR / f"tts_{id(request)}.wav"

    try:
        await _synthesize_to_wav(request.text, request.voice, wav_output_path)
    except Exception as synthesis_error:
        raise HTTPException(status_code=500, detail=str(synthesis_error))

    if request.output_filename:
        return {"status": "ok", "path": str(wav_output_path)}

    # Stream bytes back so the pipeline can pipe directly into RVC
    return StreamingResponse(
        open(wav_output_path, "rb"),
        media_type="audio/wav",
        headers={"X-Output-Path": str(wav_output_path)},
    )


@app.get("/voices")
async def list_voices():
    """Return available edge-tts voices. Useful for the Gradio dropdown."""
    voices_manager = await edge_tts.VoicesManager.create()
    return [
        {"name": voice["FriendlyName"], "short_name": voice["ShortName"]}
        for voice in voices_manager.voices
    ]


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host=TTS_HOST, port=TTS_PORT)
