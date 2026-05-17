from __future__ import annotations

"""
Single-file CoCoPops / popular-music IDyOM analysis pipeline.

This file consolidates the popular-music side of the project. It assumes that
the original Lisp IDyOM outputs have already been generated and summarized into
event-level CSVs. It does not re-run Lisp IDyOM; instead it starts from the
IDyOM event tables and recurrence-window table currently used in the analysis.

Main outputs:
1. Experiment 1: chorus recurrence vs ordinary repeated fragment.
2. Experiment 2: chorus onset vs chorus body.
3. Experiment 3: chorus recurrence vs verse recurrence.
4. Experiment 3 song-level paired-difference robustness model.
5. Experiment 3 note-level OLS with song-clustered robust standard errors.
6. Poster-ready Experiment 3 figure.
7. IC curves for verse1/verse2/chorus1/chorus2 around section onset.
"""

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


ROOT = Path("D:/music")
DEFAULT_INPUT_DIR = ROOT / "output/idyom_cocopops_melody"
DEFAULT_OUTPUT_DIR = ROOT / "output/pop_music_idyom_pipeline"

SOURCES = {
    "cocopops_billboard": "Billboard",
    "cocopops_rollingstone": "RollingStone",
}

MODEL_SPECS = {
    # Plain LTM was re-run separately but the joined column name is still
    # idyom_ltm_plus_ic because the summarizer keeps the same schema.
    "LTM": ("cocopops_original_idyom_ltm_plain_event_ic.csv", "idyom_ltm_plus_ic"),
    "LTM+": ("cocopops_original_idyom_event_ic.csv", "idyom_ltm_plus_ic"),
    "BOTH+": ("cocopops_original_idyom_event_ic.csv", "idyom_both_plus_ic"),
    "STM": ("cocopops_original_idyom_event_ic.csv", "idyom_stm_only_ic"),
}

NOTE_MODEL_TERMS = [
    ("b0", "Intercept: control condition at average covariates"),
    ("b1", "First IC slope in control condition"),
    ("b2", "Focal-condition shift in second IC"),
    ("b3", "Focal-condition difference in first-to-second slope"),
    ("b4", "Within-window / within-section position"),
    ("b5", "First IC x within-position"),
    ("b6", "Pitch similarity"),
    ("b7", "Mean song position"),
]


@dataclass
class FitResult:
    beta: np.ndarray
    se: np.ndarray
    t: np.ndarray
    p2: np.ndarray
    ci_low: np.ndarray
    ci_high: np.ndarray
    df: int
    r2: float


