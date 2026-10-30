from __future__ import annotations

import math
import os
import tempfile
import threading
import webbrowser
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from secrets import token_urlsafe

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from chord_sections import __version__
from chord_sections.analysis import AnalysisResult, analyze_file, transpose_audio_file
from chord_sections.local_ai import (
    MODEL_SIZES,
    available_engines,
    separate_stems,
    transcribe_audio,
    transcribe_song,
)
from chord_sections.lyrics import LyricLine
from chord_sections.music import key_names
from chord_sections.pdf_report import render_pdf


MAX_UPLOAD_BYTES = 300 * 1024 * 1024
MAX_CACHED_REPORTS = 5
ALLOWED_EXTENSIONS = {".aif", ".aiff", ".caf", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav"}
FEEDBACK_URL = "https://github.com/yohoo217/tabCreater/issues/new?template=feedback.yml"


@dataclass(frozen=True)
class SavedAnalysis:
    result: AnalysisResult
    title: str
    lyrics: tuple[LyricLine, ...] = ()


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
app.config["TEMPLATES_AUTO_RELOAD"] = True
_saved_analyses: OrderedDict[str, SavedAnalysis] = OrderedDict()
_saved_analyses_lock = threading.Lock()


@app.get("/")
def index():
    return render_template(
        "index.html",
        app_version=__version__,
        feedback_url=FEEDBACK_URL,
    )


@app.get("/api/ai-status")
def ai_status():
    engines = available_engines()
    return jsonify(
        {
            "ready": all(engines.values()),
            "engines": engines,
            "model_sizes": MODEL_SIZES,
        }
    )


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="音檔超過 300 MB 上限。"), 413


@app.post("/api/analyze")
def analyze_upload():
    uploaded_file = request.files.get("audio")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="請先選擇音檔。"), 400

    safe_filename = secure_filename(uploaded_file.filename)
    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(error="不支援此音檔格式，請使用 WAV、MP3、M4A、FLAC、OGG 或 AIFF。"), 400

    try:
        bpm = _optional_float("bpm")
        numerator = _integer("time_signature_numerator", 4)
        denominator = _integer("time_signature_denominator", 4)
        beats_per_chord = _float("beats_per_chord", 2.0)
        bars_per_section = _float("bars_per_section", 4.0)
        downbeat_offset = _float("downbeat_offset_seconds", 0.0)
        chroma_method = request.form.get("chroma_method", "stft")
    except ValueError as error:
        return jsonify(error=str(error)), 400
    if chroma_method not in {"stft", "cqt"}:
        return jsonify(error="不支援的分析解析度。"), 400

    title = request.form.get("title", "").strip()
    if not title:
        title = Path(safe_filename).stem
    title = title[:120]

    try:
        with tempfile.TemporaryDirectory(prefix="chord-sections-") as directory:
            audio_path = Path(directory) / f"upload{extension}"
            uploaded_file.save(audio_path)
            result = analyze_file(
                audio_path,
                bpm=bpm,
                time_signature_numerator=numerator,
                time_signature_denominator=denominator,
                beats_per_chord=beats_per_chord,
                bars_per_section=bars_per_section,
                downbeat_offset_seconds=downbeat_offset,
                harmonic_focus=request.form.get("harmonic_focus") == "on",
                chroma_method=chroma_method,
            )
    except (FileNotFoundError, ValueError) as error:
        return jsonify(error=str(error)), 400

    report_id = token_urlsafe(18)
    with _saved_analyses_lock:
        _saved_analyses[report_id] = SavedAnalysis(result, title)
        while len(_saved_analyses) > MAX_CACHED_REPORTS:
            _saved_analyses.popitem(last=False)

    return jsonify(_serialize_result(result, title, report_id))


