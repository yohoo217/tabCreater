from __future__ import annotations

import importlib.util
import re
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
    source_path = Path(audio_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {source_path}")

    if separate_vocals:
        with tempfile.TemporaryDirectory(prefix="chord-sections-vocals-") as directory:
            vocals_path, _instrumental_path = separate_stems(source_path, Path(directory))
            return transcribe_audio(vocals_path, model_size=model_size, language=language)
    return transcribe_audio(source_path, model_size=model_size, language=language)


def separate_stems(
    audio_path: str | Path,
    output_directory: str | Path,
) -> tuple[Path, Path]:
    if not available_engines()["demucs"]:
        raise RuntimeError(
            "尚未安裝人聲分離模型。請在專案虛擬環境執行：python -m pip install -e '.[ai]'"
        )
    source_path = Path(audio_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {source_path}")
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
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
        str(output_path),
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

    separated_directory = output_path / "htdemucs" / source_path.stem
    vocals_path = separated_directory / "vocals.wav"
    instrumental_path = separated_directory / "no_vocals.wav"
    if not vocals_path.is_file() or not instrumental_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Demucs 沒有產生完整的人聲與伴奏音軌。{detail[-1000:]}")
    return vocals_path, instrumental_path


def transcribe_audio(
    audio_path: str | Path,
    *,
    model_size: str = "small",
    language: str | None = None,
) -> tuple[LyricLine, ...]:
    if not available_engines()["faster_whisper"]:
        raise RuntimeError(
            "尚未安裝歌詞辨識模型。請在專案虛擬環境執行：python -m pip install -e '.[ai]'"
        )
    if model_size not in MODEL_SIZES:
        raise ValueError("歌詞模型需選擇 base 或 small。")
    if language not in (None, "zh", "en", "ja", "ko"):
        raise ValueError("語言需選擇自動、中文、英文、日文或韓文。")
    transcription_path = Path(audio_path)
    if not transcription_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {transcription_path}")
    return _transcribe(transcription_path, model_size, language)


def _transcribe(audio_path: Path, model_size: str, language: str | None) -> tuple[LyricLine, ...]:
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        lines: list[LyricLine] = []
        for segment in segments:
            text = _collapse_repeated_phrase(segment.text.strip())
            if text and segment.end > segment.start:
                lines.append(LyricLine(float(segment.start), float(segment.end), text))
    except (OSError, ValueError, RuntimeError) as error:
        raise RuntimeError(
            f"歌詞辨識失敗。若是第一次使用，請確認網路可下載模型（{MODEL_SIZES[model_size]}），"
            f"再重試。詳細錯誤：{error}"
        ) from error

    return tuple(lines)


def _collapse_repeated_phrase(text: str) -> str:
    words = list(re.finditer(r"[\w]+(?:['’][\w]+)*", text, flags=re.UNICODE))
    normalized = [word.group().casefold() for word in words]
    best: tuple[int, int, int] | None = None

    for start in range(len(words)):
        max_period = min(12, (len(words) - start) // 4)
        for period in range(2, max_period + 1):
            repeats = 1
            while (
                start + (repeats + 1) * period <= len(words)
                and normalized[start : start + period]
                == normalized[start + repeats * period : start + (repeats + 1) * period]
            ):
                repeats += 1
            if repeats >= 4 and (
                best is None or repeats * period > best[2] * best[1]
            ):
                best = (start, period, repeats)

    if best is None:
        return text

    start, period, repeats = best
    kept_end = words[start + period * 2 - 1].end()
    repeated_end = words[start + period * repeats - 1].end()
    return text[:kept_end] + text[repeated_end:]
