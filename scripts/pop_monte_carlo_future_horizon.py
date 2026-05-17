from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


DEFAULT_BINS = [round(i / 10, 1) for i in range(1, 11)]
START = "<s>"


@dataclass
class FutureScore:
    piece_id: str
    source: str
    fold: int
    bin: float
    notes_before_c2: int
    target_type: str
    target_notes: str
    future_ic: float
    probability: float
    rollouts: int


class CpitchVOM:
    def __init__(self, max_order: int = 8, alpha: float = 0.1) -> None:
        self.max_order = max_order
        self.alpha = alpha
        self.vocab: list[int] = []
        self.vocab_index: dict[int, int] = {}
        self.counts: dict[tuple[object, ...], Counter[int]] = defaultdict(Counter)
        self._dist_cache: dict[tuple[object, ...], tuple[list[float], float]] = {}
        self._cdf_cache: dict[tuple[object, ...], np.ndarray] = {}

    def fit(self, sequences: list[list[int]]) -> "CpitchVOM":
        vocab = sorted({note for seq in sequences for note in seq})
        self.vocab = vocab
        self.vocab_index = {note: idx for idx, note in enumerate(vocab)}
        for seq in sequences:
            history: list[object] = [START] * self.max_order
            for note in seq:
                self._update(note, history)
                history.append(note)
        return self

    def _update(self, note: int, history: list[object]) -> None:
        for order in range(self.max_order + 1):
            context = tuple(history[-order:]) if order else ()
            self.counts[context][note] += 1

    def distribution(self, history: list[object]) -> tuple[list[float], float]:
        key = tuple(history[-self.max_order :])
        cached = self._dist_cache.get(key)
        if cached is not None:
            return cached
        vocab_n = len(self.vocab)
        if vocab_n == 0:
            return [], 0.0
        counter: Counter[int] | None = None
        for order in range(min(self.max_order, len(key)), -1, -1):
            context = tuple(key[-order:]) if order else ()
            if context in self.counts:
                counter = self.counts[context]
                break
        if counter is None:
            probs = [1.0 / vocab_n] * vocab_n
        else:
            total = sum(counter.values())
            denom = total + self.alpha * vocab_n
            probs = [(counter[note] + self.alpha) / denom for note in self.vocab]
        ent = -sum(p * math.log2(p) for p in probs if p > 0)
        self._dist_cache[key] = (probs, ent)
        return probs, ent

    def probability(self, note: int, history: list[object]) -> float:
        probs, _ = self.distribution(history)
        idx = self.vocab_index.get(note)
        if idx is None:
            return 1.0 / max(1, len(self.vocab))
        return probs[idx]

    def sample(self, history: list[object], rng: random.Random) -> int:
        probs, _ = self.distribution(history)
        draw = rng.random()
        cumulative = 0.0
        for note, prob in zip(self.vocab, probs):
            cumulative += prob
            if draw <= cumulative:
                return note
        return self.vocab[-1]

    def sample_bridge(self, context: list[int], horizon: int, rng: random.Random) -> list[int]:
        history: list[object] = [START] * self.max_order + list(context)
        bridge = []
        for _ in range(horizon):
            note = self.sample(history, rng)
            bridge.append(note)
            history.append(note)
        return bridge

    def target_log2_probability(self, context: list[int], target: list[int]) -> float:
        history: list[object] = [START] * self.max_order + list(context)
        logp = 0.0
        for note in target:
            probability = self.probability(note, history)
            logp += math.log2(max(probability, 1e-12))
            history.append(note)
        return logp

    def target_log2_probability_from_state(self, state: tuple[object, ...], target: list[int]) -> float:
        history = list(state)
        logp = 0.0
        for note in target:
            probability = self.probability(note, history)
            logp += math.log2(max(probability, 1e-12))
            history.append(note)
        return logp

    def cdf_for_state(self, state: tuple[object, ...]) -> np.ndarray:
        key = tuple(state[-self.max_order :])
        cached = self._cdf_cache.get(key)
        if cached is not None:
            return cached
        probs, _ = self.distribution(list(key))
        cdf = np.cumsum(np.array(probs, dtype=float))
        cdf[-1] = 1.0
        self._cdf_cache[key] = cdf
        return cdf

    def sample_final_state_counts(
        self,
        context: list[int],
        horizon: int,
        rollouts: int,
        rng: np.random.Generator,
    ) -> Counter[tuple[object, ...]]:
        start_state = tuple(([START] * self.max_order + list(context))[-self.max_order :])
        state_counts: Counter[tuple[object, ...]] = Counter({start_state: rollouts})
        for _ in range(horizon):
            next_counts: Counter[tuple[object, ...]] = Counter()
            for state, count in state_counts.items():
                cdf = self.cdf_for_state(state)
                draws = rng.random(count)
                note_indices = np.searchsorted(cdf, draws, side="left")
                sampled_counts = np.bincount(note_indices, minlength=len(self.vocab))
                prefix = state[1:]
                for note_index, sampled_count in enumerate(sampled_counts):
                    if sampled_count:
                        next_counts[prefix + (self.vocab[note_index],)] += int(sampled_count)
            state_counts = next_counts
        return state_counts

    def target_logmean_from_state_counts(self, states: Counter[tuple[object, ...]], target: list[int]) -> float:
        total = sum(states.values())
        weighted = [
            (self.target_log2_probability_from_state(state, target), count)
            for state, count in states.items()
        ]
        m = max(logp for logp, _ in weighted)
        return m + math.log2(sum(count * 2 ** (logp - m) for logp, count in weighted) / total)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cpitch-only Monte Carlo future-horizon C2 anticipation.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output-dir", default="output/pop_music_idyom_pipeline/monte_carlo_future_horizon")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-order", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--incipit-notes", type=int, default=4)
    parser.add_argument("--rollouts", type=int, default=100)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--raw-only", action="store_true", help="Only score the actual C2 incipit and write raw slope/onset outputs.")
    parser.add_argument(
        "--horizons",
        default="",
        help="Comma-separated fixed note horizons before C2, e.g. 1,2,4,8. If omitted, use proportional bins in the previous section.",
    )
    args = parser.parse_args()
    args.horizon_values = parse_horizons(args.horizons)
    args.timepoint_label = "Horizon" if args.horizon_values else "Bin"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    songs = load_songs(Path(args.events), args.incipit_notes, args.seed)
    assign_folds(songs, args.folds, args.seed)
    write_song_metadata(output_dir / "future_horizon_song_metadata.csv", songs)

    scores = run_future_horizon(songs, args)
    write_csv(output_dir / "future_horizon_scores.csv", [row.__dict__ for row in scores])
    raw_summary = summarize_raw(scores)
    write_csv(output_dir / "future_horizon_raw_summary.csv", raw_summary)
    slope_tests = slope_tests_raw(scores)
    write_csv(output_dir / "future_horizon_slope_tests.csv", slope_tests)
    onset_tests = onset_tests_raw(scores)
    write_csv(output_dir / "future_horizon_onset_tests.csv", onset_tests)
    plot_raw(raw_summary, onset_tests, output_dir / "future_horizon_raw_c2_ic.svg", output_dir / "future_horizon_raw_c2_ic.png", args)
    if args.raw_only:
        relative_summary = []
    else:
        relative_summary = summarize_relative(scores)
        write_csv(output_dir / "future_horizon_relative_summary.csv", relative_summary)
        plot_relative(relative_summary, output_dir / "future_horizon_relative_ic.svg", output_dir / "future_horizon_relative_ic.png")
    write_report(output_dir / "MONTE_CARLO_FUTURE_HORIZON_REPORT.md", songs, raw_summary, slope_tests, onset_tests, relative_summary, args)
    print(f"Wrote Monte Carlo future-horizon outputs to {output_dir}")


