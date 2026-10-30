import unittest

from chord_sections.music import key_root_pitch, transpose_chord, transpose_key
from chord_sections.pdf_report import _key_correction


class TranspositionTests(unittest.TestCase):
    def test_transposes_chords_and_preserves_quality(self) -> None:
        self.assertEqual(transpose_chord("C", 2), "D")
        self.assertEqual(transpose_chord("Am", 2), "Bm")
        self.assertEqual(transpose_chord("F#m", -2), "Em")
        self.assertEqual(transpose_chord("N.C.", 5), "N.C.")

    def test_capo_shape_is_transposed_down_from_sounding_chord(self) -> None:
        sounding_chord = transpose_chord("C", 2)

        self.assertEqual(sounding_chord, "D")
        self.assertEqual(transpose_chord(sounding_chord, -2), "C")

    def test_key_transposition_and_manual_original_key_correction(self) -> None:
        self.assertEqual(transpose_key("Am", 2), "Bm")
        self.assertEqual(key_root_pitch("F#m"), 6)
        self.assertEqual(_key_correction("E", "D"), -2)
        self.assertEqual(_key_correction("F#m", "Gm"), 1)


if __name__ == "__main__":
    unittest.main()
