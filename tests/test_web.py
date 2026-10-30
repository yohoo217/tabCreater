import io
import unittest
from unittest.mock import patch

from chord_sections.analysis import AnalysisResult, ChordEvent, Section
from chord_sections.lyrics import LyricLine
from chord_sections.web import _saved_analyses, _saved_analyses_lock, app


class WebInterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        with _saved_analyses_lock:
            _saved_analyses.clear()

    def test_homepage_serves_local_interface(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("和弦整理室".encode(), response.data)
        self.assertIn(b'id="language-toggle"', response.data)
        self.assertIn(b'data-i18n="hero_title"', response.data)
        self.assertIn(b'data-i18n="lyrics_title"', response.data)
        self.assertIn(b'data-i18n="conversion_help"', response.data)
        self.assertIn(b"v0.2.0", response.data)
        self.assertIn(b"issues/new?template=feedback.yml", response.data)
        self.assertIn('data-i18n="analyze_song">轉換歌曲'.encode(), response.data)
        self.assertIn(b'id="lyrics-settings"', response.data)
        self.assertIn(b'id="analysis-details"', response.data)
        self.assertNotIn(b'id="bpm"', response.data)
        self.assertNotIn(b'id="time-signature"', response.data)

    def test_rejects_unsupported_audio_format(self) -> None:
        response = self.client.post(
            "/api/analyze",
            data={"audio": (io.BytesIO(b"audio"), "song.xyz")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不支援", response.get_json()["error"])

    def test_analyze_and_download_pdf(self) -> None:
        result = AnalysisResult(
            duration=8.0,
            chords=(ChordEvent(0.0, 4.0, "C", 0.8),),
            sections=(Section("A", 0.0, 8.0, ("C",)),),
            tempo_bpm=120,
            time_signature_numerator=3,
            estimated_key="C",
        )
        with patch("chord_sections.web.analyze_file", return_value=result) as analyze:
            response = self.client.post(
                "/api/analyze",
                data={
                    "title": "測試歌曲",
                    "time_signature_numerator": "3",
                    "time_signature_denominator": "4",
                    "beats_per_chord": "2",
                    "bars_per_section": "4",
                    "downbeat_offset_seconds": "0",
                    "harmonic_focus": "on",
                    "chroma_method": "cqt",
                    "audio": (io.BytesIO(b"audio"), "song.wav"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["time_signature"], "3/4")
        self.assertEqual(analyze.call_args.kwargs["time_signature_numerator"], 3)
        self.assertEqual(analyze.call_args.kwargs["chroma_method"], "cqt")
        pdf = self.client.get(f"/api/report/{response.get_json()['report_id']}.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.mimetype, "application/pdf")
        self.assertTrue(pdf.data.startswith(b"%PDF-"))
        english_pdf = self.client.get(
            f"/api/report/{response.get_json()['report_id']}.pdf?lang=en"
        )
        self.assertEqual(english_pdf.status_code, 200)
        self.assertTrue(english_pdf.data.startswith(b"%PDF-"))
        transposed_pdf = self.client.get(
            f"/api/report/{response.get_json()['report_id']}.pdf?semitones=2&capo=2&original_key=G"
        )
        self.assertEqual(transposed_pdf.status_code, 200)
        self.assertTrue(transposed_pdf.data.startswith(b"%PDF-"))
        self.assertIn("capo2", transposed_pdf.headers["Content-Disposition"])

    def test_convert_separates_then_transcribes_then_analyzes_instrumental(self) -> None:
        result = AnalysisResult(
            duration=8.0,
            chords=(ChordEvent(0.0, 8.0, "C", 0.8),),
            sections=(Section("A", 0.0, 8.0, ("C",)),),
            tempo_bpm=120,
            estimated_key="C",
        )
        recognized = (LyricLine(0.5, 2.5, "歌詞"),)
        calls: list[str] = []

        def separate(audio_path, output_directory):
            calls.append("separate")
            return output_directory / "vocals.wav", output_directory / "no_vocals.wav"

        def transcribe(audio_path, *, model_size, language):
            calls.append("transcribe")
            self.assertEqual(audio_path.name, "vocals.wav")
            self.assertEqual(model_size, "base")
            self.assertEqual(language, "zh")
            return recognized

        def analyze(audio_path, **kwargs):
            calls.append("analyze")
            self.assertEqual(audio_path.name, "no_vocals.wav")
            self.assertEqual(kwargs["chroma_method"], "cqt")
            return result

        with (
            patch(
                "chord_sections.web.available_engines",
                return_value={"demucs": True, "faster_whisper": True},
            ),
            patch("chord_sections.web.separate_stems", side_effect=separate),
            patch("chord_sections.web.transcribe_audio", side_effect=transcribe),
            patch("chord_sections.web.analyze_file", side_effect=analyze),
        ):
            response = self.client.post(
                "/api/convert",
                data={
                    "language": "zh",
                    "model_size": "base",
                    "chroma_method": "cqt",
                    "audio": (io.BytesIO(b"audio"), "song.wav"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["separate", "transcribe", "analyze"])
        payload = response.get_json()
        self.assertEqual(payload["lyrics"][0]["text"], "歌詞")
        self.assertEqual(payload["tempo_bpm"], 120)
        self.assertIsNone(payload["time_signature"])
        with patch("chord_sections.web.render_pdf", return_value=b"%PDF-test") as render:
            pdf_response = self.client.get(
                f"/api/report/{payload['report_id']}.pdf?format=sheet"
            )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(render.call_args.kwargs["lyrics"], recognized)
        self.assertTrue(render.call_args.kwargs["song_sheet"])

    def test_convert_requires_local_separation_and_transcription_models(self) -> None:
        with patch(
            "chord_sections.web.available_engines",
            return_value={"demucs": False, "faster_whisper": True},
        ):
            response = self.client.post(
                "/api/convert",
                data={"audio": (io.BytesIO(b"audio"), "song.wav")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("人聲分離", response.get_json()["error"])

    def test_rejects_out_of_range_transposition_and_capo(self) -> None:
        result = AnalysisResult(duration=1.0, chords=(), sections=(), estimated_key="C")
        with patch("chord_sections.web.analyze_file", return_value=result):
            response = self.client.post(
                "/api/analyze",
                data={"audio": (io.BytesIO(b"audio"), "song.wav")},
                content_type="multipart/form-data",
            )
        report_id = response.get_json()["report_id"]

        self.assertEqual(
            self.client.get(f"/api/report/{report_id}.pdf?semitones=13").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(f"/api/report/{report_id}.pdf?capo=12").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(f"/api/report/{report_id}.pdf?lang=fr").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(f"/api/report/{report_id}.pdf?format=unknown").status_code,
            400,
        )

    def test_pdf_download_selects_simple_sheet_or_full_report(self) -> None:
        result = AnalysisResult(
            duration=8.0,
            chords=(ChordEvent(0.0, 8.0, "C", 0.8),),
            sections=(Section("A", 0.0, 8.0, ("C",)),),
        )
        with patch("chord_sections.web.analyze_file", return_value=result):
            analyzed = self.client.post(
                "/api/analyze",
                data={"audio": (io.BytesIO(b"audio"), "song.wav")},
                content_type="multipart/form-data",
            )
        report_id = analyzed.get_json()["report_id"]
        report_url = f"/api/report/{report_id}.pdf"

        with patch("chord_sections.web.render_pdf", return_value=b"%PDF-sheet") as render:
            sheet = self.client.get(f"{report_url}?format=sheet")
            self.assertTrue(render.call_args.kwargs["song_sheet"])
            self.assertIn("song-sheet.pdf", sheet.headers["Content-Disposition"])

            full = self.client.get(f"{report_url}?format=full")
            self.assertFalse(render.call_args.kwargs["song_sheet"])
            self.assertIn("-chords.pdf", full.headers["Content-Disposition"])

    def test_transposed_audio_download_returns_wav(self) -> None:
        with patch("chord_sections.web.transpose_audio_file", return_value=b"RIFFxxxxWAVE") as shift:
            response = self.client.post(
                "/api/transpose-audio",
                data={
                    "semitones": "2",
                    "audio": (io.BytesIO(b"audio"), "song.mp3"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/wav")
        self.assertIn("song-+2st.wav", response.headers["Content-Disposition"])
        self.assertEqual(shift.call_args.args[1], 2)

    def test_rejects_invalid_audio_transposition(self) -> None:
        response = self.client.post(
            "/api/transpose-audio",
            data={
                "semitones": "13",
                "audio": (io.BytesIO(b"audio"), "song.wav"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)

    def test_ai_status_reports_installed_engines(self) -> None:
        with patch(
            "chord_sections.web.available_engines",
            return_value={"demucs": True, "faster_whisper": False},
        ):
            response = self.client.get("/api/ai-status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["engines"],
            {"demucs": True, "faster_whisper": False},
        )

    def test_transcribe_save_lyrics_and_include_them_in_pdf(self) -> None:
        result = AnalysisResult(
            duration=8.0,
            chords=(ChordEvent(0.0, 4.0, "C", 0.8),),
            sections=(Section("A", 0.0, 8.0, ("C",)),),
            estimated_key="C",
        )
        with patch("chord_sections.web.analyze_file", return_value=result):
            analyzed = self.client.post(
                "/api/analyze",
                data={"audio": (io.BytesIO(b"audio"), "song.wav")},
                content_type="multipart/form-data",
            )
        report_id = analyzed.get_json()["report_id"]
        recognized = (LyricLine(0.5, 2.5, "hello song"),)
        with patch("chord_sections.web.transcribe_song", return_value=recognized) as transcribe:
            response = self.client.post(
                "/api/transcribe",
                data={
                    "report_id": report_id,
                    "language": "en",
                    "model_size": "base",
                    "audio": (io.BytesIO(b"audio"), "song.wav"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["lyrics"][0]["text"], "hello song")
        self.assertEqual(transcribe.call_args.kwargs["language"], "en")
        self.assertFalse(transcribe.call_args.kwargs["separate_vocals"])

        saved = self.client.put(
            f"/api/lyrics/{report_id}",
            json={"lyrics": [{"start": 0.5, "end": 2.5, "text": "corrected lyrics"}]},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_json()["saved"], 1)

        with patch("chord_sections.web.render_pdf", return_value=b"%PDF-test") as render:
            pdf = self.client.get(f"/api/report/{report_id}.pdf")

        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(render.call_args.kwargs["lyrics"], (LyricLine(0.5, 2.5, "corrected lyrics"),))

    def test_rejects_invalid_lyrics(self) -> None:
        result = AnalysisResult(duration=8.0, chords=(), sections=())
        with patch("chord_sections.web.analyze_file", return_value=result):
            analyzed = self.client.post(
                "/api/analyze",
                data={"audio": (io.BytesIO(b"audio"), "song.wav")},
                content_type="multipart/form-data",
            )
        report_id = analyzed.get_json()["report_id"]

        response = self.client.put(
            f"/api/lyrics/{report_id}",
            json={"lyrics": [{"start": 7.0, "end": 9.0, "text": "outside song"}]},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
