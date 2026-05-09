from __future__ import annotations

import csv
import struct
from pathlib import Path
from typing import Iterable

from .data import Event


def _require_music21():
    try:
        import music21  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "MIDI conversion requires music21. Install it with: pip install music21"
        ) from exc
    return music21


def load_melody_events_from_midi(
    midi_path: str | Path,
    *,
    source: str,
    genre: str,
    split: str,
    is_ai: bool = False,
    boundary_mode: str = "measure",
) -> list[Event]:
    """Convert one MIDI file into normalized melody events.

    Major keys are transposed to C major and minor keys to A minor. The melody part is
    selected as the part with the highest average MIDI pitch.
    """

    music21 = _require_music21()
    path = Path(midi_path)
    score = music21.converter.parse(path)
    key = score.analyze("key")
    target = music21.pitch.Pitch("A") if key.mode == "minor" else music21.pitch.Pitch("C")
    interval = music21.interval.Interval(key.tonic, target)
    score = score.transpose(interval)

    parts = list(score.parts) if score.parts else [score]
    melody_part = max(parts, key=_average_pitch)

    events: list[Event] = []
    for note in melody_part.flatten().notes:
        if not hasattr(note, "pitch"):
            continue
        onset = float(note.offset)
        events.append(
            Event(
                piece_id=path.stem,
                source=source,
                genre=genre,
                is_ai=is_ai,
                split=split,
                onset=onset,
                pitch=int(note.pitch.midi),
                duration=float(note.quarterLength),
                chord="NA",
                boundary=_is_boundary(note, boundary_mode),
            )
        )
    return events


def convert_midi_directory(
    midi_dir: str | Path,
    output_csv: str | Path,
    *,
    source: str,
    genre: str,
    split: str,
    is_ai: bool = False,
    boundary_mode: str = "measure",
) -> Path:
    rows: list[dict] = []
    for midi_path in sorted(Path(midi_dir).glob("**/*")):
        if midi_path.suffix.lower() not in {".mid", ".midi", ".kar"}:
            continue
        for event in load_melody_events_from_midi(
            midi_path,
            source=source,
            genre=genre,
            split=split,
            is_ai=is_ai,
            boundary_mode=boundary_mode,
        ):
            rows.append(event.__dict__)

    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "piece_id",
            "source",
            "genre",
            "is_ai",
            "split",
            "onset",
            "pitch",
            "duration",
            "chord",
            "boundary",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "is_ai": int(row["is_ai"]), "boundary": int(row["boundary"])})
    return output


def _average_pitch(part) -> float:
    pitches = [note.pitch.midi for note in part.flatten().notes if hasattr(note, "pitch")]
    return sum(pitches) / len(pitches) if pitches else -1.0


def _is_boundary(note, boundary_mode: str) -> bool:
    if boundary_mode == "none":
        return False
    if boundary_mode != "measure":
        raise ValueError("boundary_mode must be measure or none")
    return abs(float(note.offset) - round(float(note.offset))) < 1e-9 and int(note.offset) % 4 == 0


def parse_midi_notes(data: bytes) -> tuple[int, list[dict]]:
    """Parse enough Standard MIDI to recover note events.

    Returns `(ticks_per_quarter, notes)`, where notes contain channel, pitch, velocity,
    start, and end in MIDI ticks. This deliberately avoids external dependencies so the
    experiment can run in a clean Python environment.
    """

    if data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI file")
    header_length = struct.unpack(">I", data[4:8])[0]
    if header_length < 6:
        raise ValueError("invalid MIDI header")
    _, track_count, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        ticks_per_quarter = 480
    else:
        ticks_per_quarter = division

    offset = 8 + header_length
    notes: list[dict] = []
    for _ in range(track_count):
        if data[offset : offset + 4] != b"MTrk":
            raise ValueError("missing MIDI track header")
        track_length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        track_data = data[offset + 8 : offset + 8 + track_length]
        offset += 8 + track_length
        notes.extend(_parse_track(track_data))
    notes.sort(key=lambda item: (item["start"], item["pitch"], item["end"]))
    return ticks_per_quarter, notes


