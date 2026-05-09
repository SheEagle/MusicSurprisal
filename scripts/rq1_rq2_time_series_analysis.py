from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.analysis import build_surprisal_rows
from music_surprisal.data import Event, group_by_piece as group_events_by_piece, token_function
from music_surprisal.ngram import NGramModel, START
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep time-series analysis for RQ1 and RQ2."
    )
    parser.add_argument("--events", default="data/events_dcml_jtc_all_rq.csv")
    parser.add_argument("--output", default="output/formal_dcml_jtc_all_rq/rq1_rq2_time_series")
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--bins", type=int, default=100)
    parser.add_argument("--local-window", type=int, default=16)
    parser.add_argument("--boundary-window", type=int, default=12)
    parser.add_argument("--threshold-quantile", type=float, default=0.90)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print("Loading DCML classical and JTC jazz events...")
    dcml = load_events(args.events, sources={"dcml"})
    jtc = load_events(args.events, sources={"jtc"})

    print("Computing surprisal rows...")
    rows = build_surprisal_rows(dcml, order=args.order, token_kind=args.token_kind)
    rows.extend(build_surprisal_rows(jtc, order=args.order, token_kind=args.token_kind))
    coverage_rows = model_coverage_diagnostics(
        {"dcml": dcml, "jtc": jtc},
        order=args.order,
        token_kind=args.token_kind,
    )
    by_piece = group_by_piece(rows)
    source_thresholds = high_surprisal_thresholds(rows, args.threshold_quantile)
    entropy_cutpoints = pooled_entropy_cutpoints(rows, states=5)

    print("Running RQ1 whole-piece time-series analysis...")
    piece_profile_rows = piece_normalized_profiles(by_piece, bins=args.bins)
    rq1_profile_rows = profile_accum(piece_profile_rows)
    rq1_local_rows = rq1_local_variance_profile(
        by_piece, bins=args.bins, window=args.local_window
    )
    rq1_piece_rows = rq1_piece_time_structure_features(
        by_piece,
        thresholds=source_thresholds,
        cutpoints=entropy_cutpoints,
        local_window=args.local_window,
    )
    rq1_effect_rows = between_source_effects(rq1_piece_rows, rq1_feature_names())
    rq1_shape_rows = curve_shape_distance(rq1_profile_rows, "mean_surprisal")

    write_csv(output / "rq1_piece_normalized_surprisal_profiles.csv", piece_profile_rows)
    write_csv(output / "rq1_raw_normalized_surprisal_profile.csv", rq1_profile_rows)
    write_csv(output / "rq1_raw_local_variance_profile.csv", rq1_local_rows)
    write_csv(output / "rq1_piece_time_structure_features.csv", rq1_piece_rows)
    write_csv(output / "rq1_between_genre_time_structure_effects.csv", rq1_effect_rows)
    write_csv(output / "rq1_curve_shape_distance_summary.csv", rq1_shape_rows)
    write_csv(output / "rq1_model_coverage_diagnostics.csv", coverage_rows)

    draw_piece_overlay(
        piece_profile_rows,
        rq1_profile_rows,
        output / "rq1_all_piece_surprisal_overlay.svg",
        "RQ1 all piece surprisal curves",
    )
    draw_profile(
        rq1_profile_rows,
        output / "rq1_raw_mean_surprisal_profile.svg",
        "RQ1 normalized mean surprisal profile",
        "mean_surprisal",
        "Surprisal (bits)",
    )
    draw_profile(
        rq1_local_rows,
        output / "rq1_local_variance_profile.svg",
        "RQ1 normalized local volatility profile",
        "mean_local_variance",
        "Local variance",
    )
    draw_difference(
        rq1_profile_rows,
        output / "rq1_between_genre_profile_difference.svg",
        "RQ1 jazz minus classical mean profile",
        "mean_surprisal",
    )
    draw_effect_bars(
        rq1_effect_rows,
        output / "rq1_time_structure_effects.svg",
        "RQ1 time-structure effects",
        "cohens_d_b_minus_a",
    )

    print("Running RQ2 boundary-aligned time-series analysis...")
    (
        rq2_piece_curve_rows,
        rq2_profile_rows,
        rq2_piece_feature_rows,
    ) = rq2_boundary_time_series(
        by_piece,
        thresholds=source_thresholds,
        local_window=args.local_window,
        boundary_window=args.boundary_window,
    )
    rq2_effect_rows = between_source_effects(
        rq2_piece_feature_rows, rq2_feature_names()
    )
    rq2_shape_rows = curve_shape_distance(rq2_profile_rows, "mean_ngram")

    write_csv(output / "rq2_piece_boundary_aligned_curves.csv", rq2_piece_curve_rows)
    write_csv(output / "rq2_boundary_time_series_profile.csv", rq2_profile_rows)
    write_csv(output / "rq2_piece_boundary_time_structure_features.csv", rq2_piece_feature_rows)
    write_csv(output / "rq2_between_genre_boundary_time_structure_effects.csv", rq2_effect_rows)
    write_csv(output / "rq2_boundary_curve_shape_distance_summary.csv", rq2_shape_rows)

    draw_boundary_piece_overlay(
        rq2_piece_curve_rows,
        rq2_profile_rows,
        output / "rq2_all_piece_boundary_curve_overlay.svg",
        "RQ2 all piece boundary-aligned curves",
    )
    draw_boundary_profile(
        rq2_profile_rows,
        output / "rq2_boundary_aligned_mean_profile.svg",
        "RQ2 boundary-aligned surprisal profile",
    )
    draw_boundary_single_metric(
        rq2_profile_rows,
        output / "rq2_boundary_local_variance_profile.svg",
        "RQ2 boundary-aligned local volatility",
        "mean_local_variance",
        "Local variance",
    )
    draw_boundary_rates(
        rq2_profile_rows,
        output / "rq2_boundary_event_rate_profile.svg",
        "RQ2 high states, peaks, and changepoints near boundaries",
    )
    draw_effect_bars(
        rq2_effect_rows,
        output / "rq2_boundary_time_structure_effects.svg",
        "RQ2 boundary time-structure effects",
        "cohens_d_b_minus_a",
    )

    write_summary(
        output / "RQ1_RQ2_TIME_SERIES_SUMMARY.md",
        args,
        coverage_rows,
        source_thresholds,
        rq1_shape_rows,
        rq1_effect_rows,
        rq2_shape_rows,
        rq2_effect_rows,
    )
    write_index(output)
    print(f"Wrote RQ1/RQ2 time-series analysis to {output}")


