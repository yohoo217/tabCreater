from __future__ import annotations

import csv
import json
from dataclasses import asdict
from io import StringIO

from chord_sections.analysis import AnalysisResult, ChordEvent, Section


def _format_time(seconds: float) -> str:
    total_tenths = max(0, round(seconds * 10))
    minutes, remaining_tenths = divmod(total_tenths, 600)
    seconds_part, tenths = divmod(remaining_tenths, 10)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}.{tenths}"
    return f"{minutes:02d}:{seconds_part:02d}.{tenths}"


def _chords_in_section(section: Section) -> str:
    result: list[str] = []
    for chord in section.chords:
        if not result or result[-1] != chord:
            result.append(chord)
    return " → ".join(result) if result else "N.C."


def render_markdown(result: AnalysisResult) -> str:
    lines = [
        "# 和弦與段落分析",
        "",
        f"- 音訊長度：{_format_time(result.duration)}",
        f"- 和弦事件：{len(result.chords)}",
        f"- 拍速：{f'{result.tempo_bpm:g} BPM' if result.tempo_bpm is not None else '未能估計'}",
        f"- 拍號：{result.time_signature_numerator}/{result.time_signature_denominator}",
        f"- 調性估計：{result.estimated_key or '未能估計'}",
        "- 注意：段落是依固定時間片段的和聲相似度分組；和弦為自動估計。",
        "- 信心指標是和弦模板符合度與候選差距的啟發式分數，不是校準機率或辨識準確率。",
        "",
        "## 段落",
        "",
        "| 段落 | 時間 | 和弦進行 |",
        "|---|---|---|",
    ]
    for section in result.sections:
        lines.append(
            f"| {section.label} | {_format_time(section.start)}–{_format_time(section.end)} "
            f"| {_chords_in_section(section)} |"
        )

    lines.extend(
        [
            "",
            "## 和弦時間軸",
            "",
            "| 開始 | 結束 | 和弦 | 信心指標 |",
            "|---|---|---|---:|",
        ]
    )
    for event in result.chords:
        lines.append(
            f"| {_format_time(event.start)} | {_format_time(event.end)} "
            f"| {event.chord} | {event.confidence:.0%} |"
        )
    return "\n".join(lines) + "\n"


def render_csv(result: AnalysisResult) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(("start_seconds", "end_seconds", "chord", "confidence", "section"))
    for event in result.chords:
        section_label = _section_for_event(event, result.sections)
        writer.writerow((f"{event.start:.3f}", f"{event.end:.3f}", event.chord, f"{event.confidence:.4f}", section_label))
    return output.getvalue()


def render_json(result: AnalysisResult) -> str:
    return json.dumps(
        {
            "duration_seconds": result.duration,
            "chords": [asdict(event) for event in result.chords],
            "sections": [asdict(section) for section in result.sections],
            "notes": [
                "Chord labels are estimates for major/minor triads.",
                "Sections group fixed-length chunks by harmonic similarity; they are not semantic verse/chorus labels.",
            ],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _section_for_event(event: ChordEvent, sections: tuple[Section, ...]) -> str:
    for section in sections:
        if event.start >= section.start and event.start < section.end:
            return section.label
    return ""