def load_songs(path: Path, incipit_notes: int, seed: int) -> list[dict]:
    by_piece: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_piece[row["piece_id"]].append(row)

    songs = []
    for piece_id, rows in sorted(by_piece.items()):
        rows.sort(key=lambda row: (float(row["onset"]), int(float(row.get("note_id_1") or row.get("event_index") or 0))))
        cpitch = [int(float(row["pitch"])) for row in rows]
        starts = [i for i, row in enumerate(rows) if truthy(row.get("section_start"))]
        segments = []
        for pos, start in enumerate(starts):
            end = starts[pos + 1] if pos + 1 < len(starts) else len(rows)
            label = normalize_section(rows[start].get("section_label", ""))
            if end > start:
                segments.append({"label": label, "start": start, "end": end})
        chorus = [seg for seg in segments if seg["label"] == "chorus"]
        verse = [seg for seg in segments if seg["label"] == "verse"]
        if len(chorus) < 2 or len(verse) < 2:
            continue
        c2 = chorus[1]
        v2 = verse[1]
        previous = previous_segment(segments, c2)
        if previous is None:
            continue
        c2_target = cpitch[c2["start"] : min(c2["start"] + incipit_notes, c2["end"])]
        v2_target = cpitch[v2["start"] : min(v2["start"] + incipit_notes, v2["end"])]
        if len(c2_target) < incipit_notes or len(v2_target) < incipit_notes:
            continue
        songs.append({
            "piece_id": piece_id,
            "source": rows[0].get("source", ""),
            "cpitch": cpitch,
            "previous_label": previous["label"],
            "previous_start": previous["start"],
            "previous_end": previous["end"],
            "c2_start": c2["start"],
            "v2_start": v2["start"],
            "c2_target": c2_target,
            "v2_target": v2_target,
        })

    rng = random.Random(seed)
    pool_by_source: dict[str, list[tuple[str, list[int]]]] = defaultdict(list)
    for song in songs:
        pool_by_source[song["source"]].append((song["piece_id"], song["c2_target"]))
    for song in songs:
        pool = [item for item in pool_by_source[song["source"]] if item[0] != song["piece_id"]]
        if not pool:
            pool = pool_by_source[song["source"]]
        song["other_song_c2_target"] = list(rng.choice(pool)[1])
        shuffled = list(song["c2_target"])
        rng.shuffle(shuffled)
        song["shuffled_c2_target"] = shuffled
    return songs


