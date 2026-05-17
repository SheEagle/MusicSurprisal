from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a matched human-vs-AI event CSV.")
    parser.add_argument("--human-events", required=True)
    parser.add_argument("--ai-events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--human-source", required=True)
    parser.add_argument("--ai-source", required=True)
    parser.add_argument(
        "--human-max-pieces-per-split",
        type=int,
        default=120,
        help="0 means keep all human pieces.",
    )
    parser.add_argument("--ai-max-pieces", type=int, default=0, help="0 means keep all AI pieces.")
    args = parser.parse_args()

    rows: list[dict] = []
    rows.extend(
        read_selected(
            args.human_events,
            source=args.human_source,
            max_pieces_per_split=args.human_max_pieces_per_split,
        )
    )
    rows.extend(
        read_selected(
            args.ai_events,
            source=args.ai_source,
            max_total_pieces=args.ai_max_pieces,
        )
    )
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    print_counts(rows)


def read_selected(
    path: str | Path,
    *,
    source: str,
    max_pieces_per_split: int = 0,
    max_total_pieces: int = 0,
) -> list[dict]:
    selected_by_split: dict[str, set[str]] = defaultdict(set)
    selected_total: set[str] = set()
    rows: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["source"] != source:
                continue
            piece_id = row["piece_id"]
            split = row["split"]
            if max_total_pieces and piece_id not in selected_total:
                if len(selected_total) >= max_total_pieces:
                    continue
                selected_total.add(piece_id)
            elif max_total_pieces and piece_id not in selected_total:
                continue

            if max_pieces_per_split and piece_id not in selected_by_split[split]:
                if len(selected_by_split[split]) >= max_pieces_per_split:
                    continue
                selected_by_split[split].add(piece_id)
            elif max_pieces_per_split and piece_id not in selected_by_split[split]:
                continue

            rows.append(row)
    return rows


def write_rows(path: str | Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No rows selected")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_counts(rows: list[dict]) -> None:
    counts: dict[tuple[str, str], set[str]] = defaultdict(set)
    events: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        key = (row["source"], row["split"])
        counts[key].add(row["piece_id"])
        events[key] += 1
    for key in sorted(counts):
        print(f"{key[0]} {key[1]}: {events[key]} events, {len(counts[key])} pieces")


if __name__ == "__main__":
    main()
