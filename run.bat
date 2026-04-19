@echo off
setlocal

echo [run] Starting TTS server on port 5050...
start "TTS Server" /min envs\tts\Scripts\python tts_server.py

timeout /t 3 /nobreak >nul

echo [run] Starting Gradio UI on port 7860...
start "Gradio UI" envs\tts\Scripts\python ui.py

echo.
echo [run] Services started.
echo       TTS server : http://127.0.0.1:5050
echo       Gradio UI  : http://127.0.0.1:7860
echo.
echo Press any key to shut down both services...
pause >nul

taskkill /FI "WINDOWTITLE eq TTS Server*" /F
taskkill /FI "WINDOWTITLE eq Gradio UI*" /F
endlocal
