from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import write_rows
from music_surprisal.midi_io import melody_events_from_midi_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Music Transformer MIDI samples to event CSV.")
    parser.add_argument("--midi-dir", default="datasets/raw/music_transformer/a1")
    parser.add_argument("--output", default="data/events_music_transformer.csv")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument(
        "--melody-mode",
        default="highest_onset",
        choices=["highest_onset", "highest_channel", "all"],
    )
    args = parser.parse_args()

    files = sorted(Path(args.midi_dir).glob("*.mid"), key=lambda path: int(path.stem))
    if args.max_files:
        files = files[: args.max_files]

    events = []
    for path in files:
        events.extend(
            melody_events_from_midi_bytes(
                path.read_bytes(),
                piece_id=f"music_transformer_{path.stem}",
                source="music_transformer",
                genre="classical_piano",
                split=args.split,
                is_ai=True,
                melody_mode=args.melody_mode,
                boundary_bars=4,
            )
        )

    rows = [event.__dict__ for event in events]
    for row in rows:
        row["is_ai"] = int(row["is_ai"])
        row["boundary"] = int(row["boundary"])
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} Music Transformer events from {len(files)} files to {args.output}")


if __name__ == "__main__":
    main()