@app.post("/api/convert")
def convert_upload():
    uploaded_file = request.files.get("audio")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="請先選擇音檔。"), 400

    safe_filename = secure_filename(uploaded_file.filename)
    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(error="不支援此音檔格式，請使用 WAV、MP3、M4A、FLAC、OGG 或 AIFF。"), 400

    engines = available_engines()
    if not engines["demucs"] or not engines["faster_whisper"]:
        return jsonify(
            error="自動轉換需要人聲分離與歌詞辨識模型。請在專案虛擬環境執行：python -m pip install -e '.[ai]'"
        ), 503

    model_size = request.form.get("model_size", "small")
    language = request.form.get("language", "auto")
    chroma_method = request.form.get("chroma_method", "stft")
    if model_size not in MODEL_SIZES:
        return jsonify(error="歌詞模型需選擇 base 或 small。"), 400
    if language not in {"auto", "zh", "en", "ja", "ko"}:
        return jsonify(error="不支援的歌詞辨識語言。"), 400
    if chroma_method not in {"stft", "cqt"}:
        return jsonify(error="不支援的分析解析度。"), 400

    title = request.form.get("title", "").strip() or Path(safe_filename).stem
    title = title[:120]
    try:
        with tempfile.TemporaryDirectory(prefix="chord-sections-convert-") as directory:
            work_directory = Path(directory)
            audio_path = work_directory / f"upload{extension}"
            uploaded_file.save(audio_path)
            vocals_path, instrumental_path = separate_stems(
                audio_path,
                work_directory / "separated",
            )
            lyrics = transcribe_audio(
                vocals_path,
                model_size=model_size,
                language=None if language == "auto" else language,
            )
            result = analyze_file(
                instrumental_path,
                harmonic_focus=request.form.get("harmonic_focus") == "on",
                chroma_method=chroma_method,
            )
    except (FileNotFoundError, ValueError) as error:
        return jsonify(error=str(error)), 400
    except RuntimeError as error:
        return jsonify(error=str(error)), 503

    report_id = token_urlsafe(18)
    with _saved_analyses_lock:
        _saved_analyses[report_id] = SavedAnalysis(result, title, lyrics)
        while len(_saved_analyses) > MAX_CACHED_REPORTS:
            _saved_analyses.popitem(last=False)

    payload = _serialize_result(result, title, report_id)
    payload["lyrics"] = [
        {"start": line.start, "end": line.end, "text": line.text}
        for line in lyrics
    ]
    payload["time_signature"] = None
    return jsonify(payload)


@app.get("/api/report/<report_id>.pdf")
def download_pdf(report_id: str):
    with _saved_analyses_lock:
        saved = _saved_analyses.get(report_id)
    if saved is None:
        abort(404, description="分析結果已過期，請重新分析音檔。")

    try:
        semitones = int(request.args.get("semitones", "0"))
        capo_fret = int(request.args.get("capo", "0"))
    except ValueError:
        abort(400, description="移調與 capo 位置必須是整數。")
    if not -12 <= semitones <= 12:
        abort(400, description="移調範圍必須介於 -12 至 +12 半音。")
    if not 0 <= capo_fret <= 11:
        abort(400, description="capo 位置必須介於 0 至 11 品。")
    original_key = request.args.get("original_key", "auto")
    if original_key != "auto" and original_key not in key_names():
        abort(400, description="不支援的原調名稱。")
    language = request.args.get("lang", "zh")
    if language not in {"zh", "en"}:
        abort(400, description="不支援的報告語言。")
    report_format = request.args.get("format", "full")
    if report_format not in {"full", "sheet"}:
        abort(400, description="不支援的 PDF 格式。")

    content = render_pdf(
        saved.result,
        saved.title,
        semitones=semitones,
        capo_fret=capo_fret,
        original_key=None if original_key == "auto" else original_key,
        lyrics=saved.lyrics,
        language=language,
        song_sheet=report_format == "sheet",
    )
    suffix = f"-{semitones:+d}st" if semitones else ""
    suffix += f"-capo{capo_fret}" if capo_fret else ""
    suffix += "-song-sheet" if report_format == "sheet" else "-chords"
    download_name = f"{secure_filename(saved.title) or 'song'}{suffix}.pdf"
    from io import BytesIO

    return send_file(
        BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


@app.post("/api/transpose-audio")
def download_transposed_audio():
    uploaded_file = request.files.get("audio")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="請先選擇音檔。"), 400

    safe_filename = secure_filename(uploaded_file.filename)
    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(error="不支援此音檔格式。"), 400
    try:
        semitones = _integer("semitones", 0)
        if not -12 <= semitones <= 12:
            raise ValueError("移調範圍必須介於 -12 至 +12 半音。")
        with tempfile.TemporaryDirectory(prefix="chord-sections-pitch-") as directory:
            audio_path = Path(directory) / f"source{extension}"
            uploaded_file.save(audio_path)
            content = transpose_audio_file(audio_path, semitones)
    except (FileNotFoundError, ValueError) as error:
        return jsonify(error=str(error)), 400

    stem = Path(safe_filename).stem or "song"
    suffix = f"{semitones:+d}st" if semitones else "original"
    from io import BytesIO

    return send_file(
        BytesIO(content),
        mimetype="audio/wav",
        as_attachment=True,
        download_name=f"{stem}-{suffix}.wav",
    )


