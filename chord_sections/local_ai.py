from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from chord_sections.lyrics import LyricLine


MODEL_SIZES = {
    "base": "about 145 MB",
    "small": "about 484 MB",
}


def available_engines() -> dict[str, bool]:
    return {
        "demucs": importlib.util.find_spec("demucs") is not None,
        "faster_whisper": importlib.util.find_spec("faster_whisper") is not None,
    }


def transcribe_song(
    audio_path: str | Path,
    *,
    model_size: str = "small",
    language: str | None = None,
    separate_vocals: bool = True,
) -> tuple[LyricLine, ...]:
    engines = available_engines()
    if not engines["faster_whisper"]:
        raise RuntimeError(
            "尚未安裝歌詞辨識模型。請在專案虛擬環境執行：python -m pip install -e '.[ai]'"
        )
    if separate_vocals and not engines["demucs"]:
        raise RuntimeError(
            "尚未安裝人聲分離模型。請在專案虛擬環境執行：python -m pip install -e '.[ai]'"
        )
    if model_size not in MODEL_SIZES:
        raise ValueError("歌詞模型需選擇 base 或 small。")
    if language not in (None, "zh", "en", "ja", "ko"):
        raise ValueError("語言需選擇自動、中文、英文、日文或韓文。")

    source_path = Path(audio_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {source_path}")

    transcription_path = source_path
    if separate_vocals:
        with tempfile.TemporaryDirectory(prefix="chord-sections-vocals-") as directory:
            transcription_path = _separate_vocals(source_path, Path(directory))
            return _transcribe(transcription_path, model_size, language)
    return _transcribe(transcription_path, model_size, language)


def _separate_vocals(source_path: Path, output_directory: Path) -> Path:
    command = [
        sys.executable,
        "-m",
        "demucs.separate",
        "-n",
        "htdemucs",
        "--two-stems=vocals",
        "--shifts",
        "1",
        "--device",
        "cpu",
        "-o",
        str(output_directory),
        str(source_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("人聲分離超過 60 分鐘，已停止處理。") from error
    except subprocess.CalledProcessError as error:
        details = (error.stderr or error.stdout or "Demucs returned an error").strip()
        raise RuntimeError(f"人聲分離失敗：{details[-2000:]}") from error

    separated_path = output_directory / "htdemucs" / source_path.stem / "vocals.wav"
    if not separated_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Demucs 沒有產生人聲音軌。{detail[-1000:]}")
    return separated_path


def _transcribe(audio_path: Path, model_size: str, language: str | None) -> tuple[LyricLine, ...]:
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        lines: list[LyricLine] = []
        for segment in segments:
            text = segment.text.strip()
            if text and segment.end > segment.start:
                lines.append(LyricLine(float(segment.start), float(segment.end), text))
    except (OSError, ValueError, RuntimeError) as error:
        raise RuntimeError(
            f"歌詞辨識失敗。若是第一次使用，請確認網路可下載模型（{MODEL_SIZES[model_size]}），"
            f"再重試。詳細錯誤：{error}"
        ) from error

    return tuple(lines)
