from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats


MAIN_SECTIONS = ["intro", "verse", "pre_chorus", "chorus", "bridge", "outro"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Combine three original Lisp IDyOM runs into harmony-conditioned cpitch IC: "
            "IC(cpitch | chord) = IC(chord, cpitch) - IC(chord)."
        )
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--cpitch-dat", required=True)
    parser.add_argument("--chord-dat", required=True)
    parser.add_argument("--joint-dat", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-title", default="Original IDyOM Harmony-Conditioned Cpitch")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = read_csv(Path(args.events))
    cpitch = read_idyom_dat(Path(args.cpitch_dat))
    chord = read_idyom_dat(Path(args.chord_dat))
    joint = read_idyom_dat(Path(args.joint_dat))

    merged = merge_events(events, cpitch, chord, joint)
    event_path = output_dir / "original_idyom_harmony_conditioned_event_ic.csv"
    section_path = output_dir / "original_idyom_harmony_conditioned_section_summary.csv"
    contrast_path = output_dir / "original_idyom_harmony_conditioned_bridge_contrasts.csv"
    report_path = output_dir / "ORIGINAL_IDYOM_HARMONY_CONDITIONED_REPORT.md"

    section_summary = summarize_by_section(merged)
    bridge_contrasts = bridge_contrast_tests(merged)
    write_csv(event_path, merged)
    write_csv(section_path, section_summary)
    write_csv(contrast_path, bridge_contrasts)
    write_report(report_path, args.report_title, merged, section_summary, bridge_contrasts)
    print(f"Wrote {event_path}")
    print(f"Wrote {report_path}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_idyom_dat(path: Path) -> dict[tuple[str, int], dict[str, float]]:
    out: dict[tuple[str, int], dict[str, float]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            melody_name = (row.get("melody.name") or "").strip('"')
            if not melody_name or melody_name.upper() == "NIL":
                continue
            note_id = int(float(row["note.id"]))
            out[(melody_name, note_id)] = {
                "ic": parse_float(row.get("ic") or row.get("cpitch.ic")),
                "entropy": parse_float(row.get("entropy") or row.get("cpitch.entropy")),
                "probability": parse_float(row.get("probability") or row.get("cpitch.probability")),
            }
    return out


def merge_events(
    events: list[dict[str, str]],
    cpitch: dict[tuple[str, int], dict[str, float]],
    chord: dict[tuple[str, int], dict[str, float]],
    joint: dict[tuple[str, int], dict[str, float]],
) -> list[dict[str, object]]:
    note_ids = infer_note_ids(events)
    merged: list[dict[str, object]] = []
    missing = 0
    for row, note_id in zip(events, note_ids):
        piece_id = row["piece_id"]
        key = (piece_id, note_id)
        cp = cpitch.get(key)
        ch = chord.get(key)
        jo = joint.get(key)
        if cp is None or ch is None or jo is None:
            missing += 1
            continue
        ic_cond = jo["ic"] - ch["ic"]
        ent_cond = jo["entropy"] - ch["entropy"]
        out: dict[str, object] = dict(row)
        out["note_id_1"] = note_id
        out["section_group"] = section_group(row.get("section_label", ""))
        out["idyom_ic_cpitch_only"] = cp["ic"]
        out["idyom_entropy_cpitch_only"] = cp["entropy"]
        out["idyom_ic_chord"] = ch["ic"]
        out["idyom_entropy_chord"] = ch["entropy"]
        out["idyom_ic_chord_cpitch_joint"] = jo["ic"]
        out["idyom_entropy_chord_cpitch_joint"] = jo["entropy"]
        out["idyom_ic_cpitch_given_chord"] = ic_cond
        out["idyom_entropy_cpitch_given_chord"] = ent_cond
        out["idyom_harmony_gain"] = cp["ic"] - ic_cond
        merged.append(out)
    if missing:
        print(f"Skipped {missing} events missing one or more IDyOM rows")
    return merged


def infer_note_ids(rows: list[dict[str, str]]) -> list[int]:
    counters: dict[str, int] = {}
    out = []
    for row in rows:
        piece_id = row["piece_id"]
        counters[piece_id] = counters.get(piece_id, 0) + 1
        out.append(counters[piece_id])
    return out


def summarize_by_section(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    song_section: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        section = str(row["section_group"])
        if section in MAIN_SECTIONS:
            song_section[(str(row["piece_id"]), str(row.get("source", "")), section)].append(row)

    song_means: dict[tuple[str, str, str], dict[str, float]] = {}
    metrics = [
        "idyom_ic_cpitch_only",
        "idyom_ic_cpitch_given_chord",
        "idyom_harmony_gain",
        "idyom_entropy_cpitch_only",
        "idyom_entropy_cpitch_given_chord",
    ]
    for key, items in song_section.items():
        song_means[key] = {metric: float(np.mean([float(item[metric]) for item in items])) for metric in metrics}

    out = []
    for source in sorted({key[1] for key in song_means} | {"ALL"}):
        subset = song_means if source == "ALL" else {key: val for key, val in song_means.items() if key[1] == source}
        for section in MAIN_SECTIONS:
            for metric in metrics:
                values = np.array([val[metric] for key, val in subset.items() if key[2] == section], dtype=float)
                if len(values) < 2:
                    continue
                lo, hi = ci95(values)
                out.append({
                    "source": source,
                    "section_group": section,
                    "metric": metric,
                    "n_songs": len(values),
                    "mean": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                })
    return out


def bridge_contrast_tests(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    section_summary = summarize_song_section(rows)
    metrics = ["idyom_ic_cpitch_only", "idyom_ic_cpitch_given_chord", "idyom_harmony_gain"]
    out = []
    for source in sorted({key[1] for key in section_summary} | {"ALL"}):
        subset = section_summary if source == "ALL" else {key: val for key, val in section_summary.items() if key[1] == source}
        piece_ids = sorted({key[0] for key in subset})
        for comparator in ["verse", "chorus"]:
            for metric in metrics:
                diffs = []
                for piece_id in piece_ids:
                    src = next((key[1] for key in subset if key[0] == piece_id), "")
                    bridge = subset.get((piece_id, src, "bridge"))
                    comp = subset.get((piece_id, src, comparator))
                    if bridge is not None and comp is not None:
                        diffs.append(bridge[metric] - comp[metric])
                if len(diffs) < 2:
                    continue
                values = np.array(diffs, dtype=float)
                lo, hi = ci95(values)
                t, p = stats.ttest_1samp(values, 0.0)
                out.append({
                    "source": source,
                    "contrast": f"bridge_minus_{comparator}",
                    "metric": metric,
                    "n_songs": len(values),
                    "mean_difference": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "t": float(t),
                    "p": float(p),
                })
    return out


def summarize_song_section(rows: list[dict[str, object]]) -> dict[tuple[str, str, str], dict[str, float]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    metrics = ["idyom_ic_cpitch_only", "idyom_ic_cpitch_given_chord", "idyom_harmony_gain"]
    for row in rows:
        section = str(row["section_group"])
        if section in MAIN_SECTIONS:
            grouped[(str(row["piece_id"]), str(row.get("source", "")), section)].append(row)
    return {
        key: {metric: float(np.mean([float(item[metric]) for item in items])) for metric in metrics}
        for key, items in grouped.items()
    }


def write_report(
    path: Path,
    title: str,
    rows: list[dict[str, object]],
    section_summary: list[dict[str, object]],
    bridge_contrasts: list[dict[str, object]],
) -> None:
    lines = [
        f"# {title}",
        "",
        "This is an original Lisp IDyOM implementation of harmony-conditioned cpitch IC.",
        "",
        "Formula:",
        "",
        "```text",
        "IC(cpitch | chord, past) ~= IC(chord, cpitch | past) - IC(chord | past)",
        "Harmony gain = IC(cpitch-only) - IC(cpitch | chord)",
        "```",
        "",
        "Implementation note: chord and chord+cpitch are encoded as symbolic CPITCH vocabularies before being passed to original IDyOM. Section labels are used only after scoring.",
        "",
        f"- Event rows scored: {len(rows)}",
        f"- Songs scored: {len(set(str(row['piece_id']) for row in rows))}",
        "",
        "## Mean By Section",
        "",
        "| Section | Cpitch-only IC | Cpitch given chord IC | Harmony gain |",
        "|---|---:|---:|---:|",
    ]
    for section in MAIN_SECTIONS:
        cp = lookup(section_summary, section, "idyom_ic_cpitch_only")
        cond = lookup(section_summary, section, "idyom_ic_cpitch_given_chord")
        gain = lookup(section_summary, section, "idyom_harmony_gain")
        if cp and cond and gain:
            lines.append(f"| {section} | {fmt_ci(cp)} | {fmt_ci(cond)} | {fmt_ci(gain)} |")
    lines.extend([
        "",
        "## Bridge Contrasts",
        "",
        "| Contrast | Metric | N | Difference [95% CI] | p |",
        "|---|---|---:|---:|---:|",
    ])
    for row in bridge_contrasts:
        if row["source"] != "ALL":
            continue
        lines.append(
            f"| {row['contrast']} | {row['metric']} | {row['n_songs']} | "
            f"{fmt(row['mean_difference'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def lookup(summary: list[dict[str, object]], section: str, metric: str) -> dict[str, object] | None:
    return next(
        (
            row
            for row in summary
            if row["source"] == "ALL" and row["section_group"] == section and row["metric"] == metric
        ),
        None,
    )


def section_group(value: str) -> str:
    value = value.lower().strip().replace("-", "_").replace(" ", "_") or "unknown"
    if "pre_chorus" in value or "prechorus" in value:
        return "pre_chorus"
    if "chorus" in value or "refrain" in value:
        return "chorus"
    if value.startswith("verse") or value in {"vp", "vp2"}:
        return "verse"
    if value in {"bridge", "b", "bp"}:
        return "bridge"
    if value in {"intro", "instrumental"}:
        return "intro"
    if value in {"outro", "fadeout", "coda"}:
        return "outro"
    return "other"


def parse_float(value: str | None) -> float:
    if value in {None, "", "NA"}:
        return float("nan")
    return float(value)


def ci95(values: np.ndarray) -> tuple[float, float]:
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean
    half_width = float(stats.t.ppf(0.975, len(values) - 1) * values.std(ddof=1) / math.sqrt(len(values)))
    return mean - half_width, mean + half_width


def fmt(value: object) -> str:
    value = float(value)
    return "nan" if math.isnan(value) else f"{value:.3f}"


def fmt_p(value: object) -> str:
    value = float(value)
    if math.isnan(value):
        return "nan"
    return "<.001" if value < 0.001 else f"{value:.3f}"


def fmt_ci(row: dict[str, object]) -> str:
    return f"{fmt(row['mean'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}]"


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
