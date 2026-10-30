from __future__ import annotations

import re

from chord_sections.analysis import NOTE_NAMES


_NOTE_TO_PITCH = {name: index for index, name in enumerate(NOTE_NAMES)}
_NOTE_TO_PITCH.update(
    {
        "Db": 1,
        "Eb": 3,
        "Gb": 6,
        "Ab": 8,
        "Bb": 10,
    }
)
_CHORD_PATTERN = re.compile(r"^([A-G])([#b]?)(.*)$")
_KEY_PATTERN = re.compile(r"^([A-G])([#b]?)(m?)$")


def transpose_note(note: str, semitones: int) -> str:
    pitch = _NOTE_TO_PITCH.get(note)
    if pitch is None:
        raise ValueError(f"Unsupported note name: {note}")
    return NOTE_NAMES[(pitch + semitones) % 12]


def transpose_chord(chord: str, semitones: int) -> str:
    if chord == "N.C." or semitones == 0:
        return chord
    match = _CHORD_PATTERN.fullmatch(chord)
    if match is None:
        return chord
    root = match.group(1) + match.group(2)
    return f"{transpose_note(root, semitones)}{match.group(3)}"


def transpose_key(key: str | None, semitones: int) -> str | None:
    if key is None:
        return None
    match = _KEY_PATTERN.fullmatch(key)
    if match is None:
        return key
    root = match.group(1) + match.group(2)
    return f"{transpose_note(root, semitones)}{match.group(3)}"


def key_root_pitch(key: str | None) -> int | None:
    if key is None:
        return None
    match = _KEY_PATTERN.fullmatch(key)
    if match is None:
        return None
    return _NOTE_TO_PITCH.get(match.group(1) + match.group(2))


def key_names() -> tuple[str, ...]:
    return tuple(
        key
        for root in NOTE_NAMES
        for key in (root, f"{root}m")
    )
