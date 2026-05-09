from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev


FEATURES = [
    "mean",
    "variance",
    "peak_rate",
    "peak_mass",
    "mean_abs_diff",
    "smoothness",
    "lag1_autocorr",
    "lag4_autocorr",
    "max_autocorr_lag2_16",
    "surprisal_entropy",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-generator RQ4 generalization tests.")
    parser.add_argument(
        "--pairs",
        nargs="+",
        required=True,
        help="Pair output directories containing rq4_time_series_features.csv.",
    )
    parser.add_argument("--output", default="output/ai_symbolic_detection/cross_generator")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    pair_data = {Path(path).name: read_features(Path(path) / "rq4_time_series_features.csv") for path in args.pairs}

    rows: list[dict] = []
    for train_name, train_rows in pair_data.items():
        for test_name, test_rows in pair_data.items():
            if train_name == test_name:
                continue
            metrics = train_centroid_and_test(train_rows, test_rows)
            rows.append({"train_pair": train_name, "test_pair": test_name, **metrics})

    write_csv(output / "cross_generator_results.csv", rows)
    (output / "cross_generator_results.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    draw_results(rows, output / "cross_generator_results.svg")
    print(f"Wrote cross-generator results to {output}")


def read_features(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def train_centroid_and_test(train_rows: list[dict], test_rows: list[dict]) -> dict:
    means = {feature: mean(float(row[feature]) for row in train_rows) for feature in FEATURES}
    sds = {
        feature: pstdev(float(row[feature]) for row in train_rows) or 1.0
        for feature in FEATURES
    }
    centroids: dict[int, list[float]] = {}
    for label in (0, 1):
        label_rows = [row for row in train_rows if int(row["is_ai"]) == label]
        centroids[label] = [
            mean((float(row[feature]) - means[feature]) / sds[feature] for row in label_rows)
            for feature in FEATURES
        ]

    truth: list[int] = []
    predictions: list[int] = []
    scores: list[float] = []
    for row in test_rows:
        vector = [(float(row[feature]) - means[feature]) / sds[feature] for feature in FEATURES]
        d0 = distance(vector, centroids[0])
        d1 = distance(vector, centroids[1])
        score = d0 - d1
        predictions.append(1 if score >= 0 else 0)
        scores.append(score)
        truth.append(int(row["is_ai"]))

    return classification_metrics(truth, predictions, scores)


def classification_metrics(truth: list[int], predictions: list[int], scores: list[float]) -> dict:
    tp = sum(1 for y, p in zip(truth, predictions) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(truth, predictions) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(truth, predictions) if y == 1 and p == 0)
    tn = sum(1 for y, p in zip(truth, predictions) if y == 0 and p == 0)
    accuracy = (tp + tn) / len(truth) if truth else math.nan
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc_score(truth, scores),
        "n_test": len(truth),
    }


def auc_score(labels: list[int], scores: list[float]) -> float:
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return math.nan
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index + 1
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            end += 1
        avg_rank = (index + 1 + end) / 2
        rank_sum += avg_rank * sum(label for _, label in pairs[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def draw_results(rows: list[dict], output: Path) -> None:
    width, height = 820, 420
    left, bottom = 80, 340
    slot = 180
    body = [
        '<text class="title" x="60" y="38">Cross-generator generalization</text>',
        f'<line class="axis" x1="{left}" y1="{bottom}" x2="{width-40}" y2="{bottom}"/>',
        f'<line class="axis" x1="{left}" y1="70" x2="{left}" y2="{bottom}"/>',
        '<text class="small" x="22" y="344">0.0</text>',
        '<text class="small" x="22" y="76">1.0</text>',
    ]
    for i, row in enumerate(rows):
        x = left + 60 + i * slot
        acc_h = float(row["accuracy"]) * 250
        auc_h = float(row["auc"]) * 250
        body.append(f'<rect x="{x}" y="{bottom-acc_h:.1f}" width="48" height="{acc_h:.1f}" fill="#2f6f9f"/>')
        body.append(f'<rect x="{x+55}" y="{bottom-auc_h:.1f}" width="48" height="{auc_h:.1f}" fill="#7a4fb3"/>')
        body.append(f'<text class="small" x="{x-10}" y="368">{short(row["train_pair"])}</text>')
        body.append(f'<text class="small" x="{x-10}" y="384">→ {short(row["test_pair"])}</text>')
    body.append('<text class="small" x="590" y="86"><tspan fill="#2f6f9f">accuracy</tspan> / <tspan fill="#7a4fb3">AUC</tspan></text>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def short(name: str) -> str:
    return name.replace("jsb_vs_", "").replace("_test1", "").replace("_sample20", "")


def svg_wrap(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #1d252c; }}
    .title {{ font-size: 22px; font-weight: 700; }}
    .small {{ font-size: 11px; fill: #52606d; }}
    .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
  </style>
{body}
</svg>
"""


if __name__ == "__main__":
    main()