def run_future_horizon(songs: list[dict], args: argparse.Namespace) -> list[FutureScore]:
    rng = np.random.default_rng(args.seed)
    out: list[FutureScore] = []
    for fold in range(args.folds):
        train = [song["cpitch"] for song in songs if song["fold"] != fold]
        model = CpitchVOM(max_order=args.max_order, alpha=args.alpha).fit(train)
        print(f"Scoring fold {fold + 1}/{args.folds} with {sum(song['fold'] == fold for song in songs)} test songs")
        for song in songs:
            if song["fold"] == fold:
                out.extend(score_song(song, model, args, rng))
    return out


def score_song(song: dict, model: CpitchVOM, args: argparse.Namespace, rng: np.random.Generator) -> list[FutureScore]:
    rows = []
    previous_len = song["previous_end"] - song["previous_start"]
    targets = {
        "actual_c2": song["c2_target"],
    }
    if not args.raw_only:
        targets.update({
            "v2_opening": song["v2_target"],
            "other_song_c2": song["other_song_c2_target"],
            "shuffled_c2": song["shuffled_c2_target"],
        })
    for bin_value, tau, horizon in iter_scoring_points(song, previous_len, args):
        context = song["cpitch"][:tau]
        final_states = model.sample_final_state_counts(context, horizon, args.rollouts, rng)
        for target_type, target in targets.items():
            log_mean = model.target_logmean_from_state_counts(final_states, target)
            rows.append(FutureScore(
                piece_id=song["piece_id"],
                source=song["source"],
                fold=song["fold"],
                bin=bin_value,
                notes_before_c2=horizon,
                target_type=target_type,
                target_notes=" ".join(map(str, targets[target_type])),
                future_ic=-log_mean / len(targets[target_type]),
                probability=2 ** log_mean,
                rollouts=args.rollouts,
            ))
    return rows


def iter_scoring_points(song: dict, previous_len: int, args: argparse.Namespace) -> list[tuple[float, int, int]]:
    points = []
    if args.horizon_values:
        for horizon in sorted(args.horizon_values, reverse=True):
            tau = song["c2_start"] - horizon
            if tau < song["previous_start"] or tau < 1:
                continue
            points.append((float(horizon), tau, horizon))
        return points
    for bin_value in DEFAULT_BINS:
        within = max(1, min(previous_len, math.ceil(previous_len * bin_value)))
        tau = song["previous_start"] + within
        horizon = max(0, song["c2_start"] - tau)
        points.append((bin_value, tau, horizon))
    return points


