from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pop_monte_carlo_future_horizon import CpitchVOM, assign_folds, ci95, write_csv


START = "<s>"
MAIN_SECTIONS = ["intro", "verse", "pre_chorus", "chorus", "bridge", "outro"]
MODEL_LABELS = {
    "ic_cpitch_only": "Cpitch-only",
    "ic_harmony": "Harmony-conditioned",
}


@dataclass
class EventIC:
    piece_id: str
    source: str
    fold: int
    event_index: int
    onset: float
    cpitch: int
    chord: str
    section_label: str
    section_group: str
    section_instance: int
    section_position: int
    section_start: int
    ic_cpitch_only: float
    entropy_cpitch_only: float
    ic_harmony: float
    entropy_harmony: float
    harmony_gain: float


class HarmonyConditionedVOM:
    def __init__(self, max_order: int = 8, alpha: float = 0.1, vocab: set[int] | None = None) -> None:
        self.max_order = max_order
        self.alpha = alpha
        self.vocab = sorted(vocab or [])
        self.vocab_index = {note: idx for idx, note in enumerate(self.vocab)}
        self.counts: dict[tuple[object, ...], Counter[int]] = defaultdict(Counter)
        self._cache: dict[tuple[object, ...], tuple[list[float], float]] = {}

    def fit(self, songs: list[dict]) -> "HarmonyConditionedVOM":
        if not self.vocab:
            self.vocab = sorted({note for song in songs for note in song["cpitch"]})
            self.vocab_index = {note: idx for idx, note in enumerate(self.vocab)}
        for song in songs:
            pitches = song["cpitch"]
            chords = song["chords"]
            for idx, note in enumerate(pitches):
                self._update(note, pitches[:idx], chords[:idx], chords[idx])
        return self

    def _update(self, note: int, pitch_history: list[int], chord_history: list[str], current_chord: str) -> None:
        max_order = min(self.max_order, len(pitch_history))
        for order in range(max_order + 1):
            context = self._context(pitch_history, chord_history, current_chord, order)
            self.counts[context][note] += 1

    def _context(self, pitch_history: list[int], chord_history: list[str], current_chord: str, order: int) -> tuple[object, ...]:
        if order == 0:
            return (("current_chord", current_chord),)
        pairs = tuple(zip(pitch_history[-order:], chord_history[-order:]))
        return (("current_chord", current_chord),) + pairs

    def distribution(self, pitch_history: list[int], chord_history: list[str], current_chord: str) -> tuple[list[float], float]:
        key = self._context(pitch_history[-self.max_order :], chord_history[-self.max_order :], current_chord, min(self.max_order, len(pitch_history)))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        counter = None
        for order in range(min(self.max_order, len(pitch_history)), -1, -1):
            context = self._context(pitch_history, chord_history, current_chord, order)
            if context in self.counts:
                counter = self.counts[context]
                break
        probs, ent = smoothed_distribution(counter, self.vocab, self.alpha)
        self._cache[key] = (probs, ent)
        return probs, ent

    def score_event(self, note: int, pitch_history: list[int], chord_history: list[str], current_chord: str) -> tuple[float, float]:
        probs, ent = self.distribution(pitch_history, chord_history, current_chord)
        idx = self.vocab_index.get(note)
        p = probs[idx] if idx is not None else 1.0 / max(1, len(self.vocab))
        return -math.log2(max(p, 1e-12)), ent


def main() -> None:
    parser = argparse.ArgumentParser(description="Harmony-conditioned cpitch IC for CoCoPops.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output-dir", default="output/pop_music_idyom_pipeline/harmony_conditioned_cpitch")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-order", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    songs = load_songs(Path(args.events))
    assign_folds(songs, args.folds, args.seed)
    rows = score_events(songs, args)
    row_dicts = [row.__dict__ for row in rows]
    write_csv(output_dir / "harmony_conditioned_event_ic.csv", row_dicts)

    section_summary = summarize_by_section(rows)
    bridge_contrasts = bridge_contrast_tests(rows)
    return_effects = return_effect_tests(rows)
    onset_windows = build_onset_windows(rows)
    write_csv(output_dir / "harmony_conditioned_section_summary.csv", section_summary)
    write_csv(output_dir / "harmony_conditioned_bridge_contrasts.csv", bridge_contrasts)
    write_csv(output_dir / "harmony_conditioned_return_effects.csv", return_effects)
    write_csv(output_dir / "harmony_conditioned_onset_windows.csv", onset_windows)

    plot_section_ic(section_summary, output_dir / "section_mean_ic.svg", output_dir / "section_mean_ic.png")
    plot_harmony_gain(section_summary, output_dir / "section_harmony_gain.svg", output_dir / "section_harmony_gain.png")
    plot_onset_windows(onset_windows, output_dir / "section_onset_ic_curve.svg", output_dir / "section_onset_ic_curve.png")
    write_report(output_dir / "HARMONY_CONDITIONED_CPITCH_REPORT.md", songs, args, section_summary, bridge_contrasts, return_effects)
    print(f"Wrote harmony-conditioned cpitch outputs to {output_dir}")


