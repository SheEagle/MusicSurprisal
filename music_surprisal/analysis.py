from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .data import (
    Event,
    distance_to_next_boundary,
    event_sequences,
    group_by_piece,
    split_events,
    token_function,
    write_rows,
)
from .ngram import NGramModel, shuffled_sequences
from .stats import (
    auc_score,
    lag1_autocorrelation,
    paired_sign_permutation_pvalue,
    summarize,
)


def build_surprisal_rows(
    events: list[Event], order: int = 3, token_kind: str = "pitch", seed: int = 13
) -> list[dict]:
    train, eval_events = split_events(events)
    train_sequences = list(event_sequences(train, token_kind).values())

    ngram = NGramModel(order=order).fit(train_sequences)
    unigram = NGramModel(order=1).fit(train_sequences)
    shuffled = NGramModel(order=order).fit(shuffled_sequences(train_sequences, seed=seed))

    to_token = token_function(token_kind)
    rows: list[dict] = []
    for piece_id, piece_events in group_by_piece(eval_events).items():
        tokens = [to_token(event) for event in piece_events]
        ngram_values = ngram.sequence_surprisal(tokens)
        unigram_values = unigram.sequence_surprisal(tokens)
        shuffled_values = shuffled.sequence_surprisal(tokens)
        distances = distance_to_next_boundary(piece_events)

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
                    "distance_to_next_boundary": distances[index]
                    if distances[index] is not None
                    else "",
                    "token": repr(tokens[index]),
                    "surprisal_ngram": ngram_values[index],
                    "surprisal_unigram": unigram_values[index],
                    "surprisal_shuffled": shuffled_values[index],
                }
            )
    return rows


def rq1_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        key = (row["genre"], row["source"], row["is_ai"])
        grouped[key].append(float(row["surprisal_ngram"]))

    summary_rows: list[dict] = []
    for (genre, source, is_ai), values in sorted(grouped.items()):
        stats = summarize(values)
        summary_rows.append(
            {
                "genre": genre,
                "source": source,
                "is_ai": is_ai,
                **stats,
            }
        )
    return summary_rows


def filter_rows_by_genre(rows: list[dict], genres: set[str] | None) -> list[dict]:
    if not genres:
        return rows
    return [row for row in rows if row["genre"] in genres]


def rq2_boundary_summary(
    rows: list[dict], pre_window: int = 3, permutations: int = 1000
) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    piece_effects: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        pre = [
            row
            for row in piece_rows
            if row["distance_to_next_boundary"] != ""
            and 1 <= int(row["distance_to_next_boundary"]) <= pre_window
        ]
        far = [
            row
            for row in piece_rows
            if row["distance_to_next_boundary"] == ""
            or int(row["distance_to_next_boundary"]) > pre_window
        ]
        if not pre or not far:
            continue

        meta = piece_rows[0]
        effect_ngram = mean(float(row["surprisal_ngram"]) for row in pre) - mean(
            float(row["surprisal_ngram"]) for row in far
        )
        effect_unigram = mean(float(row["surprisal_unigram"]) for row in pre) - mean(
            float(row["surprisal_unigram"]) for row in far
        )
        effect_shuffled = mean(float(row["surprisal_shuffled"]) for row in pre) - mean(
            float(row["surprisal_shuffled"]) for row in far
        )
        piece_effects.append(
            {
                "piece_id": piece_id,
                "genre": meta["genre"],
                "source": meta["source"],
                "is_ai": meta["is_ai"],
                "effect_ngram": effect_ngram,
                "effect_unigram": effect_unigram,
                "effect_shuffled": effect_shuffled,
                "ngram_minus_unigram": effect_ngram - effect_unigram,
                "ngram_minus_shuffled": effect_ngram - effect_shuffled,
            }
        )

    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for effect in piece_effects:
        grouped[(effect["genre"], effect["source"], effect["is_ai"])].append(effect)

    output: list[dict] = []
    for (genre, source, is_ai), effects in sorted(grouped.items()):
        ngram_minus_unigram = [effect["ngram_minus_unigram"] for effect in effects]
        ngram_minus_shuffled = [effect["ngram_minus_shuffled"] for effect in effects]
        output.append(
            {
                "genre": genre,
                "source": source,
                "is_ai": is_ai,
                "pieces": len(effects),
                "mean_effect_ngram": mean(effect["effect_ngram"] for effect in effects),
                "mean_effect_unigram": mean(
                    effect["effect_unigram"] for effect in effects
                ),
                "mean_effect_shuffled": mean(
                    effect["effect_shuffled"] for effect in effects
                ),
                "mean_ngram_minus_unigram": mean(ngram_minus_unigram),
                "p_ngram_minus_unigram": paired_sign_permutation_pvalue(
                    ngram_minus_unigram, permutations=permutations
                ),
                "mean_ngram_minus_shuffled": mean(ngram_minus_shuffled),
                "p_ngram_minus_shuffled": paired_sign_permutation_pvalue(
                    ngram_minus_shuffled, permutations=permutations
                ),
            }
        )
    return output


