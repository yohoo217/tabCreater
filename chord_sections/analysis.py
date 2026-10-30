from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import audioread
import librosa
import numpy as np
import soundfile as sf


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


@dataclass(frozen=True)
class ChordEvent:
    start: float
    end: float
    chord: str
    confidence: float


@dataclass(frozen=True)
class Section:
    label: str
    start: float
    end: float
    chords: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    duration: float
    chords: tuple[ChordEvent, ...]
    sections: tuple[Section, ...]
    tempo_bpm: float | None = None
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
    estimated_key: str | None = None


def _chord_templates() -> tuple[tuple[str, np.ndarray], ...]:
    templates: list[tuple[str, np.ndarray]] = []
    for root, name in enumerate(NOTE_NAMES):
        for quality, intervals in (("", (0, 4, 7)), ("m", (0, 3, 7))):
            template = np.zeros(12, dtype=np.float64)
            template[(root + np.asarray(intervals)) % 12] = (1.0, 0.75, 0.55)
            template /= np.linalg.norm(template)
            templates.append((f"{name}{quality}", template))
    return tuple(templates)


CHORD_TEMPLATES = _chord_templates()


def _load_audio(path: Path, target_sr: int) -> tuple[np.ndarray, int]:
    try:
        audio, sr = librosa.load(path, sr=target_sr, mono=True)
        return audio, int(sr)
    except sf.LibsndfileError:
        try:
            with audioread.audio_open(str(path)) as source:
                chunks = [np.frombuffer(chunk, dtype="<i2") for chunk in source]
                if not chunks:
                    return np.empty(0, dtype=np.float32), target_sr
                samples = np.concatenate(chunks)
                if samples.size % source.channels:
                    raise ValueError(f"Audio decoder returned incomplete samples: {path}")
                audio = samples.reshape(-1, source.channels).T.astype(np.float32) / 32768.0
                audio = librosa.to_mono(audio)
                source_sr = source.samplerate
        except (audioread.DecodeError, audioread.NoBackendError) as error:
            raise ValueError(
                f"Could not decode audio file: {path}. Install a compatible decoder such as FFmpeg."
            ) from error

        if source_sr != target_sr:
            audio = librosa.resample(audio, orig_sr=source_sr, target_sr=target_sr)
        return np.asarray(audio, dtype=np.float32), target_sr


def transpose_audio_file(path: str | Path, semitones: int) -> bytes:
    """Pitch-shift an audio file and return the decoded result as PCM WAV bytes."""
    if not -12 <= semitones <= 12:
        raise ValueError("semitones must be between -12 and 12")

    audio_path = Path(path)
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    sr = 22050
    audio, _ = _load_audio(audio_path, sr)
    if audio.size == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")
    shifted = librosa.effects.pitch_shift(y=audio, sr=sr, n_steps=semitones)

    output = BytesIO()
    sf.write(output, shifted, sr, format="WAV", subtype="PCM_16")
    return output.getvalue()


def _classify_chroma(chroma: np.ndarray) -> tuple[str, float]:
    magnitude = float(np.linalg.norm(chroma))
    if magnitude <= np.finfo(np.float64).eps:
        return "N.C.", 0.0

    normalized = chroma / magnitude
    scores = np.asarray([np.dot(normalized, template) for _, template in CHORD_TEMPLATES])
    best_index = int(np.argmax(scores))
    best_score = float(scores[best_index])
    scores[best_index] = -np.inf
    second_score = float(np.max(scores))
    margin = max(0.0, best_score - second_score)
    if best_score < 0.2:
        return "N.C.", 0.0
    fit = float(np.clip((best_score - 0.2) / 0.75, 0.0, 1.0))
    separation = float(
        np.clip((margin / max(1.0 - second_score, np.finfo(np.float64).eps)) / 0.2, 0.0, 1.0)
    )
    confidence = 0.65 * fit + 0.35 * separation
    return CHORD_TEMPLATES[best_index][0], confidence