def melody_events_from_midi_bytes(
    data: bytes,
    *,
    piece_id: str,
    source: str,
    genre: str,
    split: str,
    is_ai: bool,
    melody_mode: str = "highest_onset",
    boundary_bars: int = 4,
) -> list[Event]:
    ticks_per_quarter, notes = parse_midi_notes(data)
    if not notes:
        return []
    selected = _select_melody_notes(notes, melody_mode)
    chord_by_start = _chord_labels_by_start(notes)

    events: list[Event] = []
    for note in selected:
        onset_quarters = note["start"] / ticks_per_quarter
        duration_quarters = max(1, note["end"] - note["start"]) / ticks_per_quarter
        events.append(
            Event(
                piece_id=piece_id,
                source=source,
                genre=genre,
                is_ai=is_ai,
                split=split,
                onset=onset_quarters,
                pitch=int(note["pitch"]),
                duration=duration_quarters,
                chord=chord_by_start.get(note["start"], "NA"),
                boundary=_bar_boundary(onset_quarters, boundary_bars),
            )
        )
    return events


def _parse_track(track_data: bytes) -> list[dict]:
    position = 0
    tick = 0
    running_status: int | None = None
    active: dict[tuple[int, int], list[tuple[int, int]]] = {}
    notes: list[dict] = []

    while position < len(track_data):
        delta, position = _read_varlen(track_data, position)
        tick += delta
        status = track_data[position]
        if status & 0x80:
            position += 1
            if status < 0xF0:
                running_status = status
        elif running_status is not None:
            status = running_status
        else:
            raise ValueError("running status encountered before status byte")

        if status == 0xFF:
            meta_type = track_data[position]
            position += 1
            length, position = _read_varlen(track_data, position)
            position += length
            if meta_type == 0x2F:
                break
            continue
        if status in {0xF0, 0xF7}:
            length, position = _read_varlen(track_data, position)
            position += length
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        data_len = 1 if event_type in {0xC0, 0xD0} else 2
        payload = track_data[position : position + data_len]
        position += data_len

        if event_type not in {0x80, 0x90}:
            continue
        pitch = payload[0]
        velocity = payload[1] if len(payload) > 1 else 0
        key = (channel, pitch)
        if event_type == 0x90 and velocity > 0:
            active.setdefault(key, []).append((tick, velocity))
        else:
            starts = active.get(key)
            if starts:
                start, start_velocity = starts.pop(0)
                if tick > start:
                    notes.append(
                        {
                            "channel": channel,
                            "pitch": pitch,
                            "velocity": start_velocity,
                            "start": start,
                            "end": tick,
                        }
                    )
    return notes


def _read_varlen(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[position]
        position += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, position


def _select_melody_notes(notes: Iterable[dict], mode: str) -> list[dict]:
    notes = list(notes)
    if mode == "all":
        return notes
    if mode == "highest_channel":
        by_channel: dict[int, list[dict]] = {}
        for note in notes:
            by_channel.setdefault(note["channel"], []).append(note)
        channel = max(
            by_channel,
            key=lambda item: sum(note["pitch"] for note in by_channel[item])
            / max(1, len(by_channel[item])),
        )
        return by_channel[channel]
    if mode != "highest_onset":
        raise ValueError("melody_mode must be highest_onset, highest_channel, or all")

    by_start: dict[int, dict] = {}
    for note in notes:
        current = by_start.get(note["start"])
        if current is None or note["pitch"] > current["pitch"]:
            by_start[note["start"]] = note
    return [by_start[start] for start in sorted(by_start)]


def _chord_labels_by_start(notes: Iterable[dict]) -> dict[int, str]:
    by_start: dict[int, set[int]] = {}
    for note in notes:
        by_start.setdefault(note["start"], set()).add(int(note["pitch"]) % 12)
    return {
        start: ".".join(str(pc) for pc in sorted(pitch_classes))
        for start, pitch_classes in by_start.items()
    }


def _bar_boundary(onset_quarters: float, boundary_bars: int) -> bool:
    bar_length = 4.0
    if boundary_bars <= 0:
        return False
    boundary_length = boundary_bars * bar_length
    return abs(onset_quarters / boundary_length - round(onset_quarters / boundary_length)) < 1e-6