def summarize_raw(rows: list[FutureScore]) -> list[dict[str, object]]:
    actual = [row for row in rows if row.target_type == "actual_c2"]
    out = []
    for source in sorted({row.source for row in actual} | {"ALL"}):
        source_rows = actual if source == "ALL" else [row for row in actual if row.source == source]
        for bin_value in row_timepoints(source_rows):
            subset = [row for row in source_rows if row.bin == bin_value]
            if len(subset) < 2:
                continue
            values = np.array([row.future_ic for row in subset], dtype=float)
            notes_before = np.array([row.notes_before_c2 for row in subset], dtype=float)
            lo, hi = ci95(values)
            out.append({
                "source": source,
                "bin": bin_value,
                "n_songs": len(values),
                "mean_notes_before_c2": notes_before.mean(),
                "median_notes_before_c2": float(np.median(notes_before)),
                "mean_future_ic_actual_c2": values.mean(),
                "ci95_low": lo,
                "ci95_high": hi,
            })
    return out


def slope_tests_raw(rows: list[FutureScore]) -> list[dict[str, object]]:
    actual = [row for row in rows if row.target_type == "actual_c2"]
    out = []
    for source in sorted({row.source for row in actual} | {"ALL"}):
        source_rows = actual if source == "ALL" else [row for row in actual if row.source == source]
        by_song: dict[str, list[FutureScore]] = defaultdict(list)
        for row in source_rows:
            by_song[row.piece_id].append(row)
        slopes = []
        for song_rows in by_song.values():
            if len(song_rows) < 3:
                continue
            x = np.array([row.notes_before_c2 for row in song_rows], dtype=float)
            y = np.array([row.future_ic for row in song_rows], dtype=float)
            slopes.append(float(np.polyfit(x, y, 1)[0]))
        if len(slopes) < 2:
            continue
        values = np.array(slopes, dtype=float)
        lo, hi = ci95(values)
        t, p = stats.ttest_1samp(values, 0.0)
        out.append({
            "source": source,
            "n_songs": len(values),
            "mean_slope_future_ic_per_note_before": values.mean(),
            "ci95_low": lo,
            "ci95_high": hi,
            "t": t,
            "p": p,
        })
    return out


def onset_tests_raw(rows: list[FutureScore]) -> list[dict[str, object]]:
    actual = [row for row in rows if row.target_type == "actual_c2"]
    out = []
    all_timepoints = row_timepoints(actual)
    horizon_mode = all_timepoints and max(all_timepoints) > 1.0
    if horizon_mode:
        baseline_points = sorted(all_timepoints, reverse=True)[:2]
        candidate_points = [point for point in sorted(all_timepoints, reverse=True) if point not in baseline_points]
    else:
        baseline_points = [0.1, 0.2]
        candidate_points = [point for point in sorted(all_timepoints) if point > 0.2]
    for source in sorted({row.source for row in actual} | {"ALL"}):
        source_rows = actual if source == "ALL" else [row for row in actual if row.source == source]
        by_song: dict[str, dict[float, FutureScore]] = defaultdict(dict)
        for row in source_rows:
            by_song[row.piece_id][row.bin] = row
        for bin_value in candidate_points:
            effects = []
            notes_before = []
            for song_bins in by_song.values():
                if bin_value not in song_bins or any(point not in song_bins for point in baseline_points):
                    continue
                baseline = sum(song_bins[point].future_ic for point in baseline_points) / len(baseline_points)
                effects.append(baseline - song_bins[bin_value].future_ic)
                notes_before.append(song_bins[bin_value].notes_before_c2)
            if len(effects) < 2:
                continue
            values = np.array(effects, dtype=float)
            lo, hi = ci95(values)
            t, p = stats.ttest_1samp(values, 0.0)
            out.append({
                "source": source,
                "bin": bin_value,
                "n_songs": len(values),
                "mean_notes_before_c2": float(np.mean(notes_before)),
                "median_notes_before_c2": float(np.median(notes_before)),
                "mean_early_baseline_minus_current_future_ic": values.mean(),
                "ci95_low": lo,
                "ci95_high": hi,
                "t": t,
                "p": p,
                "sustained_onset": 0,
            })
    for source in sorted({row["source"] for row in out}):
        subset = sorted(
            [row for row in out if row["source"] == source],
            key=lambda row: row["bin"],
            reverse=horizon_mode,
        )
        for idx, row in enumerate(subset):
            if (
                row["mean_early_baseline_minus_current_future_ic"] > 0
                and row["p"] < 0.05
                and all(later["mean_early_baseline_minus_current_future_ic"] > 0 and later["p"] < 0.05 for later in subset[idx:])
            ):
                row["sustained_onset"] = 1
                break
    return out


