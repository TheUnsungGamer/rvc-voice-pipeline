"""
Gradio Web UI — runs under envs/tts (Python 3.10).
Start: python ui.py  (TTS server must already be running)
"""

import os
from pathlib import Path

import gradio as gr

from pipeline import OUTPUT_DIR, REPO_ROOT, run_chain, run_rvc_on_wav, synthesize_text_to_wav

MODELS_DIR = REPO_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)


def _find_model_files(extension: str) -> list[str]:
    return [str(p) for p in sorted(MODELS_DIR.glob(f"**/*{extension}"))]


def _refresh_model_lists() -> tuple[list[str], list[str]]:
    return _find_model_files(".pth"), _find_model_files(".index")


# ── Tab: TTS only ────────────────────────────────────────────────────────────

def handle_tts_only(
    input_text: str,
    selected_voice: str,
) -> tuple[str, str]:
    if not input_text.strip():
        return None, "Error: text cannot be empty."

    try:
        saved_wav_path = synthesize_text_to_wav(
            text=input_text,
            voice=selected_voice,
            output_filename="tts_output.wav",
        )
        return str(saved_wav_path), f"Saved to {saved_wav_path}"
    except Exception as error:
        return None, f"Error: {error}"


# ── Tab: RVC only ────────────────────────────────────────────────────────────

def handle_rvc_only(
    uploaded_audio_path: str,
    selected_pth_model: str,
    selected_index_file: str,
    pitch_shift_semitones: int,
    index_influence_ratio: float,
    inference_device: str,
) -> tuple[str, str]:
    if not uploaded_audio_path:
        return None, "Error: upload an audio file first."
    if not selected_pth_model:
        return None, "Error: select a .pth model."

    output_wav_path = OUTPUT_DIR / "rvc_output.wav"
    index_path = Path(selected_index_file) if selected_index_file else None

    try:
        run_rvc_on_wav(
            input_wav_path=Path(uploaded_audio_path),
            output_wav_path=output_wav_path,
            model_pth_path=Path(selected_pth_model),
            index_path=index_path,
            pitch_shift_semitones=pitch_shift_semitones,
            index_influence_ratio=index_influence_ratio,
            device=inference_device,
        )
        return str(output_wav_path), f"Saved to {output_wav_path}"
    except Exception as error:
        return None, f"Error: {error}"


# ── Tab: Chain (TTS → RVC) ───────────────────────────────────────────────────

def handle_chain(
    input_text: str,
    selected_voice: str,
    selected_pth_model: str,
    selected_index_file: str,
    pitch_shift_semitones: int,
    index_influence_ratio: float,
    inference_device: str,
) -> tuple[str, str]:
    if not input_text.strip():
        return None, "Error: text cannot be empty."
    if not selected_pth_model:
        return None, "Error: select a .pth model."

    index_path = Path(selected_index_file) if selected_index_file else None

    try:
        final_wav_path = run_chain(
            text=input_text,
            voice=selected_voice,
            model_pth_path=Path(selected_pth_model),
            index_path=index_path,
            pitch_shift_semitones=pitch_shift_semitones,
            output_stem="chain_output",
            device=inference_device,
        )
        return str(final_wav_path), f"Saved to {final_wav_path}"
    except Exception as error:
        return None, f"Error: {error}"


# ── Build UI ──────────────────────────────────────────────────────────────────

