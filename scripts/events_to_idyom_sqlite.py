from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


EVENT_COLUMNS = [
    ("EVENT_ID", "INTEGER NOT NULL"),
    ("COMPOSITION_ID", "INTEGER NOT NULL"),
    ("DATASET_ID", "INTEGER NOT NULL"),
    ("ONSET", "INTEGER"),
    ("CPITCH", "INTEGER"),
    ("MPITCH", "INTEGER"),
    ("ACCIDENTAL", "INTEGER"),
    ("DUR", "INTEGER"),
    ("DELTAST", "INTEGER"),
    ("BIOI", "INTEGER"),
    ("KEYSIG", "INTEGER"),
    ("MODE", "INTEGER"),
    ("BARLENGTH", "INTEGER"),
    ("PULSES", "INTEGER"),
    ("PHRASE", "INTEGER"),
    ("TEMPO", "INTEGER"),
    ("DYN", "INTEGER"),
    ("ORNAMENT", "INTEGER"),
    ("COMMA", "INTEGER"),
    ("ARTICULATION", "INTEGER"),
    ("VOICE", "INTEGER"),
    ("MPITCH12", "INTEGER"),
    ("VERTINT12", "INTEGER"),
    ("ARTICULATION_DYN", "INTEGER"),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert project event CSV rows into an IDyOM-compatible sqlite database."
    )
    parser.add_argument("--events", required=True, help="Project event CSV, e.g. data/events_cocopops_pop.csv.")
    parser.add_argument("--output", required=True, help="Output sqlite path.")
    parser.add_argument("--dataset-id", type=int, required=True)
    parser.add_argument("--description", default="")
    parser.add_argument(
        "--ticks-per-quarter",
        type=int,
        default=24,
        help="Multiplier used for onset/duration before inserting into IDyOM. DCML uses 24; CoCoPops melody outputs used 96.",
    )
    parser.add_argument("--id-column", default="piece_id", help="Column used to group events into IDYOM compositions.")
    parser.add_argument("--piece-column", default="piece_id")
    parser.add_argument(
        "--chord-to-vertint12",
        action="store_true",
        help="Encode the event CSV chord column as integer IDs in VERTINT12 so IDyOM can model it as a symbolic viewpoint.",
    )
    parser.add_argument(
        "--chord-root-pc-to-vertint12",
        action="store_true",
        help="Encode the current chord root pitch class from the chord column in VERTINT12.",
    )
    parser.add_argument("--chord-map-output", default="", help="Optional CSV path for the chord_id mapping.")
    parser.add_argument(
        "--cpitch-mode",
        choices=["pitch", "chord", "chord_pitch_pair"],
        default="pitch",
        help=(
            "What to store in the IDyOM CPITCH column. 'pitch' stores the event pitch; "
            "'chord' stores chord IDs; 'chord_pitch_pair' stores IDs for simultaneous chord/pitch pairs."
        ),
    )
    parser.add_argument("--cpitch-map-output", default="", help="Optional CSV path for symbolic CPITCH ID mappings.")
    args = parser.parse_args()

    rows = read_rows(Path(args.events))
    if not rows:
        raise ValueError(f"No events found in {args.events}")
    if args.id_column not in rows[0]:
        args.id_column = args.piece_column

    composition_map = make_composition_map(rows, args.id_column)
    if args.chord_to_vertint12 and args.chord_root_pc_to_vertint12:
        raise ValueError("Use either --chord-to-vertint12 or --chord-root-pc-to-vertint12, not both.")
    chord_map = make_chord_map(rows) if args.chord_to_vertint12 else {}
    cpitch_map = make_cpitch_symbol_map(rows, args.cpitch_mode)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    con = sqlite3.connect(output)
    try:
        create_schema(con)
        insert_dataset(con, args.dataset_id, args.description or Path(args.events).stem, args.ticks_per_quarter)
        insert_compositions(con, rows, composition_map, args, args.ticks_per_quarter)
        insert_events(
            con,
            rows,
            composition_map,
            args.id_column,
            args.dataset_id,
            args.ticks_per_quarter,
            chord_map,
            args.chord_root_pc_to_vertint12,
            args.cpitch_mode,
            cpitch_map,
        )
        con.commit()
    finally:
        con.close()
    if args.chord_map_output and chord_map:
        write_chord_map(Path(args.chord_map_output), chord_map)
    if args.cpitch_map_output and cpitch_map:
        write_cpitch_map(Path(args.cpitch_map_output), cpitch_map, args.cpitch_mode)
    print(f"Wrote IDyOM sqlite database to {output}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_composition_map(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    if rows and column not in rows[0]:
        column = "piece_id"
    values = sorted({row.get(column, "") for row in rows}, key=sort_key)
    return {value: index + 1 for index, value in enumerate(values)}


def make_chord_map(rows: list[dict[str, str]]) -> dict[str, int]:
    chords = sorted({normalize_chord(row.get("chord")) for row in rows})
    return {chord: idx + 1 for idx, chord in enumerate(chords)}


def make_cpitch_symbol_map(rows: list[dict[str, str]], mode: str) -> dict[str, int]:
    if mode == "pitch":
        return {}
    symbols = sorted({cpitch_symbol(row, mode) for row in rows})
    return {symbol: idx + 1 for idx, symbol in enumerate(symbols)}


def write_chord_map(path: Path, chord_map: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["chord", "chord_id"])
        writer.writeheader()
        for chord, chord_id in sorted(chord_map.items(), key=lambda item: item[1]):
            writer.writerow({"chord": chord, "chord_id": chord_id})


def write_cpitch_map(path: Path, cpitch_map: dict[str, int], mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "chord":
        fieldnames = ["symbol_id", "chord"]
    else:
        fieldnames = ["symbol_id", "chord", "pitch"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for symbol, symbol_id in sorted(cpitch_map.items(), key=lambda item: item[1]):
            row = {"symbol_id": symbol_id}
            if mode == "chord":
                row["chord"] = symbol
            else:
                chord, pitch = symbol.rsplit("|", 1)
                row["chord"] = chord
                row["pitch"] = pitch
            writer.writerow(row)


def sort_key(value: str) -> tuple[int, str]:
    try:
        return int(float(value)), value
    except (TypeError, ValueError):
        return 10**12, value


def create_schema(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE MTP_DATASET ("
        "DATASET_ID INTEGER NOT NULL PRIMARY KEY, "
        "DESCRIPTION VARCHAR(255), TIMEBASE INTEGER, MIDC INTEGER)"
    )
    con.execute(
        "CREATE TABLE MTP_COMPOSITION ("
        "COMPOSITION_ID INTEGER NOT NULL, DATASET_ID INTEGER NOT NULL, "
        "TIMEBASE INTEGER, DESCRIPTION VARCHAR(255), "
        "PRIMARY KEY (COMPOSITION_ID, DATASET_ID))"
    )
    columns_sql = ", ".join(f"{name} {kind}" for name, kind in EVENT_COLUMNS)
    con.execute(
        f"CREATE TABLE MTP_EVENT ({columns_sql}, "
        "PRIMARY KEY (EVENT_ID, COMPOSITION_ID, DATASET_ID))"
    )


def insert_dataset(con: sqlite3.Connection, dataset_id: int, description: str, timebase: int) -> None:
    con.execute(
        "INSERT INTO MTP_DATASET (DATASET_ID, DESCRIPTION, TIMEBASE, MIDC) VALUES (?, ?, ?, ?)",
        (dataset_id, description, timebase, 60),
    )


def insert_compositions(
    con: sqlite3.Connection,
    rows: list[dict[str, str]],
    composition_map: dict[str, int],
    args: argparse.Namespace,
    timebase: int,
) -> None:
    first_by_composition: dict[str, dict[str, str]] = {}
    for row in rows:
        first_by_composition.setdefault(row.get(args.id_column, ""), row)
    for raw_id, composition_id in sorted(composition_map.items(), key=lambda item: item[1]):
        row = first_by_composition[raw_id]
        description = row.get(args.piece_column) or raw_id or str(composition_id)
        con.execute(
            "INSERT INTO MTP_COMPOSITION (COMPOSITION_ID, DATASET_ID, TIMEBASE, DESCRIPTION) "
            "VALUES (?, ?, ?, ?)",
            (composition_id, args.dataset_id, timebase, description),
        )


def insert_events(
    con: sqlite3.Connection,
    rows: list[dict[str, str]],
    composition_map: dict[str, int],
    id_column: str,
    dataset_id: int,
    ticks_per_quarter: int,
    chord_map: dict[str, int] | None = None,
    chord_root_pc_to_vertint12: bool = False,
    cpitch_mode: str = "pitch",
    cpitch_map: dict[str, int] | None = None,
) -> None:
    counters: dict[int, int] = {}
    insert_sql = (
        f"INSERT INTO MTP_EVENT ({', '.join(name for name, _ in EVENT_COLUMNS)}) "
        f"VALUES ({', '.join('?' for _ in EVENT_COLUMNS)})"
    )
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            composition_map[row.get(id_column, "")],
            number(row.get("onset")),
            number(row.get("note_id_1")),
        ),
    )
    for row in sorted_rows:
        composition_id = composition_map[row.get(id_column, "")]
        event_id = counters.get(composition_id, 0)
        counters[composition_id] = event_id + 1
        onset = to_ticks(row.get("onset"), ticks_per_quarter)
        duration = max(1, to_ticks(row.get("duration"), ticks_per_quarter))
        pitch = cpitch_value(row, cpitch_mode, cpitch_map or {})
        if chord_root_pc_to_vertint12:
            chord_id = chord_root_pc(row.get("chord"))
        else:
            chord_id = chord_map.get(normalize_chord(row.get("chord"))) if chord_map else None
        values = {
            "EVENT_ID": event_id,
            "COMPOSITION_ID": composition_id,
            "DATASET_ID": dataset_id,
            "ONSET": onset,
            "CPITCH": pitch,
            "MPITCH": None,
            "ACCIDENTAL": None,
            "DUR": duration,
            "DELTAST": 0 if event_id else 0,
            "BIOI": duration,
            "KEYSIG": None,
            "MODE": None,
            "BARLENGTH": None,
            "PULSES": None,
            "PHRASE": None,
            "TEMPO": None,
            "DYN": None,
            "ORNAMENT": None,
            "COMMA": None,
            "ARTICULATION": None,
            "VOICE": 1,
            "MPITCH12": None,
            "VERTINT12": chord_id,
            "ARTICULATION_DYN": None,
        }
        con.execute(insert_sql, [values[name] for name, _ in EVENT_COLUMNS])


def to_ticks(value: str | None, ticks_per_quarter: int) -> int:
    return int(round(number(value) * ticks_per_quarter))


def number(value: str | None) -> float:
    if value in {None, "", "NA"}:
        return 0.0
    return float(value)


def normalize_chord(value: str | None) -> str:
    value = (value or "").strip()
    return value if value else "N"


def cpitch_symbol(row: dict[str, str], mode: str) -> str:
    chord = normalize_chord(row.get("chord"))
    if mode == "chord":
        return chord
    pitch = str(int(round(number(row.get("pitch")))))
    return f"{chord}|{pitch}"


def cpitch_value(row: dict[str, str], mode: str, cpitch_map: dict[str, int]) -> int:
    if mode == "pitch":
        return int(round(number(row.get("pitch"))))
    return cpitch_map[cpitch_symbol(row, mode)]


ROOT_PC = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "FB": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "CB": 11,
}


def chord_root_pc(value: str | None) -> int | None:
    chord = normalize_chord(value)
    if chord in {"", "N", ".", "NA"}:
        return None
    root = chord.split(":", 1)[0].strip().upper().replace("-", "B")
    return ROOT_PC.get(root)


if __name__ == "__main__":
    main()