def main() -> None:
    parser = argparse.ArgumentParser(description="Run consolidated popular-music IDyOM analyses.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    recurrence_path = input_dir / "cocopops_recurrence_gain_windows.csv"
    recurrence_rows = read_recurrence_rows(recurrence_path)
    event_maps = {
        model: read_event_ic(input_dir / filename, column)
        for model, (filename, column) in MODEL_SPECS.items()
    }

    note_rows = []
    note_rows.extend(run_note_experiment_1(recurrence_rows, event_maps, output_dir))
    note_rows.extend(run_note_experiment_2(recurrence_rows, event_maps, output_dir))
    note_rows.extend(run_note_experiment_3(recurrence_rows, event_maps, output_dir))
    write_csv(output_dir / "note_level_cluster_robust_all_experiments.csv", note_rows)

    song_rows = run_experiment_3_song_level(recurrence_rows, event_maps, output_dir)
    write_csv(output_dir / "experiment3_song_level_paired_difference.csv", song_rows)
    write_experiment3_song_markdown(output_dir / "experiment3_song_level_paired_difference.md", song_rows)
    plot_experiment3_poster(output_dir / "experiment3_song_level_poster.svg", output_dir / "experiment3_song_level_poster.png", song_rows)

    curve_rows = run_four_occurrence_curves(recurrence_rows, event_maps, output_dir)
    write_csv(output_dir / "section_ic_curve_summary.csv", curve_rows)

    write_overview(output_dir / "POP_MUSIC_IDYOM_PIPELINE_README.md", note_rows, song_rows)
    print(f"Wrote consolidated popular-music outputs to {output_dir}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def read_recurrence_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["offset"] = as_int(row.get("offset"))
            row["first_note_id_1"] = as_int(row.get("first_note_id_1"))
            row["second_note_id_1"] = as_int(row.get("second_note_id_1"))
            for key in ["pitch_similarity", "mean_onset_position", "repeat_distance"]:
                row[key] = as_float(row.get(key))
            rows.append(row)
    return rows


def read_event_ic(path: Path, column: str) -> dict[tuple[str, int], float]:
    output = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            note_id = as_int(row.get("note_id_1"))
            ic = as_float(row.get(column))
            if note_id is not None and finite(ic):
                output[(row["piece_id"], note_id)] = ic
    return output


# ---------------------------------------------------------------------------
# Note-level models
# ---------------------------------------------------------------------------


def run_note_experiment_1(
    recurrence_rows: list[dict],
    event_maps: dict[str, dict[tuple[str, int], float]],
    output_dir: Path,
) -> list[dict]:
    # Chorus recurrence vs ordinary repeated fragment, onset window 0-2.
    rows = []
    for source_key, source_label in SOURCES.items():
        valid = pieces_with_groups(recurrence_rows, source_key, {"chorus", "ordinary"}, onset_only=True)
        for model, ic_map in event_maps.items():
            model_rows = []
            for row in recurrence_rows:
                if row["source"] != source_key or row["piece_id"] not in valid:
                    continue
                if row["offset"] not in {0, 1, 2}:
                    continue
                group = recurrence_group(row)
                if group not in {"chorus", "ordinary"}:
                    continue
                condition = 1.0 if group == "chorus" else 0.0
                item = note_model_row(row, ic_map, condition)
                if item is not None:
                    model_rows.append(item)
            rows.extend(fit_note_model_rows("experiment1_chorus_vs_ordinary", source_label, model, model_rows))
    write_note_report(output_dir / "experiment1_chorus_vs_ordinary_cluster_robust.md", rows)
    return rows


def run_note_experiment_2(
    recurrence_rows: list[dict],
    event_maps: dict[str, dict[tuple[str, int], float]],
    output_dir: Path,
) -> list[dict]:
    # Chorus onset offsets 0-2 vs chorus body offsets 3-8.
    rows = []
    for source_key, source_label in SOURCES.items():
        valid = pieces_with_groups(recurrence_rows, source_key, {"chorus"}, onset_only=True)
        for model, ic_map in event_maps.items():
            model_rows = []
            for row in recurrence_rows:
                if row["source"] != source_key or row["piece_id"] not in valid:
                    continue
                if recurrence_group(row) != "chorus" or row["offset"] not in {0, 1, 2, 3, 4, 5, 6, 7, 8}:
                    continue
                condition = 1.0 if row["offset"] in {0, 1, 2} else 0.0
                item = note_model_row(row, ic_map, condition)
                if item is not None:
                    model_rows.append(item)
            rows.extend(fit_note_model_rows("experiment2_chorus_onset_vs_body", source_label, model, model_rows))
    write_note_report(output_dir / "experiment2_chorus_onset_vs_body_cluster_robust.md", rows)
    return rows


def run_note_experiment_3(
    recurrence_rows: list[dict],
    event_maps: dict[str, dict[tuple[str, int], float]],
    output_dir: Path,
) -> list[dict]:
    # Chorus recurrence vs verse recurrence, offsets 0-8.
    rows = []
    for source_key, source_label in SOURCES.items():
        valid = pieces_with_groups(recurrence_rows, source_key, {"chorus", "verse"}, onset_only=True)
        for model, ic_map in event_maps.items():
            model_rows = []
            for row in recurrence_rows:
                if row["source"] != source_key or row["piece_id"] not in valid:
                    continue
                if row["offset"] not in {0, 1, 2, 3, 4, 5, 6, 7, 8}:
                    continue
                group = recurrence_group(row)
                if group not in {"chorus", "verse"}:
                    continue
                condition = 1.0 if group == "verse" else 0.0
                item = note_model_row(row, ic_map, condition)
                if item is not None:
                    model_rows.append(item)
            rows.extend(fit_note_model_rows("experiment3_verse_vs_chorus", source_label, model, model_rows))
    write_note_report(output_dir / "experiment3_verse_vs_chorus_cluster_robust.md", rows)
    return rows


def note_model_row(row: dict, ic_map: dict[tuple[str, int], float], condition: float) -> dict | None:
    first_ic = ic_map.get((row["piece_id"], row["first_note_id_1"]))
    second_ic = ic_map.get((row["piece_id"], row["second_note_id_1"]))
    values = [first_ic, second_ic, row["pitch_similarity"], row["mean_onset_position"]]
    if not all(finite(value) for value in values):
        return None
    return {
        "piece_id": row["piece_id"],
        "ic1": first_ic,
        "ic2": second_ic,
        "condition": condition,
        "within_position": float(row["offset"]),
        "pitch_similarity": row["pitch_similarity"],
        "mean_onset_position": row["mean_onset_position"],
    }


def fit_note_model_rows(experiment: str, source: str, model: str, rows: list[dict]) -> list[dict]:
    y, x, clusters = note_design(rows)
    fit = ols_fit(y, x, clusters=clusters)
    n_chorus_or_control = sum(1 for row in rows if row["condition"] == 0.0)
    n_focal = sum(1 for row in rows if row["condition"] == 1.0)
    output = []
    for i, (term, description) in enumerate(NOTE_MODEL_TERMS):
        output.append({
            "experiment": experiment,
            "source": source,
            "model": model,
            "n_rows": len(rows),
            "n_song_clusters": len(set(clusters)),
            "n_control_rows": n_chorus_or_control,
            "n_focal_rows": n_focal,
            "df": fit.df,
            "r2": fit.r2,
            "term": term,
            "description": description,
            "beta": fit.beta[i],
            "se": fit.se[i],
            "t": fit.t[i],
            "p2": fit.p2[i],
            "ci_low": fit.ci_low[i],
            "ci_high": fit.ci_high[i],
        })
    return output


def note_design(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    ic1 = np.array([row["ic1"] for row in rows], dtype=float)
    condition = np.array([row["condition"] for row in rows], dtype=float)
    within = np.array([row["within_position"] for row in rows], dtype=float)
    pitch = np.array([row["pitch_similarity"] for row in rows], dtype=float)
    song_pos = np.array([row["mean_onset_position"] for row in rows], dtype=float)
    y = np.array([row["ic2"] for row in rows], dtype=float)
    ic1_c = center(ic1)
    within_c = center(within)
    pitch_c = center(pitch)
    song_pos_c = center(song_pos)
    x = np.column_stack([
        np.ones(len(rows)),
        ic1_c,
        condition,
        ic1_c * condition,
        within_c,
        ic1_c * within_c,
        pitch_c,
        song_pos_c,
    ])
    return y, x, [row["piece_id"] for row in rows]


# ---------------------------------------------------------------------------
# Experiment 3 song-level paired difference
# ---------------------------------------------------------------------------


def run_experiment_3_song_level(
    recurrence_rows: list[dict],
    event_maps: dict[str, dict[tuple[str, int], float]],
    output_dir: Path,
) -> list[dict]:
    rows = []
    for source_key, source_label in SOURCES.items():
        valid = pieces_with_groups(recurrence_rows, source_key, {"chorus", "verse"}, onset_only=True)
        for model, ic_map in event_maps.items():
            song_rows = build_song_level_exp3_rows(recurrence_rows, ic_map, source_key, valid)
            fit = fit_song_level_exp3(song_rows)
            rows.append({
                "source": source_label,
                "model": model,
                **fit,
            })
    return rows


def build_song_level_exp3_rows(
    recurrence_rows: list[dict],
    ic_map: dict[tuple[str, int], float],
    source: str,
    valid: set[str],
) -> list[dict]:
    grouped = defaultdict(list)
    for row in recurrence_rows:
        if row["source"] != source or row["piece_id"] not in valid:
            continue
        if row["offset"] not in {0, 1, 2, 3, 4, 5, 6, 7, 8}:
            continue
        group = recurrence_group(row)
        if group not in {"chorus", "verse"}:
            continue
        first_ic = ic_map.get((row["piece_id"], row["first_note_id_1"]))
        second_ic = ic_map.get((row["piece_id"], row["second_note_id_1"]))
        values = [first_ic, second_ic, row["pitch_similarity"], row["mean_onset_position"]]
        if not all(finite(value) for value in values):
            continue
        grouped[(row["piece_id"], group)].append({
            "ic1": first_ic,
            "ic2": second_ic,
            "pitch_similarity": row["pitch_similarity"],
            "mean_onset_position": row["mean_onset_position"],
        })

    by_song = defaultdict(dict)
    for (piece_id, group), values in grouped.items():
        by_song[piece_id][group] = {
            "ic1": mean([v["ic1"] for v in values]),
            "ic2": mean([v["ic2"] for v in values]),
            "pitch_similarity": mean([v["pitch_similarity"] for v in values]),
            "mean_onset_position": mean([v["mean_onset_position"] for v in values]),
        }

    out = []
    for piece_id, groups in sorted(by_song.items()):
        if "chorus" not in groups or "verse" not in groups:
            continue
        chorus = groups["chorus"]
        verse = groups["verse"]
        out.append({
            "piece_id": piece_id,
            "d_ic2": verse["ic2"] - chorus["ic2"],
            "d_ic1": verse["ic1"] - chorus["ic1"],
            "d_pitch_similarity": verse["pitch_similarity"] - chorus["pitch_similarity"],
            "d_mean_onset_position": verse["mean_onset_position"] - chorus["mean_onset_position"],
            "chorus_ic2": chorus["ic2"],
            "verse_ic2": verse["ic2"],
        })
    return out


def fit_song_level_exp3(rows: list[dict]) -> dict:
    y = np.array([row["d_ic2"] for row in rows], dtype=float)
    covariates = np.array([
        [row["d_ic1"], row["d_pitch_similarity"], row["d_mean_onset_position"]]
        for row in rows
    ], dtype=float)
    x = np.column_stack([np.ones(len(rows)), covariates - np.mean(covariates, axis=0)])
    fit = ols_fit(y, x)
    return {
        "n_songs": len(rows),
        "df": fit.df,
        "mean_chorus_ic2": mean([row["chorus_ic2"] for row in rows]),
        "mean_verse_ic2": mean([row["verse_ic2"] for row in rows]),
        "beta0_verse_minus_chorus": fit.beta[0],
        "beta0_se": fit.se[0],
        "beta0_p": fit.p2[0],
        "beta0_ci_low": fit.ci_low[0],
        "beta0_ci_high": fit.ci_high[0],
        "beta_delta_ic1": fit.beta[1],
        "p_delta_ic1": fit.p2[1],
        "beta_delta_pitch_similarity": fit.beta[2],
        "p_delta_pitch_similarity": fit.p2[2],
        "beta_delta_mean_onset_position": fit.beta[3],
        "p_delta_mean_onset_position": fit.p2[3],
        "r2": fit.r2,
    }


# ---------------------------------------------------------------------------
# Curves and figures
# ---------------------------------------------------------------------------


def run_four_occurrence_curves(
    recurrence_rows: list[dict],
    event_maps: dict[str, dict[tuple[str, int], float]],
    output_dir: Path,
) -> list[dict]:
    curve_dir = output_dir / "section_ic_curves_four_occurrences"
    curve_dir.mkdir(parents=True, exist_ok=True)
    eligible = pieces_with_groups(recurrence_rows, source_key=None, required={"chorus", "verse"}, onset_only=True)
    all_summary = []
    for model, ic_map in event_maps.items():
        rows = []
        for row in recurrence_rows:
            if row["piece_id"] not in eligible:
                continue
            if row["offset"] is None or row["offset"] < -8 or row["offset"] > 8:
                continue
            group = recurrence_group(row)
            if group not in {"verse", "chorus"}:
                continue
            for occurrence, note_key in [("first", "first_note_id_1"), ("second", "second_note_id_1")]:
                ic = ic_map.get((row["piece_id"], row[note_key]))
                if finite(ic):
                    rows.append({
                        "model": model,
                        "piece_id": row["piece_id"],
                        "section": group,
                        "occurrence": occurrence,
                        "offset": row["offset"],
                        "ic": ic,
                    })
        summary = summarize_curve_rows(rows, model)
        all_summary.extend(summary)
        plot_single_curve_model(curve_dir, model, summary, len(eligible))
    plot_all_curve_models(curve_dir, all_summary, len(eligible))
    return all_summary


def summarize_curve_rows(rows: list[dict], model: str) -> list[dict]:
    per_song = defaultdict(list)
    for row in rows:
        key = (row["piece_id"], row["section"], row["occurrence"], row["offset"])
        per_song[key].append(row["ic"])
    grouped = defaultdict(list)
    for (piece_id, section, occurrence, offset), values in per_song.items():
        grouped[(section, occurrence, offset)].append(mean(values))

    out = []
    for (section, occurrence, offset), values in sorted(grouped.items()):
        arr = np.array(values, dtype=float)
        se = float(np.std(arr, ddof=1) / math.sqrt(len(arr))) if len(arr) > 1 else math.nan
        ci = 1.96 * se if finite(se) else math.nan
        out.append({
            "model": model,
            "section": section,
            "occurrence": occurrence,
            "offset": offset,
            "mean_ic": float(np.mean(arr)),
            "se": se,
            "ci95_low": float(np.mean(arr) - ci) if finite(ci) else math.nan,
            "ci95_high": float(np.mean(arr) + ci) if finite(ci) else math.nan,
            "n_songs": len(arr),
        })
    return out


def plot_experiment3_poster(svg_path: Path, png_path: Path, rows: list[dict]) -> None:
    model_order = ["LTM", "LTM+", "BOTH+", "STM"]
    colors = {"LTM": "#8A95A3", "LTM+": "#2364AA", "BOTH+": "#2A9D8F", "STM": "#E76F51"}
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), sharex=True, sharey=True, gridspec_kw={"wspace": 0.08})
    x_min, x_max = -0.28, 0.76
    for ax, source in zip(axes, ["Billboard", "RollingStone"]):
        source_rows = {row["model"]: row for row in rows if row["source"] == source}
        panel_n = int(next(iter(source_rows.values()))["n_songs"])
        ax.axvspan(0, x_max, color="#F1F7F5", zorder=0)
        ax.axvline(0, color="#4B5563", linewidth=1.2, zorder=1)
        for i, model in enumerate(model_order):
            row = source_rows[model]
            y = len(model_order) - 1 - i
            beta = row["beta0_verse_minus_chorus"]
            lo = row["beta0_ci_low"]
            hi = row["beta0_ci_high"]
            ax.errorbar(beta, y, xerr=[[beta - lo], [hi - beta]], fmt="o",
                        markersize=9.5, linewidth=2.3, elinewidth=2.3, capsize=5,
                        color=colors[model], markeredgecolor="white", markeredgewidth=1.2, zorder=3)
            ax.text(beta + 0.035, y + 0.16, stars(row["beta0_p"]), color=colors[model],
                    fontsize=11, weight="bold", ha="left", va="center")
        ax.set_title(f"{source}  (N = {panel_n} songs)", fontsize=14, pad=10, weight="bold")
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-0.75, len(model_order) - 0.25)
        ax.grid(axis="x", color="#D1D5DB", linewidth=0.8, alpha=0.7)
        ax.tick_params(axis="x", labelsize=10)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(model_order)))
    axes[0].set_yticklabels(list(reversed(model_order)), fontsize=12)
    axes[1].tick_params(axis="y", labelleft=False)
    fig.text(0.5, 0.94, "Rightward shift = lower second-occurrence IC for chorus\nmore concentrated prediction and higher information efficiency",
             ha="center", va="center", fontsize=13, color="#166534", weight="bold",
             bbox=dict(boxstyle="round,pad=0.42", facecolor="#DCFCE7", edgecolor="#86EFAC"))
    fig.text(0.5, 0.07, "Chorus predictive advantage: verse - chorus second-occurrence IC (bits)",
             ha="center", fontsize=11, color="#111827")
    fig.text(0.09, 0.03, "* p < .05    ** p < .01    *** p < .001", ha="left", fontsize=9, color="#4B5563")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.82, bottom=0.15, wspace=0.08)
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_single_curve_model(out_dir: Path, model: str, rows: list[dict], n: int) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    draw_ic_curves(ax, rows)
    ax.set_title(f"{model}: IC around verse and chorus onset", fontsize=16, weight="bold", pad=14)
    ax.text(0.01, 0.98, f"Songs included: {n} with verse1, verse2, chorus1, and chorus2",
            transform=ax.transAxes, ha="left", va="top", fontsize=10, color="#4B5563")
    style_curve_axis(ax)
    fig.tight_layout()
    stem = model.lower().replace("+", "plus")
    fig.savefig(out_dir / f"ic_curve_{stem}.svg", bbox_inches="tight")
    fig.savefig(out_dir / f"ic_curve_{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_all_curve_models(out_dir: Path, rows: list[dict], n: int) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True, sharey=True)
    for ax, model in zip(axes.flat, MODEL_SPECS):
        draw_ic_curves(ax, [row for row in rows if row["model"] == model])
        ax.set_title(model, fontsize=14, weight="bold")
        style_curve_axis(ax, compact=True)
    fig.suptitle("Mean IC around verse and chorus onset", fontsize=18, weight="bold", y=0.98)
    fig.text(0.5, 0.94, f"Solid = first occurrence, dashed = second occurrence. Songs included: {n} with all four occurrences.",
             ha="center", fontsize=11, color="#374151")
    fig.supxlabel("Offset from section onset (notes)", fontsize=12)
    fig.supylabel("Mean IC (bits)", fontsize=12)
    fig.tight_layout(rect=(0.04, 0.04, 1, 0.92))
    fig.savefig(out_dir / "ic_curves_all_models.svg", bbox_inches="tight")
    fig.savefig(out_dir / "ic_curves_all_models.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def draw_ic_curves(ax, rows: list[dict]) -> None:
    curves = [
        ("verse", "first", "Verse 1", "#E76F51", "-"),
        ("verse", "second", "Verse 2", "#E76F51", "--"),
        ("chorus", "first", "Chorus 1", "#2364AA", "-"),
        ("chorus", "second", "Chorus 2", "#2364AA", "--"),
    ]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["section"], row["occurrence"])].append(row)
    for section, occurrence, label, color, linestyle in curves:
        group = sorted(grouped[(section, occurrence)], key=lambda item: item["offset"])
        if not group:
            continue
        x = np.array([row["offset"] for row in group], dtype=float)
        y = np.array([row["mean_ic"] for row in group], dtype=float)
        lo = np.array([row["ci95_low"] for row in group], dtype=float)
        hi = np.array([row["ci95_high"] for row in group], dtype=float)
        ax.plot(x, y, color=color, linestyle=linestyle, linewidth=2.4, label=label)
        ax.fill_between(x, lo, hi, color=color, alpha=0.08, linewidth=0)


