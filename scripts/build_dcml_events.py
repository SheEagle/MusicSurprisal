from __future__ import annotations

import argparse
import csv
import sys
from bisect import bisect_right
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DCML event table for classical RQ2.")
    parser.add_argument("--dcml-dir", default="datasets/raw/dcml/dcml_corpora")
    parser.add_argument("--output", default="data/events_dcml_classical.csv")
    args = parser.parse_args()

    dcml = Path(args.dcml_dir)
    events = build_events(dcml)
    rows = [event.__dict__ for event in events]
    for row in rows:
        row["is_ai"] = int(row["is_ai"])
        row["boundary"] = int(row["boundary"])
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} DCML events to {args.output}")
    print_counts(events)


def build_events(dcml: Path) -> list[Event]:
    harmony_by_piece, boundary_by_piece = read_harmonies(dcml / "dcml_corpora.expanded.tsv")
    split_by_piece = make_splits(dcml / "dcml_corpora.metadata.tsv")
    notes_by_onset: dict[tuple[str, str, float], list[dict]] = defaultdict(list)

    with (dcml / "dcml_corpora.notes.tsv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row.get("gracenote"):
                continue
            if not row.get("midi") or not row.get("quarterbeats"):
                continue
            try:
                midi = int(float(row["midi"]))
                onset = parse_number(row["quarterbeats"])
                duration = parse_number(row["duration_qb"])
            except ValueError:
                continue
            key = (row["corpus"], row["piece"], onset)
            notes_by_onset[key].append(
                {
                    "midi": midi,
                    "duration": duration,
                    "staff": int(row["staff"]) if row.get("staff") else 99,
                    "voice": int(row["voice"]) if row.get("voice") else 99,
                }
            )

    events: list[Event] = []
    for (corpus, piece, onset), notes in sorted(notes_by_onset.items()):
        selected = max(notes, key=lambda note: (note["midi"], -note["staff"], -note["voice"]))
        piece_key = (corpus, piece)
        harmony = lookup_harmony(harmony_by_piece.get(piece_key, []), onset)
        events.append(
            Event(
                piece_id=f"dcml_{corpus}_{piece}",
                source="dcml",
                genre="classical",
                is_ai=False,
                split=split_by_piece.get(piece_key, "train"),
                onset=onset,
                pitch=selected["midi"],
                duration=selected["duration"],
                chord=harmony,
                boundary=onset in boundary_by_piece.get(piece_key, set()),
            )
        )
    return events


def read_harmonies(path: Path) -> tuple[dict[tuple[str, str], list[tuple[float, str]]], dict[tuple[str, str], set[float]]]:
    harmony_by_piece: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)
    boundary_by_piece: dict[tuple[str, str], set[float]] = defaultdict(set)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if not row.get("quarterbeats"):
                continue
            key = (row["corpus"], row["piece"])
            onset = parse_number(row["quarterbeats"])
            label = row.get("label") or row.get("chord") or row.get("numeral") or "NA"
            harmony_by_piece[key].append((onset, label))
            phraseend = row.get("phraseend", "")
            cadence = row.get("cadence", "")
            if cadence or "}" in phraseend:
                boundary_by_piece[key].add(onset)
    return dict(harmony_by_piece), dict(boundary_by_piece)


def lookup_harmony(harmonies: list[tuple[float, str]], onset: float) -> str:
    if not harmonies:
        return "NA"
    positions = [item[0] for item in harmonies]
    index = bisect_right(positions, onset) - 1
    return harmonies[index][1] if index >= 0 else harmonies[0][1]


def parse_number(value: str) -> float:
    value = value.strip()
    if "/" in value:
        return float(Fraction(value))
    return float(value)


def make_splits(metadata_path: Path) -> dict[tuple[str, str], str]:
    pieces_by_corpus: dict[str, list[str]] = defaultdict(list)
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            pieces_by_corpus[row["corpus"]].append(row["piece"])

    splits: dict[tuple[str, str], str] = {}
    for corpus, pieces in pieces_by_corpus.items():
        pieces = sorted(set(pieces))
        for index, piece in enumerate(pieces):
            frac = index / max(1, len(pieces))
            if frac < 0.7:
                split = "train"
            elif frac < 0.85:
                split = "valid"
            else:
                split = "test"
            splits[(corpus, piece)] = split
    return splits


def print_counts(events: list[Event]) -> None:
    counts: dict[tuple[str, str], set[str]] = defaultdict(set)
    event_counts: dict[tuple[str, str], int] = defaultdict(int)
    boundary_count = 0
    for event in events:
        key = (event.source, event.split)
        counts[key].add(event.piece_id)
        event_counts[key] += 1
        boundary_count += int(event.boundary)
    for key in sorted(counts):
        print(f"{key[0]} {key[1]}: {event_counts[key]} events, {len(counts[key])} pieces")
    print(f"boundaries: {boundary_count}")


if __name__ == "__main__":
    main()