def load_songs(path: Path) -> list[dict]:
    by_piece: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_piece[row["piece_id"]].append(row)
    songs = []
    for piece_id, rows in sorted(by_piece.items()):
        rows.sort(key=lambda row: (float(row["onset"]), int(float(row.get("event_index") or 0))))
        section_positions = section_position_indices(rows)
        songs.append({
            "piece_id": piece_id,
            "source": rows[0].get("source", ""),
            "rows": rows,
            "cpitch": [int(float(row["pitch"])) for row in rows],
            "chords": [normalize_chord(row.get("chord", "")) for row in rows],
            "section_positions": section_positions,
        })
    return songs


def section_position_indices(rows: list[dict[str, str]]) -> list[int]:
    out = []
    pos = -1
    current_key = None
    for row in rows:
        key = (normalize_section(row.get("section_label", "")), int(float(row.get("section_instance") or 0)))
        if truthy(row.get("section_start")) or key != current_key:
            current_key = key
            pos = 0
        else:
            pos += 1
        out.append(pos)
    return out


def score_events(songs: list[dict], args: argparse.Namespace) -> list[EventIC]:
    vocab = {note for song in songs for note in song["cpitch"]}
    out = []
    for fold in range(args.folds):
        train = [song for song in songs if song["fold"] != fold]
        test = [song for song in songs if song["fold"] == fold]
        cpitch_model = CpitchVOM(args.max_order, args.alpha).fit([song["cpitch"] for song in train])
        harmony_model = HarmonyConditionedVOM(args.max_order, args.alpha, vocab).fit(train)
        print(f"Scoring fold {fold + 1}/{args.folds} with {len(test)} test songs")
        for song in test:
            out.extend(score_song(song, cpitch_model, harmony_model))
    return out


def score_song(song: dict, cpitch_model: CpitchVOM, harmony_model: HarmonyConditionedVOM) -> list[EventIC]:
    out = []
    pitch_history: list[int] = []
    chord_history: list[str] = []
    for idx, row in enumerate(song["rows"]):
        note = int(float(row["pitch"]))
        chord = normalize_chord(row.get("chord", ""))
        probs, ent_cpitch = cpitch_model.distribution(pitch_history)
        note_index = cpitch_model.vocab_index.get(note)
        p_cpitch = probs[note_index] if note_index is not None else 1.0 / max(1, len(cpitch_model.vocab))
        ic_cpitch = -math.log2(max(p_cpitch, 1e-12))
        ic_harmony, ent_harmony = harmony_model.score_event(note, pitch_history, chord_history, chord)
        section_label = normalize_section(row.get("section_label", ""))
        out.append(EventIC(
            piece_id=song["piece_id"],
            source=song["source"],
            fold=song["fold"],
            event_index=int(float(row.get("event_index") or idx)),
            onset=float(row.get("onset") or 0.0),
            cpitch=note,
            chord=chord,
            section_label=section_label,
            section_group=section_group(section_label),
            section_instance=int(float(row.get("section_instance") or 0)),
            section_position=song["section_positions"][idx],
            section_start=1 if truthy(row.get("section_start")) else 0,
            ic_cpitch_only=ic_cpitch,
            entropy_cpitch_only=ent_cpitch,
            ic_harmony=ic_harmony,
            entropy_harmony=ent_harmony,
            harmony_gain=ic_cpitch - ic_harmony,
        ))
        pitch_history.append(note)
        chord_history.append(chord)
    return out


def summarize_by_section(rows: list[EventIC]) -> list[dict[str, object]]:
    song_section = aggregate_song_section(rows)
    out = []
    for source in sorted({key[1] for key in song_section} | {"ALL"}):
        source_items = song_section if source == "ALL" else {key: val for key, val in song_section.items() if key[1] == source}
        for section in MAIN_SECTIONS:
            values_by_metric = defaultdict(list)
            for (piece_id, _, section_group_name), metrics in source_items.items():
                if section_group_name == section:
                    for metric, value in metrics.items():
                        values_by_metric[metric].append(value)
            for metric in ["ic_cpitch_only", "ic_harmony", "harmony_gain", "entropy_cpitch_only", "entropy_harmony"]:
                values = np.array(values_by_metric.get(metric, []), dtype=float)
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


