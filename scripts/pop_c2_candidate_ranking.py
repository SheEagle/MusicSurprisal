from __future__ import annotations

import argparse
import csv
import math
import random
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


@dataclass
class CandidateScore:
    piece_id: str
    source: str
    fold: int
    horizon: int
    target_type: str
    target_notes: str
    mean_ic: float
    probability: float
    rank: int
    margin_vs_target: str
    margin_ic: float


def main() -> None:
    parser = argparse.ArgumentParser(description="C2 opening candidate-rank analysis from true pre-C2 contexts.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output-dir", default="output/pop_music_idyom_pipeline/c2_candidate_ranking")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-order", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--incipit-notes", type=int, default=4)
    parser.add_argument("--horizons", default="16,8,4,2,1")
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()
    args.horizon_values = parse_ints(args.horizons)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    songs = load_songs(Path(args.events), args.incipit_notes, args.seed)
    assign_folds(songs, args.folds, args.seed)
    rows = run_analysis(songs, args)

    write_csv(output_dir / "c2_candidate_scores.csv", [row.__dict__ for row in rows])
    write_song_metadata(output_dir / "c2_candidate_song_metadata.csv", songs)

    rank_summary = summarize_ranks(rows)
    margin_summary = summarize_margins(rows)
    raw_summary = summarize_raw_ic(rows)
    write_csv(output_dir / "c2_candidate_rank_summary.csv", rank_summary)
    write_csv(output_dir / "c2_candidate_margin_summary.csv", margin_summary)
    write_csv(output_dir / "c2_candidate_raw_ic_summary.csv", raw_summary)

    plot_rank(rank_summary, output_dir / "c2_candidate_actual_rank.svg", output_dir / "c2_candidate_actual_rank.png")
    plot_margin(margin_summary, output_dir / "c2_candidate_margins.svg", output_dir / "c2_candidate_margins.png")
    write_report(output_dir / "C2_CANDIDATE_RANKING_REPORT.md", songs, args, rank_summary, margin_summary, raw_summary)
    print(f"Wrote C2 candidate-ranking outputs to {output_dir}")


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
        c1, c2 = chorus[0], chorus[1]
        v2 = verse[1]
        targets = {
            "actual_c2": cpitch[c2["start"] : min(c2["start"] + incipit_notes, c2["end"])],
            "c1_opening": cpitch[c1["start"] : min(c1["start"] + incipit_notes, c1["end"])],
            "v2_opening": cpitch[v2["start"] : min(v2["start"] + incipit_notes, v2["end"])],
        }
        if any(len(target) < incipit_notes for target in targets.values()):
            continue
        matched = find_same_song_nonchorus_matched(cpitch, segments, targets["actual_c2"], incipit_notes, exclude_starts={v2["start"]})
        if matched is None:
            continue
        targets["same_song_nonchorus_matched"] = matched
        songs.append({
            "piece_id": piece_id,
            "source": rows[0].get("source", ""),
            "cpitch": cpitch,
            "segments": segments,
            "c2_start": c2["start"],
            "targets": targets,
        })

    rng = random.Random(seed)
    for song in songs:
        shuffled = list(song["targets"]["actual_c2"])
        rng.shuffle(shuffled)
        song["targets"]["shuffled_c2"] = shuffled
    return songs


def find_same_song_nonchorus_matched(
    cpitch: list[int],
    segments: list[dict],
    target: list[int],
    length: int,
    exclude_starts: set[int],
) -> list[int] | None:
    best_window = None
    best_score = float("inf")
    target_array = np.array(target, dtype=float)
    for segment in segments:
        if segment["label"] == "chorus":
            continue
        for start in range(segment["start"], segment["end"] - length + 1):
            if start in exclude_starts:
                continue
            window = cpitch[start : start + length]
            score = window_match_score(target_array, np.array(window, dtype=float))
            if score < best_score:
                best_score = score
                best_window = window
    return list(best_window) if best_window is not None else None


def window_match_score(target: np.ndarray, candidate: np.ndarray) -> float:
    target_steps = np.diff(target)
    candidate_steps = np.diff(candidate)
    return float(
        abs(target.mean() - candidate.mean())
        + abs(np.ptp(target) - np.ptp(candidate))
        + 0.5 * np.mean(np.abs(target_steps - candidate_steps))
    )


def run_analysis(songs: list[dict], args: argparse.Namespace) -> list[CandidateScore]:
    rows = []
    for fold in range(args.folds):
        train = [song["cpitch"] for song in songs if song["fold"] != fold]
        model = CpitchVOM(max_order=args.max_order, alpha=args.alpha).fit(train)
        test_songs = [song for song in songs if song["fold"] == fold]
        print(f"Scoring fold {fold + 1}/{args.folds} with {len(test_songs)} test songs")
        for song in test_songs:
            rows.extend(score_song(song, model, args))
    return rows


