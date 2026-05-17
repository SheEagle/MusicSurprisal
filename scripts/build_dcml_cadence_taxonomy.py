from __future__ import annotations

import argparse
import csv
from fractions import Fraction
from pathlib import Path


CADENCES = {"PAC", "IAC", "HC", "DC", "EC"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a DCML cadence taxonomy CSV from raw DCML harmony annotations.")
    parser.add_argument("--dcml-dir", default="datasets/raw/dcml/dcml_corpora")
    parser.add_argument("--output", default="output/formal_dcml_jtc_pop909_slms_all_rq/boundary_taxonomy/dcml_boundary_taxonomy.csv")
    args = parser.parse_args()

    path = Path(args.dcml_dir) / "dcml_corpora.expanded.tsv"
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            cadence = normalize_cadence(row.get("cadence", ""))
            if cadence not in CADENCES:
                continue
            if not row.get("quarterbeats"):
                continue
            corpus = row["corpus"]
            piece = row["piece"]
            onset = parse_number(row["quarterbeats"])
            rows.append({
                "corpus": corpus,
                "piece": piece,
                "piece_id": f"dcml_{corpus}_{piece}",
                "onset": onset,
                "cadence_type": cadence,
                "boundary_family": "cadence",
                "raw_cadence": row.get("cadence", ""),
                "phraseend": row.get("phraseend", ""),
            })

    write_csv(Path(args.output), rows)
    print(f"Wrote {len(rows)} DCML cadence taxonomy rows to {args.output}")


def normalize_cadence(value: str) -> str:
    value = value.strip().upper()
    for cadence in CADENCES:
        if value == cadence or value.startswith(cadence + ".") or value.startswith(cadence + "_"):
            return cadence
    return ""


def parse_number(value: str) -> float:
    value = value.strip()
    if "/" in value:
        return float(Fraction(value))
    return float(value)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["corpus", "piece", "piece_id", "onset", "cadence_type", "boundary_family", "raw_cadence", "phraseend"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
