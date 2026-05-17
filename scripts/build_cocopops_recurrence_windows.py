from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CoCoPops recurrence windows for the popular-music IDyOM analyses.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output", default="output/idyom_cocopops_melody/cocopops_recurrence_gain_windows.csv")
    parser.add_argument("--window-before", type=int, default=8)
    parser.add_argument("--window-after", type=int, default=8)
    parser.add_argument("--ordinary-length", type=int, default=9)
    args = parser.parse_args()

    rows = read_events(Path(args.events))
    out: list[dict[str, object]] = []
    for piece_id, piece_rows in group_by(rows, "piece_id").items():
        piece_rows.sort(key=lambda row: (float(row["onset"]), int(row["note_id_1"])))
        add_section_recurrences(out, piece_rows, piece_id, args.window_before, args.window_after)
        add_ordinary_fragment(out, piece_rows, piece_id, args.ordinary_length)

    write_csv(Path(args.output), out)
    print(f"Wrote {len(out)} CoCoPops recurrence-window rows to {args.output}")


def read_events(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    piece_to_id = {piece: index for index, piece in enumerate(sorted({row["piece_id"] for row in rows}))}
    counters: dict[str, int] = defaultdict(int)
    for row in rows:
        piece = row["piece_id"]
        counters[piece] += 1
        row.setdefault("composition_id_0", str(piece_to_id[piece]))
        row.setdefault("melody_id_1", str(piece_to_id[piece] + 1))
        row.setdefault("event_id_0", str(counters[piece] - 1))
        row.setdefault("note_id_1", str(counters[piece]))
    return rows


def add_section_recurrences(out: list[dict[str, object]], rows: list[dict[str, str]], piece_id: str, before: int, after: int) -> None:
    section_starts = [idx for idx, row in enumerate(rows) if truthy(row.get("section_start"))]
    sections: dict[str, list[int]] = defaultdict(list)
    for idx in section_starts:
        label = normalize_section(rows[idx].get("section_label", ""))
        if label in {"verse", "chorus"}:
            sections[label].append(idx)

    for label, starts in sections.items():
        if len(starts) < 2:
            continue
        first, second = starts[0], starts[1]
        first_global = 1
        second_global = 2
        for offset in range(-before, after + 1):
            i = first + offset
            j = second + offset
            if i < 0 or j < 0 or i >= len(rows) or j >= len(rows):
                continue
            out.append(make_window_row(rows, i, j, piece_id, "section", label, offset, first_global, second_global))


def add_ordinary_fragment(out: list[dict[str, object]], rows: list[dict[str, str]], piece_id: str, length: int) -> None:
    if len(rows) < length * 2:
        return
    by_fragment: dict[tuple[int, ...], int] = {}
    section_start_notes = {int(row["note_id_1"]) for row in rows if truthy(row.get("section_start"))}
    for start in range(0, len(rows) - length + 1):
        if int(rows[start]["note_id_1"]) in section_start_notes:
            continue
        fragment = tuple(int(float(row["pitch"])) for row in rows[start:start + length])
        first = by_fragment.get(fragment)
        if first is None:
            by_fragment[fragment] = start
            continue
        if start - first < length:
            continue
        for offset in range(length):
            out.append(make_window_row(rows, first + offset, start + offset, piece_id, "ordinary_fragment", "ordinary", offset, 1, 2))
        return


def make_window_row(
    rows: list[dict[str, str]],
    first_idx: int,
    second_idx: int,
    piece_id: str,
    recurrence_type: str,
    section_label: str,
    offset: int,
    first_global: int,
    second_global: int,
) -> dict[str, object]:
    first = rows[first_idx]
    second = rows[second_idx]
    first_pitch = int(float(first["pitch"]))
    second_pitch = int(float(second["pitch"]))
    song_start = float(rows[0]["onset"])
    song_end = max(float(row["onset"]) for row in rows) or 1.0
    first_pos = normalized_position(float(first["onset"]), song_start, song_end)
    second_pos = normalized_position(float(second["onset"]), song_start, song_end)
    return {
        "piece_id": piece_id,
        "source": first.get("source", ""),
        "recurrence_type": recurrence_type,
        "section_label": section_label,
        "offset": offset,
        "first_note_id_1": first["note_id_1"],
        "second_note_id_1": second["note_id_1"],
        "first_transition_label": first.get("transition_label", ""),
        "second_transition_label": second.get("transition_label", ""),
        "first_previous_section_label": first.get("previous_section_label", ""),
        "second_previous_section_label": second.get("previous_section_label", ""),
        "fragment": "",
        "first_global_occurrence": first_global,
        "second_global_occurrence": second_global,
        "repeat_distance": int(second["note_id_1"]) - int(first["note_id_1"]),
        "first_onset_position": first_pos,
        "second_onset_position": second_pos,
        "mean_onset_position": (first_pos + second_pos) / 2.0,
        "first_pitch": first_pitch,
        "second_pitch": second_pitch,
        "pitch_match": float(first_pitch == second_pitch),
        "pitch_abs_diff": abs(first_pitch - second_pitch),
        "pitch_similarity": max(0.0, 1.0 - abs(first_pitch - second_pitch) / 12.0),
    }


def normalized_position(onset: float, start: float, end: float) -> float:
    return (onset - start) / max(1e-9, end - start)


def normalize_section(value: str) -> str:
    value = value.lower().strip()
    if "chorus" in value or "refrain" in value:
        return "chorus"
    if "verse" in value:
        return "verse"
    return value


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[row[key]].append(row)
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
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
