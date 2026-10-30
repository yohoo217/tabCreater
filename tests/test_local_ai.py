import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from chord_sections.local_ai import _collapse_repeated_phrase, _transcribe


class TranscriptionTests(unittest.TestCase):
    def test_transcription_does_not_voice_gate_song_edges(self) -> None:
        segment = types.SimpleNamespace(start=7.0, end=9.0, text=" first lyric ")
        model = Mock()
        model.transcribe.return_value = ([segment], object())
        whisper_module = types.ModuleType("faster_whisper")
        whisper_module.WhisperModel = Mock(return_value=model)

        with tempfile.TemporaryDirectory() as directory:
            audio_path = Path(directory) / "vocals.wav"
            audio_path.touch()
            with patch.dict(sys.modules, {"faster_whisper": whisper_module}):
                result = _transcribe(audio_path, "small", "en")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "first lyric")
        self.assertIs(model.transcribe.call_args.kwargs["vad_filter"], False)
        self.assertEqual(model.transcribe.call_args.kwargs["language"], "en")

    def test_collapses_extreme_repeated_whisper_phrase(self) -> None:
        repeated = "said you were made for me, " * 12

        self.assertEqual(
            _collapse_repeated_phrase(repeated).strip(),
            "said you were made for me, said you were made for me,",
        )

    def test_preserves_short_lyric_repetitions(self) -> None:
        lyric = "I love you, I love you, I love you."

        self.assertEqual(_collapse_repeated_phrase(lyric), lyric)


if __name__ == "__main__":
    unittest.main()
