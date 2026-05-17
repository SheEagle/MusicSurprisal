from __future__ import annotations

import argparse
import csv
import itertools
import math
import random
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev, stdev

import numpy as np
from scipy import stats


"""
Classical cadence project pipeline.

This single file consolidates the current classical-only analysis used in the
project. It assumes that the original Lisp IDyOM has already produced event-level
melody and harmony IC/entropy CSV files. It then rebuilds the cadence-aligned
melody-harmony dataset and runs the paper-facing analyses:

1. Cadence windows around t = 0 for Mozart and Beethoven.
2. Terminal melody/harmony IC summaries.
3. Domain dominance: harmony_zIC - melody_zIC, especially DC vs EC.
4. Post-cadential increase: melody Delta zIC(t0->t1) - harmony Delta zIC(t0->t1).
5. Experiment 3: cadence category x time ANOVA for t-1, t, t+1.
6. Poster-ready SVG figures and Markdown summaries.

The script intentionally excludes the separate popular-music project.
"""


CADENCES = ["PAC", "IAC", "HC", "DC", "EC"]
CORPORA = {
    "beethoven_piano_sonatas": {
        "short": "Beethoven",
        "prefix": "beethoven",
        "harmony": "output/idyom_dcml_harmony_beethoven/dcml_harmony_original_idyom_event_ic.csv",
    },
    "mozart_piano_sonatas": {
        "short": "Mozart",
        "prefix": "mozart",
        "harmony": "output/idyom_dcml_harmony_mozart/dcml_harmony_original_idyom_event_ic.csv",
    },
}
COLORS = {
    "PAC": "#1f77b4",
    "IAC": "#2ca02c",
    "HC": "#d62728",
    "DC": "#ff7f0e",
    "EC": "#9467bd",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the classical DCML cadence analysis in one Python file.")
    parser.add_argument(
        "--melody",
        default="output/idyom_dcml_melody_beethoven_mozart/dcml_melody_original_idyom_event_ic.csv",
        help="Original Lisp IDyOM melody event CSV.",
    )
    parser.add_argument(
        "--taxonomy",
        default="output/formal_dcml_jtc_pop909_slms_all_rq/boundary_taxonomy/dcml_boundary_taxonomy.csv",
        help="DCML cadence taxonomy CSV.",
    )
    parser.add_argument("--output-dir", default="output/classical_cadence_pipeline")
    parser.add_argument("--window", type=int, default=3)
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    random.seed(args.seed)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    terminal_all: list[dict] = []
    window_all: list[dict] = []
    profile_all: list[dict] = []
    coupling_summary_all: list[dict] = []

    for corpus, config in CORPORA.items():
        corpus_output = output / config["prefix"]
        corpus_output.mkdir(parents=True, exist_ok=True)
        melody = load_track(Path(args.melody), "melody", corpus)
        harmony = load_track(Path(config["harmony"]), "harmony", corpus)
        markers = load_cadence_markers(Path(args.taxonomy), set(melody), corpus)

        terminal, windows, profiles, summary = build_cadence_windows(
            markers, melody, harmony, corpus=corpus, window=args.window
        )
        terminal_all.extend(terminal)
        window_all.extend(windows)
        profile_all.extend(profiles)
        coupling_summary_all.extend(summary)

        prefix = config["prefix"]
        write_csv(corpus_output / f"{prefix}_terminal_melody_harmony.csv", terminal)
        write_csv(corpus_output / f"{prefix}_window_melody_harmony.csv", windows)
        write_csv(corpus_output / f"{prefix}_profile_melody_harmony.csv", profiles)
        write_csv(corpus_output / f"{prefix}_terminal_summary.csv", summary)
        draw_terminal_scatter(terminal, corpus_output / f"{prefix}_terminal_ic_scatter.svg", config["short"])
        draw_entropy_profile(profiles, corpus_output / f"{prefix}_entropy_profile.svg", config["short"], args.window)

    write_csv(output / "classical_terminal_melody_harmony.csv", terminal_all)
    write_csv(output / "classical_window_melody_harmony.csv", window_all)
    write_csv(output / "classical_profile_melody_harmony.csv", profile_all)
    write_csv(output / "classical_terminal_summary.csv", coupling_summary_all)

    dominance_rows, dominance_summary, dominance_contrasts = run_domain_dominance(
        terminal_all, bootstrap_n=args.bootstrap
    )
    write_csv(output / "dominance_event_values.csv", dominance_rows)
    write_csv(output / "dominance_summary.csv", dominance_summary)
    write_csv(output / "dominance_pairwise_contrasts.csv", dominance_contrasts)
    draw_standardized_dc_ec_space(dominance_rows, output / "dc_ec_standardized_ic_space.svg")

    post_instance, post_piece, post_tests = run_post_cadential_increase(window_all)
    write_csv(output / "post_cadential_instance_delta_delta_zic.csv", post_instance)
    write_csv(output / "post_cadential_piece_delta_delta_zic.csv", post_piece)
    write_csv(output / "post_cadential_delta_delta_tests.csv", post_tests)
    draw_post_cadential_bars(post_tests, output / "post_cadential_delta_delta_by_composer.svg")

    experiment_rows, anova_rows, simple_rows, planned_rows = run_experiment3(window_all)
    write_csv(output / "experiment3_piece_time_values.csv", experiment_rows)
    write_csv(output / "experiment3_anova_summary.csv", anova_rows)
    write_csv(output / "experiment3_simple_time_effects.csv", simple_rows)
    write_csv(output / "experiment3_planned_comparisons.csv", planned_rows)

    write_report(
        output / "CLASSICAL_CADENCE_PIPELINE_REPORT.md",
        coupling_summary_all,
        dominance_summary,
        dominance_contrasts,
        post_tests,
        anova_rows,
        planned_rows,
    )
    print(f"Wrote classical cadence pipeline outputs to {output}")


# ---------------------------------------------------------------------------
# Data loading and cadence windows


def load_track(path: Path, kind: str, corpus: str) -> dict[str, list[dict]]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    ic_key = "idyom_ic" if kind == "melody" else "harmony_ic"
    entropy_key = "idyom_entropy" if kind == "melody" else "harmony_entropy"
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if corpus not in row["piece_id"]:
                continue
            item = dict(row)
            item["onset_float"] = float(row["onset"])
            item["ic_float"] = float(row[ic_key])
            item["entropy_float"] = float(row[entropy_key])
            by_piece[row["piece_id"]].append(item)
    for rows in by_piece.values():
        rows.sort(key=lambda item: item["onset_float"])
        previous = None
        for item in rows:
            item["entropy_delta"] = "" if previous is None else item["entropy_float"] - previous["entropy_float"]
            previous = item
    return by_piece


def load_cadence_markers(path: Path, piece_ids: set[str], corpus: str) -> list[dict]:
    out = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("corpus") != corpus:
                continue
            if row.get("piece_id") not in piece_ids:
                continue
            cadence = row.get("cadence_type", "")
            if cadence not in CADENCES:
                continue
            out.append(row)
    return out


def build_cadence_windows(
    markers: list[dict],
    melody: dict[str, list[dict]],
    harmony: dict[str, list[dict]],
    *,
    corpus: str,
    window: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    terminal_rows: list[dict] = []
    window_rows: list[dict] = []
    accum: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for marker_id, marker in enumerate(markers):
        piece_id = marker["piece_id"]
        mrows = melody.get(piece_id, [])
        hrows = harmony.get(piece_id, [])
        if not mrows or not hrows:
            continue
        target = float(marker["onset"])
        mi = nearest_index([row["onset_float"] for row in mrows], target, tolerance=0.01)
        hi = nearest_index([row["onset_float"] for row in hrows], target, tolerance=0.01)
        if mi is None or hi is None:
            continue
        if mi < window or mi >= len(mrows) - window:
            continue

        cadence = marker["cadence_type"]
        m0, h0 = mrows[mi], hrows[hi]
        terminal_rows.append(
            {
                "corpus": corpus,
                "piece_id": piece_id,
                "marker_id": marker_id,
                "cadence_type": cadence,
                "onset": target,
                "melody_ic": m0["ic_float"],
                "harmony_ic": h0["ic_float"],
                "melody_entropy": m0["entropy_float"],
                "harmony_entropy": h0["entropy_float"],
                "melody_entropy_delta": blank_or_float(m0["entropy_delta"]),
                "harmony_entropy_delta": blank_or_float(h0["entropy_delta"]),
                "entropy_gradient_difference": delta_difference(m0, h0),
            }
        )

        honsets = [row["onset_float"] for row in hrows]
        for rel in range(-window, window + 1):
            m = mrows[mi + rel]
            h = hrows[max(0, bisect_right(honsets, m["onset_float"]) - 1)]
            row = {
                "corpus": corpus,
                "piece_id": piece_id,
                "marker_id": marker_id,
                "cadence_type": cadence,
                "relative_event": rel,
                "melody_onset": m["onset_float"],
                "harmony_onset": h["onset_float"],
                "melody_ic": m["ic_float"],
                "harmony_ic": h["ic_float"],
                "melody_entropy": m["entropy_float"],
                "harmony_entropy": h["entropy_float"],
                "melody_entropy_delta": blank_or_float(m["entropy_delta"]),
                "harmony_entropy_delta": blank_or_float(h["entropy_delta"]),
                "entropy_gradient_difference": delta_difference(m, h),
            }
            window_rows.append(row)
            for key in [
                "melody_ic",
                "harmony_ic",
                "melody_entropy",
                "harmony_entropy",
                "melody_entropy_delta",
                "harmony_entropy_delta",
                "entropy_gradient_difference",
            ]:
                if row[key] != "":
                    accum[(cadence, rel)][key].append(float(row[key]))

    profile_rows = []
    for (cadence, rel), values in sorted(accum.items(), key=lambda item: (CADENCES.index(item[0][0]), item[0][1])):
        row = {"corpus": corpus, "cadence_type": cadence, "relative_event": rel}
        row["markers"] = sum(1 for item in terminal_rows if item["cadence_type"] == cadence)
        row["pieces"] = len({item["piece_id"] for item in terminal_rows if item["cadence_type"] == cadence})
        for key, vals in values.items():
            row[f"mean_{key}"] = mean(vals) if vals else ""
        profile_rows.append(row)

    summary_rows = []
    for cadence in CADENCES:
        subset = [row for row in terminal_rows if row["cadence_type"] == cadence]
        if not subset:
            continue
        summary_rows.append(
            {
                "corpus": corpus,
                "cadence_type": cadence,
                "markers": len(subset),
                "pieces": len({row["piece_id"] for row in subset}),
                "mean_melody_ic_t0": mean(float(row["melody_ic"]) for row in subset),
                "mean_harmony_ic_t0": mean(float(row["harmony_ic"]) for row in subset),
                "mean_melody_entropy_t0": mean(float(row["melody_entropy"]) for row in subset),
                "mean_harmony_entropy_t0": mean(float(row["harmony_entropy"]) for row in subset),
                "terminal_ic_correlation": pearson(
                    [float(row["harmony_ic"]) for row in subset],
                    [float(row["melody_ic"]) for row in subset],
                ),
            }
        )
    return terminal_rows, window_rows, profile_rows, summary_rows


def nearest_index(values: list[float], target: float, tolerance: float) -> int | None:
    idx = bisect_left(values, target)
    candidates = []
    if idx < len(values):
        candidates.append(idx)
    if idx > 0:
        candidates.append(idx - 1)
    if not candidates:
        return None
    best = min(candidates, key=lambda item: abs(values[item] - target))
    return best if abs(values[best] - target) <= tolerance else None


def blank_or_float(value):
    return "" if value == "" else float(value)


def delta_difference(m: dict, h: dict) -> float | str:
    if m["entropy_delta"] == "" or h["entropy_delta"] == "":
        return ""
    return float(m["entropy_delta"]) - float(h["entropy_delta"])


# ---------------------------------------------------------------------------
# Analysis 1: domain dominance


def run_domain_dominance(rows: list[dict], bootstrap_n: int) -> tuple[list[dict], list[dict], list[dict]]:
    values = [dict(row) for row in rows if row["cadence_type"] in CADENCES]
    for corpus in sorted({row["corpus"] for row in values}):
        subset = [row for row in values if row["corpus"] == corpus]
        mz = z_params([float(row["melody_ic"]) for row in subset])
        hz = z_params([float(row["harmony_ic"]) for row in subset])
        for row in subset:
            row["melody_ic_z"] = z(float(row["melody_ic"]), mz)
            row["harmony_ic_z"] = z(float(row["harmony_ic"]), hz)
            row["dominance_index"] = row["harmony_ic_z"] - row["melody_ic_z"]

    summary = []
    for corpus in sorted({row["corpus"] for row in values}):
        for cadence in CADENCES:
            subset = [row for row in values if row["corpus"] == corpus and row["cadence_type"] == cadence]
            if len(subset) < 2:
                continue
            dom = piece_level_values(subset, "dominance_index")
            low, high = bootstrap_ci(dom, bootstrap_n)
            summary.append(
                {
                    "corpus": corpus,
                    "cadence_type": cadence,
                    "n_events": len(subset),
                    "n_pieces": len(dom),
                    "mean_melody_ic_z": mean(piece_level_values(subset, "melody_ic_z")),
                    "mean_harmony_ic_z": mean(piece_level_values(subset, "harmony_ic_z")),
                    "mean_dominance_index": mean(dom),
                    "ci95_low": low,
                    "ci95_high": high,
                }
            )

    contrasts = []
    for corpus in sorted({row["corpus"] for row in values}):
        for a, b in itertools.combinations(CADENCES, 2):
            va = piece_level_values(
                [row for row in values if row["corpus"] == corpus and row["cadence_type"] == a], "dominance_index"
            )
            vb = piece_level_values(
                [row for row in values if row["corpus"] == corpus and row["cadence_type"] == b], "dominance_index"
            )
            if len(va) < 2 or len(vb) < 2:
                continue
            estimates = [mean(random.choice(va) for _ in va) - mean(random.choice(vb) for _ in vb) for _ in range(bootstrap_n)]
            p = 2 * min(sum(x <= 0 for x in estimates) / bootstrap_n, sum(x >= 0 for x in estimates) / bootstrap_n)
            contrasts.append(
                {
                    "corpus": corpus,
                    "contrast": f"{a}-{b}",
                    "cadence_a": a,
                    "cadence_b": b,
                    "mean_diff": mean(va) - mean(vb),
                    "ci95_low": percentile(estimates, 2.5),
                    "ci95_high": percentile(estimates, 97.5),
                    "p_value": min(1.0, p),
                }
            )
    return values, summary, add_fdr(contrasts, "p_value")


# ---------------------------------------------------------------------------
# Analysis 2: post-cadential melody-vs-harmony increase


def run_post_cadential_increase(window_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    rows = [dict(row) for row in window_rows if row["cadence_type"] in CADENCES]
    for corpus in sorted({row["corpus"] for row in rows}):
        for track in ["melody", "harmony"]:
            params = z_params([float(row[f"{track}_ic"]) for row in rows if row["corpus"] == corpus])
            for row in rows:
                if row["corpus"] == corpus:
                    row[f"{track}_ic_z"] = z(float(row[f"{track}_ic"]), params)

    by_marker = defaultdict(dict)
    for row in rows:
        by_marker[(row["corpus"], row["piece_id"], row["marker_id"], row["cadence_type"])][int(row["relative_event"])] = row

    instance_rows = []
    for (corpus, piece_id, marker_id, cadence), rels in sorted(by_marker.items()):
        if 0 not in rels or 1 not in rels:
            continue
        r0, r1 = rels[0], rels[1]
        melody_delta = r1["melody_ic_z"] - r0["melody_ic_z"]
        harmony_delta = r1["harmony_ic_z"] - r0["harmony_ic_z"]
        instance_rows.append(
            {
                "corpus": corpus,
                "piece_id": piece_id,
                "marker_id": marker_id,
                "cadence_type": cadence,
                "melody_delta_zic_t1_minus_t0": melody_delta,
                "harmony_delta_zic_t1_minus_t0": harmony_delta,
                "delta_delta_zic": melody_delta - harmony_delta,
            }
        )

    grouped = defaultdict(list)
    for row in instance_rows:
        grouped[(row["corpus"], row["piece_id"], row["cadence_type"])].append(row)
    piece_rows = []
    for (corpus, piece_id, cadence), items in sorted(grouped.items()):
        piece_rows.append(
            {
                "corpus": corpus,
                "piece_id": piece_id,
                "cadence_type": cadence,
                "n_cadence_instances": len(items),
                "mean_melody_delta_zic": mean(float(item["melody_delta_zic_t1_minus_t0"]) for item in items),
                "mean_harmony_delta_zic": mean(float(item["harmony_delta_zic_t1_minus_t0"]) for item in items),
                "mean_delta_delta_zic": mean(float(item["delta_delta_zic"]) for item in items),
            }
        )

    tests = []
    groups = [("overall", "all", "all", piece_rows)]
    for corpus in sorted({row["corpus"] for row in piece_rows}):
        groups.append(("by_corpus", corpus, "all", [row for row in piece_rows if row["corpus"] == corpus]))
    for cadence in CADENCES:
        groups.append(("by_cadence", "all", cadence, [row for row in piece_rows if row["cadence_type"] == cadence]))
    for corpus in sorted({row["corpus"] for row in piece_rows}):
        for cadence in CADENCES:
            groups.append(
                (
                    "by_corpus_cadence",
                    corpus,
                    cadence,
                    [row for row in piece_rows if row["corpus"] == corpus and row["cadence_type"] == cadence],
                )
            )
    for analysis, corpus, cadence, subset in groups:
        if len(subset) < 3:
            continue
        values = [float(row["mean_delta_delta_zic"]) for row in subset]
        mvals = [float(row["mean_melody_delta_zic"]) for row in subset]
        hvals = [float(row["mean_harmony_delta_zic"]) for row in subset]
        tests.append(one_sample_row(analysis, corpus, cadence, values, mvals, hvals))
    tests = add_fdr([row for row in tests if row["analysis"] != "overall"], "p_greater") + [
        row for row in tests if row["analysis"] == "overall"
    ]
    return instance_rows, piece_rows, tests


def one_sample_row(analysis: str, corpus: str, cadence: str, values: list[float], mvals: list[float], hvals: list[float]) -> dict:
    n = len(values)
    avg = mean(values)
    sd = stdev(values)
    se = sd / math.sqrt(n)
    t_stat, p_two = stats.ttest_1samp(values, popmean=0.0)
    p_greater = stats.ttest_1samp(values, popmean=0.0, alternative="greater").pvalue
    tcrit = stats.t.ppf(0.975, df=n - 1)
    return {
        "analysis": analysis,
        "corpus": corpus,
        "cadence_type": cadence,
        "n_piece_cadence_units": n,
        "mean_melody_delta_zic": mean(mvals),
        "mean_harmony_delta_zic": mean(hvals),
        "mean_delta_delta_zic": avg,
        "sd_delta_delta_zic": sd,
        "ci95_low": avg - tcrit * se,
        "ci95_high": avg + tcrit * se,
        "t": t_stat,
        "df": n - 1,
        "p_two_sided": p_two,
        "p_greater": p_greater,
    }


# ---------------------------------------------------------------------------
# Analysis 3: Sears-style Experiment 3


def run_experiment3(window_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    times = [-1, 0, 1]
    grouped = defaultdict(list)
    for row in window_rows:
        rel = int(row["relative_event"])
        if row["cadence_type"] not in CADENCES or rel not in times:
            continue
        grouped[(row["corpus"], row["piece_id"], row["cadence_type"], rel)].append(row)

    rows = []
    for (corpus, piece_id, cadence, rel), items in grouped.items():
        for track in ["melody", "harmony"]:
            rows.append(
                {
                    "corpus": corpus,
                    "piece_id": piece_id,
                    "cadence_type": cadence,
                    "time": rel,
                    "track": track,
                    "ic": mean(float(row[f"{track}_ic"]) for row in items),
                    "n_events": len(items),
                }
            )

    anova_rows = []
    simple_rows = []
    planned_rows = []
    for corpus in sorted({row["corpus"] for row in rows}):
        for track in ["melody", "harmony"]:
            subset = [row for row in rows if row["corpus"] == corpus and row["track"] == track]
            anova_rows.append(run_anova(subset, corpus, track))
            simple_rows.extend(simple_time_effects(subset, corpus, track))
            planned_rows.extend(planned_comparisons(subset, corpus, track))
    return rows, anova_rows, add_fdr(simple_rows, "p_value"), add_fdr(planned_rows, "p_value")


def run_anova(rows: list[dict], corpus: str, track: str) -> dict:
    y = np.array([float(row["ic"]) for row in rows], dtype=float)
    full = fit_ols(y, design_matrix(rows, True, True, True))
    additive = fit_ols(y, design_matrix(rows, True, True, False))
    no_cat = fit_ols(y, design_matrix(rows, False, True, False))
    no_time = fit_ols(y, design_matrix(rows, True, False, False))
    category = nested_f(no_cat, additive)
    time = nested_f(no_time, additive)
    interaction = nested_f(additive, full)
    return {
        "corpus": corpus,
        "track": track,
        "n": len(rows),
        "n_pieces": len({row["piece_id"] for row in rows}),
        "levene_p": levene_cell_p(rows),
        "category_F": category["F"],
        "category_p": category["p"],
        "time_F": time["F"],
        "time_p": time["p"],
        "interaction_F": interaction["F"],
        "interaction_p": interaction["p"],
    }


def simple_time_effects(rows: list[dict], corpus: str, track: str) -> list[dict]:
    out = []
    for cadence in CADENCES:
        subset = [row for row in rows if row["cadence_type"] == cadence]
        if len(subset) < 6:
            continue
        y = np.array([float(row["ic"]) for row in subset], dtype=float)
        result = nested_f(fit_ols(y, np.ones((len(subset), 1))), fit_ols(y, design_time(subset)))
        out.append(
            {
                "corpus": corpus,
                "track": track,
                "cadence_type": cadence,
                "n_pieces": len({row["piece_id"] for row in subset}),
                "F": result["F"],
                "p_value": result["p"],
            }
        )
    return out


def planned_comparisons(rows: list[dict], corpus: str, track: str) -> list[dict]:
    by_piece = defaultdict(dict)
    for row in rows:
        by_piece[(row["piece_id"], row["cadence_type"])][int(row["time"])] = float(row["ic"])
    out = []
    for cadence in CADENCES:
        terminal_flanks = []
        post_terminal = []
        for (_, c), values in by_piece.items():
            if c != cadence or not all(t in values for t in [-1, 0, 1]):
                continue
            terminal_flanks.append(values[0] - (values[-1] + values[1]) / 2)
            post_terminal.append(values[1] - values[0])
        out.extend(contrast_rows(corpus, track, cadence, "terminal_minus_flanks", terminal_flanks))
        out.extend(contrast_rows(corpus, track, cadence, "post_minus_terminal", post_terminal))
    return out


def contrast_rows(corpus: str, track: str, cadence: str, contrast: str, values: list[float]) -> list[dict]:
    if len(values) < 3:
        return []
    avg = mean(values)
    sd = stdev(values)
    se = sd / math.sqrt(len(values))
    t_stat, p = stats.ttest_1samp(values, popmean=0)
    tcrit = stats.t.ppf(0.975, len(values) - 1)
    return [
        {
            "corpus": corpus,
            "track": track,
            "cadence_type": cadence,
            "contrast": contrast,
            "n_pieces": len(values),
            "mean_diff": avg,
            "ci95_low": avg - tcrit * se,
            "ci95_high": avg + tcrit * se,
            "t": t_stat,
            "df": len(values) - 1,
            "p_value": p,
            "p_bonferroni_2": min(1.0, p * 2),
        }
    ]


def design_matrix(rows: list[dict], include_category: bool, include_time: bool, include_interaction: bool) -> np.ndarray:
    cols = [np.ones(len(rows))]
    if include_category:
        for cadence in CADENCES[1:]:
            cols.append(np.array([1.0 if row["cadence_type"] == cadence else 0.0 for row in rows]))
    if include_time:
        for time in [0, 1]:
            cols.append(np.array([1.0 if int(row["time"]) == time else 0.0 for row in rows]))
    if include_interaction:
        for cadence in CADENCES[1:]:
            for time in [0, 1]:
                cols.append(np.array([1.0 if row["cadence_type"] == cadence and int(row["time"]) == time else 0.0 for row in rows]))
    return np.column_stack(cols)


def design_time(rows: list[dict]) -> np.ndarray:
    cols = [np.ones(len(rows))]
    for time in [0, 1]:
        cols.append(np.array([1.0 if int(row["time"]) == time else 0.0 for row in rows]))
    return np.column_stack(cols)


def fit_ols(y: np.ndarray, x: np.ndarray) -> dict:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ beta
    return {"rss": float(np.sum(residual**2)), "df_resid": len(y) - int(np.linalg.matrix_rank(x))}


def nested_f(reduced: dict, full: dict) -> dict:
    df1 = reduced["df_resid"] - full["df_resid"]
    df2 = full["df_resid"]
    f_value = ((reduced["rss"] - full["rss"]) / df1) / (full["rss"] / df2)
    return {"F": f_value, "p": stats.f.sf(f_value, df1, df2)}


def levene_cell_p(rows: list[dict]) -> float:
    groups = []
    for cadence in CADENCES:
        for time in [-1, 0, 1]:
            values = [float(row["ic"]) for row in rows if row["cadence_type"] == cadence and int(row["time"]) == time]
            if len(values) >= 2:
                groups.append(values)
    return float(stats.levene(*groups, center="median").pvalue) if len(groups) >= 2 else float("nan")


# ---------------------------------------------------------------------------
# SVG figures


def draw_terminal_scatter(rows: list[dict], path: Path, title: str) -> None:
    rows = [row for row in rows if row["cadence_type"] in CADENCES]
    if not rows:
        return
    xs = [float(row["harmony_ic"]) for row in rows]
    ys = [float(row["melody_ic"]) for row in rows]
    w, h, m = 820, 560, 72
    body = [svg_open(w, h, f"{title}: terminal harmony IC vs melody IC")]
    draw_axes(body, w, h, m, "Harmony IC", "Melody IC")
    for row in rows:
        x = scale(float(row["harmony_ic"]), min(xs), max(xs), m, w - m)
        y = scale(float(row["melody_ic"]), min(ys), max(ys), h - m, m)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="{COLORS[row["cadence_type"]]}" opacity="0.45"/>')
    draw_legend(body, CADENCES, w - 170, 78)
    body.append("</svg>")
    path.write_text("\n".join(body), encoding="utf-8")


def draw_entropy_profile(rows: list[dict], path: Path, title: str, window: int) -> None:
    w, h, m = 980, 540, 72
    vals = [
        float(row[key])
        for row in rows
        for key in ["mean_melody_entropy", "mean_harmony_entropy"]
        if row.get(key) not in {"", None}
    ]
    body = [svg_open(w, h, f"{title}: boundary-aligned entropy")]
    draw_axes(body, w, h, m, "Relative melody event", "Entropy")
    zx = scale(0, -window, window, m, w - m)
    body.append(f'<line x1="{zx:.1f}" y1="{m}" x2="{zx:.1f}" y2="{h-m}" stroke="#777" stroke-dasharray="5 5"/>')
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["cadence_type"]].append(row)
    for cadence in CADENCES:
        items = sorted(grouped.get(cadence, []), key=lambda row: int(row["relative_event"]))
        if not items:
            continue
        line(body, items, "mean_melody_entropy", window, w, h, m, min(vals), max(vals), COLORS[cadence], "")
        line(body, items, "mean_harmony_entropy", window, w, h, m, min(vals), max(vals), COLORS[cadence], 'stroke-dasharray="7 5"')
    draw_legend(body, CADENCES, w - 170, 78)
    body.append("</svg>")
    path.write_text("\n".join(body), encoding="utf-8")


def draw_standardized_dc_ec_space(rows: list[dict], path: Path) -> None:
    rows = [row for row in rows if row["cadence_type"] in {"DC", "EC"}]
    w, h = 1320, 560
    body = [svg_open(w, h, "DC vs EC in standardized IC space")]
    panels = [("beethoven_piano_sonatas", "Beethoven", 80), ("mozart_piano_sonatas", "Mozart", 700)]
    for corpus, title, x0 in panels:
        panel = [row for row in rows if row["corpus"] == corpus]
        draw_panel_scatter(body, panel, x0, 92, 520, 360, title)
    body.append("</svg>")
    path.write_text("\n".join(body), encoding="utf-8")


def draw_panel_scatter(body: list[str], rows: list[dict], x0: int, y0: int, w: int, h: int, title: str) -> None:
    xs = [float(row["harmony_ic_z"]) for row in rows]
    ys = [float(row["melody_ic_z"]) for row in rows]
    lo = min(xs + ys + [-2.5])
    hi = max(xs + ys + [2.5])
    body.append(f'<text x="{x0 + w/2}" y="{y0 - 28}" text-anchor="middle" class="panel">{title}</text>')
    draw_box_axes(body, x0, y0, w, h, "z(Harmony IC)", "z(Melody IC)")
    zx = scale(0, lo, hi, x0, x0 + w)
    zy = scale(0, lo, hi, y0 + h, y0)
    body.append(f'<line x1="{zx:.1f}" y1="{y0}" x2="{zx:.1f}" y2="{y0+h}" stroke="#111" stroke-dasharray="7 5"/>')
    body.append(f'<line x1="{x0}" y1="{zy:.1f}" x2="{x0+w}" y2="{zy:.1f}" stroke="#111" stroke-dasharray="7 5"/>')
    for row in rows:
        x = scale(float(row["harmony_ic_z"]), lo, hi, x0, x0 + w)
        y = scale(float(row["melody_ic_z"]), lo, hi, y0 + h, y0)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="{COLORS[row["cadence_type"]]}" opacity="0.78"/>')
    draw_legend(body, ["DC", "EC"], x0 + w - 90, y0 + 22)


def draw_post_cadential_bars(rows: list[dict], path: Path) -> None:
    data = {
        (row["corpus"], row["cadence_type"]): row
        for row in rows
        if row["analysis"] == "by_corpus_cadence" and row["cadence_type"] in CADENCES
    }
    lows = [float(row["ci95_low"]) for row in data.values()]
    highs = [float(row["ci95_high"]) for row in data.values()]
    ymin, ymax = min(-0.28, min(lows) - 0.22), max(highs) + 0.42
    w, h = 1420, 630
    body = [svg_open(w, h, "Post-cadential IC increase: melody vs harmony")]
    body.append(
        '<text x="710" y="65" text-anchor="middle" class="sub">DeltaDelta zIC = melody zIC increase (t0 to t1) minus harmony zIC increase; error bars = 95% CI</text>'
    )
    draw_bar_panel(body, data, "beethoven_piano_sonatas", "Beethoven", 92, 112, 594, 398, ymin, ymax)
    draw_bar_panel(body, data, "mozart_piano_sonatas", "Mozart", 778, 112, 594, 398, ymin, ymax)
    body.append("</svg>")
    path.write_text("\n".join(body), encoding="utf-8")


def draw_bar_panel(body, data, corpus, title, x0, y0, w, h, ymin, ymax) -> None:
    body.append(f'<text x="{x0+w/2}" y="{y0-24}" text-anchor="middle" class="panel">{title}</text>')
    draw_box_axes(body, x0, y0, w, h, "", "DeltaDelta zIC")
    zy = scale(0, ymin, ymax, y0 + h, y0)
    body.append(f'<line x1="{x0}" y1="{zy:.1f}" x2="{x0+w}" y2="{zy:.1f}" stroke="#111" stroke-dasharray="7 5"/>')
    bar_w = w / len(CADENCES) * 0.58
    for i, cadence in enumerate(CADENCES):
        row = data[(corpus, cadence)]
        cx = x0 + (i + 0.5) * w / len(CADENCES)
        val = float(row["mean_delta_delta_zic"])
        low, high = float(row["ci95_low"]), float(row["ci95_high"])
        top = scale(max(val, 0), ymin, ymax, y0 + h, y0)
        bottom = scale(min(val, 0), ymin, ymax, y0 + h, y0)
        body.append(
            f'<rect x="{cx-bar_w/2:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{max(2, abs(bottom-top)):.1f}" fill="{COLORS[cadence]}" opacity="0.94" stroke="#1f2937"/>'
        )
        y_low = scale(low, ymin, ymax, y0 + h, y0)
        y_high = scale(high, ymin, ymax, y0 + h, y0)
        body.append(f'<line x1="{cx:.1f}" y1="{y_high:.1f}" x2="{cx:.1f}" y2="{y_low:.1f}" stroke="#1f2937" stroke-width="1.8"/>')
        body.append(f'<line x1="{cx-9:.1f}" y1="{y_high:.1f}" x2="{cx+9:.1f}" y2="{y_high:.1f}" stroke="#1f2937" stroke-width="1.8"/>')
        body.append(f'<line x1="{cx-9:.1f}" y1="{y_low:.1f}" x2="{cx+9:.1f}" y2="{y_low:.1f}" stroke="#1f2937" stroke-width="1.8"/>')
        body.append(f'<text x="{cx:.1f}" y="{min(y_low, y_high)-12:.1f}" text-anchor="middle" class="star">{stars(float(row["p_greater_fdr"]))}</text>')
        body.append(f'<text x="{cx:.1f}" y="{y0+h+32}" text-anchor="middle" class="label">{cadence}</text>')


# ---------------------------------------------------------------------------
# Reporting and helpers


def write_report(
    path: Path,
    coupling_summary: list[dict],
    dominance_summary: list[dict],
    dominance_contrasts: list[dict],
    post_tests: list[dict],
    anova_rows: list[dict],
    planned_rows: list[dict],
) -> None:
    dc_ec = [
        row
        for row in dominance_contrasts
        if {row["cadence_a"], row["cadence_b"]} == {"DC", "EC"} and float(row["p_fdr"]) < 0.05
    ]
    post_main = [row for row in post_tests if row["analysis"] in {"overall", "by_corpus"}]
    lines = [
        "# Classical Cadence Pipeline Report",
        "",
        "This report is generated by `scripts/classical_cadence_pipeline.py`.",
        "",
        "## Terminal Melody-Harmony Summary",
        "",
        "| Corpus | Cadence | Markers | Pieces | Melody IC | Harmony IC | Melody H | Harmony H |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in coupling_summary:
        lines.append(
            f"| {short(row['corpus'])} | {row['cadence_type']} | {row['markers']} | {row['pieces']} | {fmt(row['mean_melody_ic_t0'])} | {fmt(row['mean_harmony_ic_t0'])} | {fmt(row['mean_melody_entropy_t0'])} | {fmt(row['mean_harmony_entropy_t0'])} |"
        )
    lines.extend(
        [
            "",
            "## Finding 1: DC vs EC Domain Dominance",
            "",
            "`dominance_index = harmony_ic_z - melody_ic_z`; positive values mean harmony-domain surprise is more prominent.",
            "",
            "| Corpus | Cadence | Melody z | Harmony z | Dominance | 95% CI |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in dominance_summary:
        if row["cadence_type"] in {"DC", "EC"}:
            lines.append(
                f"| {short(row['corpus'])} | {row['cadence_type']} | {fmt(row['mean_melody_ic_z'])} | {fmt(row['mean_harmony_ic_z'])} | {fmt(row['mean_dominance_index'])} | [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] |"
            )
    lines.extend(["", "Significant DC/EC contrasts:", ""])
    for row in dc_ec:
        lines.append(
            f"- {short(row['corpus'])} {row['contrast']}: mean diff = {fmt(row['mean_diff'])}, 95% CI [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}], FDR q = {fmt_p(row['p_fdr'])}."
        )
    lines.extend(
        [
            "",
            "## Finding 2: Post-Cadential Melody Rebound",
            "",
            "`DeltaDelta zIC = melody_delta_zIC(t0->t1) - harmony_delta_zIC(t0->t1)`.",
            "",
            "| Analysis | Corpus | Cadence | N | Melody delta | Harmony delta | DeltaDelta | 95% CI | P greater | FDR q |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(post_main, key=lambda r: (r["analysis"], r["corpus"])):
        lines.append(
            f"| {row['analysis']} | {short(row['corpus'])} | {row['cadence_type']} | {row['n_piece_cadence_units']} | {fmt(row['mean_melody_delta_zic'])} | {fmt(row['mean_harmony_delta_zic'])} | {fmt(row['mean_delta_delta_zic'])} | [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p_greater'])} | {fmt_p(row.get('p_greater_fdr', ''))} |"
        )
    lines.extend(
        [
            "",
            "## Experiment 3: Cadence Category x Time",
            "",
            "| Corpus | Track | Interaction F | Interaction p | Levene p |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in anova_rows:
        lines.append(
            f"| {short(row['corpus'])} | {row['track']} | {fmt(row['interaction_F'])} | {fmt_p(row['interaction_p'])} | {fmt_p(row['levene_p'])} |"
        )
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `dc_ec_standardized_ic_space.svg`",
            "- `post_cadential_delta_delta_by_composer.svg`",
            "- Per-composer folders contain terminal IC scatterplots and entropy profiles.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def z_params(values: list[float]) -> tuple[float, float]:
    return mean(values), pstdev(values)


def z(value: float, params: tuple[float, float]) -> float:
    mu, sd = params
    return (value - mu) / sd if sd else 0.0


def piece_level_values(rows: list[dict], metric: str) -> list[float]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(float(row[metric]))
    return [mean(values) for values in grouped.values()]


def bootstrap_ci(values: list[float], n: int) -> tuple[float, float]:
    estimates = [mean(random.choice(values) for _ in values) for _ in range(n)]
    return percentile(estimates, 2.5), percentile(estimates, 97.5)


def percentile(values: list[float], pct: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * pct / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] if lo == hi else values[lo] + (values[hi] - values[lo]) * (pos - lo)


def add_fdr(rows: list[dict], p_key: str) -> list[dict]:
    rows = [dict(row) for row in rows]
    indexed = sorted(enumerate(rows), key=lambda item: float(item[1][p_key]))
    m = len(indexed)
    adjusted = [1.0] * len(rows)
    running = 1.0
    for rank_from_end, (idx, row) in enumerate(reversed(indexed), start=1):
        rank = m - rank_from_end + 1
        running = min(running, float(row[p_key]) * m / rank)
        adjusted[idx] = min(1.0, running)
    out_key = "p_fdr" if p_key == "p_value" else f"{p_key}_fdr"
    for row, q in zip(rows, adjusted):
        row[out_key] = q
    return rows


def pearson(xs: list[float], ys: list[float]) -> float | str:
    if len(xs) < 3:
        return ""
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return ""
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def svg_open(width: int, height: int, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        "<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111827}.title{font-size:22px;font-weight:700}.panel{font-size:20px;font-weight:700}.sub{font-size:14px;fill:#374151}.label{font-size:13px}.star{font-size:21px;font-weight:700}.axis{stroke:#6b7280;stroke-width:1.2}</style>\n"
        '<rect width="100%" height="100%" fill="#fff"/>\n'
        f'<text x="24" y="34" class="title">{title}</text>'
    )


def draw_axes(body: list[str], width: int, height: int, margin: int, xlabel: str, ylabel: str) -> None:
    body.append(f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>')
    body.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" class="axis"/>')
    body.append(f'<text x="{width/2}" y="{height-22}" text-anchor="middle" class="label">{xlabel}</text>')
    body.append(f'<text x="18" y="38" class="label">{ylabel}</text>')


def draw_box_axes(body: list[str], x: int, y: int, w: int, h: int, xlabel: str, ylabel: str) -> None:
    body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" class="axis"/>')
    if xlabel:
        body.append(f'<text x="{x+w/2}" y="{y+h+48}" text-anchor="middle" class="label">{xlabel}</text>')
    if ylabel:
        body.append(f'<text x="{x-58}" y="{y+h/2}" text-anchor="middle" transform="rotate(-90 {x-58} {y+h/2})" class="label">{ylabel}</text>')


def draw_legend(body: list[str], labels: list[str], x: float, y: float) -> None:
    for i, label in enumerate(labels):
        yy = y + i * 22
        body.append(f'<circle cx="{x}" cy="{yy}" r="5" fill="{COLORS[label]}"/>')
        body.append(f'<text x="{x+14}" y="{yy+5}" class="label">{label}</text>')


def line(body, items, metric, window, w, h, m, ymin, ymax, color, extra) -> None:
    pts = []
    for row in items:
        if row.get(metric) in {"", None}:
            continue
        x = scale(int(row["relative_event"]), -window, window, m, w - m)
        y = scale(float(row[metric]), ymin, ymax, h - m, m)
        pts.append(f"{x:.1f},{y:.1f}")
    body.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" {extra} points="{" ".join(pts)}"/>')


def scale(v: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if math.isclose(lo, hi):
        return (out_lo + out_hi) / 2
    return out_lo + (v - lo) / (hi - lo) * (out_hi - out_lo)


def stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def short(corpus: str) -> str:
    if corpus == "all":
        return "all"
    return CORPORA.get(corpus, {}).get("short", corpus)


def fmt(value) -> str:
    if value == "":
        return ""
    return f"{float(value):.3f}"


def fmt_p(value) -> str:
    if value in {"", None}:
        return ""
    value = float(value)
    return "<0.001" if value < 0.001 else f"{value:.3f}"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
