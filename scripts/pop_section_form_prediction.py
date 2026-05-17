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


LABEL_MAP = {
    "intro": "I",
    "verse": "V",
    "chorus": "C",
    "refrain": "C",
    "c_chorus": "C",
    "pre_chorus": "PC",
    "prechorus": "PC",
    "bridge": "B",
    "b": "B",
    "bp": "B",
    "middle": "B",
    "outro": "O",
    "coda": "O",
    "fadeout": "O",
    "fade_out": "O",
    "solo": "S",
    "instrumental": "S",
    "interlude": "INT",
    "link": "L",
    "trans": "T",
    "transition": "T",
    "tag": "TAG",
    "a": "A",
    "unknown": "UNK",
}


@dataclass
class Prediction:
    piece_id: str
    source: str
    fold: int
    model: str
    section: str
    event_type: str
    occurrence: int
    index: int
    context: str
    probability: float
    ic: float
    entropy: float
    effective_order: int


class SectionMarkov:
    def __init__(self, max_order: int = 4, alpha: float = 0.1, vocab: set[str] | None = None) -> None:
        self.max_order = max_order
        self.alpha = alpha
        self.vocab = set(vocab or [])
        self.counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)

    def fit(self, songs: list[list[str]]) -> "SectionMarkov":
        for seq in songs:
            for i, event in enumerate(seq):
                self.update(event, seq[:i])
        return self

    def update(self, event: str, history: list[str]) -> None:
        self.vocab.add(event)
        history = history[-self.max_order :]
        for k in range(min(self.max_order, len(history)) + 1):
            context = tuple(history[-k:]) if k else ()
            self.counts[context][event] += 1

    def distribution(self, history: list[str]) -> tuple[dict[str, float], int]:
        vocab = sorted(self.vocab)
        if not vocab:
            return {}, 0
        context = history[-self.max_order :]
        used_order = 0
        counter: Counter[str] | None = None
        for k in range(len(context), -1, -1):
            ctx = tuple(context[-k:]) if k else ()
            if ctx in self.counts:
                counter = self.counts[ctx]
                used_order = k
                break
        if counter is None:
            return {event: 1.0 / len(vocab) for event in vocab}, 0
        total = sum(counter.values())
        denom = total + self.alpha * len(vocab)
        return {event: (counter[event] + self.alpha) / denom for event in vocab}, used_order

    def predict(self, event: str, history: list[str]) -> tuple[float, float, int]:
        dist, order = self.distribution(history)
        if event not in dist:
            vocab_size = max(1, len(self.vocab))
            probability = self.alpha / (self.alpha * vocab_size)
        else:
            probability = dist[event]
        return probability, entropy(dist), order


def main() -> None:
    parser = argparse.ArgumentParser(description="Section-level formal prediction for CoCoPops chorus returns.")
    parser.add_argument("--events", default="data/events_cocopops_pop.csv")
    parser.add_argument("--output-dir", default="output/pop_music_idyom_pipeline/section_form_prediction")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-order", type=int, default=4)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    songs = load_section_sequences(Path(args.events))
    assign_folds(songs, args.folds, args.seed)
    write_section_sequences(output_dir / "section_sequences.csv", songs)
    predictions = run_kfold_predictions(songs, args.folds, args.max_order, args.alpha)
    write_predictions(output_dir / "section_return_predictions.csv", predictions)

    paired_rows = paired_song_effects(predictions)
    write_csv(output_dir / "section_return_paired_song_effects.csv", paired_rows)
    summary_rows = summarize_paired(paired_rows)
    write_csv(output_dir / "section_return_summary.csv", summary_rows)
    plot_summary(summary_rows, output_dir / "section_return_ic_advantage.svg", output_dir / "section_return_ic_advantage.png")
    write_report(output_dir / "SECTION_FORM_PREDICTION_REPORT.md", songs, predictions, summary_rows, args)
    print(f"Wrote section-level form prediction outputs to {output_dir}")


def load_section_sequences(path: Path) -> list[dict]:
    by_piece: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if truthy(row.get("section_start")):
                by_piece[row["piece_id"]].append(row)

    songs = []
    for piece_id, rows in sorted(by_piece.items()):
        rows.sort(key=lambda row: float(row.get("onset", 0.0)))
        seq = [normalize_label(row.get("section_label", "")) for row in rows]
        seq = [label for label in seq if label]
        if len(seq) < 2:
            continue
        songs.append({
            "piece_id": piece_id,
            "source": rows[0].get("source", ""),
            "sequence": seq,
        })
    return songs


