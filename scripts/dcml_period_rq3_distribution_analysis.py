from __future__ import annotations

import argparse
import csv
import math
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, group_by_piece
from music_surprisal.harmony_labels import simplify_chord
from music_surprisal.ngram import NGramModel, START
from scripts.build_dcml_events import parse_number
from scripts.dcml_period_time_series_analysis import (
    attach_periods,
    corpus_aliases,
    load_period_metadata,
    piece_prefixes,
)
from scripts.run_formal_experiment import load_events


NOTE_PCS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
MAJOR_DEGREE_PCS = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}
MINOR_DEGREE_PCS = {"I": 0, "II": 2, "III": 3, "IV": 5, "V": 7, "VI": 8, "VII": 10}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RQ3: melody surprisal distributions by harmony function and chord tone."
    )
    parser.add_argument("--events", default="data/events_dcml_classical.csv")
    parser.add_argument(
        "--metadata",
        default="datasets/raw/dcml/dcml_corpora/dcml_corpora.metadata.tsv",
    )
    parser.add_argument(
        "--expanded",
        default="datasets/raw/dcml/dcml_corpora/dcml_corpora.expanded.tsv",
    )
    parser.add_argument(
        "--output",
        default="output/formal_dcml_jtc_all_rq/dcml_period_rq3_distribution",
    )
    parser.add_argument("--order", type=int, default=3)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    period_meta = load_period_metadata(Path(args.metadata))
    events = attach_periods(load_events(args.events, sources={"dcml"}), period_meta)
    scoped_events = [
        event
        for event in events
        if event.genre in {"classical_period", "romantic_period"}
    ]
    chord_tones = load_chord_tone_lookup(Path(args.expanded))
    rows = build_distribution_rows(scoped_events, chord_tones, order=args.order)

    function_summary = summarize_by(rows, ["period", "chord_function"])
    function_effects = function_pair_effects(rows)
    chord_tone_summary = summarize_by(rows, ["period", "is_chord_tone"])
    chord_tone_effects = chord_tone_pair_effects(rows)
    mutual_information = mutual_information_rows(rows)

    write_csv(output / "rq3_distribution_events_sample.csv", rows[:100000])
    write_csv(output / "rq3_function_surprisal_summary.csv", function_summary)
    write_csv(output / "rq3_function_surprisal_effects.csv", function_effects)
    write_csv(output / "rq3_chord_tone_surprisal_summary.csv", chord_tone_summary)
    write_csv(output / "rq3_chord_tone_surprisal_effects.csv", chord_tone_effects)
    write_csv(output / "rq3_pitch_function_mutual_information.csv", mutual_information)

    draw_group_bars(
        function_summary,
        output / "rq3_function_surprisal_summary.svg",
        "RQ3 melody-only surprisal by harmonic function",
        "chord_function",
    )
    draw_group_bars(
        chord_tone_summary,
        output / "rq3_chord_tone_surprisal_summary.svg",
        "RQ3 melody-only surprisal by chord-tone status",
        "is_chord_tone",
    )
    draw_mi_bars(
        mutual_information,
        output / "rq3_pitch_function_mutual_information.svg",
    )
    write_summary(
        output / "RQ3_DISTRIBUTION_SUMMARY.md",
        rows,
        function_summary,
        function_effects,
        chord_tone_summary,
        chord_tone_effects,
        mutual_information,
    )
    write_index(output)
    print(f"Wrote DCML period RQ3 distribution analysis to {output}")


def build_distribution_rows(
    events: list[Event],
    chord_tones: dict[tuple[str, str], list[tuple[float, set[int]]]],
    *,
    order: int,
) -> list[dict]:
    train = [event for event in events if event.split == "train"]
    eval_events = [event for event in events if event.split != "train"]
    model = NGramModel(order=order).fit(
        [[event.pitch for event in piece] for piece in group_by_piece(train).values()]
    )

    rows: list[dict] = []
    for piece_id, piece_events in group_by_piece(eval_events).items():
        history: list[object] = [START] * (order - 1)
        corpus_piece = parse_dcml_piece_id(piece_id)
        tone_segments = chord_tones.get(corpus_piece, [])
        for index, event in enumerate(piece_events):
            surprisal = model.surprisal(event.pitch, history)
            function = simplify_chord(event.chord, "function")
            tone_pcs = lookup_chord_tones(tone_segments, event.onset)
            is_chord_tone = ""
            if tone_pcs:
                is_chord_tone = str(int(event.pitch % 12 in tone_pcs))
            rows.append(
                {
                    "piece_id": piece_id,
                    "period": event.genre,
                    "split": event.split,
                    "event_index": index,
                    "onset": event.onset,
                    "pitch": event.pitch,
                    "pitch_class": event.pitch % 12,
                    "raw_chord": event.chord,
                    "chord_function": function,
                    "is_chord_tone": is_chord_tone,
                    "surprisal": surprisal,
                    "boundary": int(event.boundary),
                }
            )
            history.append(event.pitch)
    return rows


