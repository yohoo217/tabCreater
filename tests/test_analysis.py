import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import soundfile as sf

from chord_sections.analysis import (
    _classify_chroma,
    _load_audio,
    _make_chord_events,
    _make_sections,
    analyze_file,
    transpose_audio_file,
)


class ChordAnalysisTests(unittest.TestCase):
    def test_classifies_major_and_minor_triads(self) -> None:
        c_major = np.zeros(12)
        c_major[[0, 4, 7]] = (1.0, 0.75, 0.55)
        a_minor = np.zeros(12)
        a_minor[[9, 0, 4]] = (1.0, 0.75, 0.55)

        self.assertEqual(_classify_chroma(c_major)[0], "C")
        self.assertEqual(_classify_chroma(a_minor)[0], "Am")

    def test_silence_is_no_chord(self) -> None:
        self.assertEqual(_classify_chroma(np.zeros(12)), ("N.C.", 0.0))

    def test_confidence_score_is_heuristic_bounded_value(self) -> None:
        c_major = np.zeros(12)
        c_major[[0, 4, 7]] = (1.0, 0.75, 0.55)

        chord, confidence = _classify_chroma(c_major)

        self.assertEqual(chord, "C")
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_adjacent_identical_chords_merge(self) -> None:
        chroma = np.zeros((12, 4))
        chroma[[0, 4, 7], :] = np.array([[1.0], [0.75], [0.55]])
        events = _make_chord_events(chroma, sr=8, hop_length=1, duration=0.5, window_seconds=0.25)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].chord, "C")
        self.assertAlmostEqual(events[0].end, 0.5)

    def test_chord_events_follow_user_downbeat_offset(self) -> None:
        chroma = np.zeros((12, 8))
        chroma[[0, 4, 7], :2] = np.array([[1.0], [0.75], [0.55]])
        chroma[[5, 9, 0], 2:] = np.array([[1.0], [0.75], [0.55]])

        events = _make_chord_events(
            chroma,
            sr=8,
            hop_length=1,
            duration=1.0,
            window_seconds=0.5,
            offset_seconds=0.25,
        )

        self.assertAlmostEqual(events[0].start, 0.0)
        self.assertAlmostEqual(events[0].end, 0.25)
        self.assertAlmostEqual(events[1].start, 0.25)

    def test_repeated_harmonic_chunks_share_section_label(self) -> None:
        sr = 8
        hop_length = 1
        block = np.tile(np.array([[1.0], [0.5], [0.25]] + [[0.0]] * 9), (1, 4))
        chroma = np.concatenate((block, np.zeros((12, 4)), block), axis=1)
        events = ()

        sections = _make_sections(
            chroma,
            sr=1,
            hop_length=1,
            duration=12.0,
            section_seconds=4.0,
            similarity_threshold=0.88,
            events=events,
        )

        self.assertEqual([section.label for section in sections], ["A", "B", "A"])

    def test_section_does_not_extend_past_audio_duration(self) -> None:
        sections = _make_sections(
            np.zeros((12, 690)),
            sr=22050,
            hop_length=512,
            duration=16.0,
            section_seconds=4.0,
            similarity_threshold=0.88,
            events=(),
        )

        self.assertEqual(len(sections), 4)
        self.assertTrue(all(section.end > section.start for section in sections))
        self.assertEqual(sections[-1].end, 16.0)

    def test_audio_reader_falls_back_when_libsndfile_rejects_file(self) -> None:
        class FakeReader:
            channels = 1
            samplerate = 22050

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def __iter__(self):
                samples = np.array([16384, -16384], dtype="<i2")
                return iter((samples.tobytes(),))

        with (
            patch("chord_sections.analysis.librosa.load", side_effect=sf.LibsndfileError("unsupported format")),
            patch("chord_sections.analysis.audioread.audio_open", return_value=FakeReader()),
        ):
            audio, sr = _load_audio(Path("sample.mp3"), target_sr=22050)

        self.assertEqual(sr, 22050)
        np.testing.assert_allclose(audio, np.array([0.5, -0.5], dtype=np.float32))

    def test_analysis_uses_manual_tempo_and_time_signature(self) -> None:
        sample_rate = 22050
        time = np.arange(sample_rate * 2) / sample_rate
        audio = sum(
            np.sin(2 * np.pi * frequency * time)
            for frequency in (130.81, 164.81, 196.00)
        ).astype(np.float32) / 3
        with TemporaryDirectory() as directory:
            path = Path(directory) / "chord.wav"
            sf.write(path, audio, sample_rate)
            result = analyze_file(
                path,
                bpm=120,
                time_signature_numerator=3,
                time_signature_denominator=4,
                beats_per_chord=1,
                bars_per_section=2,
            )

        self.assertEqual(result.tempo_bpm, 120)
        self.assertEqual((result.time_signature_numerator, result.time_signature_denominator), (3, 4))
        self.assertEqual(result.chords[0].chord, "C")

    def test_pitch_shift_returns_wav_audio(self) -> None:
        sample_rate = 22050
        time = np.arange(sample_rate // 2) / sample_rate
        audio = np.sin(2 * np.pi * 440 * time).astype(np.float32)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            sf.write(path, audio, sample_rate)
            shifted = transpose_audio_file(path, 2)

        self.assertTrue(shifted.startswith(b"RIFF"))
        self.assertIn(b"WAVE", shifted[:16])


if __name__ == "__main__":
    unittest.main()
