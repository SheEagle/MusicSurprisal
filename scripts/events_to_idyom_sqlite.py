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
    args = parser.parse_args()

    rows = read_rows(Path(args.events))
    if not rows:
        raise ValueError(f"No events found in {args.events}")
    if args.id_column not in rows[0]:
        args.id_column = args.piece_column

    composition_map = make_composition_map(rows, args.id_column)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    con = sqlite3.connect(output)
    try:
        create_schema(con)
        insert_dataset(con, args.dataset_id, args.description or Path(args.events).stem, args.ticks_per_quarter)
        insert_compositions(con, rows, composition_map, args, args.ticks_per_quarter)
        insert_events(con, rows, composition_map, args.id_column, args.dataset_id, args.ticks_per_quarter)
        con.commit()
    finally:
        con.close()
    print(f"Wrote IDyOM sqlite database to {output}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_composition_map(rows: list[dict[str, str]], column: str) -> dict[str, int]:
    if rows and column not in rows[0]:
        column = "piece_id"
    values = sorted({row.get(column, "") for row in rows}, key=sort_key)
    return {value: index + 1 for index, value in enumerate(values)}


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
        pitch = int(round(number(row.get("pitch"))))
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
            "VERTINT12": None,
            "ARTICULATION_DYN": None,
        }
        con.execute(insert_sql, [values[name] for name, _ in EVENT_COLUMNS])


def to_ticks(value: str | None, ticks_per_quarter: int) -> int:
    return int(round(number(value) * ticks_per_quarter))


def number(value: str | None) -> float:
    if value in {None, "", "NA"}:
        return 0.0
    return float(value)


if __name__ == "__main__":
    main()