@app.post("/api/transcribe")
def transcribe_upload():
    report_id = request.form.get("report_id", "")
    with _saved_analyses_lock:
        saved = _saved_analyses.get(report_id)
    if saved is None:
        return jsonify(error="分析結果已過期，請重新分析歌曲後再辨識歌詞。"), 404

    uploaded_file = request.files.get("audio")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="請先選擇音檔。"), 400
    safe_filename = secure_filename(uploaded_file.filename)
    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(error="不支援此音檔格式。"), 400
    model_size = request.form.get("model_size", "small")
    language = request.form.get("language", "auto")
    if language not in {"auto", "zh", "en", "ja", "ko"}:
        return jsonify(error="不支援的歌詞辨識語言。"), 400

    try:
        with tempfile.TemporaryDirectory(prefix="chord-sections-lyrics-") as directory:
            audio_path = Path(directory) / f"upload{extension}"
            uploaded_file.save(audio_path)
            lyrics = transcribe_song(
                audio_path,
                model_size=model_size,
                language=None if language == "auto" else language,
                separate_vocals=request.form.get("separate_vocals") == "on",
            )
    except (FileNotFoundError, ValueError) as error:
        return jsonify(error=str(error)), 400
    except RuntimeError as error:
        return jsonify(error=str(error)), 503

    with _saved_analyses_lock:
        latest = _saved_analyses.get(report_id)
        if latest is None:
            return jsonify(error="分析結果已過期，請重新分析歌曲。"), 404
        _saved_analyses[report_id] = replace(latest, lyrics=lyrics)

    return jsonify(
        {
            "report_id": report_id,
            "lyrics": [
                {"start": line.start, "end": line.end, "text": line.text}
                for line in lyrics
            ],
            "note": "歌詞是自動辨識結果；唱歌辨識可能有漏字或錯字，請逐行校對。",
        }
    )


@app.put("/api/lyrics/<report_id>")
def save_lyrics(report_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("lyrics"), list):
        return jsonify(error="歌詞資料格式錯誤。"), 400
    if len(payload["lyrics"]) > 2000:
        return jsonify(error="歌詞行數超過上限。"), 400

    with _saved_analyses_lock:
        saved = _saved_analyses.get(report_id)
    if saved is None:
        return jsonify(error="分析結果已過期，請重新分析歌曲。"), 404

    lyrics: list[LyricLine] = []
    for row in payload["lyrics"]:
        if not isinstance(row, dict) or not isinstance(row.get("text"), str):
            return jsonify(error="每行歌詞都需要文字、開始時間與結束時間。"), 400
        try:
            start = float(row["start"])
            end = float(row["end"])
        except (KeyError, TypeError, ValueError):
            return jsonify(error="歌詞時間必須是數字。"), 400
        text = row["text"].strip()
        if len(text) > 500:
            return jsonify(error="單行歌詞不可超過 500 字。"), 400
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or not 0 <= start < end <= saved.result.duration
            or not text
        ):
            return jsonify(error="歌詞時間需在歌曲範圍內，且結束時間必須晚於開始時間。"), 400
        lyrics.append(LyricLine(start, end, text))

    with _saved_analyses_lock:
        latest = _saved_analyses.get(report_id)
        if latest is None:
            return jsonify(error="分析結果已過期，請重新分析歌曲。"), 404
        _saved_analyses[report_id] = replace(latest, lyrics=tuple(lyrics))
    return jsonify({"saved": len(lyrics)})


def _serialize_result(result: AnalysisResult, title: str, report_id: str) -> dict[str, object]:
    return {
        "report_id": report_id,
        "title": title,
        "duration": result.duration,
        "tempo_bpm": result.tempo_bpm,
        "time_signature": f"{result.time_signature_numerator}/{result.time_signature_denominator}",
        "estimated_key": result.estimated_key,
        "chords": [
            {
                "start": event.start,
                "end": event.end,
                "chord": event.chord,
                "original_chord": event.chord,
                "confidence": event.confidence,
                "confidence_label": _confidence_label(event.confidence),
            }
            for event in result.chords
        ],
        "sections": [
            {
                "label": section.label,
                "start": section.start,
                "end": section.end,
                "chords": list(section.chords),
            }
            for section in result.sections
        ],
        "notes": [
            "信心指標是和弦模板符合度與候選差距的啟發式分數，不是校準機率或辨識準確率。",
            "段落是依和聲相似度分組，不代表程式已判斷主歌或副歌。",
        ],
    }


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "較高"
    if confidence >= 0.5:
        return "中"
    return "偏低"


def _optional_float(field: str) -> float | None:
    raw = request.form.get(field, "").strip()
    if not raw:
        return None
    return _parse_float(field, raw)


def _float(field: str, default: float) -> float:
    raw = request.form.get(field, "").strip()
    return default if not raw else _parse_float(field, raw)


def _parse_float(field: str, raw: str) -> float:
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{field} 必須是數字。") from error


def _integer(field: str, default: int) -> int:
    raw = request.form.get(field, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{field} 必須是整數。") from error


def main() -> None:
    port = int(os.environ.get("CHORD_SECTIONS_PORT", "8765"))
    url = f"http://127.0.0.1:{port}"
    print(f"Chord Sections 正在本機執行：{url}")
    print("停止服務請回到終端機按 Ctrl+C。")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
