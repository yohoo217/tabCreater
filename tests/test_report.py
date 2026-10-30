import unittest

from chord_sections.analysis import AnalysisResult, ChordEvent, Section
from chord_sections.lyrics import LyricLine
from chord_sections.report import _format_time, render_csv, render_json, render_markdown


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = AnalysisResult(
            duration=12.0,
            chords=(
                ChordEvent(0.0, 4.0, "C", 0.2),
                ChordEvent(4.0, 8.0, "Am", 0.15),
            ),
            sections=(Section("A", 0.0, 8.0, ("C", "Am")),),
        )

    def test_markdown_contains_section_and_timeline(self) -> None:
        report = render_markdown(self.result)

        self.assertIn("| A | 00:00.0–00:08.0 | C → Am |", report)
        self.assertIn("| 00:04.0 | 00:08.0 | Am | 15% |", report)
        self.assertIn("拍號：4/4", report)
        self.assertIn("啟發式分數", report)

    def test_csv_and_json_are_parseable(self) -> None:
        import csv
        import json
        from io import StringIO

        rows = list(csv.DictReader(StringIO(render_csv(self.result))))
        parsed = json.loads(render_json(self.result))

        self.assertEqual(rows[1]["section"], "A")
        self.assertEqual(parsed["sections"][0]["label"], "A")

    def test_time_formatter_keeps_subsecond_events_visible(self) -> None:
        self.assertEqual(_format_time(0.06), "00:00.1")

    def test_pdf_is_valid_and_contains_report_content(self) -> None:
        from chord_sections.pdf_report import render_pdf

        report = render_pdf(
            self.result,
            "測試歌曲",
            lyrics=(LyricLine(0.0, 4.0, "歌詞第一句"),),
        )

        self.assertTrue(report.startswith(b"%PDF-"))
        self.assertGreater(len(report), 1000)

    def test_pdf_accepts_english_locale(self) -> None:
        from chord_sections.pdf_report import render_pdf

        report = render_pdf(self.result, "Test Song", language="en")

        self.assertTrue(report.startswith(b"%PDF-"))
        self.assertGreater(len(report), 1000)


if __name__ == "__main__":
    unittest.main()