def aggregate_song_section(rows: list[EventIC]) -> dict[tuple[str, str, str], dict[str, float]]:
    grouped: dict[tuple[str, str, str], list[EventIC]] = defaultdict(list)
    for row in rows:
        if row.section_group in MAIN_SECTIONS:
            grouped[(row.piece_id, row.source, row.section_group)].append(row)
    out = {}
    for key, items in grouped.items():
        out[key] = {
            "ic_cpitch_only": float(np.mean([row.ic_cpitch_only for row in items])),
            "ic_harmony": float(np.mean([row.ic_harmony for row in items])),
            "harmony_gain": float(np.mean([row.harmony_gain for row in items])),
            "entropy_cpitch_only": float(np.mean([row.entropy_cpitch_only for row in items])),
            "entropy_harmony": float(np.mean([row.entropy_harmony for row in items])),
        }
    return out


def bridge_contrast_tests(rows: list[EventIC]) -> list[dict[str, object]]:
    song_section = aggregate_song_section(rows)
    out = []
    for source in sorted({key[1] for key in song_section} | {"ALL"}):
        source_items = song_section if source == "ALL" else {key: val for key, val in song_section.items() if key[1] == source}
        piece_ids = sorted({key[0] for key in source_items})
        for comparator in ["verse", "chorus"]:
            for metric in ["ic_cpitch_only", "ic_harmony", "harmony_gain"]:
                diffs = []
                for piece_id in piece_ids:
                    bridge = source_items.get((piece_id, source_items_key_source(source_items, piece_id), "bridge"))
                    comp = source_items.get((piece_id, source_items_key_source(source_items, piece_id), comparator))
                    if bridge is None or comp is None:
                        continue
                    diffs.append(bridge[metric] - comp[metric])
                if len(diffs) < 2:
                    continue
                values = np.array(diffs, dtype=float)
                lo, hi = ci95(values)
                t, p = ttest(values)
                out.append({
                    "source": source,
                    "contrast": f"bridge_minus_{comparator}",
                    "metric": metric,
                    "n_songs": len(values),
                    "mean_difference": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "t": t,
                    "p": p,
                })
    return out


def source_items_key_source(items: dict[tuple[str, str, str], dict[str, float]], piece_id: str) -> str:
    for key in items:
        if key[0] == piece_id:
            return key[1]
    return ""


def return_effect_tests(rows: list[EventIC]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, int], list[EventIC]] = defaultdict(list)
    for row in rows:
        if row.section_group in {"verse", "chorus", "bridge"} and row.section_instance in {1, 2}:
            grouped[(row.piece_id, row.source, row.section_group, row.section_instance)].append(row)
    means = {}
    for key, items in grouped.items():
        means[key] = {
            "ic_cpitch_only": float(np.mean([row.ic_cpitch_only for row in items])),
            "ic_harmony": float(np.mean([row.ic_harmony for row in items])),
            "harmony_gain": float(np.mean([row.harmony_gain for row in items])),
        }
    out = []
    for source in sorted({key[1] for key in means} | {"ALL"}):
        source_means = means if source == "ALL" else {key: val for key, val in means.items() if key[1] == source}
        piece_ids = sorted({key[0] for key in source_means})
        for section in ["verse", "chorus", "bridge"]:
            for metric in ["ic_cpitch_only", "ic_harmony", "harmony_gain"]:
                diffs = []
                for piece_id in piece_ids:
                    src = source_items_key_source(source_means, piece_id)
                    first = source_means.get((piece_id, src, section, 1))
                    second = source_means.get((piece_id, src, section, 2))
                    if first is None or second is None:
                        continue
                    diffs.append(first[metric] - second[metric])
                if len(diffs) < 2:
                    continue
                values = np.array(diffs, dtype=float)
                lo, hi = ci95(values)
                t, p = ttest(values)
                out.append({
                    "source": source,
                    "section_group": section,
                    "metric": metric,
                    "n_songs": len(values),
                    "mean_first_minus_second": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "t": t,
                    "p": p,
                })
    return out


