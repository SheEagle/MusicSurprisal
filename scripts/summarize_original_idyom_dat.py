from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge original Lisp IDyOM .dat output back onto project event rows."
    )
    parser.add_argument("--events", required=True, help="Original project event CSV.")
    parser.add_argument("--output", required=True, help="Merged event-level CSV.")
    parser.add_argument(
        "--dat",
        action="append",
        required=True,
        help="Model label and .dat path, e.g. ltm_plus=D:/.../file.dat. Can be repeated.",
    )
    parser.add_argument(
        "--schema",
        choices=["pop", "melody", "harmony"],
        default="pop",
        help="Output naming convention.",
    )
    args = parser.parse_args()

    event_rows = read_csv(Path(args.events))
    model_tables = [parse_dat_arg(item) for item in args.dat]
    model_maps = [(label, read_idyom_dat(path)) for label, path in model_tables]
    keys = infer_event_keys(event_rows)

    merged = []
    for index, row in enumerate(event_rows):
        key = keys[index]
        out = dict(row)
        out.setdefault("composition_id_0", str(key[0] - 1))
        out.setdefault("melody_id_1", str(key[0]))
        out.setdefault("event_id_0", str(key[1] - 1))
        out.setdefault("note_id_1", str(key[1]))
        for label, values in model_maps:
            item = values.get(key)
            if item is None:
                continue
            add_model_columns(out, label, item, args.schema)
        add_derived_columns(out, args.schema)
        merged.append(out)

    write_csv(Path(args.output), merged)
    print(f"Wrote merged IDyOM event CSV to {args.output}")


def parse_dat_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError("--dat must be label=path")
    label, path = value.split("=", 1)
    return label.strip(), Path(path.strip())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_idyom_dat(path: Path) -> dict[tuple[int, int], dict[str, str]]:
    out: dict[tuple[int, int], dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            melody_id = int(float(row["melody.id"]))
            note_id = int(float(row["note.id"]))
            out[(melody_id, note_id)] = {
                "melody_id": row["melody.id"],
                "note_id": row["note.id"],
                "cpitch": row.get("cpitch", ""),
                "ic": value(row, "ic", "cpitch.ic"),
                "entropy": value(row, "entropy", "cpitch.entropy"),
                "probability": value(row, "probability", "cpitch.probability"),
                "order_ltm": row.get("cpitch.order.ltm.cpitch", ""),
                "order_stm": row.get("cpitch.order.stm.cpitch", ""),
            }
    return out


def infer_event_keys(rows: list[dict[str, str]]) -> list[tuple[int, int]]:
    if rows and {"melody_id_1", "note_id_1"}.issubset(rows[0]):
        return [
            (int(float(row["melody_id_1"])), int(float(row["note_id_1"])))
            for row in rows
        ]

    piece_ids = sorted({row.get("piece_id", "") for row in rows})
    piece_to_melody = {piece_id: index + 1 for index, piece_id in enumerate(piece_ids)}
    note_counter: dict[str, int] = {}
    keys = []
    for row in rows:
        piece_id = row.get("piece_id", "")
        note_counter[piece_id] = note_counter.get(piece_id, 0) + 1
        keys.append((piece_to_melody[piece_id], note_counter[piece_id]))
    return keys


def value(row: dict[str, str], preferred: str, fallback: str) -> str:
    return row.get(preferred) or row.get(fallback) or ""


def add_model_columns(out: dict[str, str], label: str, item: dict[str, str], schema: str) -> None:
    if schema == "melody":
        out["idyom_melody_id"] = item["melody_id"]
        out["idyom_note_id"] = item["note_id"]
        out["idyom_cpitch"] = item["cpitch"]
        out["idyom_ic"] = item["ic"]
        out["idyom_entropy"] = item["entropy"]
        out["idyom_probability"] = item["probability"]
        out["idyom_order_ltm"] = item["order_ltm"]
        out["idyom_order_stm"] = item["order_stm"]
    elif schema == "harmony":
        out["idyom_melody_id"] = item["melody_id"]
        out["idyom_note_id"] = item["note_id"]
        out["idyom_cpitch"] = item["cpitch"]
        out["harmony_ic"] = item["ic"]
        out["harmony_entropy"] = item["entropy"]
        out["harmony_probability"] = item["probability"]
        out["harmony_order_ltm"] = item["order_ltm"]
        out["harmony_order_stm"] = item["order_stm"]
    else:
        prefix = f"idyom_{label}"
        out[f"{prefix}_ic"] = item["ic"]
        out[f"{prefix}_entropy"] = item["entropy"]
        out[f"{prefix}_probability"] = item["probability"]
        out[f"{prefix}_order_ltm"] = item["order_ltm"]
        out[f"{prefix}_order_stm"] = item["order_stm"]


def add_derived_columns(out: dict[str, str], schema: str) -> None:
    if schema != "pop":
        return
    both = to_float(out.get("idyom_both_plus_ic"))
    ltm = to_float(out.get("idyom_ltm_plus_ic"))
    if both is not None and ltm is not None:
        out["idyom_stm_delta_ic"] = str(both - ltm)


def to_float(value: str | None) -> float | None:
    try:
        if value in {None, "", "NA"}:
            return None
        return float(value)
    except ValueError:
        return None


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