def summarize_relative(rows: list[FutureScore]) -> list[dict[str, object]]:
    by_key: dict[tuple[str, str, float], dict[str, FutureScore]] = defaultdict(dict)
    for row in rows:
        by_key[(row.source, row.piece_id, row.bin)][row.target_type] = row
    paired = []
    for (source, piece_id, bin_value), targets in by_key.items():
        actual = targets.get("actual_c2")
        if actual is None:
            continue
        for baseline in ["v2_opening", "other_song_c2", "shuffled_c2"]:
            if baseline not in targets:
                continue
            paired.append({
                "source": source,
                "piece_id": piece_id,
                "bin": bin_value,
                "baseline": baseline,
                "actual_future_ic": actual.future_ic,
                "baseline_future_ic": targets[baseline].future_ic,
                "baseline_minus_actual_future_ic": targets[baseline].future_ic - actual.future_ic,
                "notes_before_c2": actual.notes_before_c2,
            })
    out = []
    for source in sorted({row["source"] for row in paired} | {"ALL"}):
        source_rows = paired if source == "ALL" else [row for row in paired if row["source"] == source]
        for baseline in ["v2_opening", "other_song_c2", "shuffled_c2"]:
            for bin_value in sorted({row["bin"] for row in source_rows if row["baseline"] == baseline}):
                subset = [row for row in source_rows if row["baseline"] == baseline and row["bin"] == bin_value]
                if len(subset) < 2:
                    continue
                values = np.array([row["baseline_minus_actual_future_ic"] for row in subset], dtype=float)
                actual = np.array([row["actual_future_ic"] for row in subset], dtype=float)
                baseline_ic = np.array([row["baseline_future_ic"] for row in subset], dtype=float)
                notes_before = np.array([row["notes_before_c2"] for row in subset], dtype=float)
                lo, hi = ci95(values)
                t, p = stats.ttest_1samp(values, 0.0)
                out.append({
                    "source": source,
                    "baseline": baseline,
                    "bin": bin_value,
                    "n_songs": len(values),
                    "mean_notes_before_c2": notes_before.mean(),
                    "median_notes_before_c2": float(np.median(notes_before)),
                    "mean_actual_c2_future_ic": actual.mean(),
                    "mean_baseline_future_ic": baseline_ic.mean(),
                    "mean_baseline_minus_actual_future_ic": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "t": t,
                    "p": p,
                })
    return out