def _make_chord_events(
    chroma: np.ndarray,
    sr: int,
    hop_length: int,
    duration: float,
    window_seconds: float,
    offset_seconds: float = 0.0,
) -> tuple[ChordEvent, ...]:
    frames_per_window = max(1, round(window_seconds * sr / hop_length))
    events: list[ChordEvent] = []
    frame_count = chroma.shape[1]

    window = frames_per_window * hop_length / sr
    boundaries = [0.0]
    boundary = offset_seconds
    while boundary > 0.0 and boundary < duration:
        boundaries.append(boundary)
        boundary += window
    if offset_seconds == 0.0:
        boundary = window
    while boundary < duration:
        boundaries.append(boundary)
        boundary += window
    boundaries.append(duration)

    for start, end in zip(boundaries, boundaries[1:]):
        first_frame = max(0, int(start * sr / hop_length))
        last_frame = min(frame_count, max(first_frame + 1, int(np.ceil(end * sr / hop_length))))
        if end <= start:
            continue
        chroma_slice = chroma[:, first_frame:last_frame]
        if chroma_slice.shape[1] == 0:
            continue
        chord, confidence = _classify_chroma(np.mean(chroma_slice, axis=1))
        if events and events[-1].chord == chord:
            previous = events[-1]
            previous_duration = previous.end - previous.start
            current_duration = end - start
            average_confidence = (
                previous.confidence * previous_duration + confidence * current_duration
            ) / (previous_duration + current_duration)
            events[-1] = ChordEvent(previous.start, end, chord, average_confidence)
        else:
            events.append(ChordEvent(start, end, chord, confidence))

    return tuple(events)


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator <= np.finfo(np.float64).eps:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _estimate_key(chroma: np.ndarray) -> str | None:
    major_profile = np.asarray((6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88))
    minor_profile = np.asarray((6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17))
    profile = np.mean(chroma, axis=1)
    if float(np.linalg.norm(profile)) <= np.finfo(np.float64).eps:
        return None

    profile = (profile - np.mean(profile)) / max(float(np.std(profile)), np.finfo(np.float64).eps)
    candidates: list[tuple[float, str]] = []
    for tonic, note in enumerate(NOTE_NAMES):
        for quality, template in (("", major_profile), ("m", minor_profile)):
            shifted = np.roll(template, tonic)
            shifted = (shifted - np.mean(shifted)) / np.std(shifted)
            candidates.append((float(np.dot(profile, shifted)), f"{note}{quality}"))
    return max(candidates)[1]


def _estimate_tempo(audio: np.ndarray, sr: int, hop_length: int) -> float | None:
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr, hop_length=hop_length, units="time")
    value = float(np.asarray(tempo).reshape(-1)[0])
    return round(value, 1) if 30.0 <= value <= 300.0 else None


def _make_sections(
    chroma: np.ndarray,
    sr: int,
    hop_length: int,
    duration: float,
    section_seconds: float,
    similarity_threshold: float,
    events: tuple[ChordEvent, ...],
) -> tuple[Section, ...]:
    frames_per_section = max(1, round(section_seconds * sr / hop_length))
    fingerprints: list[np.ndarray] = []
    boundaries: list[tuple[float, float]] = []

    for first_frame in range(0, chroma.shape[1], frames_per_section):
        last_frame = min(chroma.shape[1], first_frame + frames_per_section)
        start = first_frame * hop_length / sr
        end = min(duration, last_frame * hop_length / sr)
        if end <= start:
            continue
        if first_frame and last_frame - first_frame < max(2, round(frames_per_section * 0.1)):
            continue
        block = chroma[:, first_frame:last_frame]
        # Retain temporal order so sections with the same average harmony but
        # different chord order are less likely to be grouped together.
        subdivisions = np.array_split(block, 4, axis=1)
        fingerprint = np.concatenate(
            [np.mean(part, axis=1) if part.shape[1] else np.zeros(chroma.shape[0]) for part in subdivisions]
        )
        fingerprints.append(fingerprint)
        boundaries.append((start, end))

    labels: list[str] = []
    representative_fingerprints: list[np.ndarray] = []
    representative_lengths: list[float] = []
    for fingerprint, (start, end) in zip(fingerprints, boundaries, strict=True):
        block_length = end - start
        matched_label: str | None = None
        for index, representative in enumerate(representative_fingerprints):
            if abs(block_length - representative_lengths[index]) > section_seconds * 0.2:
                continue
            if _cosine_similarity(fingerprint, representative) >= similarity_threshold:
                matched_label = chr(ord("A") + index) if index < 26 else f"S{index + 1}"
                break
        if matched_label is None:
            index = len(representative_fingerprints)
            representative_fingerprints.append(fingerprint)
            representative_lengths.append(block_length)
            matched_label = chr(ord("A") + index) if index < 26 else f"S{index + 1}"
        labels.append(matched_label)

    sections: list[Section] = []
    for label, (start, end) in zip(labels, boundaries, strict=True):
        contained_chords = tuple(
            event.chord
            for event in events
            if event.end > start and event.start < end
        )
        if sections and sections[-1].label == label:
            previous = sections[-1]
            sections[-1] = Section(
                previous.label,
                previous.start,
                end,
                previous.chords + contained_chords,
            )
        else:
            sections.append(Section(label, start, end, contained_chords))
    if sections and duration - sections[-1].end <= section_seconds * 0.1:
        last_section = sections[-1]
        sections[-1] = Section(last_section.label, last_section.start, duration, last_section.chords)
    return tuple(sections)


