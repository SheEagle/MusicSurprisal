from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, group_by_piece, token_function
from music_surprisal.ngram import NGramModel, START, shuffled_sequences
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Within-DCML period time-series analysis."
    )
    parser.add_argument("--events", default="data/events_dcml_classical.csv")
    parser.add_argument(
        "--metadata",
        default="datasets/raw/dcml/dcml_corpora/dcml_corpora.metadata.tsv",
    )
    parser.add_argument(
        "--output",
        default="output/formal_dcml_jtc_all_rq/dcml_period_time_series",
    )
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--bins", type=int, default=100)
    parser.add_argument("--boundary-window", type=int, default=12)
    parser.add_argument("--local-window", type=int, default=16)
    parser.add_argument("--threshold-quantile", type=float, default=0.90)
    parser.add_argument(
        "--include-late",
        action="store_true",
        help="Include late/impressionist pieces in inferential comparisons.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    period_meta = load_period_metadata(Path(args.metadata))
    events = attach_periods(load_events(args.events, sources={"dcml"}), period_meta)
    scoped_events = [
        event
        for event in events
        if event.genre in {"classical_period", "romantic_period"}
        or (args.include_late and event.genre == "late_period")
    ]
    if not scoped_events:
        raise ValueError("No DCML period-tagged events found")

    metadata_rows = metadata_summary(period_meta, scoped_events)
    rows = build_unified_surprisal_rows(
        scoped_events, order=args.order, token_kind=args.token_kind
    )
    by_piece = group_rows_by_piece(rows)
    thresholds = period_thresholds(rows, args.threshold_quantile)
    cutpoints = pooled_cutpoints(rows, states=5)

    profile_rows = normalized_period_profile(by_piece, bins=args.bins)
    local_rows = local_variance_period_profile(
        by_piece, bins=args.bins, window=args.local_window
    )
    piece_features = period_piece_features(
        by_piece,
        thresholds=thresholds,
        cutpoints=cutpoints,
        local_window=args.local_window,
    )
    effects = period_effects(piece_features, period_feature_names())
    shape_rows = curve_shape_distance(profile_rows, "mean_surprisal")

    (
        boundary_piece_curves,
        boundary_profile,
        boundary_features,
    ) = period_boundary_analysis(
        by_piece,
        thresholds=thresholds,
        local_window=args.local_window,
        boundary_window=args.boundary_window,
    )
    boundary_effects = period_effects(boundary_features, boundary_feature_names())
    boundary_shape = curve_shape_distance(boundary_profile, "mean_ngram")

    write_csv(output / "dcml_period_metadata_summary.csv", metadata_rows)
    write_csv(output / "dcml_period_surprisal_events_sample.csv", rows[:100000])
    write_csv(output / "dcml_period_normalized_profile.csv", profile_rows)
    write_csv(output / "dcml_period_local_variance_profile.csv", local_rows)
    write_csv(output / "dcml_period_piece_time_structure_features.csv", piece_features)
    write_csv(output / "dcml_period_time_structure_effects.csv", effects)
    write_csv(output / "dcml_period_curve_shape_distance_summary.csv", shape_rows)
    write_csv(output / "dcml_period_boundary_piece_curves.csv", boundary_piece_curves)
    write_csv(output / "dcml_period_boundary_profile.csv", boundary_profile)
    write_csv(output / "dcml_period_boundary_features.csv", boundary_features)
    write_csv(output / "dcml_period_boundary_effects.csv", boundary_effects)
    write_csv(output / "dcml_period_boundary_shape_distance_summary.csv", boundary_shape)

    draw_profile(
        profile_rows,
        output / "dcml_period_mean_surprisal_profile.svg",
        "DCML period mean surprisal profile",
        "mean_surprisal",
        "Surprisal (bits)",
        "normalized_time",
        "time_bin",
    )
    draw_profile(
        local_rows,
        output / "dcml_period_local_variance_profile.svg",
        "DCML period local volatility profile",
        "mean_local_variance",
        "Local variance",
        "normalized_time",
        "time_bin",
    )
    draw_difference(
        profile_rows,
        output / "dcml_period_profile_difference.svg",
        "Romantic minus Classical profile",
        "mean_surprisal",
        x_key="normalized_time",
        position_key="time_bin",
    )
    draw_effect_bars(
        effects,
        output / "dcml_period_time_structure_effects.svg",
        "DCML period time-structure effects",
    )
    draw_boundary_profile(
        boundary_profile,
        output / "dcml_period_boundary_profile.svg",
        "DCML period boundary-aligned profile",
    )
    draw_boundary_rates(
        boundary_profile,
        output / "dcml_period_boundary_event_rates.svg",
        "DCML period high states, peaks, and changepoints",
    )
    draw_effect_bars(
        boundary_effects,
        output / "dcml_period_boundary_effects.svg",
        "DCML period boundary effects",
    )
    write_summary(
        output / "DCML_PERIOD_TIME_SERIES_SUMMARY.md",
        args,
        metadata_rows,
        thresholds,
        shape_rows,
        effects,
        boundary_shape,
        boundary_effects,
    )
    write_index(output)
    print(f"Wrote DCML period analysis to {output}")


def load_period_metadata(path: Path) -> dict[tuple[str, str], dict]:
    output: dict[tuple[str, str], dict] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            start = parse_year(row.get("composed_start", ""))
            end = parse_year(row.get("composed_end", ""))
            year = start if start is not None else end
            output[(row["corpus"], row["piece"])] = {
                "corpus": row["corpus"],
                "piece": row["piece"],
                "composer": clean(row.get("composer") or row.get("composer_text")),
                "work_title": clean(row.get("workTitle") or row.get("title_text")),
                "composed_start": start,
                "composed_end": end,
                "period": period_from_corpus_or_year(row["corpus"], year),
                "period_year": year if year is not None else "",
            }
    return output


def attach_periods(
    events: list[Event], period_meta: dict[tuple[str, str], dict]
) -> list[Event]:
    output: list[Event] = []
    for event in events:
        corpus, piece = parse_dcml_piece_id(event.piece_id)
        meta = lookup_period_meta(period_meta, corpus, piece)
        if not meta:
            continue
        output.append(
            Event(
                piece_id=event.piece_id,
                source=event.source,
                genre=meta["period"],
                is_ai=event.is_ai,
                split=event.split,
                onset=event.onset,
                pitch=event.pitch,
                duration=event.duration,
                chord=event.chord,
                boundary=event.boundary,
            )
        )
    return output


def lookup_period_meta(
    period_meta: dict[tuple[str, str], dict], corpus: str, piece: str
) -> dict | None:
    candidates = [(corpus, piece)]
    alias = corpus_aliases().get(corpus)
    if alias:
        candidates.append((alias, piece))
        candidates.append((alias, piece_prefixes().get(corpus, "") + piece))
        prefix = piece_prefixes().get(corpus, "")
        if prefix and piece.startswith(prefix):
            candidates.append((alias, piece[len(prefix) :]))
    for candidate in candidates:
        if candidate in period_meta:
            return period_meta[candidate]
    return None


def corpus_aliases() -> dict[str, str]:
    return {
        "beethoven": "beethoven_piano_sonatas",
        "chopin": "chopin_mazurkas",
        "debussy": "debussy_suite_bergamasque",
        "dvorak": "dvorak_silhouettes",
        "grieg": "grieg_lyric_pieces",
        "liszt": "liszt_pelerinage",
        "medtner": "medtner_tales",
        "mozart": "mozart_piano_sonatas",
        "schumann": "schumann_kinderszenen",
        "tchaikovsky": "tchaikovsky_seasons",
    }


def piece_prefixes() -> dict[str, str]:
    return {
        "beethoven": "piano_sonatas_",
        "chopin": "mazurkas_",
        "debussy": "suite_bergamasque_",
        "dvorak": "silhouettes_",
        "grieg": "lyric_pieces_",
        "liszt": "pelerinage_",
        "medtner": "tales_",
        "mozart": "piano_sonatas_",
        "schumann": "kinderszenen_",
        "tchaikovsky": "seasons_",
    }


def parse_dcml_piece_id(piece_id: str) -> tuple[str, str]:
    parts = piece_id.split("_", 2)
    if len(parts) != 3 or parts[0] != "dcml":
        raise ValueError(f"Unexpected DCML piece_id: {piece_id}")
    return parts[1], parts[2]


def parse_year(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    digits = "".join(ch for ch in value[:4] if ch.isdigit())
    return int(digits) if len(digits) == 4 else None


def period_from_corpus_or_year(corpus: str, year: int | None) -> str:
    manual = corpus_periods().get(corpus)
    if manual:
        return manual
    if year is None:
        return "unknown_period"
    if year < 1820:
        return "classical_period"
    if year < 1890:
        return "romantic_period"
    return "late_period"


def corpus_periods() -> dict[str, str]:
    return {
        "ABC": "classical_period",
        "beethoven_piano_sonatas": "classical_period",
        "corelli": "pre_classical_period",
        "mozart_piano_sonatas": "classical_period",
        "chopin_mazurkas": "romantic_period",
        "dvorak_silhouettes": "romantic_period",
        "grieg_lyric_pieces": "romantic_period",
        "liszt_pelerinage": "romantic_period",
        "medtner_tales": "romantic_period",
        "schumann_kinderszenen": "romantic_period",
        "tchaikovsky_seasons": "romantic_period",
        "debussy_suite_bergamasque": "late_period",
    }


def clean(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def metadata_summary(period_meta: dict[tuple[str, str], dict], events: list[Event]) -> list[dict]:
    piece_event_counts = Counter(event.piece_id for event in events)
    rows: list[dict] = []
    for piece_id, events_count in sorted(piece_event_counts.items()):
        corpus, piece = parse_dcml_piece_id(piece_id)
        meta = lookup_period_meta(period_meta, corpus, piece)
        if not meta:
            continue
        rows.append(
            {
                "piece_id": piece_id,
                "corpus": corpus,
                "piece": piece,
                "period": meta["period"],
                "period_year": meta["period_year"],
                "composer": meta["composer"],
                "work_title": meta["work_title"],
                "events": events_count,
            }
        )
    return rows


def build_unified_surprisal_rows(
    events: list[Event], *, order: int, token_kind: str
) -> list[dict]:
    train = [event for event in events if event.split == "train"]
    eval_events = [event for event in events if event.split != "train"]
    if not train or not eval_events:
        raise ValueError("Need train and eval events")
    to_token = token_function(token_kind)
    train_sequences = [
        [to_token(event) for event in piece_events]
        for piece_events in group_by_piece(train).values()
    ]
    ngram = NGramModel(order=order).fit(train_sequences)
    unigram = NGramModel(order=1).fit(train_sequences)
    shuffled = NGramModel(order=order).fit(shuffled_sequences(train_sequences, seed=13))
    rows: list[dict] = []
    for piece_id, piece_events in group_by_piece(eval_events).items():
        corpus, piece = parse_dcml_piece_id(piece_id)
        tokens = [to_token(event) for event in piece_events]
        ngram_values = ngram.sequence_surprisal(tokens)
        unigram_values = unigram.sequence_surprisal(tokens)
        shuffled_values = shuffled.sequence_surprisal(tokens)
        for index, event in enumerate(piece_events):
            rows.append(
                {
                    "piece_id": piece_id,
                    "corpus": corpus,
                    "piece": piece,
                    "period": event.genre,
                    "source": event.genre,
                    "genre": event.genre,
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


def group_rows_by_piece(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(row)
    for piece_rows in grouped.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
    return dict(grouped)


def period_thresholds(rows: list[dict], q: float) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["period"]].append(float(row["surprisal_ngram"]))
    return {period: percentile(sorted(values), q) for period, values in grouped.items()}


def pooled_cutpoints(rows: list[dict], states: int) -> list[float]:
    values = sorted(float(row["surprisal_ngram"]) for row in rows)
    return [percentile(values, index / states) for index in range(1, states)]


def normalized_period_profile(by_piece: dict[str, list[dict]], bins: int) -> list[dict]:
    accum: dict[tuple[str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        profile = resample(values, bins)
        period = piece_rows[0]["period"]
        for index, value in enumerate(profile):
            accum[(period, index)].append(value)
    return profile_rows(accum, "mean_surprisal", "sd_surprisal", bins)


def local_variance_period_profile(
    by_piece: dict[str, list[dict]], bins: int, window: int
) -> list[dict]:
    accum: dict[tuple[str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        profile = resample(rolling_variance(values, window), bins)
        period = piece_rows[0]["period"]
        for index, value in enumerate(profile):
            accum[(period, index)].append(value)
    return profile_rows(accum, "mean_local_variance", "sd_local_variance", bins)


def profile_rows(
    accum: dict[tuple[str, int], list[float]],
    mean_name: str,
    sd_name: str,
    bins: int,
) -> list[dict]:
    rows: list[dict] = []
    for (period, index), values in sorted(accum.items()):
        rows.append(
            {
                "period": period,
                "source": period,
                "time_bin": index,
                "normalized_time": index / max(1, bins - 1),
                "pieces": len(values),
                mean_name: mean(values),
                sd_name: pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return rows


def period_piece_features(
    by_piece: dict[str, list[dict]],
    *,
    thresholds: dict[str, float],
    cutpoints: list[float],
    local_window: int,
) -> list[dict]:
    rows: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < 4:
            continue
        period = piece_rows[0]["period"]
        threshold = thresholds[period]
        local = rolling_variance(values, local_window)
        peaks = local_peaks(values, threshold)
        cps = simple_changepoints(values, threshold, local_window)
        high_runs, low_runs = binary_runs([value >= threshold for value in values])
        states = [discretize(value, cutpoints) for value in values]
        transitions = list(zip(states, states[1:]))
        transition_counts = Counter(transitions)
        rows.append(
            {
                "piece_id": piece_id,
                "period": period,
                "source": period,
                "corpus": piece_rows[0]["corpus"],
                "events": len(values),
                "mean_surprisal": mean(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
                "curve_range": max(values) - min(values),
                "end_minus_start": zone_mean(values, 0.90, 1.00)
                - zone_mean(values, 0.00, 0.10),
                "linear_slope": linear_slope(values),
                "mean_local_variance": mean(local),
                "max_local_variance": max(local),
                "peak_rate": len(peaks) / len(values),
                "changepoint_rate": len(cps) / len(values),
                "mean_high_run": mean(high_runs) if high_runs else 0.0,
                "max_high_run": max(high_runs) if high_runs else 0,
                "state_entropy": empirical_entropy(states),
                "entropy_rate_order1": conditional_entropy(states, 1),
                "entropy_rate_order2": conditional_entropy(states, 2),
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
    return rows


def period_boundary_analysis(
    by_piece: dict[str, list[dict]],
    *,
    thresholds: dict[str, float],
    local_window: int,
    boundary_window: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    piece_curve_rows: list[dict] = []
    piece_feature_rows: list[dict] = []
    accum: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(
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
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < boundary_window * 2 + 1:
            continue
        period = piece_rows[0]["period"]
        threshold = thresholds[period]
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
                bucket = accum[(period, rel)]
                rel_bucket = rel_values[rel]
                for target in (bucket, rel_bucket):
                    target["ngram"].append(ngram)
                    target["unigram"].append(unigram)
                    target["shuffled"].append(shuffled)
                    target["local_variance"].append(local[index])
                    target["high"].append(float(index in high))
                    target["peak"].append(float(index in peaks))
                    target["changepoint"].append(float(index in cps))
        curve = {
            rel: {key: mean(values) for key, values in rel_bucket.items()}
            for rel, rel_bucket in rel_values.items()
        }
        for rel, row in sorted(curve.items()):
            piece_curve_rows.append(
                {
                    "piece_id": piece_id,
                    "period": period,
                    "source": period,
                    "corpus": piece_rows[0]["corpus"],
                    "boundaries": len(boundaries),
                    "relative_event": rel,
                    "mean_ngram": row["ngram"],
                    "mean_unigram": row["unigram"],
                    "mean_shuffled": row["shuffled"],
                    "mean_local_variance": row["local_variance"],
                    "high_state_rate": row["high"],
                    "local_peak_rate": row["peak"],
                    "changepoint_rate": row["changepoint"],
                    "mean_delta_ngram_unigram": row["ngram"] - row["unigram"],
                    "mean_delta_ngram_shuffled": row["ngram"] - row["shuffled"],
                }
            )
        piece_feature_rows.append(
            boundary_piece_features(
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
    profile: list[dict] = []
    for (period, rel), bucket in sorted(accum.items()):
        profile.append(
            {
                "period": period,
                "source": period,
                "relative_event": rel,
                "n": len(bucket["ngram"]),
                "mean_ngram": mean(bucket["ngram"]),
                "mean_unigram": mean(bucket["unigram"]),
                "mean_shuffled": mean(bucket["shuffled"]),
                "mean_local_variance": mean(bucket["local_variance"]),
                "high_state_rate": mean(bucket["high"]),
                "local_peak_rate": mean(bucket["peak"]),
                "changepoint_rate": mean(bucket["changepoint"]),
                "mean_delta_ngram_unigram": mean(bucket["ngram"]) - mean(bucket["unigram"]),
                "mean_delta_ngram_shuffled": mean(bucket["ngram"]) - mean(bucket["shuffled"]),
            }
        )
    return piece_curve_rows, profile, piece_feature_rows


def boundary_piece_features(
    piece_id: str,
    meta: dict,
    curve: dict[int, dict[str, float]],
    values: list[float],
    boundaries: list[int],
    high: set[int],
    peaks: set[int],
    cps: set[int],
    window: int,
) -> dict:
    rels = sorted(curve)
    ngram = {rel: curve[rel]["ngram"] for rel in rels}
    local = {rel: curve[rel]["local_variance"] for rel in rels}
    pre = [ngram[rel] for rel in range(-window, 0) if rel in ngram]
    post = [ngram[rel] for rel in range(0, window + 1) if rel in ngram]
    core_rels = [rel for rel in (-2, -1, 0, 1, 2) if rel in ngram]
    far_rels = [rel for rel in rels if rel in {-window, -window + 1, window - 1, window}]
    peak_rel = max(rels, key=lambda rel: ngram[rel])
    core_zone = indices_near(boundaries, len(values), 2)
    exposure = len(core_zone) / len(values) if values else 0.0
    return {
        "piece_id": piece_id,
        "period": meta["period"],
        "source": meta["period"],
        "corpus": meta["corpus"],
        "events": len(values),
        "boundaries": len(boundaries),
        "boundary_curve_range": max(ngram.values()) - min(ngram.values()),
        "boundary_value": ngram.get(0, 0.0),
        "peak_relative_event": peak_rel,
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
        "high_event_boundary_enrichment": enrichment(high, core_zone, exposure),
        "peak_boundary_enrichment": enrichment(peaks, core_zone, exposure),
        "changepoint_boundary_enrichment": enrichment(cps, core_zone, exposure),
    }


def period_feature_names() -> list[str]:
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


def boundary_feature_names() -> list[str]:
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
        "high_event_boundary_enrichment",
        "peak_boundary_enrichment",
        "changepoint_boundary_enrichment",
    ]


def period_effects(rows: list[dict], features: list[str]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["period"]].append(row)
    if "classical_period" not in grouped or "romantic_period" not in grouped:
        return []
    a, b = "classical_period", "romantic_period"
    output: list[dict] = []
    for feature in features:
        av = [float(row[feature]) for row in grouped[a]]
        bv = [float(row[feature]) for row in grouped[b]]
        output.append(
            {
                "period_a": a,
                "period_b": b,
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
    a, b = "classical_period", "romantic_period"
    position_key = "time_bin" if "time_bin" in rows[0] else "relative_event"
    by_key = {(row["period"], int(row[position_key])): row for row in rows}
    positions = sorted({int(row[position_key]) for row in rows})
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
        {"metric": "mean_romantic_minus_classical", "value": mean(diffs)},
        {"metric": "rms_curve_difference", "value": math.sqrt(mean(x * x for x in diffs))},
        {"metric": "max_romantic_excess", "value": diffs[max_idx], "position": positions[max_idx]},
        {"metric": "max_classical_excess", "value": diffs[min_idx], "position": positions[min_idx]},
        {"metric": "signed_area_romantic_minus_classical", "value": mean(diffs)},
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
    selected: list[int] = []
    last = -10**9
    for index in candidates:
        if index - last >= window:
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


def draw_profile(
    rows: list[dict],
    output: Path,
    title: str,
    value_key: str,
    y_label: str,
    x_key: str,
    position_key: str,
) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 165, 70, 80
    all_values = [float(row[value_key]) for row in rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    body = axis_body(width, height, left, right, top, bottom, title, "Normalized piece time", y_label)
    for period_rows in group_rows(rows, "period").values():
        period_rows = sorted(period_rows, key=lambda row: int(row[position_key]))
        period = period_rows[0]["period"]
        points = " ".join(
            f"{sx(float(row[x_key]), left, width-right):.1f},{sy(float(row[value_key]), ymin, ymax, top, height-bottom):.1f}"
            for row in period_rows
        )
        body.append(f'<polyline points="{points}" fill="none" stroke="{color(period)}" stroke-width="4"/>')
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_difference(
    rows: list[dict],
    output: Path,
    title: str,
    value_key: str,
    *,
    x_key: str,
    position_key: str,
) -> None:
    a, b = "classical_period", "romantic_period"
    by_key = {(row["period"], int(row[position_key])): row for row in rows}
    positions = sorted({int(row[position_key]) for row in rows})
    diffs = [
        float(by_key[(b, pos)][value_key]) - float(by_key[(a, pos)][value_key])
        for pos in positions
        if (a, pos) in by_key and (b, pos) in by_key
    ]
    if not diffs:
        output.write_text("", encoding="utf-8")
        return
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
        '<text class="label" transform="translate(24 315) rotate(-90)">Romantic minus Classical</text>',
    ]
    points = " ".join(
        f"{sx(i / max(1, len(diffs)-1), left, width-right):.1f},{sy(value, ymin, ymax, top, height-bottom):.1f}"
        for i, value in enumerate(diffs)
    )
    body.append(f'<polyline points="{points}" fill="none" stroke="#7a4fb3" stroke-width="3"/>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_profile(rows: list[dict], output: Path, title: str) -> None:
    width, height = 980, 560
    left, right, top, bottom = 80, 165, 70, 80
    all_values = [
        float(row[key])
        for row in rows
        for key in ("mean_ngram", "mean_unigram", "mean_shuffled")
    ]
    ymin, ymax = min(all_values) - 0.4, max(all_values) + 0.4
    rels = sorted({int(row["relative_event"]) for row in rows})
    body = boundary_axis_body(width, height, left, right, top, bottom, title, "Surprisal (bits)", rels)
    dash = {"mean_ngram": "", "mean_unigram": "6 4", "mean_shuffled": "2 4"}
    for period_rows in group_rows(rows, "period").values():
        period_rows = sorted(period_rows, key=lambda row: int(row["relative_event"]))
        period = period_rows[0]["period"]
        for key in ("mean_ngram", "mean_unigram", "mean_shuffled"):
            points = " ".join(
                f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row[key]), ymin, ymax, top, height-bottom):.1f}"
                for row in period_rows
            )
            dash_attr = f' stroke-dasharray="{dash[key]}"' if dash[key] else ""
            opacity = "0.95" if key == "mean_ngram" else "0.60"
            body.append(
                f'<polyline points="{points}" fill="none" stroke="{color(period)}" stroke-width="3" opacity="{opacity}"{dash_attr}/>'
            )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_boundary_rates(rows: list[dict], output: Path, title: str) -> None:
    width, height = 980, 540
    left, right, top, bottom = 80, 165, 70, 80
    rels = sorted({int(row["relative_event"]) for row in rows})
    keys = [("high_state_rate", ""), ("local_peak_rate", "6 4"), ("changepoint_rate", "2 4")]
    all_values = [float(row[key]) for row in rows for key, _ in keys]
    ymin, ymax = 0.0, max(all_values) + 0.02
    body = boundary_axis_body(width, height, left, right, top, bottom, title, "Event rate", rels)
    body.append('<text class="small" x="580" y="88">solid=high state, dashed=peak, dotted=changepoint</text>')
    for period_rows in group_rows(rows, "period").values():
        period_rows = sorted(period_rows, key=lambda row: int(row["relative_event"]))
        period = period_rows[0]["period"]
        for key, dash in keys:
            points = " ".join(
                f"{rel_sx(int(row['relative_event']), rels, left, width-right):.1f},{sy(float(row[key]), ymin, ymax, top, height-bottom):.1f}"
                for row in period_rows
            )
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            body.append(
                f'<polyline points="{points}" fill="none" stroke="{color(period)}" stroke-width="3" opacity="0.85"{dash_attr}/>'
            )
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_effect_bars(rows: list[dict], output: Path, title: str) -> None:
    keep = sorted(rows, key=lambda row: abs(float(row["cohens_d_b_minus_a"])), reverse=True)[:10]
    if not keep:
        output.write_text("", encoding="utf-8")
        return
    width, height = 980, max(420, 110 + len(keep) * 44)
    left, right, top, bottom = 320, 80, 65, 60
    values = [float(row["cohens_d_b_minus_a"]) for row in keep]
    limit = max(0.25, max(abs(value) for value in values) * 1.15)
    zero = xscale(0, -limit, limit, left, width-right)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{height-bottom}"/>',
        '<text class="small" x="610" y="88">positive = Romantic higher than Classical</text>',
    ]
    row_gap = (height - top - bottom) / len(keep)
    for index, row in enumerate(keep):
        value = float(row["cohens_d_b_minus_a"])
        y = top + row_gap * index + row_gap * 0.5
        end = xscale(value, -limit, limit, left, width-right)
        x = min(zero, end)
        bar_width = max(1, abs(end - zero))
        fill = "#b84a6b" if value >= 0 else "#2f6f9f"
        body.append(f'<text class="small" x="25" y="{y+4:.1f}">{escape(row["feature"])}</text>')
        body.append(f'<rect x="{x:.1f}" y="{y-10:.1f}" width="{bar_width:.1f}" height="20" fill="{fill}" rx="2"/>')
        body.append(f'<text class="small" x="{end + (8 if value >= 0 else -44):.1f}" y="{y+4:.1f}">{value:.2f}</text>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_summary(
    output: Path,
    args: argparse.Namespace,
    metadata_rows: list[dict],
    thresholds: dict[str, float],
    shape_rows: list[dict],
    effects: list[dict],
    boundary_shape: list[dict],
    boundary_effects: list[dict],
) -> None:
    period_counts: dict[str, dict[str, object]] = {}
    for row in metadata_rows:
        item = period_counts.setdefault(row["period"], {"pieces": 0, "events": 0, "corpora": set()})
        item["pieces"] = int(item["pieces"]) + 1
        item["events"] = int(item["events"]) + int(row["events"])
        item["corpora"].add(row["corpus"])
    lines = [
        "# DCML Period Time-Series Summary",
        "",
        "Periods use the manually specified corpus-level Classical/Romantic grouping.",
        "",
        "## Period Coverage",
        "",
    ]
    for period, item in sorted(period_counts.items()):
        corpora = ", ".join(sorted(item["corpora"]))
        lines.append(
            f"- `{period}`: {item['pieces']} pieces, {item['events']} events; corpora: {corpora}"
        )
    lines.extend(["", "## High-Surprisal Thresholds", ""])
    for period, threshold in sorted(thresholds.items()):
        lines.append(f"- `{period}`: {threshold:.3f}")
    lines.extend(["", "## RQ1 Within-Classical Curve Shape", ""])
    for row in shape_rows:
        details = f"- `{row['metric']}`: {float(row['value']):.3f}"
        if "position" in row:
            details += f" at position {row['position']}"
        lines.append(details)
    lines.extend(["", "## RQ1 Period Time-Structure Effects", ""])
    for row in effects:
        lines.append(
            f"- `{row['feature']}`: classical={float(row['a_mean']):.3f}, "
            f"romantic={float(row['b_mean']):.3f}, "
            f"romantic-classical={float(row['b_minus_a']):.3f}, "
            f"d={float(row['cohens_d_b_minus_a']):.3f}"
        )
    lines.extend(["", "## RQ2 Period Boundary Curve Shape", ""])
    for row in boundary_shape:
        details = f"- `{row['metric']}`: {float(row['value']):.3f}"
        if "position" in row:
            details += f" at rel {row['position']}"
        lines.append(details)
    lines.extend(["", "## RQ2 Period Boundary Effects", ""])
    for row in boundary_effects:
        lines.append(
            f"- `{row['feature']}`: classical={float(row['a_mean']):.3f}, "
            f"romantic={float(row['b_mean']):.3f}, "
            f"romantic-classical={float(row['b_minus_a']):.3f}, "
            f"d={float(row['cohens_d_b_minus_a']):.3f}"
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def write_index(output: Path) -> None:
    svgs = sorted(path.name for path in output.glob("*.svg"))
    links = "\n".join(f'<li><a href="{name}">{name}</a></li>' for name in svgs)
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>DCML Period Figures</title>
<body style="font-family:Arial,Helvetica,sans-serif;max-width:900px;margin:40px auto;line-height:1.5">
<h1>DCML Period Figures</h1>
<ul>
{links}
</ul>
</body>
</html>
"""
    (output / "index.html").write_text(html, encoding="utf-8")


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


def color(period: str) -> str:
    return {
        "classical_period": "#2f6f9f",
        "romantic_period": "#b84a6b",
        "late_period": "#7a4fb3",
        "pre_classical_period": "#7c8a99",
    }.get(period, "#555")


def pretty_period(period: str) -> str:
    return period.replace("_period", "").replace("_", " ").title()


def legend(body: list[str], x: int, y: int) -> None:
    periods = [
        ("classical_period", "Classical"),
        ("romantic_period", "Romantic"),
        ("late_period", "Late"),
    ]
    for index, (period, label) in enumerate(periods):
        yy = y + index * 26
        body.append(f'<line x1="{x}" y1="{yy}" x2="{x+28}" y2="{yy}" stroke="{color(period)}" stroke-width="4"/>')
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