def plot_raw(
    summary: list[dict[str, object]],
    onset_rows: list[dict[str, object]],
    svg_path: Path,
    png_path: Path,
    args: argparse.Namespace,
) -> None:
    rows = sorted([row for row in summary if row["source"] == "ALL"], key=lambda row: row["bin"])
    x = np.array([row["mean_notes_before_c2"] for row in rows], dtype=float)
    y = np.array([row["mean_future_ic_actual_c2"] for row in rows], dtype=float)
    lo = np.array([row["ci95_low"] for row in rows], dtype=float)
    hi = np.array([row["ci95_high"] for row in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.plot(x, y, marker="o", lw=2, color="#4C78A8")
    ax.fill_between(x, lo, hi, color="#4C78A8", alpha=0.18, linewidth=0)
    onset = next((row for row in onset_rows if row["source"] == "ALL" and row["sustained_onset"]), None)
    if onset:
        ax.axvline(onset["mean_notes_before_c2"], color="#D62728", lw=1.4, ls="--")
        label = f"onset {int(onset['bin'])} notes" if args.horizon_values else f"onset {onset['bin']:.1f}"
        ax.text(onset["mean_notes_before_c2"], max(hi), label, color="#D62728", ha="right", va="top")
    ax.invert_xaxis()
    ax.set_xlabel("Mean notes before C2 onset")
    ax.set_ylabel("Future IC of actual C2 opening (bits)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def plot_relative(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in summary if row["source"] == "ALL"]
    labels = {"v2_opening": "V2 opening", "other_song_c2": "Other-song C2", "shuffled_c2": "Shuffled C2"}
    colors = {"v2_opening": "#54A24B", "other_song_c2": "#4C78A8", "shuffled_c2": "#F58518"}
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    for baseline in ["v2_opening", "other_song_c2", "shuffled_c2"]:
        items = sorted([row for row in rows if row["baseline"] == baseline], key=lambda row: row["bin"])
        x = np.array([row["mean_notes_before_c2"] for row in items], dtype=float)
        y = np.array([row["mean_baseline_minus_actual_future_ic"] for row in items], dtype=float)
        lo = np.array([row["ci95_low"] for row in items], dtype=float)
        hi = np.array([row["ci95_high"] for row in items], dtype=float)
        ax.plot(x, y, marker="o", lw=2, label=labels[baseline], color=colors[baseline])
        ax.fill_between(x, lo, hi, color=colors[baseline], alpha=0.16, linewidth=0)
    ax.axhline(0, color="#555555", lw=1)
    ax.invert_xaxis()
    ax.set_xlabel("Mean notes before C2 onset")
    ax.set_ylabel("Control future IC - actual C2 future IC (bits)")
    ax.text(0.02, 0.96, "Positive = actual C2 is more predictable at the future horizon", transform=ax.transAxes, va="top")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def write_report(
    path: Path,
    songs: list[dict],
    raw_summary: list[dict],
    slope_rows: list[dict],
    onset_rows: list[dict],
    relative_rows: list[dict],
    args: argparse.Namespace,
) -> None:
    lines = [
        "# Cpitch Monte Carlo Future-Horizon Prediction",
        "",
        "This analysis samples intervening cpitch paths up to the true C2 horizon, then scores the actual C2 cpitch incipit after each sampled path.",
        "",
        f"- Eligible songs: {len(songs)}",
        f"- Folds: {args.folds}",
        f"- Max order: {args.max_order}",
        f"- Incipit length: {args.incipit_notes} cpitch events",
        f"- Rollouts: {args.rollouts}",
        f"- Timepoints: fixed horizons {', '.join(map(str, args.horizon_values))} notes before C2" if args.horizon_values else "- Timepoints: proportional bins 10%-100% of the section before C2",
        f"- Raw only: {args.raw_only}",
        "",
        "## Raw Future IC Slope",
        "",
        "| Source | N songs | Mean slope per note before C2 [95% CI] | p |",
        "|---|---:|---:|---:|",
    ]
    for row in slope_rows:
        lines.append(
            f"| {row['source']} | {row['n_songs']} | "
            f"{fmt(row['mean_slope_future_ic_per_note_before'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
        )
    lines.extend([
        "",
        "## Raw Future IC Onset",
        "",
        f"| Source | {args.timepoint_label} | Notes before C2 | Baseline - current future IC [95% CI] | p | Onset |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in onset_rows:
        lines.append(
            f"| {row['source']} | {row['bin']:.1f} | {fmt(row['mean_notes_before_c2'])} | "
            f"{fmt(row['mean_early_baseline_minus_current_future_ic'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | "
            f"{fmt_p(row['p'])} | {row['sustained_onset']} |"
        )
    if relative_rows:
        lines.extend([
            "",
            "## Relative Future IC, All Songs",
            "",
            f"| Baseline | {args.timepoint_label} | N | Actual C2 future IC | Baseline future IC | Effect [95% CI] | p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for row in relative_rows:
            if row["source"] != "ALL":
                continue
            lines.append(
                f"| {row['baseline']} | {row['bin']:.1f} | {row['n_songs']} | "
                f"{fmt(row['mean_actual_c2_future_ic'])} | {fmt(row['mean_baseline_future_ic'])} | "
                f"{fmt(row['mean_baseline_minus_actual_future_ic'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
            )
    lines.extend(["", "## Headline", "", future_headline(slope_rows, onset_rows, relative_rows, bool(args.horizon_values))])
    path.write_text("\n".join(lines), encoding="utf-8")


def future_headline(slope_rows: list[dict], onset_rows: list[dict], relative_rows: list[dict], horizon_mode: bool) -> str:
    slope = next((row for row in slope_rows if row["source"] == "ALL"), None)
    onset = next((row for row in onset_rows if row["source"] == "ALL" and row["sustained_onset"]), None)
    parts = []
    if slope:
        direction = "gets lower closer to C2" if slope["mean_slope_future_ic_per_note_before"] > 0 else "does not get lower closer to C2"
        parts.append(
            f"Raw future IC {direction}: slope {fmt(slope['mean_slope_future_ic_per_note_before'])} per note before C2, p = {fmt_p(slope['p'])}."
        )
    if onset:
        label = f"horizon {int(onset['bin'])}" if horizon_mode else f"bin {onset['bin']:.1f}"
        parts.append(f"Sustained onset: {label}, about {fmt(onset['mean_notes_before_c2'])} notes before C2.")
    else:
        baseline = "8/4-note horizon baseline" if horizon_mode else "10/20% baseline criterion"
        parts.append(f"No sustained raw future-IC onset under the {baseline}.")
    if not relative_rows:
        return " ".join(parts)
    rel = [row for row in relative_rows if row["source"] == "ALL"]
    for baseline in ["other_song_c2", "shuffled_c2", "v2_opening"]:
        subset = sorted([row for row in rel if row["baseline"] == baseline], key=lambda row: row["bin"], reverse=horizon_mode)
        sustained = [
            row for idx, row in enumerate(subset)
            if row["mean_baseline_minus_actual_future_ic"] > 0
            and row["p"] < 0.05
            and all(later["mean_baseline_minus_actual_future_ic"] > 0 and later["p"] < 0.05 for later in subset[idx:])
        ]
        if sustained:
            label = f"horizon {int(sustained[0]['bin'])}" if horizon_mode else f"bin {sustained[0]['bin']:.1f}"
            parts.append(f"`{baseline}`: actual C2 advantage from {label}.")
        else:
            parts.append(f"`{baseline}`: no sustained actual C2 advantage.")
    return " ".join(parts)


def write_song_metadata(path: Path, songs: list[dict]) -> None:
    rows = []
    for song in songs:
        rows.append({
            "piece_id": song["piece_id"],
            "source": song["source"],
            "fold": song["fold"],
            "previous_section": song["previous_label"],
            "previous_start_note": song["previous_start"] + 1,
            "previous_end_note": song["previous_end"],
            "c2_start_note": song["c2_start"] + 1,
            "v2_start_note": song["v2_start"] + 1,
            "c2_target": " ".join(map(str, song["c2_target"])),
            "v2_target": " ".join(map(str, song["v2_target"])),
            "other_song_c2_target": " ".join(map(str, song["other_song_c2_target"])),
            "shuffled_c2_target": " ".join(map(str, song["shuffled_c2_target"])),
        })
    write_csv(path, rows)


def previous_segment(segments: list[dict], target: dict) -> dict | None:
    previous = None
    for segment in segments:
        if segment["start"] >= target["start"]:
            break
        previous = segment
    return previous


def parse_horizons(value: str) -> list[int]:
    if not value.strip():
        return []
    horizons = sorted({int(item.strip()) for item in value.split(",") if item.strip()})
    if any(horizon <= 0 for horizon in horizons):
        raise ValueError("--horizons must contain positive integers")
    return horizons


def row_timepoints(rows: list[FutureScore]) -> list[float]:
    return sorted({row.bin for row in rows})


def assign_folds(songs: list[dict], folds: int, seed: int) -> None:
    rng = random.Random(seed)
    indices = list(range(len(songs)))
    rng.shuffle(indices)
    for rank, idx in enumerate(indices):
        songs[idx]["fold"] = rank % folds


def normalize_section(value: str) -> str:
    value = value.lower().strip().replace("-", "_").replace(" ", "_")
    if "chorus" in value or "refrain" in value:
        return "chorus"
    if value == "verse" or value.startswith("verse"):
        return "verse"
    if "pre_chorus" in value or "prechorus" in value:
        return "pre_chorus"
    if value in {"bridge", "b", "bp"}:
        return "bridge"
    return value or "unknown"


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def logmeanexp_base2(log_values: list[float]) -> float:
    m = max(log_values)
    return m + math.log2(sum(2 ** (value - m) for value in log_values) / len(log_values))


def ci95(values: np.ndarray) -> tuple[float, float]:
    se = values.std(ddof=1) / math.sqrt(len(values))
    tcrit = stats.t.ppf(0.975, len(values) - 1)
    mean = float(values.mean())
    return mean - tcrit * se, mean + tcrit * se


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


def fmt(value: object) -> str:
    return f"{float(value):.3f}"


def fmt_p(value: object) -> str:
    p = float(value)
    return "<.001" if p < 0.001 else f"{p:.3f}"


if __name__ == "__main__":
    main()