def build_gradio_app() -> gr.Blocks:
    initial_pth_models, initial_index_files = _refresh_model_lists()

    with gr.Blocks(title="RVC Voice Pipeline") as gradio_app:
        gr.Markdown("## RVC Voice Pipeline")
        gr.Markdown(
            "Drop your `.pth` and `.index` files into the `models/` folder, "
            "then hit **Refresh models** before running."
        )

        with gr.Row():
            refresh_models_button = gr.Button("Refresh models", size="sm")
            device_dropdown = gr.Dropdown(
                choices=["cuda:0", "cpu"],
                value="cuda:0",
                label="Device",
                scale=1,
            )

        # Shared model selectors (defined once, reused across tabs via .change())
        with gr.Row():
            pth_model_dropdown = gr.Dropdown(
                choices=initial_pth_models,
                label=".pth model",
                value=initial_pth_models[0] if initial_pth_models else None,
                scale=2,
            )
            index_file_dropdown = gr.Dropdown(
                choices=["(none)"] + initial_index_files,
                label=".index file",
                value="(none)",
                scale=2,
            )

        refresh_models_button.click(
            fn=lambda: (
                gr.update(choices=_find_model_files(".pth")),
                gr.update(choices=["(none)"] + _find_model_files(".index")),
            ),
            outputs=[pth_model_dropdown, index_file_dropdown],
        )

        with gr.Tabs():

            # ── TTS tab ──────────────────────────────────────────────────────
            with gr.Tab("TTS only"):
                tts_text_input = gr.Textbox(
                    label="Text to synthesize",
                    lines=4,
                    placeholder="Enter text here...",
                )
                tts_voice_input = gr.Textbox(
                    label="Edge-TTS voice",
                    value="en-US-AriaNeural",
                )
                tts_run_button = gr.Button("Synthesize", variant="primary")
                tts_audio_output = gr.Audio(label="Output", type="filepath")
                tts_status_label = gr.Label(label="Status")

                tts_run_button.click(
                    fn=handle_tts_only,
                    inputs=[tts_text_input, tts_voice_input],
                    outputs=[tts_audio_output, tts_status_label],
                )

            # ── RVC tab ──────────────────────────────────────────────────────
            with gr.Tab("RVC only"):
                rvc_audio_upload = gr.Audio(label="Input audio", type="filepath")
                with gr.Row():
                    rvc_pitch_slider = gr.Slider(
                        minimum=-24, maximum=24, value=0, step=1,
                        label="Pitch shift (semitones)",
                    )
                    rvc_index_ratio_slider = gr.Slider(
                        minimum=0.0, maximum=1.0, value=0.75, step=0.05,
                        label="Index influence",
                    )
                rvc_run_button = gr.Button("Convert", variant="primary")
                rvc_audio_output = gr.Audio(label="Output", type="filepath")
                rvc_status_label = gr.Label(label="Status")

                rvc_run_button.click(
                    fn=handle_rvc_only,
                    inputs=[
                        rvc_audio_upload,
                        pth_model_dropdown,
                        index_file_dropdown,
                        rvc_pitch_slider,
                        rvc_index_ratio_slider,
                        device_dropdown,
                    ],
                    outputs=[rvc_audio_output, rvc_status_label],
                )

            # ── Chain tab ────────────────────────────────────────────────────
            with gr.Tab("Chain (TTS → RVC)"):
                chain_text_input = gr.Textbox(
                    label="Text to synthesize and convert",
                    lines=4,
                    placeholder="Enter text here...",
                )
                chain_voice_input = gr.Textbox(
                    label="Edge-TTS voice",
                    value="en-US-AriaNeural",
                )
                with gr.Row():
                    chain_pitch_slider = gr.Slider(
                        minimum=-24, maximum=24, value=0, step=1,
                        label="Pitch shift (semitones)",
                    )
                    chain_index_ratio_slider = gr.Slider(
                        minimum=0.0, maximum=1.0, value=0.75, step=0.05,
                        label="Index influence",
                    )
                chain_run_button = gr.Button("Run chain", variant="primary")
                chain_audio_output = gr.Audio(label="Output", type="filepath")
                chain_status_label = gr.Label(label="Status")

                chain_run_button.click(
                    fn=handle_chain,
                    inputs=[
                        chain_text_input,
                        chain_voice_input,
                        pth_model_dropdown,
                        index_file_dropdown,
                        chain_pitch_slider,
                        chain_index_ratio_slider,
                        device_dropdown,
                    ],
                    outputs=[chain_audio_output, chain_status_label],
                )

    return gradio_app


if __name__ == "__main__":
    gradio_ui = build_gradio_app()
    gradio_ui.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("UI_PORT", "7860")),
        share=False,
    )