def build_onset_windows(rows: list[EventIC], left: int = -8, right: int = 8) -> list[dict[str, object]]:
    by_piece: dict[str, list[EventIC]] = defaultdict(list)
    for row in rows:
        by_piece[row.piece_id].append(row)
    samples = []
    for piece_rows in by_piece.values():
        piece_rows.sort(key=lambda row: row.event_index)
        for idx, row in enumerate(piece_rows):
            if not row.section_start or row.section_group not in {"verse", "chorus", "bridge"}:
                continue
            for offset in range(left, right + 1):
                pos = idx + offset
                if pos < 0 or pos >= len(piece_rows):
                    continue
                target = piece_rows[pos]
                samples.append({
                    "piece_id": row.piece_id,
                    "source": row.source,
                    "section_group": row.section_group,
                    "offset": offset,
                    "ic_cpitch_only": target.ic_cpitch_only,
                    "ic_harmony": target.ic_harmony,
                    "harmony_gain": target.harmony_gain,
                })
    out = []
    for source in sorted({sample["source"] for sample in samples} | {"ALL"}):
        source_samples = samples if source == "ALL" else [sample for sample in samples if sample["source"] == source]
        for section in ["verse", "chorus", "bridge"]:
            for offset in range(left, right + 1):
                subset = [sample for sample in source_samples if sample["section_group"] == section and sample["offset"] == offset]
                if len(subset) < 2:
                    continue
                for metric in ["ic_cpitch_only", "ic_harmony", "harmony_gain"]:
                    values = np.array([sample[metric] for sample in subset], dtype=float)
                    lo, hi = ci95(values)
                    out.append({
                        "source": source,
                        "section_group": section,
                        "offset": offset,
                        "metric": metric,
                        "n_events": len(values),
                        "mean": values.mean(),
                        "ci95_low": lo,
                        "ci95_high": hi,
                    })
    return out


