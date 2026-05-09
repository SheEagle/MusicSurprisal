from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.analysis import build_surprisal_rows, evaluate_ai_classifier
from music_surprisal.data import Event, group_by_piece, split_events, token_function
from music_surprisal.ngram import NGramModel, shuffled_sequences
from music_surprisal.data import write_rows
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Deep RQ4 AI-vs-human surprisal analysis.")
    parser.add_argument("--events", default="data/events_dcml_jtc_all_rq.csv")
    parser.add_argument("--output", default="output/formal_dcml_jtc_all_rq/rq4_deep")
    parser.add_argument("--human-source", default="jsb")
    parser.add_argument("--ai-source", default="js_fake")
    parser.add_argument("--pair-name", default="jsb_vs_js_fake")
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--permutations", type=int, default=1000)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.human_source} and {args.ai_source} events...")
    events = load_events(args.events, sources={args.human_source, args.ai_source})
    print("Computing human-trained RQ4 surprisal rows...")
    rows = build_human_trained_surprisal_rows(
        events,
        human_source=args.human_source,
        order=args.order,
        token_kind=args.token_kind,
    )

    threshold = human_peak_threshold(rows, q=0.90)
    print(f"Human 90th-percentile peak threshold: {threshold:.3f}")
    features = rq4_time_series_features(rows, peak_threshold=threshold)
    write_rows(output / "rq4_time_series_features.csv", features)
    write_rows(output / "rq4_feature_summary.csv", summarize_by_label(features))
    effects = between_label_effects(features)
    write_rows(output / "rq4_human_ai_effects.csv", effects)

    metrics = evaluate_ai_classifier(
        classifier_compatible_features(features), permutations=args.permutations
    )
    metrics["pair_name"] = args.pair_name
    metrics["human_source"] = args.human_source
    metrics["ai_source"] = args.ai_source
    (output / "rq4_classifier_from_deep_features.json").write_text(
        __import__("json").dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    draw_effects(effects, output / "rq4_human_ai_effects.svg")
    draw_hypothesis_panel(output / "rq4_hypothesis_panel.svg", effects)
    write_project_summary(output / "RQ4_PROJECT_SUMMARY.md", args, effects, metrics)
    print(f"Wrote deep RQ4 outputs to {output}")


def build_human_trained_surprisal_rows(
    events: list[Event], *, human_source: str, order: int, token_kind: str
) -> list[dict]:
    human_events = [event for event in events if event.source == human_source]
    train, _ = split_events(human_events)
    train_sequences = [
        [token_function(token_kind)(event) for event in piece]
        for piece in group_by_piece(train).values()
    ]
    if not train_sequences:
        raise ValueError(f"No human training sequences found for source {human_source}")

    ngram = NGramModel(order=order).fit(train_sequences)
    unigram = NGramModel(order=1).fit(train_sequences)
    shuffled = NGramModel(order=order).fit(shuffled_sequences(train_sequences, seed=13))
    to_token = token_function(token_kind)

    rows: list[dict] = []
    eval_events = [event for event in events if event.split != "train" or event.source != human_source]
    for piece_id, piece_events in group_by_piece(eval_events).items():
        tokens = [to_token(event) for event in piece_events]
        ngram_values = ngram.sequence_surprisal(tokens)
        unigram_values = unigram.sequence_surprisal(tokens)
        shuffled_values = shuffled.sequence_surprisal(tokens)
        for index, event in enumerate(piece_events):
            rows.append(
                {
                    "piece_id": piece_id,
                    "source": event.source,
                    "genre": event.genre,
                    "is_ai": int(event.is_ai),
                    "split": event.split,
                    "event_index": index,
                    "onset": event.onset,
                    "pitch": event.pitch,
                    "duration": event.duration,
                    "chord": event.chord,
                    "boundary": int(event.boundary),
                    "surprisal_ngram": ngram_values[index],
                    "surprisal_unigram": unigram_values[index],
                    "surprisal_shuffled": shuffled_values[index],
                }
            )
    return rows


def human_peak_threshold(rows: list[dict], q: float) -> float:
    values = sorted(
        float(row["surprisal_ngram"]) for row in rows if int(row["is_ai"]) == 0
    )
    return percentile(values, q)


def rq4_time_series_features(rows: list[dict], peak_threshold: float) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    output: list[dict] = []
    for piece_id, piece_rows in sorted(by_piece.items()):
        piece_rows.sort(key=lambda row: int(row["event_index"]))
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < 4:
            continue
        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        abs_diffs = [abs(diff) for diff in diffs]
        peaks = local_peaks(values, threshold=peak_threshold)
        meta = piece_rows[0]
        sd = pstdev(values) if len(values) > 1 else 0.0
        output.append(
            {
                "piece_id": piece_id,
                "source": meta["source"],
                "is_ai": int(meta["is_ai"]),
                "events": len(values),
                "mean": mean(values),
                "variance": sd**2,
                "sd": sd,
                "cv": sd / mean(values) if mean(values) else 0.0,
                "median": median(values),
                "p90": percentile(sorted(values), 0.90),
                "p95": percentile(sorted(values), 0.95),
                "max": max(values),
                "range": max(values) - min(values),
                "peak_count": len(peaks),
                "peak_rate": len(peaks) / len(values),
                "peak_mass": sum(values[i] - peak_threshold for i in peaks) / len(values),
                "mean_abs_diff": mean(abs_diffs) if abs_diffs else 0.0,
                "diff_sd": pstdev(diffs) if len(diffs) > 1 else 0.0,
                "smoothness": 1 / (1 + mean(abs_diffs)) if abs_diffs else 1.0,
                "lag1_autocorr": autocorr(values, 1),
                "lag2_autocorr": autocorr(values, 2),
                "lag4_autocorr": autocorr(values, 4),
                "lag8_autocorr": autocorr(values, 8),
                "max_autocorr_lag2_16": max(
                    autocorr(values, lag) for lag in range(2, min(16, len(values) - 1) + 1)
                )
                if len(values) > 17
                else 0.0,
                "surprisal_entropy": entropy(values, bins=10),
                "low_variation_flag": int(sd < 1.0),
            }
        )
    return output


def summarize_by_label(rows: list[dict]) -> list[dict]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[int(row["is_ai"])].append(row)
    output: list[dict] = []
    for label, items in sorted(grouped.items()):
        result = {
            "is_ai": label,
            "label": "AI" if label else "human",
            "pieces": len(items),
        }
        for feature in feature_names():
            values = [float(row[feature]) for row in items]
            result[f"{feature}_mean"] = mean(values)
            result[f"{feature}_median"] = median(values)
            result[f"{feature}_sd"] = pstdev(values) if len(values) > 1 else 0.0
        output.append(result)
    return output


def between_label_effects(rows: list[dict]) -> list[dict]:
    human = [row for row in rows if int(row["is_ai"]) == 0]
    ai = [row for row in rows if int(row["is_ai"]) == 1]
    output: list[dict] = []
    for feature in feature_names():
        hv = [float(row[feature]) for row in human]
        av = [float(row[feature]) for row in ai]
        output.append(
            {
                "feature": feature,
                "human_mean": mean(hv),
                "ai_mean": mean(av),
                "ai_minus_human": mean(av) - mean(hv),
                "cohens_d_ai_minus_human": cohens_d(hv, av),
                "human_median": median(hv),
                "ai_median": median(av),
            }
        )
    return output


def feature_names() -> list[str]:
    return [
        "mean",
        "variance",
        "sd",
        "cv",
        "p90",
        "p95",
        "max",
        "range",
        "peak_rate",
        "peak_mass",
        "mean_abs_diff",
        "diff_sd",
        "smoothness",
        "lag1_autocorr",
        "lag4_autocorr",
        "lag8_autocorr",
        "max_autocorr_lag2_16",
        "surprisal_entropy",
    ]


def classifier_compatible_features(rows: list[dict]) -> list[dict]:
    mapped: list[dict] = []
    for row in rows:
        mapped.append(
            {
                **row,
                "surprisal_mean": row["mean"],
                "surprisal_sd": row["sd"],
                "surprisal_median": row["median"],
                "surprisal_p90": row["p90"],
                "surprisal_max": row["max"],
                "boundary_delta": 0.0,
            }
        )
    return mapped


def local_peaks(values: list[float], threshold: float) -> list[int]:
    if len(values) < 3:
        return []
    return [
        i
        for i in range(1, len(values) - 1)
        if values[i] >= threshold
        and values[i] > values[i - 1]
        and values[i] >= values[i + 1]
    ]


def autocorr(values: list[float], lag: int) -> float:
    if len(values) <= lag + 1:
        return 0.0
    x = values[:-lag]
    y = values[lag:]
    mx = mean(x)
    my = mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else 0.0


def entropy(values: list[float], bins: int) -> float:
    if not values:
        return 0.0
    lo, hi = min(values), max(values)
    if hi == lo:
        return 0.0
    counts = [0] * bins
    for value in values:
        idx = min(bins - 1, int((value - lo) / (hi - lo) * bins))
        counts[idx] += 1
    total = sum(counts)
    return -sum((c / total) * math.log2(c / total) for c in counts if c)


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    index = q * (len(sorted_values) - 1)
    lo = math.floor(index)
    hi = math.ceil(index)
    if lo == hi:
        return sorted_values[lo]
    w = index - lo
    return sorted_values[lo] * (1 - w) + sorted_values[hi] * w


def cohens_d(human: list[float], ai: list[float]) -> float:
    if len(human) < 2 or len(ai) < 2:
        return math.nan
    pooled = math.sqrt(
        ((len(human) - 1) * pstdev(human) ** 2 + (len(ai) - 1) * pstdev(ai) ** 2)
        / (len(human) + len(ai) - 2)
    )
    return (mean(ai) - mean(human)) / pooled if pooled else math.nan


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def draw_effects(rows: list[dict], output: Path) -> None:
    keep = [
        "variance",
        "peak_rate",
        "peak_mass",
        "mean_abs_diff",
        "smoothness",
        "lag1_autocorr",
        "max_autocorr_lag2_16",
        "surprisal_entropy",
    ]
    rows = [row for row in rows if row["feature"] in keep]
    width, height = 1120, 560
    zero_y = 285
    left = 70
    slot = 125
    values = [float(row["cohens_d_ai_minus_human"]) for row in rows]
    max_abs = max(abs(v) for v in values) or 1.0
    body = [
        '<text class="title" x="70" y="38">RQ4 AI minus human effect sizes</text>',
        f'<line class="axis" x1="{left}" y1="{zero_y}" x2="{width-50}" y2="{zero_y}"/>',
        '<text class="small" x="70" y="60">Bars show Cohen&apos;s d. Negative = lower in AI; positive = higher in AI.</text>',
    ]
    for i, row in enumerate(rows):
        value = float(row["cohens_d_ai_minus_human"])
        h = abs(value) / max_abs * 190
        x = left + i * slot
        y = zero_y - h if value >= 0 else zero_y
        color = "#7a4fb3" if value >= 0 else "#b84a4a"
        body.append(f'<rect x="{x}" y="{y:.1f}" width="62" height="{h:.1f}" fill="{color}"/>')
        body.append(f'<text class="small" x="{x-4}" y="{y-8:.1f}">{value:.2f}</text>')
        body.append(
            f'<text class="small" transform="translate({x+6} 500) rotate(35)">'
            f'{row["feature"].replace("_", " ")}</text>'
        )
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_hypothesis_panel(output: Path, effects: list[dict]) -> None:
    by_feature = {row["feature"]: row for row in effects}
    rows = [
        ("Lower variance", "variance"),
        ("Fewer peaks", "peak_rate"),
        ("Less dramatic peak mass", "peak_mass"),
        ("More regular autocorr", "max_autocorr_lag2_16"),
        ("Smoother curve", "smoothness"),
    ]
    width, height = 900, 380
    body = ['<text class="title" x="60" y="40">RQ4 hypothesis checks</text>']
    y = 85
    for label, feature in rows:
        effect = by_feature[feature]
        diff = float(effect["ai_minus_human"])
        d = float(effect["cohens_d_ai_minus_human"])
        status = "supports" if hypothesis_supported(feature, diff) else "does not support"
        color = "#2f6f9f" if status == "supports" else "#b84a4a"
        body.append(f'<circle cx="72" cy="{y-4}" r="6" fill="{color}"/>')
        body.append(
            f'<text class="label" x="92" y="{y}">{label}: {status} '
            f'(AI-human={diff:.3f}, d={d:.2f})</text>'
        )
        y += 50
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_project_summary(path: Path, args: argparse.Namespace, effects: list[dict], metrics: dict) -> None:
    effect_by_feature = {row["feature"]: row for row in effects}

    def line(feature: str) -> str:
        row = effect_by_feature[feature]
        return (
            f"- `{feature}`: human mean = {float(row['human_mean']):.3f}, "
            f"AI mean = {float(row['ai_mean']):.3f}, "
            f"AI-human = {float(row['ai_minus_human']):.3f}, "
            f"Cohen's d = {float(row['cohens_d_ai_minus_human']):.2f}"
        )

    text = f"""# RQ4 Independent Project Summary

Pair: `{args.pair_name}`

Human source: `{args.human_source}`

AI source: `{args.ai_source}`

## Framing

This project treats surprisal time series as interpretable information-theoretic
features for symbolic AI music detection. The n-gram measurement model is trained
only on human training data, so AI differences are interpreted relative to human
style expectations rather than as artifacts of an AI-trained model.

## Hypothesis Checks

{line("variance")}

{line("peak_rate")}

{line("peak_mass")}

{line("smoothness")}

{line("lag1_autocorr")}

{line("max_autocorr_lag2_16")}

## Classifier

- Accuracy = {metrics.get('accuracy', float('nan')):.3f}
- F1 = {metrics.get('f1', float('nan')):.3f}
- AUC = {metrics.get('auc', float('nan')):.3f}
- Permutation p-value = {metrics.get('permutation_p_accuracy', float('nan')):.6f}
- Pieces = {metrics.get('pieces', 'NA')}

## Interpretation Note

For this pair, inspect the effect directions before committing to the original
"AI is smoother" hypothesis. A positive AI-human value for variance, peak rate, or
peak mass means the AI corpus is more volatile or peak-heavy relative to the
human-trained expectation model.
"""
    path.write_text(text, encoding="utf-8")


def hypothesis_supported(feature: str, diff: float) -> bool:
    if feature in {"variance", "peak_rate", "peak_mass"}:
        return diff < 0
    if feature in {"max_autocorr_lag2_16", "smoothness"}:
        return diff > 0
    return False


def svg_wrap(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #1d252c; }}
    .title {{ font-size: 22px; font-weight: 700; }}
    .label {{ font-size: 14px; }}
    .small {{ font-size: 11px; fill: #52606d; }}
    .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
  </style>
{body}
</svg>
"""


if __name__ == "__main__":
    main()
