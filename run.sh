#!/usr/bin/env bash
set -e

cleanup() {
    echo
    echo "[run] Shutting down..."
    kill "$TTS_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[run] Starting TTS server on port 5050..."
envs/tts/bin/python tts_server.py &
TTS_PID=$!

sleep 3

echo "[run] Starting Gradio UI on port 7860..."
envs/tts/bin/python ui.py &
UI_PID=$!

echo
echo "[run] Services started."
echo "      TTS server : http://127.0.0.1:5050"
echo "      Gradio UI  : http://127.0.0.1:7860"
echo
echo "Press Ctrl+C to shut down."
wait