def plot_section_ic(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in summary if row["source"] == "ALL" and row["metric"] in MODEL_LABELS]
    x = np.arange(len(MAIN_SECTIONS))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    colors = {"ic_cpitch_only": "#4C78A8", "ic_harmony": "#F58518"}
    for idx, metric in enumerate(["ic_cpitch_only", "ic_harmony"]):
        values = [next((row for row in rows if row["section_group"] == section and row["metric"] == metric), None) for section in MAIN_SECTIONS]
        means = [row["mean"] if row else np.nan for row in values]
        lows = [row["mean"] - row["ci95_low"] if row else 0 for row in values]
        highs = [row["ci95_high"] - row["mean"] if row else 0 for row in values]
        ax.bar(x + (idx - 0.5) * width, means, width, yerr=[lows, highs], label=MODEL_LABELS[metric], color=colors[metric], capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels([label.replace("_", "-") for label in MAIN_SECTIONS], rotation=25, ha="right")
    ax.set_ylabel("Mean IC (bits)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def plot_harmony_gain(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in summary if row["source"] == "ALL" and row["metric"] == "harmony_gain"]
    x = np.arange(len(MAIN_SECTIONS))
    values = [next((row for row in rows if row["section_group"] == section), None) for section in MAIN_SECTIONS]
    means = [row["mean"] if row else np.nan for row in values]
    lows = [row["mean"] - row["ci95_low"] if row else 0 for row in values]
    highs = [row["ci95_high"] - row["mean"] if row else 0 for row in values]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(x, means, yerr=[lows, highs], color="#54A24B", capsize=3)
    ax.axhline(0, color="#555555", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([label.replace("_", "-") for label in MAIN_SECTIONS], rotation=25, ha="right")
    ax.set_ylabel("Harmony gain (cpitch-only IC - harmony IC)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def plot_onset_windows(windows: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in windows if row["source"] == "ALL" and row["metric"] in {"ic_cpitch_only", "ic_harmony"}]
    colors = {
        ("chorus", "ic_cpitch_only"): "#4C78A8",
        ("chorus", "ic_harmony"): "#F58518",
        ("bridge", "ic_cpitch_only"): "#72B7B2",
        ("bridge", "ic_harmony"): "#E45756",
    }
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    for section in ["chorus", "bridge"]:
        for metric in ["ic_cpitch_only", "ic_harmony"]:
            items = sorted([row for row in rows if row["section_group"] == section and row["metric"] == metric], key=lambda row: row["offset"])
            x = np.array([row["offset"] for row in items], dtype=float)
            y = np.array([row["mean"] for row in items], dtype=float)
            ax.plot(x, y, lw=2, color=colors[(section, metric)], label=f"{section.replace('_','-')} {MODEL_LABELS[metric]}")
    ax.axvline(0, color="#555555", lw=1)
    ax.set_xlabel("Offset from section onset (notes)")
    ax.set_ylabel("Mean IC (bits)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def write_report(path: Path, songs: list[dict], args: argparse.Namespace, section_summary: list[dict], bridge_contrasts: list[dict], return_effects: list[dict]) -> None:
    lines = [
        "# Harmony-Conditioned Cpitch IC",
        "",
        "The models use only cpitch and chord. Section labels are used only after IC estimation for grouping and interpretation.",
        "",
        f"- Songs: {len(songs)}",
        f"- Folds: {args.folds}",
        f"- Max order: {args.max_order}",
        f"- Alpha: {args.alpha}",
        "",
        "## Mean By Section, All Songs",
        "",
        "| Section | Cpitch-only IC | Harmony IC | Harmony gain |",
        "|---|---:|---:|---:|",
    ]
    for section in MAIN_SECTIONS:
        cp = lookup_summary(section_summary, "ALL", section, "ic_cpitch_only")
        hm = lookup_summary(section_summary, "ALL", section, "ic_harmony")
        gain = lookup_summary(section_summary, "ALL", section, "harmony_gain")
        if cp and hm and gain:
            lines.append(
                f"| {section} | {fmt_ci(cp)} | {fmt_ci(hm)} | {fmt_ci(gain)} |"
            )
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
    lines.extend([
        "",
        "## Return Effects",
        "",
        "Positive values mean IC/gain decreased from first to second occurrence.",
        "",
        "| Section | Metric | N | First - second [95% CI] | p |",
        "|---|---|---:|---:|---:|",
    ])
    for row in return_effects:
        if row["source"] != "ALL":
            continue
        lines.append(
            f"| {row['section_group']} | {row['metric']} | {row['n_songs']} | "
            f"{fmt(row['mean_first_minus_second'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
        )
    lines.extend(["", "## Headline", "", headline(section_summary, bridge_contrasts)])
    path.write_text("\n".join(lines), encoding="utf-8")


def headline(section_summary: list[dict], bridge_contrasts: list[dict]) -> str:
    bridge_gain = lookup_summary(section_summary, "ALL", "bridge", "harmony_gain")
    chorus_gain = lookup_summary(section_summary, "ALL", "chorus", "harmony_gain")
    bridge_vs_chorus = next(
        (row for row in bridge_contrasts if row["source"] == "ALL" and row["contrast"] == "bridge_minus_chorus" and row["metric"] == "harmony_gain"),
        None,
    )
    if bridge_gain and chorus_gain and bridge_vs_chorus:
        return (
            f"Bridge harmony gain is {fmt_ci(bridge_gain)}, chorus harmony gain is {fmt_ci(chorus_gain)}; "
            f"bridge-minus-chorus gain difference is {fmt(bridge_vs_chorus['mean_difference'])} bits, p = {fmt_p(bridge_vs_chorus['p'])}."
        )
    return "See section summaries and bridge contrasts."


def lookup_summary(summary: list[dict], source: str, section: str, metric: str) -> dict | None:
    return next((row for row in summary if row["source"] == source and row["section_group"] == section and row["metric"] == metric), None)


def smoothed_distribution(counter: Counter[int] | None, vocab: list[int], alpha: float) -> tuple[list[float], float]:
    if not vocab:
        return [], 0.0
    if counter is None:
        probs = [1.0 / len(vocab)] * len(vocab)
    else:
        total = sum(counter.values())
        denom = total + alpha * len(vocab)
        probs = [(counter[note] + alpha) / denom for note in vocab]
    ent = -sum(p * math.log2(p) for p in probs if p > 0)
    return probs, ent


def normalize_chord(value: str) -> str:
    value = value.strip()
    return value if value else "N"


def normalize_section(value: str) -> str:
    return value.lower().strip().replace("-", "_").replace(" ", "_") or "unknown"


def section_group(value: str) -> str:
    value = normalize_section(value)
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


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def ttest(values: np.ndarray) -> tuple[float, float]:
    if len(values) < 2 or float(values.std(ddof=1)) < 1e-12:
        return float("nan"), float("nan")
    t, p = stats.ttest_1samp(values, 0.0)
    return float(t), float(p)


def fmt(value: object) -> str:
    value = float(value)
    return "nan" if math.isnan(value) else f"{value:.3f}"


def fmt_p(value: object) -> str:
    value = float(value)
    if math.isnan(value):
        return "nan"
    return "<.001" if value < 0.001 else f"{value:.3f}"


def fmt_ci(row: dict) -> str:
    return f"{fmt(row['mean'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}]"


if __name__ == "__main__":
    main()
