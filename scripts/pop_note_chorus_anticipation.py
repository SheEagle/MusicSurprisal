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


BINS = [round(i / 10, 1) for i in range(1, 11)]
START = "<s>"


@dataclass
class ScoreRow:
    piece_id: str
    source: str
    fold: int
    model: str
    bin: float
    previous_section: str
    target_type: str
    target_notes: str
    mean_ic: float
    probability: float
    entropy: float
    context_note_count: int
    target_note_count: int


class NoteMarkov:
    def __init__(self, max_order: int = 8, alpha: float = 0.1, vocab: set[int] | None = None) -> None:
        self.max_order = max_order
        self.alpha = alpha
        self.vocab = set(vocab or [])
        self.counts: dict[tuple[object, ...], Counter[int]] = defaultdict(Counter)

    def fit(self, sequences: list[list[int]]) -> "NoteMarkov":
        for seq in sequences:
            history: list[object] = [START] * self.max_order
            for note in seq:
                self.update(note, history)
                history.append(note)
        return self

    def update(self, note: int, history: list[object]) -> None:
        self.vocab.add(note)
        for order in range(self.max_order + 1):
            context = tuple(history[-order:]) if order else ()
            self.counts[context][note] += 1

    def distribution(self, history: list[object]) -> tuple[dict[int, float], float]:
        vocab = sorted(self.vocab)
        if not vocab:
            return {}, 0.0
        context = history[-self.max_order :]
        counter: Counter[int] | None = None
        for order in range(len(context), -1, -1):
            ctx = tuple(context[-order:]) if order else ()
            if ctx in self.counts:
                counter = self.counts[ctx]
                break
        if counter is None:
            probability = 1.0 / len(vocab)
            return {note: probability for note in vocab}, math.log2(len(vocab))
        total = sum(counter.values())
        denom = total + self.alpha * len(vocab)
        dist = {note: (counter[note] + self.alpha) / denom for note in vocab}
        return dist, entropy(dist)

    def score_sequence(self, target: list[int], context: list[int]) -> tuple[float, float, float]:
        history: list[object] = [START] * self.max_order + list(context)
        ics = []
        log_probability = 0.0
        entropies = []
        for note in target:
            dist, ent = self.distribution(history)
            p = dist.get(note, self.alpha / max(self.alpha * max(1, len(self.vocab)), 1e-12))
            ics.append(-math.log2(max(p, 1e-12)))
            log_probability += math.log(max(p, 1e-12))
            entropies.append(ent)
            history.append(note)
        return float(np.mean(ics)), math.exp(log_probability), float(np.mean(entropies))


def main() -> None:
    parser = argparse.ArgumentParser(description="Note-level chorus incipit anticipation before C2.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output-dir", default="output/pop_music_idyom_pipeline/note_chorus_anticipation")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-order", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--incipit-notes", type=int, default=4)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    songs = load_songs(Path(args.events), args.incipit_notes, args.seed)
    assign_folds(songs, args.folds, args.seed)
    rows = run_predictions(songs, args)
    write_csv(output_dir / "note_chorus_anticipation_scores.csv", [row.__dict__ for row in rows])
    summary = summarize(rows)
    write_csv(output_dir / "note_chorus_anticipation_summary.csv", summary)
    write_song_metadata(output_dir / "note_chorus_anticipation_song_metadata.csv", songs)
    plot_summary(summary, output_dir / "note_chorus_anticipation_curve.svg", output_dir / "note_chorus_anticipation_curve.png")
    write_report(output_dir / "NOTE_CHORUS_ANTICIPATION_REPORT.md", songs, summary, args)
    print(f"Wrote note-level chorus anticipation outputs to {output_dir}")


