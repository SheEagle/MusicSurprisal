from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build JTC jazz phrase-boundary event table.")
    parser.add_argument("--jtc-dir", default="datasets/raw/jtc/JTCv101/JTC")
    parser.add_argument("--output", default="data/events_jtc_jazz.csv")
    parser.add_argument(
        "--min-annotators",
        type=int,
        default=2,
        help="Minimum A1/A2/A3 phrase-end votes required to mark a boundary.",
    )
    args = parser.parse_args()

    events = build_events(Path(args.jtc_dir), min_annotators=args.min_annotators)
    rows = [event.__dict__ for event in events]
    for row in rows:
        row["is_ai"] = int(row["is_ai"])
        row["boundary"] = int(row["boundary"])
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} JTC events to {args.output}")
    print_counts(events)


def build_events(jtc: Path, min_annotators: int) -> list[Event]:
    melody_dir = jtc / "EXTRACTED_MELODY_TSV"
    files = sorted(melody_dir.glob("*.tsv"))
    split_by_piece = make_splits([path.stem for path in files])
    events: list[Event] = []

    for path in files:
        piece_id = f"jtc_{path.stem}"
        rows = read_melody_rows(path)
        for index, row in enumerate(rows):
            next_onset = rows[index + 1]["onset"] if index + 1 < len(rows) else row["onset"] + 1.0
            duration = max(0.01, next_onset - row["onset"])
            votes = row["a1"] + row["a2"] + row["a3"]
            events.append(
                Event(
                    piece_id=piece_id,
                    source="jtc",
                    genre="jazz",
                    is_ai=False,
                    split=split_by_piece[path.stem],
                    onset=row["onset"],
                    pitch=row["pitch"],
                    duration=duration,
                    chord="NA",
                    boundary=votes >= min_annotators,
                )
            )
    return events


def read_melody_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            try:
                rows.append(
                    {
                        "onset": float(parts[0]),
                        "pitch": int(float(parts[1])),
                        "a1": int(float(parts[2])),
                        "a2": int(float(parts[3])),
                        "a3": int(float(parts[4])),
                    }
                )
            except ValueError:
                continue
    rows.sort(key=lambda row: row["onset"])
    return rows


def make_splits(piece_ids: list[str]) -> dict[str, str]:
    split_by_piece: dict[str, str] = {}
    for index, piece_id in enumerate(sorted(piece_ids)):
        frac = index / max(1, len(piece_ids))
        if frac < 0.7:
            split = "train"
        elif frac < 0.85:
            split = "valid"
        else:
            split = "test"
        split_by_piece[piece_id] = split
    return split_by_piece


def print_counts(events: list[Event]) -> None:
    pieces: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    boundaries = 0
    for event in events:
        pieces.setdefault(event.split, set()).add(event.piece_id)
        counts[event.split] = counts.get(event.split, 0) + 1
        boundaries += int(event.boundary)
    for split in sorted(counts):
        print(f"jtc {split}: {counts[split]} events, {len(pieces[split])} pieces")
    print(f"boundaries: {boundaries}")


if __name__ == "__main__":
    main()