def group_by_piece(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(row)
    for piece_rows in grouped.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
    return dict(grouped)


def model_coverage_diagnostics(
    events_by_source: dict[str, list[Event]], *, order: int, token_kind: str
) -> list[dict]:
    rows: list[dict] = []
    to_token = token_function(token_kind)
    for source, events in sorted(events_by_source.items()):
        train = [event for event in events if event.split == "train"]
        eval_events = [event for event in events if event.split != "train"]
        if not train:
            raise ValueError(f"No train events for {source}")
        if not eval_events:
            eval_events = train
        train_pieces = group_events_by_piece(train)
        train_sequences = [
            [to_token(event) for event in piece_events]
            for piece_events in train_pieces.values()
            if piece_events
        ]
        model = NGramModel(order=order).fit(train_sequences)
        eval_stats = coverage_stats(
            model,
            group_events_by_piece(eval_events),
            token_kind=token_kind,
        )
        train_tokens = sum(len(sequence) for sequence in train_sequences)
        unique_pitches = {event.pitch for event in train}
        rows.append(
            {
                "source": source,
                "train_pieces": len(train_pieces),
                "train_events": len(train),
                "train_tokens": train_tokens,
                "eval_pieces": len(group_events_by_piece(eval_events)),
                "eval_events": len(eval_events),
                "token_kind": token_kind,
                "order": order,
                "vocab_size_including_unk": len(model.vocab),
                "vocab_size_without_unk": max(0, len(model.vocab) - 1),
                "unique_pitch_count": len(unique_pitches),
                "context_count": len(model.context_totals),
                "full_order_context_count": sum(
                    1 for context in model.context_totals if len(context) == order - 1
                ),
                **eval_stats,
            }
        )
    return rows


def coverage_stats(
    model: NGramModel, eval_pieces: dict[str, list[Event]], *, token_kind: str
) -> dict:
    to_token = token_function(token_kind)
    tokens = 0
    unknown_tokens = 0
    backoff_events = 0
    total_backoff_steps = 0
    full_context_hits = 0
    context_lengths: Counter[int] = Counter()
    for piece_events in eval_pieces.values():
        history: list[object] = [START] * (model.order - 1)
        for event in piece_events:
            token = to_token(event)
            tokens += 1
            if token not in model.vocab:
                unknown_tokens += 1
            initial_len = len(tuple(history)[-(model.order - 1) :]) if model.order > 1 else 0
            used_len = used_context_length(model, history)
            if used_len < initial_len:
                backoff_events += 1
                total_backoff_steps += initial_len - used_len
            else:
                full_context_hits += 1
            context_lengths[used_len] += 1
            history.append(token)
    return {
        "eval_tokens_scored": tokens,
        "unknown_token_count": unknown_tokens,
        "unknown_token_rate": unknown_tokens / tokens if tokens else 0.0,
        "backoff_event_count": backoff_events,
        "backoff_event_rate": backoff_events / tokens if tokens else 0.0,
        "mean_backoff_steps": total_backoff_steps / tokens if tokens else 0.0,
        "full_context_hit_rate": full_context_hits / tokens if tokens else 0.0,
        "mean_used_context_length": sum(
            length * count for length, count in context_lengths.items()
        )
        / tokens
        if tokens
        else 0.0,
    }


def used_context_length(model: NGramModel, history: list[object]) -> int:
    context_tuple = tuple(history)[-(model.order - 1) :] if model.order > 1 else ()
    while context_tuple and model.context_totals[context_tuple] == 0:
        context_tuple = context_tuple[1:]
    return len(context_tuple)


def high_surprisal_thresholds(rows: list[dict], q: float) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["source"]].append(float(row["surprisal_ngram"]))
    return {source: percentile(sorted(values), q) for source, values in grouped.items()}


def pooled_entropy_cutpoints(rows: list[dict], states: int) -> list[float]:
    values = sorted(float(row["surprisal_ngram"]) for row in rows)
    return [percentile(values, index / states) for index in range(1, states)]


def piece_normalized_profiles(
    by_piece: dict[str, list[dict]], bins: int
) -> list[dict]:
    output: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        if len(piece_rows) < 2:
            continue
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        profile = resample(values, bins)
        meta = piece_rows[0]
        for index, value in enumerate(profile):
            output.append(
                {
                    "piece_id": piece_id,
                    "source": meta["source"],
                    "genre": meta["genre"],
                    "time_bin": index,
                    "normalized_time": index / max(1, bins - 1),
                    "surprisal": value,
                }
            )
    return output


