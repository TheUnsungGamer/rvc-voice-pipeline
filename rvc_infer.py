"""
RVC inference — runs under envs/rvc (Python 3.12).
Called as a subprocess by pipeline.py so the venv boundary is respected.

Usage (direct):
    python rvc_infer.py \
        --input  output/tts_out.wav \
        --output output/rvc_out.wav \
        --model  models/my_voice.pth \
        --index  models/my_voice.index \
        --pitch  0
"""

import argparse
import sys
from pathlib import Path


def _load_rvc_model(model_pth_path: Path, device: str):
    """
    Lazy-import RVC internals so this file can be imported without triggering
    the full torch load when only --help is needed.
    """
    # rvc-beta0717 exposes VC as the main inference class.
    # Adjust this import path if your RVC checkout uses a different layout.
    try:
        from configs.config import Config
        from infer.modules.vc.modules import VC

        rvc_config = Config()
        voice_changer = VC(rvc_config)
        voice_changer.get_vc(str(model_pth_path))
        return voice_changer
    except ImportError as rvc_import_error:
        print(
            f"[rvc_infer] Could not import RVC modules: {rvc_import_error}\n"
            "Make sure envs/rvc is activated and rvc-beta0717 is installed.",
            file=sys.stderr,
        )
        sys.exit(1)


def run_rvc_inference(
    input_wav_path: Path,
    output_wav_path: Path,
    model_pth_path: Path,
    index_path: Path | None,
    pitch_shift_semitones: int,
    index_influence_ratio: float,
    filter_radius: int,
    resample_sr: int,
    rms_mix_rate: float,
    protect_voiceless_ratio: float,
    device: str,
) -> None:
    if not input_wav_path.exists():
        print(f"[rvc_infer] Input file not found: {input_wav_path}", file=sys.stderr)
        sys.exit(1)

    if not model_pth_path.exists():
        print(f"[rvc_infer] Model file not found: {model_pth_path}", file=sys.stderr)
        sys.exit(1)

    output_wav_path.parent.mkdir(parents=True, exist_ok=True)

    voice_changer = _load_rvc_model(model_pth_path, device)

    # vc_single signature matches rvc-beta0717 — adjust if you use a fork.
    _info, (converted_sample_rate, converted_audio_data) = voice_changer.vc_single(
        sid=0,
        input_audio_path=str(input_wav_path),
        f0_up_key=pitch_shift_semitones,
        f0_file=None,
        f0_method="rmvpe",
        file_index=str(index_path) if index_path and index_path.exists() else "",
        file_index2="",
        index_rate=index_influence_ratio,
        filter_radius=filter_radius,
        resample_sr=resample_sr,
        rms_mix_rate=rms_mix_rate,
        protect=protect_voiceless_ratio,
    )

    import scipy.io.wavfile as wavfile

    wavfile.write(str(output_wav_path), converted_sample_rate, converted_audio_data)
    print(f"[rvc_infer] Saved: {output_wav_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RVC inference runner")
    parser.add_argument("--input",   required=True,  type=Path, help="Input wav path")
    parser.add_argument("--output",  required=True,  type=Path, help="Output wav path")
    parser.add_argument("--model",   required=True,  type=Path, help=".pth model path")
    parser.add_argument("--index",   default=None,   type=Path, help=".index file path (optional)")
    parser.add_argument("--pitch",   default=0,      type=int,  help="Pitch shift in semitones")
    parser.add_argument("--index-ratio",    default=0.75, type=float)
    parser.add_argument("--filter-radius", default=3,    type=int)
    parser.add_argument("--resample-sr",   default=0,    type=int)
    parser.add_argument("--rms-mix-rate",  default=0.25, type=float)
    parser.add_argument("--protect",       default=0.33, type=float)
    parser.add_argument("--device",        default="cuda:0")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = _parse_args()
    run_rvc_inference(
        input_wav_path=cli_args.input,
        output_wav_path=cli_args.output,
        model_pth_path=cli_args.model,
        index_path=cli_args.index,
        pitch_shift_semitones=cli_args.pitch,
        index_influence_ratio=cli_args.index_ratio,
        filter_radius=cli_args.filter_radius,
        resample_sr=cli_args.resample_sr,
        rms_mix_rate=cli_args.rms_mix_rate,
        protect_voiceless_ratio=cli_args.protect,
        device=cli_args.device,
    )
