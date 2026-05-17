from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import zipfile
from bisect import bisect_right
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, write_rows
from music_surprisal.midi_io import melody_events_from_midi_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the all-RQ normalized event table.")
    parser.add_argument("--raw", default="datasets/raw")
    parser.add_argument("--output", default="data/events_all_rq.csv")
    parser.add_argument("--maestro-max", type=int, default=0, help="0 means all MAESTRO rows.")
    parser.add_argument("--js-fake-max", type=int, default=500)
    args = parser.parse_args()

    raw = Path(args.raw)
    events: list[Event] = []
    events.extend(load_maestro(raw, max_rows=args.maestro_max))
    events.extend(load_wjazzd(raw))
    events.extend(load_jsb(raw))
    events.extend(load_js_fakes(raw, max_files=args.js_fake_max))

    rows = [event.__dict__ for event in events]
    for row in rows:
        row["is_ai"] = int(row["is_ai"])
        row["boundary"] = int(row["boundary"])
    write_rows(args.output, rows)
    print(f"Wrote {len(rows)} events to {args.output}")
    print_counts(events)


def load_maestro(raw: Path, max_rows: int = 0) -> list[Event]:
    metadata_path = raw / "archives" / "maestro-v3.0.0.csv"
    zip_path = raw / "archives" / "maestro-v3.0.0-midi.zip"
    if not metadata_path.exists() or not zip_path.exists():
        print("Skipping MAESTRO: metadata or MIDI zip missing")
        return []

    events: list[Event] = []
    with metadata_path.open(newline="", encoding="utf-8") as handle, zipfile.ZipFile(zip_path) as archive:
        rows = list(csv.DictReader(handle))
        if max_rows:
            rows = rows[:max_rows]
        for index, row in enumerate(rows):
            midi_name = "maestro-v3.0.0/" + row["midi_filename"]
            try:
                data = archive.read(midi_name)
            except KeyError:
                continue
            piece_id = f"maestro_{index:04d}"
            events.extend(
                melody_events_from_midi_bytes(
                    data,
                    piece_id=piece_id,
                    source="maestro",
                    genre="classical",
                    split=row["split"].strip().lower(),
                    is_ai=False,
                    melody_mode="highest_onset",
                    boundary_bars=4,
                )
            )
    return events


def load_wjazzd(raw: Path) -> list[Event]:
    db_path = raw / "archives" / "wjazzd.db"
    if not db_path.exists():
        print("Skipping WJazzD: database missing")
        return []

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    melids = [row[0] for row in con.execute("select distinct melid from melody order by melid")]
    split_by_melid = _make_splits(melids)

    beat_map: dict[int, list[tuple[float, str]]] = {}
    for row in con.execute("select melid, onset, chord from beats order by melid, onset"):
        beat_map.setdefault(row["melid"], []).append((float(row["onset"]), row["chord"] or "NA"))

    section_starts: dict[int, set[int]] = {}
    for row in con.execute("select melid, start from sections"):
        section_starts.setdefault(row["melid"], set()).add(int(row["start"]))

    events: list[Event] = []
    last_bar_by_melid: dict[int, int] = {}
    query = """
        select melid, onset, pitch, duration, bar, beat
        from melody
        where pitch is not null and duration > 0
        order by melid, onset, eventid
    """
    for row in con.execute(query):
        melid = int(row["melid"])
        bar = int(row["bar"]) if row["bar"] is not None else -1
        is_section_boundary = (
            bar in section_starts.get(melid, set())
            and last_bar_by_melid.get(melid) != bar
        )
        last_bar_by_melid[melid] = bar
        events.append(
            Event(
                piece_id=f"wjazzd_{melid}",
                source="wjazzd",
                genre="jazz",
                is_ai=False,
                split=split_by_melid[melid],
                onset=float(row["onset"]),
                pitch=int(round(float(row["pitch"]))),
                duration=float(row["duration"]),
                chord=_lookup_chord(beat_map.get(melid, []), float(row["onset"])),
                boundary=is_section_boundary,
            )
        )
    con.close()
    return events


def load_jsb(raw: Path) -> list[Event]:
    path = raw / "jsb" / "Jsb16thSeparated.json"
    if not path.exists():
        print("Skipping JSB: JSON missing")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    events: list[Event] = []
    for split, pieces in data.items():
        for index, timesteps in enumerate(pieces):
            piece_id = f"jsb_{split}_{index:03d}"
            events.extend(
                timestep_piece_to_events(
                    timesteps,
                    piece_id=piece_id,
                    source="jsb",
                    genre="chorale",
                    split=split,
                    is_ai=False,
                )
            )
    return events


def load_js_fakes(raw: Path, max_files: int = 500) -> list[Event]:
    midi_dir = raw / "js-fakes" / "js-fakes-main" / "midi"
    if not midi_dir.exists():
        print("Skipping JS Fake Chorales: MIDI directory missing")
        return []
    events: list[Event] = []
    files = sorted(midi_dir.glob("*.mid"), key=lambda path: int(path.stem) if path.stem.isdigit() else path.stem)
    if max_files:
        files = files[:max_files]
    for path in files:
        events.extend(
            melody_events_from_midi_bytes(
                path.read_bytes(),
                piece_id=f"js_fake_{path.stem}",
                source="js_fake",
                genre="chorale",
                split="test",
                is_ai=True,
                melody_mode="highest_onset",
                boundary_bars=4,
            )
        )
    return events


def timestep_piece_to_events(
    timesteps: list[list[int]],
    *,
    piece_id: str,
    source: str,
    genre: str,
    split: str,
    is_ai: bool,
) -> list[Event]:
    events: list[Event] = []
    current_pitch: int | None = None
    start = 0
    current_chord = "NA"
    for index, step in enumerate(timesteps + [[-1, -1, -1, -1]]):
        active = [int(pitch) for pitch in step if int(pitch) >= 0]
        pitch = max(active) if active else None
        chord = ".".join(str(pitch % 12) for pitch in sorted(set(active))) if active else "NA"
        if pitch != current_pitch:
            if current_pitch is not None:
                events.append(
                    Event(
                        piece_id=piece_id,
                        source=source,
                        genre=genre,
                        is_ai=is_ai,
                        split=split,
                        onset=start / 4.0,
                        pitch=current_pitch,
                        duration=(index - start) / 4.0,
                        chord=current_chord,
                        boundary=start % 16 == 0,
                    )
                )
            current_pitch = pitch
            current_chord = chord
            start = index
        elif pitch is not None:
            current_chord = chord
    return events


def _lookup_chord(chords: list[tuple[float, str]], onset: float) -> str:
    if not chords:
        return "NA"
    positions = [item[0] for item in chords]
    index = bisect_right(positions, onset) - 1
    return chords[index][1] if index >= 0 else chords[0][1]


def _make_splits(ids: list[int]) -> dict[int, str]:
    split_by_id: dict[int, str] = {}
    total = len(ids)
    for index, item in enumerate(ids):
        frac = index / max(1, total)
        if frac < 0.7:
            split = "train"
        elif frac < 0.85:
            split = "valid"
        else:
            split = "test"
        split_by_id[item] = split
    return split_by_id


def print_counts(events: list[Event]) -> None:
    counts: dict[tuple[str, str], int] = {}
    pieces: dict[tuple[str, str], set[str]] = {}
    for event in events:
        key = (event.source, event.split)
        counts[key] = counts.get(key, 0) + 1
        pieces.setdefault(key, set()).add(event.piece_id)
    for key in sorted(counts):
        print(f"{key[0]} {key[1]}: {counts[key]} events, {len(pieces[key])} pieces")


if __name__ == "__main__":
    main()