def profile_accum(piece_profile_rows: list[dict]) -> list[dict]:
    accum: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in piece_profile_rows:
        accum[(row["source"], row["genre"], int(row["time_bin"]))].append(
            float(row["surprisal"])
        )
    output: list[dict] = []
    bins = max(int(row["time_bin"]) for row in piece_profile_rows) + 1
    for (source, genre, time_bin), values in sorted(accum.items()):
        output.append(
            {
                "source": source,
                "genre": genre,
                "time_bin": time_bin,
                "normalized_time": time_bin / max(1, bins - 1),
                "pieces": len(values),
                "mean_surprisal": mean(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return output


def rq1_local_variance_profile(
    by_piece: dict[str, list[dict]], bins: int, window: int
) -> list[dict]:
    accum: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        if len(piece_rows) < 2:
            continue
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        local = rolling_variance(values, window)
        profile = resample(local, bins)
        meta = piece_rows[0]
        for index, value in enumerate(profile):
            accum[(meta["source"], meta["genre"], index)].append(value)
    output: list[dict] = []
    for (source, genre, time_bin), values in sorted(accum.items()):
        output.append(
            {
                "source": source,
                "genre": genre,
                "time_bin": time_bin,
                "normalized_time": time_bin / max(1, bins - 1),
                "pieces": len(values),
                "mean_local_variance": mean(values),
                "sd_local_variance": pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return output


def rq1_piece_time_structure_features(
    by_piece: dict[str, list[dict]],
    *,
    thresholds: dict[str, float],
    cutpoints: list[float],
    local_window: int,
) -> list[dict]:
    output: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < 4:
            continue
        source = piece_rows[0]["source"]
        threshold = thresholds[source]
        local = rolling_variance(values, local_window)
        peaks = set(local_peaks(values, threshold))
        cps = set(simple_changepoints(values, threshold, local_window))
        high_runs, low_runs = binary_runs([value >= threshold for value in values])
        states = [discretize(value, cutpoints) for value in values]
        transitions = list(zip(states, states[1:]))
        transition_counts = Counter(transitions)
        output.append(
            {
                "piece_id": piece_id,
                "source": source,
                "genre": piece_rows[0]["genre"],
                "events": len(values),
                "mean_surprisal": mean(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
                "curve_range": max(values) - min(values),
                "start_10pct_mean": zone_mean(values, 0.00, 0.10),
                "middle_10pct_mean": zone_mean(values, 0.45, 0.55),
                "end_10pct_mean": zone_mean(values, 0.90, 1.00),
                "end_minus_start": zone_mean(values, 0.90, 1.00)
                - zone_mean(values, 0.00, 0.10),
                "linear_slope": linear_slope(values),
                "mean_local_variance": mean(local),
                "max_local_variance": max(local),
                "peak_rate": len(peaks) / len(values),
                "changepoint_rate": len(cps) / len(values),
                "mean_changepoint_time": mean(
                    [index / max(1, len(values) - 1) for index in cps]
                )
                if cps
                else 0.0,
                "mean_high_run": mean(high_runs) if high_runs else 0.0,
                "max_high_run": max(high_runs) if high_runs else 0,
                "mean_low_run": mean(low_runs) if low_runs else 0.0,
                "state_entropy": empirical_entropy(states),
                "entropy_rate_order1": conditional_entropy(states, order=1),
                "entropy_rate_order2": conditional_entropy(states, order=2),
                "same_state_transition_rate": sum(
                    1 for previous, current in transitions if previous == current
                )
                / len(transitions)
                if transitions
                else 0.0,
                "dominant_transition_rate": max(transition_counts.values())
                / len(transitions)
                if transitions
                else 0.0,
            }
        )
    return output


def rq2_boundary_time_series(
    by_piece: dict[str, list[dict]],
    *,
    thresholds: dict[str, float],
    local_window: int,
    boundary_window: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    piece_curve_rows: list[dict] = []
    piece_feature_rows: list[dict] = []
    accum: dict[tuple[str, str, int], dict[str, list[float]]] = defaultdict(
        lambda: {
            "ngram": [],
            "unigram": [],
            "shuffled": [],
            "local_variance": [],
            "high": [],
            "peak": [],
            "changepoint": [],
            "delta_ngram_unigram": [],
            "delta_ngram_shuffled": [],
        }
    )

    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < boundary_window * 2 + 1:
            continue
        source = piece_rows[0]["source"]
        threshold = thresholds[source]
        boundaries = [
            index
            for index, row in enumerate(piece_rows)
            if int(row["boundary"]) == 1
            and boundary_window <= index < len(piece_rows) - boundary_window
        ]
        if not boundaries:
            continue
        local = rolling_variance(values, local_window)
        peaks = set(local_peaks(values, threshold))
        cps = set(simple_changepoints(values, threshold, local_window))
        high = {index for index, value in enumerate(values) if value >= threshold}

        rel_values: dict[int, dict[str, list[float]]] = defaultdict(
            lambda: {
                "ngram": [],
                "unigram": [],
                "shuffled": [],
                "local_variance": [],
                "high": [],
                "peak": [],
                "changepoint": [],
            }
        )
        for boundary in boundaries:
            for rel in range(-boundary_window, boundary_window + 1):
                index = boundary + rel
                row = piece_rows[index]
                ngram = float(row["surprisal_ngram"])
                unigram = float(row["surprisal_unigram"])
                shuffled = float(row["surprisal_shuffled"])
                is_high = float(index in high)
                is_peak = float(index in peaks)
                is_cp = float(index in cps)
                bucket = accum[(source, row["genre"], rel)]
                bucket["ngram"].append(ngram)
                bucket["unigram"].append(unigram)
                bucket["shuffled"].append(shuffled)
                bucket["local_variance"].append(local[index])
                bucket["high"].append(is_high)
                bucket["peak"].append(is_peak)
                bucket["changepoint"].append(is_cp)
                bucket["delta_ngram_unigram"].append(ngram - unigram)
                bucket["delta_ngram_shuffled"].append(ngram - shuffled)

                rel_bucket = rel_values[rel]
                rel_bucket["ngram"].append(ngram)
                rel_bucket["unigram"].append(unigram)
                rel_bucket["shuffled"].append(shuffled)
                rel_bucket["local_variance"].append(local[index])
                rel_bucket["high"].append(is_high)
                rel_bucket["peak"].append(is_peak)
                rel_bucket["changepoint"].append(is_cp)

        curve = {
            rel: {key: mean(vals) for key, vals in rel_bucket.items()}
            for rel, rel_bucket in rel_values.items()
        }
        for rel, rel_row in sorted(curve.items()):
            piece_curve_rows.append(
                {
                    "piece_id": piece_id,
                    "source": source,
                    "genre": piece_rows[0]["genre"],
                    "boundaries": len(boundaries),
                    "relative_event": rel,
                    "mean_ngram": rel_row["ngram"],
                    "mean_unigram": rel_row["unigram"],
                    "mean_shuffled": rel_row["shuffled"],
                    "mean_local_variance": rel_row["local_variance"],
                    "high_state_rate": rel_row["high"],
                    "local_peak_rate": rel_row["peak"],
                    "changepoint_rate": rel_row["changepoint"],
                    "mean_delta_ngram_unigram": rel_row["ngram"] - rel_row["unigram"],
                    "mean_delta_ngram_shuffled": rel_row["ngram"] - rel_row["shuffled"],
                }
            )
        piece_feature_rows.append(
            rq2_piece_features_from_curve(
                piece_id,
                piece_rows[0],
                curve,
                values,
                boundaries,
                high,
                peaks,
                cps,
                boundary_window,
            )
        )

    profile_rows: list[dict] = []
    for (source, genre, rel), bucket in sorted(accum.items()):
        profile_rows.append(
            {
                "source": source,
                "genre": genre,
                "relative_event": rel,
                "n": len(bucket["ngram"]),
                "mean_ngram": mean(bucket["ngram"]),
                "mean_unigram": mean(bucket["unigram"]),
                "mean_shuffled": mean(bucket["shuffled"]),
                "mean_local_variance": mean(bucket["local_variance"]),
                "high_state_rate": mean(bucket["high"]),
                "local_peak_rate": mean(bucket["peak"]),
                "changepoint_rate": mean(bucket["changepoint"]),
                "mean_delta_ngram_unigram": mean(bucket["delta_ngram_unigram"]),
                "mean_delta_ngram_shuffled": mean(bucket["delta_ngram_shuffled"]),
            }
        )
    return piece_curve_rows, profile_rows, piece_feature_rows


def rq2_piece_features_from_curve(
    piece_id: str,
    meta: dict,
    curve: dict[int, dict[str, float]],
    values: list[float],
    boundaries: list[int],
    high: set[int],
    peaks: set[int],
    cps: set[int],
    boundary_window: int,
) -> dict:
    rels = sorted(curve)
    ngram = {rel: curve[rel]["ngram"] for rel in rels}
    local = {rel: curve[rel]["local_variance"] for rel in rels}
    pre = [ngram[rel] for rel in range(-boundary_window, 0) if rel in ngram]
    post = [ngram[rel] for rel in range(0, boundary_window + 1) if rel in ngram]
    core_rels = [rel for rel in (-2, -1, 0, 1, 2) if rel in ngram]
    far_rels = [
        rel
        for rel in rels
        if rel in {-boundary_window, -boundary_window + 1, boundary_window - 1, boundary_window}
    ]
    peak_rel = max(rels, key=lambda rel: ngram[rel])
    core_zone = indices_near(boundaries, len(values), window=2)
    exposure = len(core_zone) / len(values) if values else 0.0
    return {
        "piece_id": piece_id,
        "source": meta["source"],
        "genre": meta["genre"],
        "events": len(values),
        "boundaries": len(boundaries),
        "boundary_curve_mean": mean(ngram.values()),
        "boundary_curve_range": max(ngram.values()) - min(ngram.values()),
        "boundary_value": ngram.get(0, 0.0),
        "peak_relative_event": peak_rel,
        "peak_value": ngram[peak_rel],
        "pre_mean": mean(pre) if pre else 0.0,
        "post_mean": mean(post) if post else 0.0,
        "post_minus_pre": (mean(post) - mean(pre)) if pre and post else 0.0,
        "boundary_core_lift_vs_far": mean([ngram[rel] for rel in core_rels])
        - mean([ngram[rel] for rel in far_rels])
        if core_rels and far_rels
        else 0.0,
        "boundary_local_variance_lift_vs_far": mean([local[rel] for rel in core_rels])
        - mean([local[rel] for rel in far_rels])
        if core_rels and far_rels
        else 0.0,
        "boundary_lift_vs_unigram": curve.get(0, {}).get("ngram", 0.0)
        - curve.get(0, {}).get("unigram", 0.0),
        "boundary_lift_vs_shuffled": curve.get(0, {}).get("ngram", 0.0)
        - curve.get(0, {}).get("shuffled", 0.0),
        "normalized_boundary_z": z_at_key(ngram, 0),
        "normalized_peak_z": z_at_key(ngram, peak_rel),
        "high_event_boundary_enrichment": enrichment(high, core_zone, exposure),
        "peak_boundary_enrichment": enrichment(peaks, core_zone, exposure),
        "changepoint_boundary_enrichment": enrichment(cps, core_zone, exposure),
    }


def rq1_feature_names() -> list[str]:
    return [
        "mean_surprisal",
        "sd_surprisal",
        "curve_range",
        "end_minus_start",
        "linear_slope",
        "mean_local_variance",
        "max_local_variance",
        "peak_rate",
        "changepoint_rate",
        "mean_high_run",
        "max_high_run",
        "state_entropy",
        "entropy_rate_order1",
        "entropy_rate_order2",
        "same_state_transition_rate",
        "dominant_transition_rate",
    ]


def rq2_feature_names() -> list[str]:
    return [
        "boundary_curve_range",
        "boundary_value",
        "peak_relative_event",
        "post_minus_pre",
        "boundary_core_lift_vs_far",
        "boundary_local_variance_lift_vs_far",
        "boundary_lift_vs_unigram",
        "boundary_lift_vs_shuffled",
        "normalized_boundary_z",
        "normalized_peak_z",
        "high_event_boundary_enrichment",
        "peak_boundary_enrichment",
        "changepoint_boundary_enrichment",
    ]


def between_source_effects(rows: list[dict], features: list[str]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["source"]].append(row)
    sources = sorted(grouped)
    if len(sources) != 2:
        return []
    a, b = sources
    output: list[dict] = []
    for feature in features:
        av = [float(row[feature]) for row in grouped[a]]
        bv = [float(row[feature]) for row in grouped[b]]
        output.append(
            {
                "source_a": a,
                "source_b": b,
                "feature": feature,
                "a_mean": mean(av),
                "b_mean": mean(bv),
                "b_minus_a": mean(bv) - mean(av),
                "cohens_d_b_minus_a": cohens_d(av, bv),
                "a_median": median(av),
                "b_median": median(bv),
            }
        )
    return output


def curve_shape_distance(rows: list[dict], value_key: str) -> list[dict]:
    sources = sorted({row["source"] for row in rows})
    if len(sources) != 2:
        return []
    a, b = sources
    key_name = "time_bin" if "time_bin" in rows[0] else "relative_event"
    by_key = {(row["source"], int(row[key_name])): row for row in rows}
    positions = sorted({int(row[key_name]) for row in rows})
    diffs = [
        float(by_key[(b, pos)][value_key]) - float(by_key[(a, pos)][value_key])
        for pos in positions
        if (a, pos) in by_key and (b, pos) in by_key
    ]
    if not diffs:
        return []
    max_idx = max(range(len(diffs)), key=lambda index: diffs[index])
    min_idx = min(range(len(diffs)), key=lambda index: diffs[index])
    return [
        {"metric": f"mean_{b}_minus_{a}", "value": mean(diffs)},
        {"metric": "rms_curve_difference", "value": math.sqrt(mean(x * x for x in diffs))},
        {
            "metric": f"max_{b}_excess",
            "value": diffs[max_idx],
            "position": positions[max_idx],
        },
        {
            "metric": f"max_{a}_excess",
            "value": diffs[min_idx],
            "position": positions[min_idx],
        },
        {"metric": f"signed_area_{b}_minus_{a}", "value": mean(diffs)},
    ]


def rolling_variance(values: list[float], window: int) -> list[float]:
    half = max(1, window // 2)
    output = []
    for index in range(len(values)):
        chunk = values[max(0, index - half) : min(len(values), index + half + 1)]
        output.append(pstdev(chunk) ** 2 if len(chunk) > 1 else 0.0)
    return output


def local_peaks(values: list[float], threshold: float) -> list[int]:
    if len(values) < 3:
        return []
    return [
        index
        for index in range(1, len(values) - 1)
        if values[index] >= threshold
        and values[index] > values[index - 1]
        and values[index] >= values[index + 1]
    ]


def simple_changepoints(values: list[float], threshold: float, window: int) -> list[int]:
    if len(values) < window * 2 + 1:
        return []
    diffs = []
    for index in range(window, len(values) - window):
        left = values[index - window : index]
        right = values[index : index + window]
        diffs.append((index, abs(mean(right) - mean(left))))
    if not diffs:
        return []
    cutoff = percentile(sorted(value for _, value in diffs), 0.90)
    candidates = [index for index, value in diffs if value >= max(cutoff, threshold * 0.10)]
    return suppress_nearby(candidates, min_gap=window)


def suppress_nearby(indices: list[int], min_gap: int) -> list[int]:
    selected: list[int] = []
    last = -10**9
    for index in indices:
        if index - last >= min_gap:
            selected.append(index)
            last = index
    return selected


def binary_runs(states: list[bool]) -> tuple[list[int], list[int]]:
    high: list[int] = []
    low: list[int] = []
    if not states:
        return high, low
    current = states[0]
    length = 1
    for state in states[1:]:
        if state == current:
            length += 1
        else:
            (high if current else low).append(length)
            current = state
            length = 1
    (high if current else low).append(length)
    return high, low


def resample(values: list[float], bins: int) -> list[float]:
    if not values:
        return [0.0] * bins
    if len(values) == 1:
        return [values[0]] * bins
    output = []
    for index in range(bins):
        pos = index / max(1, bins - 1) * (len(values) - 1)
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            output.append(values[lo])
        else:
            weight = pos - lo
            output.append(values[lo] * (1 - weight) + values[hi] * weight)
    return output


def linear_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = [index / (len(values) - 1) for index in range(len(values))]
    mx = mean(xs)
    my = mean(values)
    denom = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom if denom else 0.0


def zone_mean(values: list[float], start: float, end: float) -> float:
    selected = [
        value
        for index, value in enumerate(values)
        if start <= index / max(1, len(values) - 1) <= end
    ]
    return mean(selected) if selected else 0.0


def discretize(value: float, cutpoints: list[float]) -> int:
    state = 0
    while state < len(cutpoints) and value > cutpoints[state]:
        state += 1
    return state


def empirical_entropy(states: list[int]) -> float:
    return entropy_from_counts(Counter(states).values())


def conditional_entropy(states: list[int], order: int) -> float:
    if len(states) <= order:
        return 0.0
    context_counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for index in range(order, len(states)):
        context = tuple(states[index - order : index])
        context_counts[context][states[index]] += 1
    total = len(states) - order
    output = 0.0
    for counts in context_counts.values():
        context_total = sum(counts.values())
        output += context_total / total * entropy_from_counts(counts.values())
    return output


def entropy_from_counts(counts: object) -> float:
    values = [int(count) for count in counts if int(count) > 0]
    total = sum(values)
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in values)


def indices_near(indices: list[int], length: int, window: int) -> set[int]:
    output: set[int] = set()
    for index in indices:
        for candidate in range(max(0, index - window), min(length, index + window + 1)):
            output.add(candidate)
    return output


def enrichment(items: set[int], zone: set[int], exposure: float) -> float:
    if not items or exposure == 0:
        return 0.0
    return (len(items & zone) / len(items)) / exposure


def z_at_key(values: dict[int, float], key: int) -> float:
    vals = list(values.values())
    sd = pstdev(vals) if len(vals) > 1 else 0.0
    return (values[key] - mean(vals)) / sd if sd and key in values else 0.0


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    weight = pos - lo
    return sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight


def cohens_d(a: list[float], b: list[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled = math.sqrt((pstdev(a) ** 2 + pstdev(b) ** 2) / 2)
    return (mean(b) - mean(a)) / pooled if pooled else 0.0


def draw_piece_overlay(
    piece_rows: list[dict],
    profile_rows: list[dict],
    output: Path,
    title: str,
) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [float(row["surprisal"]) for row in piece_rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    by_piece: dict[str, list[dict]] = defaultdict(list)
    for row in piece_rows:
        by_piece[row["piece_id"]].append(row)
    body = axis_body(width, height, left, right, top, bottom, title, "Normalized piece time", "Surprisal (bits)")
    for _, rows in sorted(by_piece.items()):
        rows = sorted(rows, key=lambda row: int(row["time_bin"]))
        source = rows[0]["source"]
        points = " ".join(
            f"{sx(float(row['normalized_time']), left, width-right):.1f},{sy(float(row['surprisal']), ymin, ymax, top, height-bottom):.1f}"
            for row in rows
        )
        body.append(
            f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="1" opacity="0.16"/>'
        )
    for source_rows in group_rows(profile_rows, "source").values():
        source_rows = sorted(source_rows, key=lambda row: int(row["time_bin"]))
        source = source_rows[0]["source"]
        points = " ".join(
            f"{sx(float(row['normalized_time']), left, width-right):.1f},{sy(float(row['mean_surprisal']), ymin, ymax, top, height-bottom):.1f}"
            for row in source_rows
        )
        body.append(
            f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="4"/>'
        )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_profile(rows: list[dict], output: Path, title: str, value_key: str, y_label: str) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [float(row[value_key]) for row in rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    body = axis_body(width, height, left, right, top, bottom, title, "Normalized piece time", y_label)
    for source_rows in group_rows(rows, "source").values():
        source_rows = sorted(source_rows, key=lambda row: int(row["time_bin"]))
        source = source_rows[0]["source"]
        points = " ".join(
            f"{sx(float(row['normalized_time']), left, width-right):.1f},{sy(float(row[value_key]), ymin, ymax, top, height-bottom):.1f}"
            for row in source_rows
        )
        body.append(
            f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="4"/>'
        )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_difference(rows: list[dict], output: Path, title: str, value_key: str) -> None:
    sources = sorted({row["source"] for row in rows})
    if len(sources) != 2:
        output.write_text("", encoding="utf-8")
        return
    a, b = sources
    by_key = {(row["source"], int(row["time_bin"])): row for row in rows}
    bins = sorted({int(row["time_bin"]) for row in rows})
    diffs = [
        float(by_key[(b, bin_id)][value_key]) - float(by_key[(a, bin_id)][value_key])
        for bin_id in bins
        if (a, bin_id) in by_key and (b, bin_id) in by_key
    ]
    width, height = 920, 500
    left, right, top, bottom = 80, 50, 70, 80
    ymin, ymax = min(min(diffs) - 0.3, 0), max(max(diffs) + 0.3, 0)
    zero = sy(0, ymin, ymax, top, height-bottom)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
        f'<line x1="{left}" y1="{zero:.1f}" x2="{width-right}" y2="{zero:.1f}" stroke="#777" stroke-dasharray="5 5"/>',
        '<text class="label" x="350" y="465">Normalized piece time</text>',
        f'<text class="label" transform="translate(24 315) rotate(-90)">{b} minus {a}</text>',
    ]
    points = " ".join(
        f"{sx(i / max(1, len(diffs)-1), left, width-right):.1f},{sy(value, ymin, ymax, top, height-bottom):.1f}"
        for i, value in enumerate(diffs)
    )
    body.append(f'<polyline points="{points}" fill="none" stroke="#7a4fb3" stroke-width="3"/>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_profile(rows: list[dict], output: Path, title: str) -> None:
    width, height = 980, 560
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [
        float(row[key])
        for row in rows
        for key in ("mean_ngram", "mean_unigram", "mean_shuffled")
    ]
    ymin, ymax = min(all_values) - 0.4, max(all_values) + 0.4
    rels = sorted({int(row["relative_event"]) for row in rows})
    body = boundary_axis_body(width, height, left, right, top, bottom, title, "Surprisal (bits)", rels)
    dash = {"mean_ngram": "", "mean_unigram": "6 4", "mean_shuffled": "2 4"}
    for source_rows in group_rows(rows, "source").values():
        source_rows = sorted(source_rows, key=lambda row: int(row["relative_event"]))
        source = source_rows[0]["source"]
        for key in ("mean_ngram", "mean_unigram", "mean_shuffled"):
            points = " ".join(
                f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row[key]), ymin, ymax, top, height-bottom):.1f}"
                for row in source_rows
            )
            dash_attr = f' stroke-dasharray="{dash[key]}"' if dash[key] else ""
            opacity = "0.95" if key == "mean_ngram" else "0.60"
            body.append(
                f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="3" opacity="{opacity}"{dash_attr}/>'
            )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_single_metric(
    rows: list[dict], output: Path, title: str, value_key: str, y_label: str
) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [float(row[value_key]) for row in rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    rels = sorted({int(row["relative_event"]) for row in rows})
    body = boundary_axis_body(width, height, left, right, top, bottom, title, y_label, rels)
    for source_rows in group_rows(rows, "source").values():
        source_rows = sorted(source_rows, key=lambda row: int(row["relative_event"]))
        source = source_rows[0]["source"]
        points = " ".join(
            f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row[value_key]), ymin, ymax, top, height-bottom):.1f}"
            for row in source_rows
        )
        body.append(f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="4"/>')
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_rates(rows: list[dict], output: Path, title: str) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    rels = sorted({int(row["relative_event"]) for row in rows})
    keys = [("high_state_rate", ""), ("local_peak_rate", "6 4"), ("changepoint_rate", "2 4")]
    all_values = [float(row[key]) for row in rows for key, _ in keys]
    ymin, ymax = 0.0, max(all_values) + 0.02
    body = boundary_axis_body(width, height, left, right, top, bottom, title, "Event rate", rels)
    body.append('<text class="small" x="650" y="88">solid=high state, dashed=peak, dotted=changepoint</text>')
    for source_rows in group_rows(rows, "source").values():
        source_rows = sorted(source_rows, key=lambda row: int(row["relative_event"]))
        source = source_rows[0]["source"]
        for key, dash in keys:
            points = " ".join(
                f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row[key]), ymin, ymax, top, height-bottom):.1f}"
                for row in source_rows
            )
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            body.append(
                f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="3" opacity="0.85"{dash_attr}/>'
            )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_piece_overlay(
    piece_rows: list[dict], profile_rows: list[dict], output: Path, title: str
) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [float(row["mean_ngram"]) for row in piece_rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    rels = sorted({int(row["relative_event"]) for row in piece_rows})
    body = boundary_axis_body(width, height, left, right, top, bottom, title, "Surprisal (bits)", rels)
    for rows in group_rows(piece_rows, "piece_id").values():
        rows = sorted(rows, key=lambda row: int(row["relative_event"]))
        source = rows[0]["source"]
        points = " ".join(
            f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row['mean_ngram']), ymin, ymax, top, height-bottom):.1f}"
            for row in rows
        )
        body.append(f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="1" opacity="0.18"/>')
    for rows in group_rows(profile_rows, "source").values():
        rows = sorted(rows, key=lambda row: int(row["relative_event"]))
        source = rows[0]["source"]
        points = " ".join(
            f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row['mean_ngram']), ymin, ymax, top, height-bottom):.1f}"
            for row in rows
        )
        body.append(f'<polyline points="{points}" fill="none" stroke="{color(source)}" stroke-width="4"/>')
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_effect_bars(rows: list[dict], output: Path, title: str, value_key: str) -> None:
    if not rows:
        output.write_text("", encoding="utf-8")
        return
    keep = sorted(rows, key=lambda row: abs(float(row[value_key])), reverse=True)[:10]
    width, height = 980, max(420, 110 + len(keep) * 44)
    left, right, top, bottom = 310, 80, 65, 60
    values = [float(row[value_key]) for row in keep]
    limit = max(0.25, max(abs(value) for value in values) * 1.15)
    zero = xscale(0, -limit, limit, left, width-right)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{height-bottom}"/>',
        '<text class="small" x="620" y="88">positive = JTC higher than DCML</text>',
    ]
    row_gap = (height - top - bottom) / max(1, len(keep))
    for index, row in enumerate(keep):
        value = float(row[value_key])
        y = top + row_gap * index + row_gap * 0.5
        end = xscale(value, -limit, limit, left, width-right)
        x = min(zero, end)
        bar_width = max(1, abs(end - zero))
        fill = "#c46a32" if value >= 0 else "#2f6f9f"
        body.append(f'<text class="small" x="25" y="{y+4:.1f}">{escape(row["feature"])}</text>')
        body.append(f'<rect x="{x:.1f}" y="{y-10:.1f}" width="{bar_width:.1f}" height="20" fill="{fill}" rx="2"/>')
        body.append(f'<text class="small" x="{end + (8 if value >= 0 else -44):.1f}" y="{y+4:.1f}">{value:.2f}</text>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_index(output: Path) -> None:
    svgs = sorted(path.name for path in output.glob("*.svg"))
    links = "\n".join(f'<li><a href="{name}">{name}</a></li>' for name in svgs)
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>RQ1/RQ2 Time-Series Figures</title>
<body style="font-family:Arial,Helvetica,sans-serif;max-width:900px;margin:40px auto;line-height:1.5">
<h1>RQ1/RQ2 Time-Series Figures</h1>
<ul>
{links}
</ul>
</body>
</html>
"""
    (output / "index.html").write_text(html, encoding="utf-8")


def write_summary(
    output: Path,
    args: argparse.Namespace,
    coverage_rows: list[dict],
    thresholds: dict[str, float],
    rq1_shape: list[dict],
    rq1_effects: list[dict],
    rq2_shape: list[dict],
    rq2_effects: list[dict],
) -> None:
    lines = [
        "# RQ1/RQ2 Time-Series Summary",
        "",
        f"Events: `{args.events}`",
        f"High-surprisal threshold quantile: `{args.threshold_quantile}`",
        "",
        "## Source Thresholds",
        "",
    ]
    for source, threshold in sorted(thresholds.items()):
        lines.append(f"- `{source}`: {threshold:.3f}")
    lines.extend(["", "## RQ1 Mean-Scale Caveat Diagnostics", ""])
    for row in coverage_rows:
        lines.append(
            f"- `{row['source']}`: train_tokens={int(row['train_tokens'])}, "
            f"vocab={int(row['vocab_size_without_unk'])}, "
            f"unique_pitches={int(row['unique_pitch_count'])}, "
            f"contexts={int(row['context_count'])}, "
            f"OOV={float(row['unknown_token_rate']):.4f}, "
            f"backoff={float(row['backoff_event_rate']):.4f}, "
            f"full_context_hit={float(row['full_context_hit_rate']):.4f}"
        )
    lines.extend(["", "## RQ1 Whole-Piece Curve Shape", ""])
    for row in rq1_shape:
        detail = f"- `{row['metric']}`: {float(row['value']):.3f}"
        if "position" in row:
            detail += f" at position {row['position']}"
        lines.append(detail)
    lines.extend(["", "## RQ1 Time-Structure Effects", ""])
    for row in rq1_effects:
        lines.append(
            f"- `{row['feature']}`: dcml={float(row['a_mean']):.3f}, "
            f"jtc={float(row['b_mean']):.3f}, "
            f"jtc-dcml={float(row['b_minus_a']):.3f}, "
            f"d={float(row['cohens_d_b_minus_a']):.3f}"
        )
    lines.extend(["", "## RQ2 Boundary Curve Shape", ""])
    for row in rq2_shape:
        detail = f"- `{row['metric']}`: {float(row['value']):.3f}"
        if "position" in row:
            detail += f" at rel {row['position']}"
        lines.append(detail)
    lines.extend(["", "## RQ2 Boundary Time-Structure Effects", ""])
    for row in rq2_effects:
        lines.append(
            f"- `{row['feature']}`: dcml={float(row['a_mean']):.3f}, "
            f"jtc={float(row['b_mean']):.3f}, "
            f"jtc-dcml={float(row['b_minus_a']):.3f}, "
            f"d={float(row['cohens_d_b_minus_a']):.3f}"
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def group_rows(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return dict(grouped)


def axis_body(
    width: int,
    height: int,
    left: int,
    right: int,
    top: int,
    bottom: int,
    title: str,
    x_label: str,
    y_label: str,
) -> list[str]:
    return [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
        f'<text class="label" x="{left+300}" y="{height-35}">{escape(x_label)}</text>',
        f'<text class="label" transform="translate(24 {top+260}) rotate(-90)">{escape(y_label)}</text>',
    ]


def boundary_axis_body(
    width: int,
    height: int,
    left: int,
    right: int,
    top: int,
    bottom: int,
    title: str,
    y_label: str,
    rels: list[int],
) -> list[str]:
    x0 = rel_sx(0, rels, left, width-right)
    return [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
        f'<line x1="{x0:.1f}" y1="{top}" x2="{x0:.1f}" y2="{height-bottom}" stroke="#333" stroke-width="1.4" stroke-dasharray="5 5"/>',
        f'<text class="label" x="{left+300}" y="{height-35}">Event position relative to boundary</text>',
        f'<text class="label" transform="translate(24 {top+260}) rotate(-90)">{escape(y_label)}</text>',
    ]


def sx(x: float, left: float, right: float) -> float:
    return left + x * (right - left)


def rel_sx(rel: int, rels: list[int], left: float, right: float) -> float:
    return left + (rel - min(rels)) / max(1, max(rels) - min(rels)) * (right - left)


def sy(value: float, ymin: float, ymax: float, top: float, bottom: float) -> float:
    return top + (ymax - value) / (ymax - ymin) * (bottom - top)


def xscale(value: float, xmin: float, xmax: float, left: float, right: float) -> float:
    return left + (value - xmin) / (xmax - xmin) * (right - left)


def color(source: str) -> str:
    return {"dcml": "#2f6f9f", "jtc": "#c46a32"}.get(source, "#555")


def legend(body: list[str], x: int, y: int) -> None:
    for index, (source, label) in enumerate((("dcml", "DCML classical"), ("jtc", "JTC jazz"))):
        yy = y + index * 26
        body.append(f'<line x1="{x}" y1="{yy}" x2="{x+28}" y2="{yy}" stroke="{color(source)}" stroke-width="4"/>')
        body.append(f'<text class="small" x="{x+36}" y="{yy+4}">{label}</text>')


def svg_wrap(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #1d252c; }}
    .title {{ font-size: 21px; font-weight: 700; }}
    .label {{ font-size: 13px; }}
    .small {{ font-size: 11px; fill: #52606d; }}
    .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
  </style>
{body}
</svg>
"""


def escape(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