def style_curve_axis(ax, compact: bool = False) -> None:
    ax.axvline(0, color="#111827", linewidth=1.1, alpha=0.85)
    ax.grid(True, color="#E5E7EB", linewidth=0.8)
    ax.set_xlim(-8, 8)
    ax.set_xticks(np.arange(-8, 9, 2))
    ax.set_xlabel("" if compact else "Offset from section onset (notes)", fontsize=11)
    ax.set_ylabel("" if compact else "Mean IC (bits)", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, ncol=2, fontsize=10, loc="upper right")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def ols_fit(y: np.ndarray, x: np.ndarray, clusters: list[str] | None = None) -> FitResult:
    beta, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    residuals = y - fitted
    n, k = x.shape
    if clusters is None:
        df = n - k
        sigma2 = float(residuals @ residuals / df)
        cov = sigma2 * np.linalg.inv(x.T @ x)
    else:
        df = len(set(clusters)) - 1
        cov = cluster_covariance(x, residuals, clusters)
    se = np.sqrt(np.diag(cov))
    t_values = beta / se
    p2 = np.array([2 * stats.t.sf(abs(t), df) for t in t_values])
    tcrit = stats.t.ppf(0.975, df)
    ci_low = beta - tcrit * se
    ci_high = beta + tcrit * se
    return FitResult(beta=beta, se=se, t=t_values, p2=p2, ci_low=ci_low, ci_high=ci_high, df=df, r2=r_squared(y, fitted))