def load_chord_tone_lookup(path: Path) -> dict[tuple[str, str], list[tuple[float, set[int]]]]:
    lookup: dict[tuple[str, str], list[tuple[float, set[int]]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if not row.get("quarterbeats") or not row.get("chord_tones"):
                continue
            tonic = local_tonic_pc(row)
            if tonic is None:
                continue
            pcs = fifth_coordinates_to_pcs(row["chord_tones"], tonic)
            if not pcs:
                continue
            key = (row["corpus"], row["piece"])
            lookup[key].append((parse_number(row["quarterbeats"]), pcs))
    return {key: sorted(values) for key, values in lookup.items()}


def local_tonic_pc(row: dict[str, str]) -> int | None:
    global_pc = key_pc(row.get("globalkey", ""))
    if global_pc is None:
        return None
    localkey = (row.get("localkey") or "I").strip()
    degree = roman_degree(localkey)
    if degree is None:
        return global_pc
    global_minor = row.get("globalkey_is_minor") == "1" or row.get("globalkey", "").islower()
    offsets = MINOR_DEGREE_PCS if global_minor else MAJOR_DEGREE_PCS
    return (global_pc + offsets.get(degree, 0)) % 12


def key_pc(key: str) -> int | None:
    key = key.strip()
    if not key:
        return None
    letter = key[0].upper()
    if letter not in NOTE_PCS:
        return None
    pc = NOTE_PCS[letter]
    for char in key[1:]:
        if char == "#":
            pc += 1
        elif char in {"b", "-"}:
            pc -= 1
    return pc % 12


def roman_degree(label: str) -> str | None:
    label = label.strip()
    for degree in ("VII", "VI", "IV", "III", "II", "V", "I"):
        if label.upper().lstrip("#b").startswith(degree):
            return degree
    return None


def fifth_coordinates_to_pcs(value: str, tonic_pc: int) -> set[int]:
    pcs: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            fifth_coord = int(item)
        except ValueError:
            continue
        pcs.add((tonic_pc + fifth_coord * 7) % 12)
    return pcs


def parse_dcml_piece_id(piece_id: str) -> tuple[str, str]:
    rest = piece_id.removeprefix("dcml_")
    corpus, piece = rest.split("_", 1)
    canonical_corpus = corpus_aliases().get(corpus, corpus)
    prefix = piece_prefixes().get(corpus, "")
    if prefix and piece.startswith(prefix):
        piece = piece[len(prefix) :]
    return canonical_corpus, piece


def lookup_chord_tones(segments: list[tuple[float, set[int]]], onset: float) -> set[int]:
    if not segments:
        return set()
    positions = [segment[0] for segment in segments]
    index = bisect_right(positions, onset) - 1
    return segments[index][1] if index >= 0 else segments[0][1]


def summarize_by(rows: list[dict], keys: list[str]) -> list[dict]:
    grouped: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        if any(row[key] == "" for key in keys):
            continue
        grouped[tuple(str(row[key]) for key in keys)].append(row)
    output: list[dict] = []
    for group_key, group_rows in sorted(grouped.items()):
        values = [float(row["surprisal"]) for row in group_rows]
        out = {key: value for key, value in zip(keys, group_key)}
        out.update(
            {
                "events": len(group_rows),
                "pieces": len({row["piece_id"] for row in group_rows}),
                "mean_surprisal": mean(values),
                "median_surprisal": median(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
            }
        )
        output.append(out)
    return output


def function_pair_effects(rows: list[dict]) -> list[dict]:
    return pair_effects(rows, "chord_function", [("D", "T"), ("S", "T"), ("D", "S")])


def chord_tone_pair_effects(rows: list[dict]) -> list[dict]:
    return pair_effects(rows, "is_chord_tone", [("0", "1")])


def pair_effects(rows: list[dict], key: str, pairs: list[tuple[str, str]]) -> list[dict]:
    output: list[dict] = []
    for period in ("classical_period", "romantic_period"):
        period_rows = [row for row in rows if row["period"] == period and row[key] != ""]
        for high, low in pairs:
            high_values = [float(row["surprisal"]) for row in period_rows if row[key] == high]
            low_values = [float(row["surprisal"]) for row in period_rows if row[key] == low]
            if not high_values or not low_values:
                continue
            output.append(
                {
                    "period": period,
                    "contrast": f"{high}_minus_{low}",
                    "higher_group": high,
                    "lower_group": low,
                    "higher_mean": mean(high_values),
                    "lower_mean": mean(low_values),
                    "difference": mean(high_values) - mean(low_values),
                    "cohens_d": cohens_d(low_values, high_values),
                    "higher_events": len(high_values),
                    "lower_events": len(low_values),
                }
            )
    return output


def mutual_information_rows(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    for period in ("all", "classical_period", "romantic_period"):
        selected = [
            row
            for row in rows
            if row["chord_function"] != "other"
            and (period == "all" or row["period"] == period)
        ]
        output.append(mutual_information_row(period, selected))
    return output


def mutual_information_row(period: str, rows: list[dict]) -> dict:
    pitch_counts = Counter(int(row["pitch_class"]) for row in rows)
    function_counts = Counter(str(row["chord_function"]) for row in rows)
    joint_counts = Counter(
        (int(row["pitch_class"]), str(row["chord_function"])) for row in rows
    )
    total = sum(pitch_counts.values())
    h_pitch = entropy(pitch_counts.values())
    h_pitch_given_function = 0.0
    for function, count in function_counts.items():
        local = [
            joint_count
            for (pitch, func), joint_count in joint_counts.items()
            if func == function
        ]
        h_pitch_given_function += count / total * entropy(local)
    mi = h_pitch - h_pitch_given_function
    return {
        "period": period,
        "events": total,
        "pitch_entropy": h_pitch,
        "pitch_entropy_given_function": h_pitch_given_function,
        "mutual_information_pitch_function": mi,
        "normalized_mi": mi / h_pitch if h_pitch else 0.0,
    }


def entropy(counts: object) -> float:
    values = [float(value) for value in counts if float(value) > 0]
    total = sum(values)
    return -sum((value / total) * math.log2(value / total) for value in values)


def cohens_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled = math.sqrt((pstdev(a) ** 2 + pstdev(b) ** 2) / 2)
    return (mean(b) - mean(a)) / pooled if pooled else 0.0


def draw_group_bars(rows: list[dict], output: Path, title: str, group_key: str) -> None:
    keep = [row for row in rows if row.get(group_key) != "other"]
    width, height = 860, 480
    left, right, top, bottom = 90, 40, 70, 80
    values = [float(row["mean_surprisal"]) for row in keep]
    ymin, ymax = min(values) - 0.25, max(values) + 0.25
    body = [
        f'<text class="title" x="55" y="40">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
    ]
    labels = [f"{row['period'].replace('_period', '')}:{row[group_key]}" for row in keep]
    bar_gap = (width - left - right) / max(1, len(keep))
    for index, row in enumerate(keep):
        value = float(row["mean_surprisal"])
        x = left + index * bar_gap + bar_gap * 0.18
        bar_width = bar_gap * 0.64
        y = sy(value, ymin, ymax, top, height - bottom)
        body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{height-bottom-y:.1f}" fill="{color(row["period"])}" rx="2"/>'
        )
        body.append(f'<text class="small" x="{x:.1f}" y="{y-6:.1f}">{value:.2f}</text>')
        body.append(
            f'<text class="small" transform="translate({x+bar_width/2:.1f} {height-55}) rotate(-35)" text-anchor="end">{escape(labels[index])}</text>'
        )
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_mi_bars(rows: list[dict], output: Path) -> None:
    width, height = 760, 380
    left, right, top, bottom = 90, 40, 65, 70
    values = [float(row["mutual_information_pitch_function"]) for row in rows]
    ymax = max(values) * 1.2 if values else 1.0
    body = [
        '<text class="title" x="55" y="38">RQ3 mutual information: pitch class and harmonic function</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
    ]
    bar_gap = (width - left - right) / max(1, len(rows))
    for index, row in enumerate(rows):
        value = float(row["mutual_information_pitch_function"])
        x = left + index * bar_gap + bar_gap * 0.22
        bar_width = bar_gap * 0.56
        y = sy(value, 0, ymax, top, height - bottom)
        body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{height-bottom-y:.1f}" fill="{color(row["period"])}" rx="2"/>'
        )
        body.append(f'<text class="small" x="{x:.1f}" y="{y-6:.1f}">{value:.3f}</text>')
        body.append(f'<text class="small" x="{x:.1f}" y="{height-45}">{escape(row["period"])}</text>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_summary(
    output: Path,
    rows: list[dict],
    function_summary: list[dict],
    function_effects: list[dict],
    chord_tone_summary: list[dict],
    chord_tone_effects: list[dict],
    mutual_information: list[dict],
) -> None:
    lines = [
        "# RQ3 Distribution-Based Harmony Summary",
        "",
        "This analysis keeps the melody-only n-gram surprisal fixed and asks whether surprisal differs across harmonic positions.",
        "It avoids the sparsity problem of directly conditioning the n-gram on detailed Roman numerals.",
        "",
        "## Coverage",
        "",
    ]
    for period in ("classical_period", "romantic_period"):
        period_rows = [row for row in rows if row["period"] == period]
        lines.append(
            f"- `{period}`: {len({row['piece_id'] for row in period_rows})} pieces, {len(period_rows)} events"
        )
    lines.extend(["", "## Harmonic Function", ""])
    for row in function_summary:
        lines.append(
            f"- `{row['period']}` / `{row['chord_function']}`: mean_surprisal={float(row['mean_surprisal']):.3f}, events={row['events']}"
        )
    lines.extend(["", "## Function Contrasts", ""])
    for row in function_effects:
        lines.append(
            f"- `{row['period']}` `{row['contrast']}`: diff={float(row['difference']):.3f}, d={float(row['cohens_d']):.3f}"
        )
    lines.extend(["", "## Chord Tone", ""])
    for row in chord_tone_summary:
        label = "chord_tone" if row["is_chord_tone"] == "1" else "non_chord_tone"
        lines.append(
            f"- `{row['period']}` / `{label}`: mean_surprisal={float(row['mean_surprisal']):.3f}, events={row['events']}"
        )
    lines.extend(["", "## Chord-Tone Contrasts", ""])
    for row in chord_tone_effects:
        lines.append(
            f"- `{row['period']}` non_chord_minus_chord: diff={float(row['difference']):.3f}, d={float(row['cohens_d']):.3f}"
        )
    lines.extend(["", "## Mutual Information", ""])
    for row in mutual_information:
        lines.append(
            f"- `{row['period']}`: I(pitch_class; function)={float(row['mutual_information_pitch_function']):.4f} bits, normalized={float(row['normalized_mi']):.4f}"
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def write_index(output: Path) -> None:
    svgs = sorted(path.name for path in output.glob("*.svg"))
    links = "\n".join(f'<li><a href="{name}">{name}</a></li>' for name in svgs)
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>RQ3 Distribution Figures</title>
<body style="font-family:Arial,Helvetica,sans-serif;max-width:900px;margin:40px auto;line-height:1.5">
<h1>RQ3 Distribution Figures</h1>
<ul>
{links}
</ul>
</body>
</html>
"""
    (output / "index.html").write_text(html, encoding="utf-8")


def sy(value: float, ymin: float, ymax: float, top: float, bottom: float) -> float:
    return top + (ymax - value) / (ymax - ymin) * (bottom - top)


def color(period: str) -> str:
    return {
        "classical_period": "#2f6f9f",
        "romantic_period": "#b84a6b",
        "all": "#58606e",
    }.get(period, "#555")


def svg_wrap(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #1d252c; }}
    .title {{ font-size: 20px; font-weight: 700; }}
    .small {{ font-size: 11px; fill: #52606d; }}
    .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
  </style>
{body}
</svg>
"""


def escape(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
