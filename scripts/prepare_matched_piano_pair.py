from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare length-matched MAESTRO excerpts vs Music Transformer samples."
    )
    parser.add_argument("--maestro-events", default="data/events_all_rq.csv")
    parser.add_argument("--ai-events", default="data/events_music_transformer_a1_sample500.csv")
    parser.add_argument(
        "--output",
        default="data/pairs/maestro_matched_excerpt_vs_music_transformer_sample500.csv",
    )
    parser.add_argument("--ai-source", default="music_transformer")
    parser.add_argument("--human-source", default="maestro")
    parser.add_argument("--human-train-pieces", type=int, default=180)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument(
        "--max-ai-pieces",
        type=int,
        default=500,
        help="0 means keep all AI pieces.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    print("Loading AI samples...")
    ai_by_piece = group_by_piece(
        read_rows(args.ai_events, source=args.ai_source), sort_key=("event_index", "onset")
    )
    ai_piece_ids = sorted(ai_by_piece)
    if args.max_ai_pieces:
        ai_piece_ids = ai_piece_ids[: args.max_ai_pieces]

    print("Loading MAESTRO rows...")
    maestro_rows = read_rows(args.maestro_events, source=args.human_source)
    maestro_by_split = group_maestro(maestro_rows)
    train_rows = select_train_rows(
        maestro_by_split.get("train", {}), max_pieces=args.human_train_pieces
    )
    heldout_pieces = {
        **maestro_by_split.get("validation", {}),
        **maestro_by_split.get("valid", {}),
        **maestro_by_split.get("test", {}),
    }
    if not train_rows or not heldout_pieces:
        raise ValueError("Need MAESTRO train rows and held-out rows for matching")

    print("Matching held-out MAESTRO excerpts to AI sample lengths...")
    matched_human_rows: list[dict] = []
    used_offsets: set[tuple[str, int, int]] = set()
    heldout_ids = sorted(heldout_pieces)
    for ai_piece_id in ai_piece_ids:
        ai_len = len(ai_by_piece[ai_piece_id])
        excerpt = sample_excerpt(
            heldout_pieces,
            heldout_ids,
            length=ai_len,
            rng=rng,
            used_offsets=used_offsets,
        )
        excerpt_id = f"maestro_excerpt_for_{ai_piece_id}"
        matched_human_rows.extend(relabel_excerpt(excerpt, excerpt_id))

    ai_rows = []
    for piece_id in ai_piece_ids:
        ai_rows.extend(ai_by_piece[piece_id])

    rows = train_rows + matched_human_rows + ai_rows
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    print_counts(rows)


def read_rows(path: str | Path, source: str) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["source"] == source:
                rows.append(row)
    return rows


def group_by_piece(rows: list[dict], sort_key=("onset",)) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(row)
    for piece_rows in grouped.values():
        piece_rows.sort(key=lambda row: tuple(float(row.get(key, 0) or 0) for key in sort_key))
    return dict(grouped)


def group_maestro(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    by_split: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_split[row["split"].lower()].append(row)
    return {split: group_by_piece(split_rows) for split, split_rows in by_split.items()}


def select_train_rows(train_pieces: dict[str, list[dict]], max_pieces: int) -> list[dict]:
    rows: list[dict] = []
    for piece_id in sorted(train_pieces)[:max_pieces]:
        piece_rows = [dict(row) for row in train_pieces[piece_id]]
        rows.extend(piece_rows)
    return rows


def sample_excerpt(
    pieces: dict[str, list[dict]],
    piece_ids: list[str],
    *,
    length: int,
    rng: random.Random,
    used_offsets: set[tuple[str, int, int]],
) -> list[dict]:
    candidates = [piece_id for piece_id in piece_ids if len(pieces[piece_id]) >= length]
    if not candidates:
        raise ValueError(f"No held-out MAESTRO piece can supply excerpt length {length}")
    for _ in range(1000):
        piece_id = rng.choice(candidates)
        max_start = len(pieces[piece_id]) - length
        start = rng.randint(0, max_start)
        key = (piece_id, start, length)
        if key not in used_offsets:
            used_offsets.add(key)
            return [dict(row) for row in pieces[piece_id][start : start + length]]
    piece_id = rng.choice(candidates)
    max_start = len(pieces[piece_id]) - length
    start = rng.randint(0, max_start)
    return [dict(row) for row in pieces[piece_id][start : start + length]]


def relabel_excerpt(rows: list[dict], piece_id: str) -> list[dict]:
    if not rows:
        return []
    base_onset = float(rows[0]["onset"])
    relabeled: list[dict] = []
    for index, row in enumerate(rows):
        copy = dict(row)
        copy["piece_id"] = piece_id
        copy["split"] = "test"
        copy["is_ai"] = "0"
        copy["onset"] = str(float(copy["onset"]) - base_onset)
        copy["event_index"] = str(index)
        relabeled.append(copy)
    return relabeled


def write_rows(path: str | Path, rows: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No rows to write")
    with output.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(rows[0].keys())
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_counts(rows: list[dict]) -> None:
    counts: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    events: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        key = (row["source"], row["split"], row["is_ai"])
        counts[key].add(row["piece_id"])
        events[key] += 1
    for key in sorted(counts):
        print(
            f"{key[0]} split={key[1]} is_ai={key[2]}: "
            f"{events[key]} events, {len(counts[key])} pieces"
        )


if __name__ == "__main__":
    main()