def cluster_covariance(x: np.ndarray, residuals: np.ndarray, clusters: list[str]) -> np.ndarray:
    xtx_inv = np.linalg.inv(x.T @ x)
    meat = np.zeros((x.shape[1], x.shape[1]))
    grouped = defaultdict(list)
    for i, cluster in enumerate(clusters):
        grouped[cluster].append(i)
    for indices in grouped.values():
        xg = x[indices, :]
        ug = residuals[indices]
        score = xg.T @ ug
        meat += np.outer(score, score)
    n, k = x.shape
    g = len(grouped)
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    return correction * xtx_inv @ meat @ xtx_inv


def r_squared(y: np.ndarray, fitted: np.ndarray) -> float:
    ss_res = float((y - fitted) @ (y - fitted))
    ss_tot = float((y - np.mean(y)) @ (y - np.mean(y)))
    return 1.0 - ss_res / ss_tot if ss_tot else math.nan


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def write_note_report(path: Path, rows: list[dict]) -> None:
    by_experiment = defaultdict(list)
    for row in rows:
        by_experiment[row["experiment"]].append(row)
    lines = [
        f"# {path.stem}",
        "",
        "Formula:",
        "",
        "```text",
        "IC2_ij = b0 + b1*IC1_c_ij + b2*Condition_ij",
        "       + b3*(IC1_c_ij * Condition_ij)",
        "       + b4*within_position_c_ij",
        "       + b5*(IC1_c_ij * within_position_c_ij)",
        "       + b6*pitch_similarity_c_ij",
        "       + b7*mean_onset_position_c_ij + error_ij",
        "```",
        "",
        "Standard errors are clustered by song (`piece_id`).",
        "",
        "| Experiment | Corpus | Model | Term | N notes | Song clusters | Estimate [95% CI] | SE | p |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {experiment} | {source} | {model} | {term} | {n_rows} | {n_song_clusters} | {beta} [{lo}, {hi}] | {se} | {p} |".format(
                experiment=row["experiment"],
                source=row["source"],
                model=row["model"],
                term=row["term"],
                n_rows=row["n_rows"],
                n_song_clusters=row["n_song_clusters"],
                beta=fmt(row["beta"]),
                lo=fmt(row["ci_low"]),
                hi=fmt(row["ci_high"]),
                se=fmt(row["se"]),
                p=fmt_p(row["p2"]),
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_experiment3_song_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Experiment 3: Song-Level Paired Difference",
        "",
        "Formula:",
        "",
        "```text",
        "D_s = mean(IC2_verse_s) - mean(IC2_chorus_s)",
        "D_s = beta0 + beta1*delta_IC1_s + beta2*delta_pitch_similarity_s + beta3*delta_mean_onset_position_s + error_s",
        "```",
        "",
        "Positive beta0 means verse has higher second-occurrence IC than chorus; therefore chorus is more predictable.",
        "",
        "| Corpus | Model | N songs | Chorus IC2 | Verse IC2 | beta0 verse - chorus [95% CI] | p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {source} | {model} | {n} | {chorus} | {verse} | {b} [{lo}, {hi}] | {p} |".format(
                source=row["source"],
                model=row["model"],
                n=row["n_songs"],
                chorus=fmt(row["mean_chorus_ic2"]),
                verse=fmt(row["mean_verse_ic2"]),
                b=fmt(row["beta0_verse_minus_chorus"]),
                lo=fmt(row["beta0_ci_low"]),
                hi=fmt(row["beta0_ci_high"]),
                p=fmt_p(row["beta0_p"]),
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_overview(path: Path, note_rows: list[dict], song_rows: list[dict]) -> None:
    lines = [
        "# Popular-Music IDyOM Pipeline",
        "",
        "This folder was generated by `scripts/pop_music_idyom_pipeline.py`.",
        "",
        "Inputs are original Lisp IDyOM event-level outputs plus recurrence-window rows.",
        "",
        "Key files:",
        "",
        "- `note_level_cluster_robust_all_experiments.csv`",
        "- `experiment1_chorus_vs_ordinary_cluster_robust.md`",
        "- `experiment2_chorus_onset_vs_body_cluster_robust.md`",
        "- `experiment3_verse_vs_chorus_cluster_robust.md`",
        "- `experiment3_song_level_paired_difference.csv`",
        "- `experiment3_song_level_paired_difference.md`",
        "- `experiment3_song_level_poster.svg/png`",
        "- `section_ic_curves_four_occurrences/`",
        "",
        "Experiment 3 song-level headline:",
        "",
        "| Corpus | Model | N songs | beta0 verse - chorus | p |",
        "|---|---|---:|---:|---:|",
    ]
    for row in song_rows:
        lines.append(f"| {row['source']} | {row['model']} | {row['n_songs']} | {fmt(row['beta0_verse_minus_chorus'])} | {fmt_p(row['beta0_p'])} |")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pieces_with_groups(rows: list[dict], source_key: str | None, required: set[str], onset_only: bool) -> set[str]:
    present = defaultdict(set)
    for row in rows:
        if source_key is not None and row.get("source") != source_key:
            continue
        if onset_only and row.get("offset") != 0:
            continue
        group = recurrence_group(row)
        if group in required:
            present[row["piece_id"]].add(group)
    return {piece_id for piece_id, groups in present.items() if required.issubset(groups)}


def recurrence_group(row: dict) -> str | None:
    if row.get("recurrence_type") == "ordinary_fragment":
        return "ordinary"
    if row.get("recurrence_type") == "section" and row.get("section_label") == "chorus":
        return "chorus"
    if row.get("recurrence_type") == "section" and row.get("section_label") == "verse":
        return "verse"
    return None


def center(values: np.ndarray) -> np.ndarray:
    return values - np.mean(values)


def mean(values: list[float]) -> float:
    return float(np.mean(np.array(values, dtype=float)))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def as_float(value) -> float:
    if value is None or value == "":
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def as_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def finite(value) -> bool:
    return value is not None and math.isfinite(float(value))


def fmt(value: float) -> str:
    if not finite(value):
        return ""
    return f"{float(value):.3f}"


def fmt_p(value: float) -> str:
    if not finite(value):
        return ""
    value = float(value)
    if value < 0.001:
        return "< .001"
    return f"{value:.3f}"


def stars(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "n.s."


if __name__ == "__main__":
    main()
