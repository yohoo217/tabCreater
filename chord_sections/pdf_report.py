from __future__ import annotations

from io import BytesIO
from typing import Callable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from chord_sections.analysis import AnalysisResult, Section
from chord_sections.lyrics import LyricLine
from chord_sections.music import key_root_pitch, transpose_chord, transpose_key
from chord_sections.report import _format_time


FONT_NAME = "MSung-Light"


def _register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def render_pdf(
    result: AnalysisResult,
    title: str,
    *,
    semitones: int = 0,
    capo_fret: int = 0,
    original_key: str | None = None,
    lyrics: tuple[LyricLine, ...] = (),
    language: str = "zh",
) -> bytes:
    if language not in {"zh", "en"}:
        raise ValueError("language must be 'zh' or 'en'.")
    _register_font()
    correction = _key_correction(result.estimated_key, original_key)
    effective_original_key = original_key or result.estimated_key
    target_key = transpose_key(effective_original_key, semitones)

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=46,
        bottomMargin=44,
        title=title,
        author="Chord Sections",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CJKTitle",
            parent=styles["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#183b35"),
            alignment=TA_LEFT,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LyricSheetCell",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#364641"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKHeading",
            parent=styles["Heading2"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#183b35"),
            spaceBefore=12,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKBody",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#364641"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKSmall",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#53645f"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ChordCell",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderCJK",
            parent=styles["BodyText"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
    )

    bpm = f"{result.tempo_bpm:g} BPM" if result.tempo_bpm is not None else _text(language, "unknown")
    key = effective_original_key or _text(language, "unknown")
    target_key_label = target_key or _text(language, "unknown")
    capo_label = f"Capo {capo_fret}" if capo_fret else _text(language, "no_capo")
    transposition_label = f"{semitones:+d} {_text(language, 'semitones')}" if semitones else _text(language, "original_key")
    story = [
        Paragraph(_escape(title), styles["CJKTitle"]),
        Paragraph(
            f"{_text(language, 'duration')}：{_format_time(result.duration)}　｜　"
            f"{_text(language, 'tempo')}：{bpm}　｜　"
            f"{_text(language, 'meter')}：{result.time_signature_numerator}/{result.time_signature_denominator}　｜　"
            f"{_text(language, 'original_key')}：{key}　｜　"
            f"{_text(language, 'target_key')}：{target_key_label}",
            styles["CJKBody"],
        ),
        Paragraph(
            f"{_text(language, 'transposition')}：{transposition_label}　｜　"
            f"{capo_label}（{_text(language, 'fingering_note')}）",
            styles["CJKBody"],
        ),
        Spacer(1, 8),
    ]

    def transform(chord: str) -> str:
        return transpose_chord(chord, correction + semitones)

    def fingering(chord: str) -> str:
        return transpose_chord(transform(chord), -capo_fret)

    def section_progression(section: Section) -> str:
        chords: list[str] = []
        for chord in section.chords:
            transformed = transform(chord)
            if not chords or chords[-1] != transformed:
                chords.append(transformed)
        return " → ".join(chords) or "N.C."

    if lyrics:
        story.append(Paragraph(_text(language, "lyrics_chords"), styles["CJKHeading"]))
        story.append(
            Paragraph(
                _text(language, "lyrics_chords_note"),
                styles["CJKSmall"],
            )
        )
        story.append(Spacer(1, 6))
        lyric_rows: list[list[object]] = [
            [
                Paragraph(_text(language, "time"), styles["TableHeaderCJK"]),
                Paragraph(_text(language, "lyrics_and_chords"), styles["TableHeaderCJK"]),
            ]
        ]
        for line in lyrics:
            line_chords = _chords_for_lyrics(line, result, transform) or _text(language, "no_chord")
            lyric_rows.append(
                [
                    f"{_format_time(line.start)} – {_format_time(line.end)}",
                    Paragraph(
                        f'<font color="#2a6856"><b>{_escape(line_chords)}</b></font><br/>'
                        f"{_escape(line.text)}",
                        styles["LyricSheetCell"],
                    ),
                ]
            )
        lyric_table = LongTable(lyric_rows, colWidths=(80, 430), repeatRows=1)
        lyric_table.setStyle(_table_style())
        story.append(lyric_table)
    if result.sections:
        story.extend(
            [
                Paragraph(_text(language, "section_summary"), styles["CJKHeading"]),
            ]
        )
        section_rows: list[list[object]] = [
            [
                Paragraph(_text(language, "section"), styles["TableHeaderCJK"]),
                Paragraph(_text(language, "time"), styles["TableHeaderCJK"]),
                Paragraph(_text(language, "chord_progression"), styles["TableHeaderCJK"]),
            ]
        ]
        for section in result.sections:
            section_rows.append(
                [
                    section.label,
                    f"{_format_time(section.start)} – {_format_time(section.end)}",
                    Paragraph(_escape(section_progression(section)), styles["ChordCell"]),
                ]
            )
        sections_table = Table(section_rows, colWidths=(48, 132, 330), repeatRows=1)
        sections_table.setStyle(_table_style())
        story.append(sections_table)
    story.extend(
        [
            Paragraph(_text(language, "chord_timeline"), styles["CJKHeading"]),
            Paragraph(
                _text(language, "confidence_note"),
                styles["CJKSmall"],
            ),
            Spacer(1, 6),
        ]
    )

    chord_rows: list[list[object]] = [
        [
            Paragraph(_text(language, "start"), styles["TableHeaderCJK"]),
            Paragraph(_text(language, "end"), styles["TableHeaderCJK"]),
            Paragraph(_text(language, "original_chord"), styles["TableHeaderCJK"]),
            Paragraph(_text(language, "transposed"), styles["TableHeaderCJK"]),
            Paragraph(
                f"Capo {capo_fret} {_text(language, 'shape')}" if capo_fret else _text(language, "shape"),
                styles["TableHeaderCJK"],
            ),
            Paragraph(_text(language, "confidence"), styles["TableHeaderCJK"]),
            Paragraph(_text(language, "section"), styles["TableHeaderCJK"]),
        ]
    ]
    for event in result.chords:
        chord_rows.append(
            [
                _format_time(event.start),
                _format_time(event.end),
                event.chord,
                transform(event.chord),
                fingering(event.chord),
                f"{event.confidence:.0%}",
                _section_label(event.start, result.sections),
            ]
        )
    chord_table = LongTable(chord_rows, colWidths=(61, 61, 57, 57, 70, 72, 45), repeatRows=1)
    chord_table.setStyle(_table_style())
    story.append(chord_table)

    document.build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    return output.getvalue()


def _chords_for_lyrics(
    line: LyricLine,
    result: AnalysisResult,
    transform: Callable[[str], str],
) -> str:
    chords = [
        transform(event.chord)
        for event in result.chords
        if event.end > line.start and event.start < line.end
    ]
    distinct: list[str] = []
    for chord in chords:
        if not distinct or distinct[-1] != chord:
            distinct.append(chord)
    return " → ".join(distinct) or "N.C."


def _text(language: str, key: str) -> str:
    labels = {
        "zh": {
            "unknown": "未能估計",
            "no_capo": "無 capo",
            "semitones": "半音",
            "original_key": "原調",
            "duration": "長度",
            "tempo": "拍速",
            "meter": "拍號",
            "target_key": "目標調",
            "transposition": "移調",
            "fingering_note": "指法欄為移調後的實際按法",
            "section_summary": "段落摘要",
            "section": "段落",
            "time": "時間",
            "chord_progression": "和弦進行",
            "lyrics_chords": "歌詞與和弦對齊",
            "chords": "和弦",
            "lyrics": "歌詞",
            "lyrics_and_chords": "和弦與歌詞",
            "lyrics_chords_note": "和弦列在歌詞上方；請搭配音訊確認自動估計結果。",
            "chord_timeline": "和弦時間軸",
            "confidence_note": "信心指標是啟發式分數，不是校準機率或辨識準確率。低分的和弦建議回聽確認。",
            "start": "開始",
            "end": "結束",
            "original_chord": "原曲和弦",
            "transposed": "移調後",
            "shape": "指法",
            "confidence": "信心指標",
        },
        "en": {
            "unknown": "Unavailable",
            "no_capo": "No capo",
            "semitones": "semitones",
            "original_key": "Original key",
            "duration": "Duration",
            "tempo": "Tempo",
            "meter": "Time signature",
            "target_key": "Target key",
            "transposition": "Transposition",
            "fingering_note": "Fingering shows the shapes to play",
            "section_summary": "Section summary",
            "section": "Section",
            "time": "Time",
            "chord_progression": "Chord progression",
            "lyrics_chords": "Lyrics & chords",
            "chords": "Chords",
            "lyrics": "Lyrics",
            "lyrics_and_chords": "Chords & lyrics",
            "lyrics_chords_note": "Chords are shown above each lyric line. Review the estimates while listening.",
            "chord_timeline": "Chord timeline",
            "confidence_note": "Confidence is a heuristic score, not a calibrated probability or recognition accuracy. Review low-confidence chords by listening.",
            "start": "Start",
            "end": "End",
            "original_chord": "Original chord",
            "transposed": "Transposed",
            "shape": "shape",
            "confidence": "Confidence",
        },
    }
    return labels[language][key]


def _key_correction(estimated_key: str | None, selected_key: str | None) -> int:
    if selected_key is None:
        return 0
    estimated_root = key_root_pitch(estimated_key)
    selected_root = key_root_pitch(selected_key)
    if estimated_root is None or selected_root is None:
        return 0
    correction = (selected_root - estimated_root) % 12
    return correction - 12 if correction > 6 else correction


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183b35")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 11),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#f2f6f3"))),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#183b35")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#e2e9e5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _section_label(start: float, sections: tuple[Section, ...]) -> str:
    for section in sections:
        if section.start <= start < section.end:
            return section.label
    return ""


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _draw_page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#71807a"))
    canvas.drawRightString(A4[0] - 42, 24, f"{document.page}")
    canvas.restoreState()
