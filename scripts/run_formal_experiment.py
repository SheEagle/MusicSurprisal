from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.analysis import (
    build_surprisal_rows,
    evaluate_ai_classifier,
    piece_features,
    rq1_summary,
    rq2_boundary_summary,
)
from music_surprisal.data import Event, write_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all RQs in chunks on the normalized event table."
    )
    parser.add_argument("--events", default="data/events_all_rq.csv")
    parser.add_argument("--output", default="output/formal_all_rq")
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--max-maestro-pieces", type=int, default=180)
    parser.add_argument("--classical-source", default="maestro", choices=["maestro", "dcml"])
    parser.add_argument("--jazz-source", default="wjazzd", choices=["wjazzd", "jtc"])
    parser.add_argument("--write-event-samples", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print("Loading scoped event sets...")
    classical = load_events(
        args.events,
        sources={args.classical_source},
        max_pieces={"maestro": args.max_maestro_pieces} if args.classical_source == "maestro" else {},
    )
    jazz = load_events(args.events, sources={args.jazz_source})
    rq4 = load_events(args.events, sources={"jsb", "js_fake"})

    summary = {
        "classical_events": len(classical),
        "classical_pieces": count_pieces(classical),
        "jazz_events": len(jazz),
        "jazz_pieces": count_pieces(jazz),
        "jazz_source": args.jazz_source,
        "rq4_events": len(rq4),
        "rq4_pieces": count_pieces(rq4),
        "max_maestro_pieces": args.max_maestro_pieces,
        "classical_source": args.classical_source,
        "note": "This runner covers legacy RQ1/RQ2 and JSB-vs-JS-Fake RQ4 summaries. Current RQ3 is in dcml_period_rq3_distribution_analysis.py.",
    }
    (output / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))

    print("Running RQ1/RQ2 for classical...")
    classical_rows = build_surprisal_rows(
        classical, order=args.order, token_kind=args.token_kind
    )
    print("Running RQ1/RQ2 for jazz...")
    jazz_rows = build_surprisal_rows(jazz, order=args.order, token_kind=args.token_kind)
    rq123_rows = classical_rows + jazz_rows

    write_rows(output / "rq1_genre_summary.csv", rq1_summary(rq123_rows))
    rq1_features = rq1_time_series_features(rq123_rows)
    write_rows(output / "rq1_time_series_features.csv", rq1_features)
    write_rows(output / "rq1_time_series_feature_summary.csv", rq1_feature_summary(rq1_features))
    write_rows(output / "rq1_normalized_time_profile.csv", rq1_normalized_time_profile(rq123_rows))
    write_rows(
        output / "rq2_boundary_summary.csv",
        rq2_boundary_summary(rq123_rows, permutations=args.permutations),
    )
    rq2_profile = rq2_boundary_aligned_profile(rq123_rows, window=8)
    write_rows(output / "rq2_boundary_aligned_profile.csv", rq2_profile)
    write_rows(output / "rq2_boundary_shape_summary.csv", rq2_boundary_shape_summary(rq2_profile))
    write_rows(output / "rq2_between_genre_curve_difference.csv", rq2_between_genre_difference(rq2_profile))
    write_rows(output / "piece_features_rq123.csv", piece_features(rq123_rows))

    if args.write_event_samples:
        write_rows(output / "surprisal_events_sample.csv", rq123_rows[:100000])

    print("Running RQ4 JSB vs JS Fake...")
    rq4_rows = build_surprisal_rows(rq4, order=args.order, token_kind=args.token_kind)
    rq4_features = piece_features(rq4_rows)
    write_rows(output / "piece_features_rq4.csv", rq4_features)
    rq4_metrics = evaluate_ai_classifier(
        rq4_features, permutations=max(100, args.permutations)
    )
    rq4_metrics["source_filter"] = ["js_fake", "jsb"]
    (output / "rq4_ai_classifier.json").write_text(
        json.dumps(rq4_metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Done.")


def load_events(
    path: str | Path,
    *,
    sources: set[str],
    max_pieces: dict[str, int] | None = None,
) -> list[Event]:
    max_pieces = max_pieces or {}
    selected_pieces: dict[tuple[str, str], set[str]] = defaultdict(set)
    events: list[Event] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source = row["source"]
            if source not in sources:
                continue
            piece_id = row["piece_id"]
            split = row["split"].strip().lower()
            cap = max_pieces.get(source, 0)
            split_key = (source, split)
            if cap and piece_id not in selected_pieces[split_key]:
                if len(selected_pieces[split_key]) >= cap:
                    continue
                selected_pieces[split_key].add(piece_id)
            elif cap and piece_id not in selected_pieces[split_key]:
                continue
            else:
                selected_pieces[split_key].add(piece_id)

            events.append(
                Event(
                    piece_id=piece_id,
                    source=source,
                    genre=row["genre"],
                    is_ai=row["is_ai"].strip().lower() in {"1", "true", "yes"},
                    split=split,
                    onset=float(row["onset"]),
                    pitch=int(float(row["pitch"])),
                    duration=float(row["duration"]),
                    chord=row["chord"] or "NA",
                    boundary=row["boundary"].strip().lower() in {"1", "true", "yes"},
                )
            )
    return events


def count_pieces(events: list[Event]) -> int:
    return len({event.piece_id for event in events})


def rq1_time_series_features(rows: list[dict]) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    output: list[dict] = []
    for piece_id, piece_rows in sorted(by_piece.items()):
        piece_rows.sort(key=lambda row: int(row["event_index"]))
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < 4:
            continue
        meta = piece_rows[0]
        n = len(values)
        q = max(1, n // 4)
        first = values[:q]
        last = values[-q:]
        sorted_values = sorted(values)
        p90 = percentile(sorted_values, 0.90)
        p95 = percentile(sorted_values, 0.95)
        threshold = p90
        peaks = local_peak_count(values, threshold=threshold)
        output.append(
            {
                "piece_id": piece_id,
                "genre": meta["genre"],
                "source": meta["source"],
                "is_ai": meta["is_ai"],
                "events": n,
                "mean": mean(values),
                "sd": pstdev(values) if n > 1 else 0.0,
                "median": median(values),
                "p90": p90,
                "p95": p95,
                "max": max(values),
                "range": max(values) - min(values),
                "first_quarter_mean": mean(first),
                "last_quarter_mean": mean(last),
                "end_minus_start": mean(last) - mean(first),
                "linear_slope": linear_slope(values),
                "lag1_autocorr": autocorrelation(values, lag=1),
                "lag4_autocorr": autocorrelation(values, lag=4),
                "peak_rate": peaks / n,
                "high_surprisal_rate": sum(1 for value in values if value >= threshold) / n,
            }
        )
    return output


def rq1_feature_summary(feature_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in feature_rows:
        grouped[(row["genre"], row["source"])].append(row)

    features = [
        "mean",
        "sd",
        "p90",
        "p95",
        "max",
        "range",
        "end_minus_start",
        "linear_slope",
        "lag1_autocorr",
        "lag4_autocorr",
        "peak_rate",
        "high_surprisal_rate",
    ]
    output: list[dict] = []
    for (genre, source), rows in sorted(grouped.items()):
        result = {"genre": genre, "source": source, "pieces": len(rows)}
        for feature in features:
            values = [float(row[feature]) for row in rows]
            result[f"{feature}_mean"] = mean(values)
            result[f"{feature}_sd"] = pstdev(values) if len(values) > 1 else 0.0
        output.append(result)
    return output


def rq1_normalized_time_profile(rows: list[dict], bins: int = 20) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    grouped_bins: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
        n = len(piece_rows)
        if n < 2:
            continue
        meta = piece_rows[0]
        for index, row in enumerate(piece_rows):
            bin_id = min(bins - 1, int(index / n * bins))
            grouped_bins[(meta["genre"], meta["source"], bin_id)].append(
                float(row["surprisal_ngram"])
            )

    output: list[dict] = []
    for (genre, source, bin_id), values in sorted(grouped_bins.items()):
        output.append(
            {
                "genre": genre,
                "source": source,
                "time_bin": bin_id,
                "normalized_time_start": bin_id / bins,
                "normalized_time_end": (bin_id + 1) / bins,
                "n": len(values),
                "mean_surprisal": mean(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return output


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    index = q * (len(sorted_values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    xs = [i / (n - 1) for i in range(n)]
    mx = mean(xs)
    my = mean(values)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom


def autocorrelation(values: list[float], lag: int) -> float:
    if len(values) <= lag + 1:
        return 0.0
    x = values[:-lag]
    y = values[lag:]
    mx = mean(x)
    my = mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)
    )
    return numerator / denominator if denominator else 0.0


def local_peak_count(values: list[float], threshold: float) -> int:
    if len(values) < 3:
        return 0
    return sum(
        1
        for index in range(1, len(values) - 1)
        if values[index] >= threshold
        and values[index] > values[index - 1]
        and values[index] >= values[index + 1]
    )


def rq2_boundary_aligned_profile(rows: list[dict], window: int = 8) -> list[dict]:
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_piece[row["piece_id"]].append(row)

    accum: dict[tuple[str, str, int], dict[str, list[float]]] = defaultdict(
        lambda: {
            "ngram": [],
            "unigram": [],
            "shuffled": [],
            "delta_ngram_unigram": [],
            "delta_ngram_shuffled": [],
        }
    )

    for piece_rows in by_piece.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
        boundaries = [
            index
            for index, row in enumerate(piece_rows)
            if int(row["boundary"]) == 1
            and window <= index < len(piece_rows) - window
        ]
        if not boundaries:
            continue
        meta = piece_rows[0]
        for boundary_index in boundaries:
            for rel in range(-window, window + 1):
                row = piece_rows[boundary_index + rel]
                bucket = accum[(meta["genre"], meta["source"], rel)]
                ngram = float(row["surprisal_ngram"])
                unigram = float(row["surprisal_unigram"])
                shuffled = float(row["surprisal_shuffled"])
                bucket["ngram"].append(ngram)
                bucket["unigram"].append(unigram)
                bucket["shuffled"].append(shuffled)
                bucket["delta_ngram_unigram"].append(ngram - unigram)
                bucket["delta_ngram_shuffled"].append(ngram - shuffled)

    output: list[dict] = []
    for (genre, source, rel), values in sorted(accum.items()):
        output.append(
            {
                "genre": genre,
                "source": source,
                "relative_event": rel,
                "n": len(values["ngram"]),
                "mean_ngram": mean(values["ngram"]),
                "mean_unigram": mean(values["unigram"]),
                "mean_shuffled": mean(values["shuffled"]),
                "mean_delta_ngram_unigram": mean(values["delta_ngram_unigram"]),
                "mean_delta_ngram_shuffled": mean(values["delta_ngram_shuffled"]),
            }
        )
    return output


def rq2_boundary_shape_summary(profile_rows: list[dict]) -> list[dict]:
    by_source: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in profile_rows:
        by_source[(row["genre"], row["source"])].append(row)

    output: list[dict] = []
    for (genre, source), rows in sorted(by_source.items()):
        before = [row for row in rows if int(row["relative_event"]) < 0]
        at_after = [row for row in rows if int(row["relative_event"]) >= 0]
        all_ngram = [float(row["mean_ngram"]) for row in rows]
        all_unigram = [float(row["mean_unigram"]) for row in rows]
        all_shuffled = [float(row["mean_shuffled"]) for row in rows]
        output.append(
            {
                "genre": genre,
                "source": source,
                "positions": len(rows),
                "ngram_curve_range": max(all_ngram) - min(all_ngram),
                "unigram_curve_range": max(all_unigram) - min(all_unigram),
                "shuffled_curve_range": max(all_shuffled) - min(all_shuffled),
                "ngram_before_mean": mean(float(row["mean_ngram"]) for row in before),
                "ngram_at_after_mean": mean(float(row["mean_ngram"]) for row in at_after),
                "shape_delta_at_after_minus_before": mean(
                    float(row["mean_ngram"]) for row in at_after
                )
                - mean(float(row["mean_ngram"]) for row in before),
                "mean_context_specific_delta": mean(
                    float(row["mean_delta_ngram_unigram"]) for row in rows
                ),
                "mean_order_specific_delta": mean(
                    float(row["mean_delta_ngram_shuffled"]) for row in rows
                ),
            }
        )
    return output


def rq2_between_genre_difference(profile_rows: list[dict]) -> list[dict]:
    if not profile_rows:
        return []
    sources = sorted({row["source"] for row in profile_rows})
    if len(sources) != 2:
        return []
    left, right = sources
    by_key = {
        (row["source"], int(row["relative_event"])): row for row in profile_rows
    }
    rels = sorted({int(row["relative_event"]) for row in profile_rows})
    output: list[dict] = []
    for rel in rels:
        a = by_key.get((left, rel))
        b = by_key.get((right, rel))
        if not a or not b:
            continue
        output.append(
            {
                "source_a": left,
                "source_b": right,
                "relative_event": rel,
                "a_mean_ngram": float(a["mean_ngram"]),
                "b_mean_ngram": float(b["mean_ngram"]),
                "b_minus_a_ngram": float(b["mean_ngram"]) - float(a["mean_ngram"]),
                "a_delta_ngram_unigram": float(a["mean_delta_ngram_unigram"]),
                "b_delta_ngram_unigram": float(b["mean_delta_ngram_unigram"]),
                "b_minus_a_context_delta": float(b["mean_delta_ngram_unigram"])
                - float(a["mean_delta_ngram_unigram"]),
                "a_delta_ngram_shuffled": float(a["mean_delta_ngram_shuffled"]),
                "b_delta_ngram_shuffled": float(b["mean_delta_ngram_shuffled"]),
                "b_minus_a_order_delta": float(b["mean_delta_ngram_shuffled"])
                - float(a["mean_delta_ngram_shuffled"]),
            }
        )
    return output


if __name__ == "__main__":
    main()
