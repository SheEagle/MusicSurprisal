from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build event CSV from CocoChorales note_expression CSVs.")
    parser.add_argument("--input-dir", default="datasets/raw/cocochorales_note_expression/extracted")
    parser.add_argument("--output", default="data/events_cocochorales.csv")
    parser.add_argument("--max-pieces", type=int, default=0)
    parser.add_argument("--soprano-only", action="store_true", default=True)
    args = parser.parse_args()

    events = build_events(Path(args.input_dir), max_pieces=args.max_pieces)
    rows = [event.__dict__ for event in events]
    for row in rows:
        row["is_ai"] = int(row["is_ai"])
        row["boundary"] = int(row["boundary"])
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} CocoChorales events to {args.output}")


def build_events(root: Path, max_pieces: int = 0) -> list[Event]:
    piece_dirs = sorted(
        path for path in root.glob("**/*_track*") if path.is_dir()
    )
    if max_pieces:
        piece_dirs = piece_dirs[:max_pieces]

    events: list[Event] = []
    for piece_dir in piece_dirs:
        split = infer_split(piece_dir)
        stem_csvs = sorted(piece_dir.glob("*.csv"))
        if not stem_csvs:
            stem_csvs = sorted((piece_dir / "stems_MIDI").glob("*.csv"))
        soprano = next((path for path in stem_csvs if path.name.startswith("0_")), None)
        if not soprano:
            continue
        piece_id = f"cocochorales_{piece_dir.name}"
        events.extend(read_voice_csv(soprano, piece_id=piece_id, split=split))
    return events


def read_voice_csv(path: Path, *, piece_id: str, split: str) -> list[Event]:
    events: list[Event] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pitch = int(float(row.get("pitch", "0") or 0))
            if pitch <= 0:
                continue
            onset_frames = float(row.get("onset", "0") or 0)
            offset_frames = float(row.get("offset", "0") or 0)
            onset = onset_frames * 0.004
            duration = max(0.004, (offset_frames - onset_frames) * 0.004)
            events.append(
                Event(
                    piece_id=piece_id,
                    source="cocochorales",
                    genre="chorale",
                    is_ai=True,
                    split=split,
                    onset=onset,
                    pitch=pitch,
                    duration=duration,
                    chord="NA",
                    boundary=abs((onset / 4.0) - round(onset / 4.0)) < 0.02,
                )
            )
    return events


def infer_split(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    for split in ("train", "valid", "test"):
        if split in parts:
            return split
    return "test"


if __name__ == "__main__":
    main()