def score_song(song: dict, model: CpitchVOM, args: argparse.Namespace) -> list[CandidateScore]:
    rows = []
    targets = song["targets"]
    for horizon in sorted(args.horizon_values, reverse=True):
        tau = song["c2_start"] - horizon
        if tau < 1:
            continue
        context = song["cpitch"][:tau]
        scored = []
        for target_type, target in targets.items():
            logp = model.target_log2_probability(context, target)
            scored.append({
                "target_type": target_type,
                "target": target,
                "mean_ic": -logp / len(target),
                "probability": 2 ** logp,
            })
        scored.sort(key=lambda row: row["mean_ic"])
        ranks = {row["target_type"]: rank for rank, row in enumerate(scored, start=1)}
        actual_ic = next(row["mean_ic"] for row in scored if row["target_type"] == "actual_c2")
        for item in scored:
            margin_vs = "actual_c2" if item["target_type"] != "actual_c2" else ""
            margin_ic = item["mean_ic"] - actual_ic if item["target_type"] != "actual_c2" else 0.0
            rows.append(CandidateScore(
                piece_id=song["piece_id"],
                source=song["source"],
                fold=song["fold"],
                horizon=horizon,
                target_type=item["target_type"],
                target_notes=" ".join(map(str, item["target"])),
                mean_ic=item["mean_ic"],
                probability=item["probability"],
                rank=ranks[item["target_type"]],
                margin_vs_target=margin_vs,
                margin_ic=margin_ic,
            ))
    return rows


def summarize_ranks(rows: list[CandidateScore]) -> list[dict[str, object]]:
    actual = [row for row in rows if row.target_type == "actual_c2"]
    out = []
    for source in sorted({row.source for row in actual} | {"ALL"}):
        source_rows = actual if source == "ALL" else [row for row in actual if row.source == source]
        for horizon in sorted({row.horizon for row in source_rows}, reverse=True):
            subset = [row for row in source_rows if row.horizon == horizon]
            ranks = np.array([row.rank for row in subset], dtype=float)
            lo, hi = ci95(ranks)
            top1 = float(np.mean(ranks == 1))
            top2 = float(np.mean(ranks <= 2))
            out.append({
                "source": source,
                "horizon": horizon,
                "n_songs": len(subset),
                "mean_actual_c2_rank": ranks.mean(),
                "ci95_low": lo,
                "ci95_high": hi,
                "top1_rate": top1,
                "top2_rate": top2,
            })
    return out


def summarize_margins(rows: list[CandidateScore]) -> list[dict[str, object]]:
    controls = [row for row in rows if row.target_type != "actual_c2"]
    out = []
    for source in sorted({row.source for row in controls} | {"ALL"}):
        source_rows = controls if source == "ALL" else [row for row in controls if row.source == source]
        for target_type in ["v2_opening", "c1_opening", "same_song_nonchorus_matched", "shuffled_c2"]:
            target_rows = [row for row in source_rows if row.target_type == target_type]
            for horizon in sorted({row.horizon for row in target_rows}, reverse=True):
                subset = [row for row in target_rows if row.horizon == horizon]
                if len(subset) < 2:
                    continue
                values = np.array([row.margin_ic for row in subset], dtype=float)
                lo, hi = ci95(values)
                t, p = ttest(values)
                out.append({
                    "source": source,
                    "control": target_type,
                    "horizon": horizon,
                    "n_songs": len(values),
                    "mean_control_minus_actual_c2_ic": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "t": t,
                    "p": p,
                })
    return out


def summarize_raw_ic(rows: list[CandidateScore]) -> list[dict[str, object]]:
    out = []
    for source in sorted({row.source for row in rows} | {"ALL"}):
        source_rows = rows if source == "ALL" else [row for row in rows if row.source == source]
        for target_type in ["actual_c2", "v2_opening", "c1_opening", "same_song_nonchorus_matched", "shuffled_c2"]:
            target_rows = [row for row in source_rows if row.target_type == target_type]
            for horizon in sorted({row.horizon for row in target_rows}, reverse=True):
                subset = [row for row in target_rows if row.horizon == horizon]
                if len(subset) < 2:
                    continue
                values = np.array([row.mean_ic for row in subset], dtype=float)
                lo, hi = ci95(values)
                out.append({
                    "source": source,
                    "target_type": target_type,
                    "horizon": horizon,
                    "n_songs": len(values),
                    "mean_ic": values.mean(),
                    "ci95_low": lo,
                    "ci95_high": hi,
                })
    return out