def normalize_label(value: str) -> str:
    key = value.lower().strip().replace("-", "_").replace(" ", "_")
    return LABEL_MAP.get(key, key.upper() if key else "")


def assign_folds(songs: list[dict], folds: int, seed: int) -> None:
    rng = random.Random(seed)
    indices = list(range(len(songs)))
    rng.shuffle(indices)
    for rank, idx in enumerate(indices):
        songs[idx]["fold"] = rank % folds


def run_kfold_predictions(
    songs: list[dict], folds: int, max_order: int, alpha: float
) -> list[Prediction]:
    vocab = {label for song in songs for label in song["sequence"]}
    predictions: list[Prediction] = []

    for fold in range(folds):
        train_sequences = [song["sequence"] for song in songs if song["fold"] != fold]
        ltm = SectionMarkov(max_order=max_order, alpha=alpha, vocab=vocab).fit(train_sequences)
        for song in songs:
            if song["fold"] != fold:
                continue
            predictions.extend(score_song(song, fold, ltm, vocab, max_order, alpha))
    return predictions


def score_song(
    song: dict, fold: int, ltm: SectionMarkov, vocab: set[str], max_order: int, alpha: float
) -> list[Prediction]:
    seq = song["sequence"]
    stm = SectionMarkov(max_order=max_order, alpha=alpha, vocab=vocab)
    history: list[str] = []
    seen: Counter[str] = Counter()
    out: list[Prediction] = []
    for index, section in enumerate(seq):
        ltm_p, ltm_h, ltm_order = ltm.predict(section, history)
        stm_p, stm_h, stm_order = stm.predict(section, history)
        both_p, both_h = mixed_probability(section, history, ltm, stm, ltm_h, stm_h)
        seen[section] += 1
        event_type = ""
        if section == "C" and seen[section] == 2:
            event_type = "chorus_return"
        elif section == "V" and seen[section] == 2:
            event_type = "verse_return"
        if event_type:
            for model, probability, ent, order in [
                ("LTM", ltm_p, ltm_h, ltm_order),
                ("STM", stm_p, stm_h, stm_order),
                ("BOTH", both_p, both_h, max(ltm_order, stm_order)),
            ]:
                out.append(Prediction(
                    piece_id=song["piece_id"],
                    source=song["source"],
                    fold=fold,
                    model=model,
                    section=section,
                    event_type=event_type,
                    occurrence=seen[section],
                    index=index,
                    context=" ".join(history),
                    probability=probability,
                    ic=-math.log2(max(probability, 1e-12)),
                    entropy=ent,
                    effective_order=order,
                ))
        stm.update(section, history)
        history.append(section)
    return out


def mixed_probability(
    event: str,
    history: list[str],
    ltm: SectionMarkov,
    stm: SectionMarkov,
    ltm_entropy: float,
    stm_entropy: float,
) -> tuple[float, float]:
    ltm_dist, _ = ltm.distribution(history)
    stm_dist, _ = stm.distribution(history)
    vocab = sorted(set(ltm_dist) | set(stm_dist))
    if not vocab:
        return 1.0, 0.0
    ltm_weight = 1.0 / max(ltm_entropy, 1e-6)
    stm_weight = 1.0 / max(stm_entropy, 1e-6)
    total_weight = ltm_weight + stm_weight
    dist = {
        label: (ltm_weight * ltm_dist.get(label, 0.0) + stm_weight * stm_dist.get(label, 0.0)) / total_weight
        for label in vocab
    }
    return dist.get(event, 1e-12), entropy(dist)


def paired_song_effects(predictions: list[Prediction]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], dict[str, Prediction]] = defaultdict(dict)
    for row in predictions:
        grouped[(row.source, row.model, row.piece_id)][row.event_type] = row
    out = []
    for (source, model, piece_id), items in grouped.items():
        if "chorus_return" not in items or "verse_return" not in items:
            continue
        chorus = items["chorus_return"]
        verse = items["verse_return"]
        out.append({
            "source": source,
            "model": model,
            "piece_id": piece_id,
            "fold": chorus.fold,
            "chorus_ic": chorus.ic,
            "verse_ic": verse.ic,
            "verse_minus_chorus_ic": verse.ic - chorus.ic,
            "chorus_probability": chorus.probability,
            "verse_probability": verse.probability,
            "chorus_context": chorus.context,
            "verse_context": verse.context,
            "chorus_index": chorus.index,
            "verse_index": verse.index,
        })
    return out


