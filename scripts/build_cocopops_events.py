from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a CoCoPops melody event table from raw **kern/**harm files.")
    parser.add_argument("--cocopops-dir", default="datasets/raw/CoCoPops")
    parser.add_argument("--output", default="data/events_cocopops_pop.csv")
    args = parser.parse_args()

    root = Path(args.cocopops_dir)
    paths: list[tuple[str, Path]] = []
    billboard = root / "Billboard" / "Data"
    rollingstone = root / "RollingStone" / "Data"
    if billboard.exists():
        paths.extend(("cocopops_billboard", path) for path in sorted(billboard.glob("*.hum")))
    if rollingstone.exists():
        paths.extend(("cocopops_rollingstone", path) for path in sorted(rollingstone.glob("*.hum")))
    if not paths:
        raise ValueError(f"No CoCoPops .hum files found under {root}")

    rows: list[dict] = []
    composition_id = 0
    for source, path in paths:
        rows.extend(parse_piece(path, source, composition_id))
        composition_id += 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, rows)
    print(f"Wrote {len(rows)} CoCoPops melody events to {output}")


def parse_piece(path: Path, source: str, composition_id: int) -> list[dict]:
    spines: list[str] = []
    section_label = "unknown"
    previous_section = ""
    section_instance_by_label: dict[str, int] = {}
    current_section_instance = 0
    current_section_letter = ""
    note_id = 0
    onset = 0.0
    rows: list[dict] = []

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.rstrip("\n")
        if not line or line.startswith("!!"):
            continue
        fields = line.split("\t")
        if line.startswith("**"):
            spines = fields
            continue
        if not spines or len(fields) != len(spines):
            continue

        local_label = extract_section_label(fields)
        section_start = 0
        if local_label:
            previous_section = section_label
            section_label = local_label
            section_instance_by_label[section_label] = section_instance_by_label.get(section_label, 0) + 1
            current_section_instance = section_instance_by_label[section_label]
            current_section_letter = extract_section_letter(fields) or current_section_letter
            section_start = 1

        kern_index = first_spine(spines, "**kern")
        harm_index = first_spine(spines, "**harm")
        if kern_index is None:
            continue
        token = fields[kern_index]
        if token.startswith("*") or token.startswith("=") or token == ".":
            continue
        duration = kern_duration(token)
        pitches = kern_pitches(token)
        if duration is None:
            continue
        if not pitches:
            onset += duration
            continue

        chord = fields[harm_index] if harm_index is not None and harm_index < len(fields) else ""
        phrase_start = int(any("{" in field for field in fields))
        transition_label = transition(previous_section, section_label) if section_start else ""
        boundary_type = "+".join(
            part
            for part, flag in [("section_start", section_start), ("phrase_start", phrase_start)]
            if flag
        )
        if not boundary_type:
            boundary_type = "none"

        for pitch in pitches:
            rows.append({
                "composition_id_0": composition_id,
                "melody_id_1": composition_id + 1,
                "event_id_0": len(rows),
                "note_id_1": note_id + 1,
                "piece_id": f"{source}_{path.stem}",
                "source": source,
                "genre": "pop",
                "split": "train",
                "onset": onset,
                "pitch": pitch,
                "duration": duration,
                "chord": chord,
                "boundary": int(section_start or phrase_start),
                "section_label": section_label,
                "previous_section_label": previous_section if section_start else "",
                "transition_label": transition_label,
                "is_verse_chorus_transition": int(transition_label == "verse_to_chorus"),
                "is_prechorus_chorus_transition": int(transition_label == "pre_chorus_to_chorus"),
                "section_instance": current_section_instance,
                "section_letter": current_section_letter,
                "section_start": section_start,
                "phrase_start": phrase_start,
                "boundary_type": boundary_type,
                "source_file": str(path),
            })
            note_id += 1
        onset += duration
    return rows


def extract_section_label(fields: list[str]) -> str | None:
    text = " ".join(field for field in fields if field.startswith("*") or field.startswith("!"))
    match = re.search(r"(?:section|form|verse|chorus|bridge|intro|outro|pre[-_ ]?chorus)[^A-Za-z0-9]*([A-Za-z0-9_]*)", text, re.I)
    if not match and not any(word in text.lower() for word in ["verse", "chorus", "bridge", "intro", "outro"]):
        return None
    return normalize_section(text)


def extract_section_letter(fields: list[str]) -> str:
    text = " ".join(fields)
    match = re.search(r"\bsection\s*[:=]?\s*([A-Za-z])\b", text, re.I)
    return match.group(1).upper() if match else ""


def normalize_section(text: str) -> str:
    lower = text.lower().replace("-", "_").replace(" ", "_")
    if "pre_chorus" in lower or "prechorus" in lower:
        return "pre_chorus"
    if "chorus" in lower or "refrain" in lower:
        return "chorus"
    if "verse" in lower or "stanza" in lower:
        return "verse"
    if "bridge" in lower or "middle" in lower:
        return "bridge"
    if "intro" in lower:
        return "intro"
    if "outro" in lower or "coda" in lower:
        return "outro"
    return "other"


def transition(previous: str, current: str) -> str:
    if not previous:
        return f"unknown_to_{current}"
    if previous == current:
        return f"{current}_to_{current}"
    return f"{previous}_to_{current}"


def first_spine(spines: list[str], kind: str) -> int | None:
    for i, spine in enumerate(spines):
        if spine == kind:
            return i
    return None


def kern_duration(token: str) -> float | None:
    match = re.search(r"(\d+)", token)
    if not match:
        return None
    base = 4.0 / float(match.group(1))
    dots = token.count(".")
    add = base
    total = base
    for _ in range(dots):
        add /= 2.0
        total += add
    return total


def kern_pitches(token: str) -> list[int]:
    if "r" in token or token.startswith("*") or token.startswith("="):
        return []
    pitches = []
    for match in re.finditer(r"[A-Ga-g]+[#n-]*", token):
        text = match.group(0)
        letter = text[0]
        pc = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[letter.lower()]
        if "#" in text:
            pc += text.count("#")
        if "-" in text:
            pc -= text.count("-")
        if letter.islower():
            octave = 4 + len(re.match(r"[a-g]+", text).group(0)) - 1
        else:
            octave = 3 - (len(re.match(r"[A-G]+", text).group(0)) - 1)
        pitches.append((octave + 1) * 12 + pc)
    return pitches


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