def analyze_file(
    path: str | Path,
    *,
    window_seconds: float = 1.0,
    section_seconds: float = 8.0,
    similarity_threshold: float = 0.88,
    bpm: float | None = None,
    time_signature_numerator: int = 4,
    time_signature_denominator: int = 4,
    beats_per_chord: float | None = None,
    bars_per_section: float | None = None,
    downbeat_offset_seconds: float = 0.0,
    harmonic_focus: bool = True,
    chroma_method: str = "stft",
) -> AnalysisResult:
    """Estimate chord events and repeated harmonic sections from an audio file."""
    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than zero")
    if section_seconds <= 0:
        raise ValueError("section_seconds must be greater than zero")
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1")
    if bpm is not None and not 30.0 <= bpm <= 300.0:
        raise ValueError("bpm must be between 30 and 300")
    if not 1 <= time_signature_numerator <= 16:
        raise ValueError("time signature numerator must be between 1 and 16")
    if time_signature_denominator not in (2, 4, 8, 16):
        raise ValueError("time signature denominator must be 2, 4, 8, or 16")
    if beats_per_chord is not None and not 0.25 <= beats_per_chord <= 16:
        raise ValueError("beats_per_chord must be between 0.25 and 16")
    if bars_per_section is not None and not 1 <= bars_per_section <= 32:
        raise ValueError("bars_per_section must be between 1 and 32")
    if downbeat_offset_seconds < 0:
        raise ValueError("downbeat_offset_seconds must be zero or greater")
    if chroma_method not in {"stft", "cqt"}:
        raise ValueError("chroma_method must be 'stft' or 'cqt'")

    audio_path = Path(path)
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    sr = 22050
    hop_length = 512
    audio, _ = _load_audio(audio_path, sr)
    if audio.size == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

    duration = float(audio.size / sr)
    if downbeat_offset_seconds >= duration:
        raise ValueError("downbeat_offset_seconds must be shorter than the audio duration")

    analysis_audio = librosa.effects.harmonic(audio) if harmonic_focus else audio
    if chroma_method == "cqt":
        chroma = librosa.feature.chroma_cqt(
            y=analysis_audio,
            sr=sr,
            hop_length=hop_length,
        )
    else:
        chroma = librosa.feature.chroma_stft(
            y=analysis_audio,
            sr=sr,
            n_fft=4096,
            hop_length=hop_length,
        )
    detected_tempo = _estimate_tempo(analysis_audio, sr, hop_length) if bpm is None else None
    selected_tempo = bpm if bpm is not None else detected_tempo
    if selected_tempo is not None and beats_per_chord is not None:
        window_seconds = beats_per_chord * 60.0 / selected_tempo * 4.0 / time_signature_denominator
    if selected_tempo is not None and bars_per_section is not None:
        section_seconds = (
            bars_per_section
            * time_signature_numerator
            * 60.0
            / selected_tempo
            * 4.0
            / time_signature_denominator
        )
    chords = _make_chord_events(
        chroma,
        sr,
        hop_length,
        duration,
        window_seconds,
        downbeat_offset_seconds,
    )
    sections = _make_sections(
        chroma,
        sr,
        hop_length,
        duration,
        section_seconds,
        similarity_threshold,
        chords,
    )
    return AnalysisResult(
        duration,
        chords,
        sections,
        selected_tempo,
        time_signature_numerator,
        time_signature_denominator,
        _estimate_key(chroma),
    )