def load_songs(path: Path, incipit_notes: int, seed: int) -> list[dict]:
    by_piece: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_piece[row["piece_id"]].append(row)

    songs = []
    for piece_id, rows in sorted(by_piece.items()):
        rows.sort(key=lambda row: (float(row["onset"]), int(float(row.get("note_id_1") or row.get("event_index") or 0))))
        notes = [int(float(row["pitch"])) for row in rows]
        starts = [i for i, row in enumerate(rows) if truthy(row.get("section_start"))]
        segments = []
        for pos, start in enumerate(starts):
            end = starts[pos + 1] if pos + 1 < len(starts) else len(rows)
            label = normalize_section(rows[start].get("section_label", ""))
            if end - start <= 0:
                continue
            segments.append({"label": label, "start": start, "end": end})
        chorus_segments = [seg for seg in segments if seg["label"] == "chorus"]
        verse_segments = [seg for seg in segments if seg["label"] == "verse"]
        if len(chorus_segments) < 2 or len(verse_segments) < 2:
            continue
        c2 = chorus_segments[1]
        v2 = verse_segments[1]
        previous = previous_segment(segments, c2)
        if previous is None:
            continue
        c2_target = notes[c2["start"] : min(c2["start"] + incipit_notes, c2["end"])]
        v2_target = notes[v2["start"] : min(v2["start"] + incipit_notes, v2["end"])]
        if len(c2_target) < incipit_notes or len(v2_target) < incipit_notes:
            continue
        songs.append({
            "piece_id": piece_id,
            "source": rows[0].get("source", ""),
            "notes": notes,
            "c2_target": c2_target,
            "v2_target": v2_target,
            "previous_label": previous["label"],
            "previous_start": previous["start"],
            "previous_end": previous["end"],
            "c2_start": c2["start"],
            "v2_start": v2["start"],
        })

    rng = random.Random(seed)
    c2_pool_by_source: dict[str, list[tuple[str, list[int]]]] = defaultdict(list)
    for song in songs:
        c2_pool_by_source[song["source"]].append((song["piece_id"], song["c2_target"]))
    for song in songs:
        pool = [item for item in c2_pool_by_source[song["source"]] if item[0] != song["piece_id"]]
        if not pool:
            pool = [item for item in c2_pool_by_source[song["source"]]]
        song["other_song_c2_target"] = list(rng.choice(pool)[1])
        shuffled = list(song["c2_target"])
        rng.shuffle(shuffled)
        song["shuffled_c2_target"] = shuffled
    return songs


def previous_segment(segments: list[dict], target: dict) -> dict | None:
    previous = None
    for segment in segments:
        if segment["start"] >= target["start"]:
            break
        previous = segment
    return previous


def assign_folds(songs: list[dict], folds: int, seed: int) -> None:
    rng = random.Random(seed)
    indices = list(range(len(songs)))
    rng.shuffle(indices)
    for rank, idx in enumerate(indices):
        songs[idx]["fold"] = rank % folds


def run_predictions(songs: list[dict], args: argparse.Namespace) -> list[ScoreRow]:
    vocab = {note for song in songs for note in song["notes"]}
    rows: list[ScoreRow] = []
    for fold in range(args.folds):
        train_sequences = [song["notes"] for song in songs if song["fold"] != fold]
        ltm = NoteMarkov(args.max_order, args.alpha, vocab).fit(train_sequences)
        for song in songs:
            if song["fold"] != fold:
                continue
            rows.extend(score_song(song, ltm, vocab, args))
    return rows


def score_song(song: dict, ltm: NoteMarkov, vocab: set[int], args: argparse.Namespace) -> list[ScoreRow]:
    out = []
    previous_len = song["previous_end"] - song["previous_start"]
    targets = {
        "actual_c2": song["c2_target"],
        "v2_opening": song["v2_target"],
        "other_song_c2": song["other_song_c2_target"],
        "shuffled_c2": song["shuffled_c2_target"],
    }
    for bin_value in BINS:
        within = max(1, min(previous_len, math.ceil(previous_len * bin_value)))
        context_end = song["previous_start"] + within
        context = song["notes"][:context_end]
        stm = NoteMarkov(args.max_order, args.alpha, vocab).fit([context])
        for target_type, target in targets.items():
            ltm_ic, ltm_probability, ltm_entropy = ltm.score_sequence(target, context)
            stm_ic, stm_probability, stm_entropy = stm.score_sequence(target, context)
            both_ic, both_probability, both_entropy = score_both(target, context, ltm, stm)
            for model, ic, probability, ent in [
                ("LTM", ltm_ic, ltm_probability, ltm_entropy),
                ("STM", stm_ic, stm_probability, stm_entropy),
                ("BOTH", both_ic, both_probability, both_entropy),
            ]:
                out.append(ScoreRow(
                    piece_id=song["piece_id"],
                    source=song["source"],
                    fold=song["fold"],
                    model=model,
                    bin=bin_value,
                    previous_section=song["previous_label"],
                    target_type=target_type,
                    target_notes=" ".join(map(str, target)),
                    mean_ic=ic,
                    probability=probability,
                    entropy=ent,
                    context_note_count=len(context),
                    target_note_count=len(target),
                ))
    return out