def summarize_paired(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for source in sorted({row["source"] for row in rows} | {"ALL"}):
        source_rows = rows if source == "ALL" else [row for row in rows if row["source"] == source]
        for model in ["LTM", "STM", "BOTH"]:
            values = np.array([float(row["verse_minus_chorus_ic"]) for row in source_rows if row["model"] == model], dtype=float)
            chorus = np.array([float(row["chorus_ic"]) for row in source_rows if row["model"] == model], dtype=float)
            verse = np.array([float(row["verse_ic"]) for row in source_rows if row["model"] == model], dtype=float)
            if len(values) < 2:
                continue
            se = values.std(ddof=1) / math.sqrt(len(values))
            tcrit = stats.t.ppf(0.975, len(values) - 1)
            t, p = stats.ttest_1samp(values, 0.0)
            out.append({
                "source": source,
                "model": model,
                "n_songs": len(values),
                "mean_chorus_ic": chorus.mean(),
                "mean_verse_ic": verse.mean(),
                "mean_verse_minus_chorus_ic": values.mean(),
                "ci95_low": values.mean() - tcrit * se,
                "ci95_high": values.mean() + tcrit * se,
                "t": t,
                "p": p,
            })
    return out


def plot_summary(rows: list[dict[str, object]], svg_path: Path, png_path: Path) -> None:
    rows = [row for row in rows if row["source"] == "ALL"]
    models = ["LTM", "STM", "BOTH"]
    values = [next(row for row in rows if row["model"] == model) for model in models]
    colors = {"LTM": "#4C78A8", "STM": "#F58518", "BOTH": "#54A24B"}
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(models))
    means = [row["mean_verse_minus_chorus_ic"] for row in values]
    err_low = [row["mean_verse_minus_chorus_ic"] - row["ci95_low"] for row in values]
    err_high = [row["ci95_high"] - row["mean_verse_minus_chorus_ic"] for row in values]
    ax.bar(x, means, color=[colors[m] for m in models], width=0.62)
    ax.errorbar(x, means, yerr=[err_low, err_high], fmt="none", color="#222222", capsize=5, lw=1.4)
    ax.axhline(0, color="#555555", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylabel("Verse return IC - chorus return IC (bits)")
    ax.text(0.02, 0.96, "Positive = chorus return is more expected", transform=ax.transAxes, va="top")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=220)
    plt.close(fig)


def write_report(path: Path, songs: list[dict], predictions: list[Prediction], summary: list[dict], args: argparse.Namespace) -> None:
    lines = [
        "# Section-Level Formal Prediction",
        "",
        "This experiment treats section labels as symbolic events and estimates the IC of formal returns with k-fold cross-validation.",
        "",
        f"- Songs with section sequences: {len(songs)}",
        f"- Folds: {args.folds}",
        f"- Max order: {args.max_order}",
        f"- Smoothing alpha: {args.alpha}",
        "",
        "The key paired effect is `verse return IC - chorus return IC`; positive values mean the second chorus is more expected than the second verse at the section-transition level.",
        "",
        "| Source | Model | N songs | Chorus IC | Verse IC | Verse - chorus IC [95% CI] | p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['source']} | {row['model']} | {row['n_songs']} | "
            f"{fmt(row['mean_chorus_ic'])} | {fmt(row['mean_verse_ic'])} | "
            f"{fmt(row['mean_verse_minus_chorus_ic'])} [{fmt(row['ci95_low'])}, {fmt(row['ci95_high'])}] | {fmt_p(row['p'])} |"
        )
    lines.extend([
        "",
        "Outputs:",
        "",
        "- `section_return_predictions.csv`: event-level section return predictions.",
        "- `section_return_paired_song_effects.csv`: within-song chorus-return vs verse-return pairs.",
        "- `section_return_summary.csv`: paired t-test summaries.",
        "- `section_return_ic_advantage.svg/png`: compact figure.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_predictions(path: Path, rows: list[Prediction]) -> None:
    write_csv(path, [row.__dict__ for row in rows])


def write_section_sequences(path: Path, songs: list[dict]) -> None:
    rows = []
    for song in songs:
        counts = Counter(song["sequence"])
        rows.append({
            "piece_id": song["piece_id"],
            "source": song["source"],
            "fold": song["fold"],
            "n_sections": len(song["sequence"]),
            "n_verse": counts["V"],
            "n_chorus": counts["C"],
            "has_verse_return": int(counts["V"] >= 2),
            "has_chorus_return": int(counts["C"] >= 2),
            "section_sequence": " ".join(song["sequence"]),
        })
    write_csv(path, rows)


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


def entropy(dist: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def fmt(value: object) -> str:
    return f"{float(value):.3f}"


def fmt_p(value: object) -> str:
    p = float(value)
    return "<.001" if p < 0.001 else f"{p:.3f}"


if __name__ == "__main__":
    main()
