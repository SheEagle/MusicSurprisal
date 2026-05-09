from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Event:
    piece_id: str
    source: str
    genre: str
    is_ai: bool
    split: str
    onset: float
    pitch: int
    duration: float
    chord: str
    boundary: bool


def read_events(path: str | Path) -> list[Event]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
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
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")

        return [
            Event(
                piece_id=row["piece_id"],
                source=row["source"],
                genre=row["genre"],
                is_ai=str(row["is_ai"]).strip().lower() in {"1", "true", "yes"},
                split=row["split"].strip().lower() or "train",
                onset=float(row["onset"]),
                pitch=int(float(row["pitch"])),
                duration=float(row["duration"]),
                chord=row["chord"].strip() or "NA",
                boundary=str(row["boundary"]).strip().lower() in {"1", "true", "yes"},
            )
            for row in reader
        ]


def write_rows(path: str | Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def group_by_piece(events: Iterable[Event]) -> dict[str, list[Event]]:
    pieces: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        pieces[event.piece_id].append(event)
    for piece_events in pieces.values():
        piece_events.sort(key=lambda item: item.onset)
    return dict(pieces)


def split_events(events: list[Event]) -> tuple[list[Event], list[Event]]:
    train = [event for event in events if event.split == "train"]
    eval_events = [event for event in events if event.split != "train"]
    if not train:
        raise ValueError("at least one training event is required")
    if not eval_events:
        eval_events = train
    return train, eval_events


def quantize_duration(duration: float, unit: float = 0.25) -> str:
    if unit <= 0:
        raise ValueError("unit must be > 0")
    steps = round(duration / unit)
    return f"d{steps}"


def token_function(kind: str) -> Callable[[Event], object]:
    if kind == "pitch":
        return lambda event: event.pitch
    if kind == "pitch_duration":
        return lambda event: (event.pitch, quantize_duration(event.duration))
    if kind == "pitch_chord":
        return lambda event: (event.pitch, event.chord)
    raise ValueError(
        "token kind must be one of: pitch, pitch_duration, pitch_chord"
    )


def event_sequences(
    events: Iterable[Event], token_kind: str = "pitch"
) -> dict[str, list[object]]:
    to_token = token_function(token_kind)
    return {
        piece_id: [to_token(event) for event in piece_events]
        for piece_id, piece_events in group_by_piece(events).items()
    }


def distance_to_next_boundary(piece_events: list[Event]) -> list[int | None]:
    distances: list[int | None] = [None] * len(piece_events)
    next_boundary: int | None = None
    for index in range(len(piece_events) - 1, -1, -1):
        if next_boundary is None:
            distances[index] = None
        else:
            distances[index] = next_boundary - index
        if piece_events[index].boundary:
            next_boundary = index
            distances[index] = 0
    return distances