def score_both(target: list[int], context: list[int], ltm: NoteMarkov, stm: NoteMarkov) -> tuple[float, float, float]:
    history: list[object] = [START] * ltm.max_order + list(context)
    ics = []
    entropies = []
    log_probability = 0.0
    for note in target:
        ltm_dist, ltm_entropy = ltm.distribution(history)
        stm_dist, stm_entropy = stm.distribution(history)
        vocab = sorted(set(ltm_dist) | set(stm_dist))
        ltm_weight = 1.0 / max(ltm_entropy, 1e-6)
        stm_weight = 1.0 / max(stm_entropy, 1e-6)
        total_weight = ltm_weight + stm_weight
        p = (
            ltm_weight * ltm_dist.get(note, 0.0) + stm_weight * stm_dist.get(note, 0.0)
        ) / max(total_weight, 1e-12)
        dist = {
            label: (ltm_weight * ltm_dist.get(label, 0.0) + stm_weight * stm_dist.get(label, 0.0)) / max(total_weight, 1e-12)
            for label in vocab
        }
        ics.append(-math.log2(max(p, 1e-12)))
        log_probability += math.log(max(p, 1e-12))
        entropies.append(entropy(dist))
        history.append(note)
    return float(np.mean(ics)), math.exp(log_probability), float(np.mean(entropies))


def summarize(rows: list[ScoreRow]) -> list[dict[str, object]]:
    by_key: dict[tuple[str, str, str, float], dict[str, ScoreRow]] = defaultdict(dict)
    for row in rows:
        by_key[(row.source, row.model, row.piece_id, row.bin)][row.target_type] = row
    paired = []
    for (source, model, piece_id, bin_value), values in by_key.items():
        actual = values.get("actual_c2")
        if actual is None:
            continue
        for baseline in ["v2_opening", "other_song_c2", "shuffled_c2"]:
            if baseline not in values:
                continue
            paired.append({
                "source": source,
                "model": model,
                "piece_id": piece_id,
                "bin": bin_value,
                "baseline": baseline,
                "actual_ic": actual.mean_ic,
                "baseline_ic": values[baseline].mean_ic,
                "baseline_minus_actual_ic": values[baseline].mean_ic - actual.mean_ic,
            })

    out = []
    for source in sorted({row["source"] for row in paired} | {"ALL"}):
        source_rows = paired if source == "ALL" else [row for row in paired if row["source"] == source]
        for model in ["LTM", "STM", "BOTH"]:
            for baseline in ["v2_opening", "other_song_c2", "shuffled_c2"]:
                for bin_value in BINS:
                    subset = [
                        row for row in source_rows
                        if row["model"] == model and row["baseline"] == baseline and row["bin"] == bin_value
                    ]
                    if len(subset) < 2:
                        continue
                    effects = np.array([row["baseline_minus_actual_ic"] for row in subset], dtype=float)
                    actual = np.array([row["actual_ic"] for row in subset], dtype=float)
                    baseline_ic = np.array([row["baseline_ic"] for row in subset], dtype=float)
                    se = effects.std(ddof=1) / math.sqrt(len(effects))
                    tcrit = stats.t.ppf(0.975, len(effects) - 1)
                    t, p = stats.ttest_1samp(effects, 0.0)
                    out.append({
                        "source": source,
                        "model": model,
                        "baseline": baseline,
                        "bin": bin_value,
                        "n_songs": len(effects),
                        "mean_actual_c2_ic": actual.mean(),
                        "mean_baseline_ic": baseline_ic.mean(),
                        "mean_baseline_minus_actual_ic": effects.mean(),
                        "ci95_low": effects.mean() - tcrit * se,
                        "ci95_high": effects.mean() + tcrit * se,
                        "t": t,
                        "p": p,
                    })
    return out