def piece_features(rows: list[dict]) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    features: list[dict] = []
    for piece_id, piece_rows in sorted(by_piece.items()):
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        pre = [
            float(row["surprisal_ngram"])
            for row in piece_rows
            if row["distance_to_next_boundary"] != ""
            and 1 <= int(row["distance_to_next_boundary"]) <= 3
        ]
        far = [
            float(row["surprisal_ngram"])
            for row in piece_rows
            if row["distance_to_next_boundary"] == ""
            or int(row["distance_to_next_boundary"]) > 3
        ]
        meta = piece_rows[0]
        stats = summarize(values)
        sorted_values = sorted(values)
        p90 = sorted_values[int(0.9 * (len(sorted_values) - 1))]
        features.append(
            {
                "piece_id": piece_id,
                "source": meta["source"],
                "genre": meta["genre"],
                "is_ai": int(meta["is_ai"]),
                "surprisal_mean": stats["mean"],
                "surprisal_sd": stats["sd"],
                "surprisal_median": stats["median"],
                "surprisal_p90": p90,
                "surprisal_max": max(values),
                "boundary_delta": (mean(pre) - mean(far)) if pre and far else 0.0,
                "lag1_autocorr": lag1_autocorrelation(values),
            }
        )
    return features


def _nearest_centroid_scores(feature_rows: list[dict], train_idx: list[int], test_idx: list[int]) -> list[float]:
    feature_names = [
        "surprisal_mean",
        "surprisal_sd",
        "surprisal_p90",
        "surprisal_max",
        "boundary_delta",
        "lag1_autocorr",
    ]
    centroids: dict[int, list[float]] = {}
    for label in (0, 1):
        selected = [i for i in train_idx if int(feature_rows[i]["is_ai"]) == label]
        if not selected:
            centroids[label] = [0.0] * len(feature_names)
            continue
        centroids[label] = [
            mean(float(feature_rows[i][name]) for i in selected) for name in feature_names
        ]

    scores: list[float] = []
    for i in test_idx:
        vector = [float(feature_rows[i][name]) for name in feature_names]
        distances = {}
        for label, centroid in centroids.items():
            distances[label] = math.sqrt(
                sum((value - center) ** 2 for value, center in zip(vector, centroid))
            )
        scores.append(distances[0] - distances[1])
    return scores


def evaluate_ai_classifier(
    feature_rows: list[dict], seed: int = 13, permutations: int = 200
) -> dict:
    labels = [int(row["is_ai"]) for row in feature_rows]
    if len(set(labels)) < 2 or len(labels) < 4:
        return {
            "error": "RQ4 needs at least four pieces and both human/AI labels.",
            "pieces": len(labels),
        }

    observed = _cross_validated_metrics(feature_rows, labels, seed)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(permutations):
        shuffled_labels = labels[:]
        rng.shuffle(shuffled_labels)
        shuffled_rows = [
            {**row, "is_ai": shuffled_labels[index]}
            for index, row in enumerate(feature_rows)
        ]
        metric = _cross_validated_metrics(shuffled_rows, shuffled_labels, seed)
        if metric["accuracy"] >= observed["accuracy"]:
            extreme += 1
    observed["permutation_p_accuracy"] = (extreme + 1) / (permutations + 1)
    observed["permutations"] = permutations
    observed["pieces"] = len(labels)
    return observed


def _cross_validated_metrics(feature_rows: list[dict], labels: list[int], seed: int) -> dict:
    indices = list(range(len(labels)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    folds = [indices[i:: min(5, len(indices))] for i in range(min(5, len(indices)))]
    predictions: list[int] = []
    scores: list[float] = []
    truth: list[int] = []
    for test_idx in folds:
        train_idx = [index for index in indices if index not in test_idx]
        fold_scores = _nearest_centroid_scores(feature_rows, train_idx, test_idx)
        scores.extend(fold_scores)
        predictions.extend([1 if score >= 0 else 0 for score in fold_scores])
        truth.extend(labels[index] for index in test_idx)

    tp = sum(1 for y, pred in zip(truth, predictions) if y == 1 and pred == 1)
    fp = sum(1 for y, pred in zip(truth, predictions) if y == 0 and pred == 1)
    fn = sum(1 for y, pred in zip(truth, predictions) if y == 1 and pred == 0)
    accuracy = sum(1 for y, pred in zip(truth, predictions) if y == pred) / len(truth)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc_score(truth, scores),
    }


def run_pipeline(
    events: list[Event],
    output_dir: str | Path,
    order: int = 3,
    token_kind: str = "pitch",
    pre_window: int = 3,
    permutations: int = 1000,
    rq123_genres: set[str] | None = None,
    rq4_sources: set[str] | None = None,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    surprisal = build_surprisal_rows(events, order=order, token_kind=token_kind)
    rq123_surprisal = filter_rows_by_genre(surprisal, rq123_genres)
    rq1 = rq1_summary(rq123_surprisal)
    rq2 = rq2_boundary_summary(
        rq123_surprisal, pre_window=pre_window, permutations=permutations
    )
    features = piece_features(surprisal)
    rq4_features = (
        [row for row in features if row["source"] in rq4_sources]
        if rq4_sources
        else features
    )
    rq4 = evaluate_ai_classifier(rq4_features, permutations=max(50, permutations // 5))
    rq4["source_filter"] = sorted(rq4_sources) if rq4_sources else "all"

    paths = {
        "surprisal_events": output / "surprisal_events.csv",
        "rq1_genre_summary": output / "rq1_genre_summary.csv",
        "rq2_boundary_summary": output / "rq2_boundary_summary.csv",
        "piece_features": output / "piece_features.csv",
        "rq4_ai_classifier": output / "rq4_ai_classifier.json",
    }
    write_rows(paths["surprisal_events"], surprisal)
    write_rows(paths["rq1_genre_summary"], rq1)
    write_rows(paths["rq2_boundary_summary"], rq2)
    write_rows(paths["piece_features"], features)
    paths["rq4_ai_classifier"].write_text(
        json.dumps(rq4, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return paths