def plot_rank(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = sorted([row for row in summary if row["source"] == "ALL"], key=lambda row: row["horizon"], reverse=True)
    x = np.array([row["horizon"] for row in rows], dtype=float)
    y = np.array([row["mean_actual_c2_rank"] for row in rows], dtype=float)
    lo = np.array([row["ci95_low"] for row in rows], dtype=float)
    hi = np.array([row["ci95_high"] for row in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(7.0, 4.1))
    ax.plot(x, y, marker="o", lw=2, color="#4C78A8")
    ax.fill_between(x, lo, hi, color="#4C78A8", alpha=0.18, linewidth=0)
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.set_xlabel("Notes before C2 onset")
    ax.set_ylabel("Actual C2 rank among candidates")
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def plot_margin(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in summary if row["source"] == "ALL"]
    labels = {
        "v2_opening": "V2 opening",
        "c1_opening": "C1 opening",
        "same_song_nonchorus_matched": "Matched non-chorus",
        "shuffled_c2": "Shuffled C2",
    }
    colors = {
        "v2_opening": "#54A24B",
        "c1_opening": "#4C78A8",
        "same_song_nonchorus_matched": "#F58518",
        "shuffled_c2": "#E45756",
    }
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    for control in labels:
        items = sorted([row for row in rows if row["control"] == control], key=lambda row: row["horizon"], reverse=True)
        x = np.array([row["horizon"] for row in items], dtype=float)
        y = np.array([row["mean_control_minus_actual_c2_ic"] for row in items], dtype=float)
        lo = np.array([row["ci95_low"] for row in items], dtype=float)
        hi = np.array([row["ci95_high"] for row in items], dtype=float)
        ax.plot(x, y, marker="o", lw=2, label=labels[control], color=colors[control])
        ax.fill_between(x, lo, hi, color=colors[control], alpha=0.14, linewidth=0)
    ax.axhline(0, color="#555555", lw=1)
    ax.invert_xaxis()
    ax.set_xlabel("Notes before C2 onset")
    ax.set_ylabel("Control IC - actual C2 IC (bits)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def write_report(path: Path, songs: list[dict], args: argparse.Namespace, rank_summary: list[dict], margin_summary: list[dict], raw_summary: list[dict]) -> None:
    lines = [
        "# C2 Candidate-Ranking Analysis",
        "",
        "At fixed true pre-C2 contexts, this analysis scores candidate 4-cpitch openings as immediate continuations.",
        "",
        f"- Eligible songs: {len(songs)}",
        f"- Folds: {args.folds}",
        f"- Max order: {args.max_order}",
        f"- Incipit length: {args.incipit_notes} cpitch events",
        f"- Horizons: {', '.join(map(str, args.horizon_values))} notes before C2",
        "- Candidates: actual_C2, V2_opening, C1_opening, same_song_nonchorus_matched, shuffled_C2",
        "",
        "## Actual C2 Rank",
        "",
        "| Source | Horizon | N | Mean rank [95% CI] | Top-1 | Top-2 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rank_summary:
        lines.append(
            f"| {row['source']} | {row['horizon']} | {row['n_songs']} | "
            f"{fmt(row['mean_actual_c2_rank'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | "
            f"{fmt(row['top1_rate'])} | {fmt(row['top2_rate'])} |"
        )
    lines.extend([
        "",
        "## Margins: Control IC - Actual C2 IC",
        "",
        "| Source | Control | Horizon | N | Margin [95% CI] | p |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in margin_summary:
        lines.append(
            f"| {row['source']} | {row['control']} | {row['horizon']} | {row['n_songs']} | "
            f"{fmt(row['mean_control_minus_actual_c2_ic'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
        )
    lines.extend(["", "## Headline", "", headline(rank_summary, margin_summary)])
    path.write_text("\n".join(lines), encoding="utf-8")


def headline(rank_summary: list[dict], margin_summary: list[dict]) -> str:
    all_rank_h1 = next(row for row in rank_summary if row["source"] == "ALL" and row["horizon"] == 1)
    margins_h1 = [row for row in margin_summary if row["source"] == "ALL" and row["horizon"] == 1]
    significant_wins = [row for row in margins_h1 if row["mean_control_minus_actual_c2_ic"] > 0 and row["p"] < 0.05]
    return (
        f"At 1 note before C2, actual C2 mean rank is {fmt(all_rank_h1['mean_actual_c2_rank'])}; "
        f"top-1 rate is {fmt(all_rank_h1['top1_rate'])}. "
        f"It significantly beats {len(significant_wins)} of 4 controls at this horizon."
    )


def write_song_metadata(path: Path, songs: list[dict]) -> None:
    rows = []
    for song in songs:
        row = {
            "piece_id": song["piece_id"],
            "source": song["source"],
            "fold": song["fold"],
            "c2_start_note": song["c2_start"] + 1,
        }
        for target_type, target in song["targets"].items():
            row[target_type] = " ".join(map(str, target))
        rows.append(row)
    write_csv(path, rows)


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


def parse_ints(value: str) -> list[int]:
    out = sorted({int(item.strip()) for item in value.split(",") if item.strip()}, reverse=True)
    if any(item <= 0 for item in out):
        raise ValueError("All horizons must be positive")
    return out


def ttest(values: np.ndarray) -> tuple[float, float]:
    if len(values) < 2 or float(values.std(ddof=1)) < 1e-12:
        return float("nan"), float("nan")
    t, p = stats.ttest_1samp(values, 0.0)
    return float(t), float(p)


def fmt(value: object) -> str:
    value = float(value)
    return "nan" if math.isnan(value) else f"{value:.3f}"


def fmt_p(value: object) -> str:
    p = float(value)
    if math.isnan(p):
        return "nan"
    return "<.001" if p < 0.001 else f"{p:.3f}"


if __name__ == "__main__":
    main()