def plot_summary(summary: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [
        row for row in summary
        if row["source"] == "ALL" and row["model"] == "BOTH" and row["baseline"] in {"other_song_c2", "shuffled_c2"}
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    labels = {"other_song_c2": "Other-song chorus", "shuffled_c2": "Shuffled C2"}
    colors = {"other_song_c2": "#4C78A8", "shuffled_c2": "#F58518"}
    for baseline in ["other_song_c2", "shuffled_c2"]:
        items = sorted([row for row in rows if row["baseline"] == baseline], key=lambda row: row["bin"])
        x = np.array([row["bin"] for row in items], dtype=float)
        y = np.array([row["mean_baseline_minus_actual_ic"] for row in items], dtype=float)
        lo = np.array([row["ci95_low"] for row in items], dtype=float)
        hi = np.array([row["ci95_high"] for row in items], dtype=float)
        ax.plot(x, y, marker="o", lw=2, label=labels[baseline], color=colors[baseline])
        ax.fill_between(x, lo, hi, color=colors[baseline], alpha=0.18, linewidth=0)
    ax.axhline(0, color="#555555", lw=1)
    ax.set_xlabel("Position through the section before C2")
    ax.set_ylabel("Baseline IC - actual C2 opening IC (bits)")
    ax.text(0.02, 0.96, "Positive = actual C2 opening is more plausible", transform=ax.transAxes, va="top")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def write_report(path: Path, songs: list[dict], summary: list[dict], args: argparse.Namespace) -> None:
    lines = [
        "# Note-Level Chorus Incipit Anticipation",
        "",
        "This analysis asks whether the upcoming C2 opening notes become a more plausible immediate continuation as the preceding section approaches the chorus boundary.",
        "",
        f"- Eligible songs: {len(songs)}",
        f"- Folds: {args.folds}",
        f"- Max order: {args.max_order}",
        f"- Incipit length: {args.incipit_notes} notes",
        "",
        "The effect is `baseline IC - actual C2 opening IC`; positive values mean the actual C2 opening is more probable than the matched baseline.",
        "",
        "## BOTH Model, All Songs",
        "",
        "| Baseline | Bin | N | Actual C2 IC | Baseline IC | Effect [95% CI] | p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        if row["source"] == "ALL" and row["model"] == "BOTH":
            lines.append(
                f"| {row['baseline']} | {row['bin']:.1f} | {row['n_songs']} | "
                f"{fmt(row['mean_actual_c2_ic'])} | {fmt(row['mean_baseline_ic'])} | "
                f"{fmt(row['mean_baseline_minus_actual_ic'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
            )
    lines.extend([
        "",
        "## Headline",
        "",
        headline(summary),
        "",
        "Interpretation: this is an immediate-start likelihood analysis, not a true future-horizon rollout. It estimates when the C2 incipit becomes compatible with the note-level context before the section begins.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def headline(summary: list[dict]) -> str:
    rows = [row for row in summary if row["source"] == "ALL" and row["model"] == "BOTH"]
    bits = []
    for baseline in ["other_song_c2", "shuffled_c2", "v2_opening"]:
        subset = sorted([row for row in rows if row["baseline"] == baseline], key=lambda row: row["bin"])
        sustained = [
            row for idx, row in enumerate(subset)
            if row["mean_baseline_minus_actual_ic"] > 0
            and row["p"] < 0.05
            and all(later["mean_baseline_minus_actual_ic"] > 0 and later["p"] < 0.05 for later in subset[idx:])
        ]
        if sustained:
            first = sustained[0]
            bits.append(f"`{baseline}`: positive from bin {first['bin']:.1f}.")
        else:
            bits.append(f"`{baseline}`: no sustained positive advantage.")
    return " ".join(bits)


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
    if value in {"intro", "outro", "fadeout", "coda", "solo", "instrumental", "interlude", "link", "trans", "transition"}:
        return value
    return value or "unknown"


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def entropy(dist: dict[int, float]) -> float:
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


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
