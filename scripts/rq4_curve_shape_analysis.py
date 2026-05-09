from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.rq4_ai_detection_analysis import build_human_trained_surprisal_rows
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RQ4 raw surprisal curve shape and local dynamics analysis."
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--human-source", required=True)
    parser.add_argument("--ai-source", required=True)
    parser.add_argument("--pair-name", required=True)
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--bins", type=int, default=100)
    parser.add_argument("--local-window", type=int, default=16)
    parser.add_argument("--threshold-quantile", type=float, default=0.90)
    parser.add_argument("--entropy-states", type=int, default=5)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.human_source} and {args.ai_source}...")
    events = load_events(args.events, sources={args.human_source, args.ai_source})
    print("Computing raw human-trained surprisal rows...")
    rows = build_human_trained_surprisal_rows(
        events,
        human_source=args.human_source,
        order=args.order,
        token_kind=args.token_kind,
    )
    threshold = human_threshold(rows, args.threshold_quantile)
    print(f"Human threshold q={args.threshold_quantile}: {threshold:.3f}")

    by_piece = group_by_piece(rows)
    profile_rows = normalized_profiles(by_piece, bins=args.bins)
    local_rows = local_variance_profiles(
        by_piece, bins=args.bins, window=args.local_window
    )
    run_rows = run_length_features(by_piece, threshold=threshold)
    changepoint_rows = changepoint_features(
        by_piece, threshold=threshold, window=args.local_window
    )
    entropy_cutpoints = human_entropy_cutpoints(rows, states=args.entropy_states)
    sequence_rows = sequence_dependency_features(
        by_piece, cutpoints=entropy_cutpoints
    )
    sequence_effect_rows = effect_summary_piece_rows(
        sequence_rows, sequence_dependency_feature_names()
    )
    shape_rows = shape_distance_summary(profile_rows)

    write_csv(output / "rq4_raw_normalized_surprisal_profile.csv", profile_rows)
    write_csv(output / "rq4_raw_local_variance_profile.csv", local_rows)
    write_csv(output / "rq4_run_length_features.csv", run_rows)
    write_csv(output / "rq4_changepoint_features.csv", changepoint_rows)
    write_csv(output / "rq4_sequence_dependency_features.csv", sequence_rows)
    write_csv(output / "rq4_sequence_dependency_summary.csv", sequence_effect_rows)
    write_csv(output / "rq4_curve_shape_distance_summary.csv", shape_rows)

    draw_profile(
        profile_rows,
        output / "rq4_raw_mean_surprisal_profile.svg",
        f"{args.pair_name}: raw normalized surprisal profile",
        "mean_surprisal",
        "Surprisal (bits)",
    )
    draw_profile(
        local_rows,
        output / "rq4_local_variance_profile.svg",
        f"{args.pair_name}: local volatility profile",
        "mean_local_variance",
        "Local variance",
    )
    draw_difference(
        profile_rows,
        output / "rq4_surprisal_profile_difference.svg",
        f"{args.pair_name}: AI minus human profile",
        "mean_surprisal",
    )
    draw_effect_bars(
        sequence_effect_rows,
        output / "rq4_sequence_dependency_effects.svg",
        f"{args.pair_name}: sequence-dependency effects",
    )
    write_summary(
        output / "RQ4_CURVE_SHAPE_SUMMARY.md",
        args,
        threshold,
        shape_rows,
        run_rows,
        changepoint_rows,
        sequence_effect_rows,
    )
    print(f"Wrote curve-shape analysis to {output}")


def group_by_piece(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(row)
    for piece_rows in grouped.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
    return dict(grouped)


def human_threshold(rows: list[dict], q: float) -> float:
    values = sorted(
        float(row["surprisal_ngram"]) for row in rows if int(row["is_ai"]) == 0
    )
    return percentile(values, q)


def normalized_profiles(by_piece: dict[str, list[dict]], bins: int) -> list[dict]:
    accum: dict[tuple[str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        label = "ai" if int(piece_rows[0]["is_ai"]) else "human"
        profile = resample(values, bins)
        for index, value in enumerate(profile):
            accum[(label, index)].append(value)
    return profile_accum_to_rows(accum, "mean_surprisal", "sd_surprisal", bins)


def local_variance_profiles(
    by_piece: dict[str, list[dict]], bins: int, window: int
) -> list[dict]:
    accum: dict[tuple[str, int], list[float]] = defaultdict(list)
    for piece_rows in by_piece.values():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        label = "ai" if int(piece_rows[0]["is_ai"]) else "human"
        local = rolling_variance(values, window=window)
        profile = resample(local, bins)
        for index, value in enumerate(profile):
            accum[(label, index)].append(value)
    return profile_accum_to_rows(accum, "mean_local_variance", "sd_local_variance", bins)


def profile_accum_to_rows(
    accum: dict[tuple[str, int], list[float]], mean_name: str, sd_name: str, bins: int
) -> list[dict]:
    rows: list[dict] = []
    for (label, index), values in sorted(accum.items()):
        rows.append(
            {
                "label": label,
                "time_bin": index,
                "normalized_time": index / max(1, bins - 1),
                "n": len(values),
                mean_name: mean(values),
                sd_name: pstdev(values) if len(values) > 1 else 0.0,
            }
        )
    return rows


def run_length_features(by_piece: dict[str, list[dict]], threshold: float) -> list[dict]:
    rows: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        label = "ai" if int(piece_rows[0]["is_ai"]) else "human"
        high_runs, low_runs = binary_runs([value >= threshold for value in values])
        rows.append(
            {
                "piece_id": piece_id,
                "label": label,
                "source": piece_rows[0]["source"],
                "events": len(values),
                "high_run_count": len(high_runs),
                "low_run_count": len(low_runs),
                "mean_high_run": mean(high_runs) if high_runs else 0.0,
                "median_high_run": median(high_runs) if high_runs else 0.0,
                "max_high_run": max(high_runs) if high_runs else 0,
                "mean_low_run": mean(low_runs) if low_runs else 0.0,
                "median_low_run": median(low_runs) if low_runs else 0.0,
                "max_low_run": max(low_runs) if low_runs else 0,
                "high_state_rate": sum(high_runs) / len(values) if values else 0.0,
            }
        )
    return rows


def changepoint_features(
    by_piece: dict[str, list[dict]], threshold: float, window: int
) -> list[dict]:
    rows: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        label = "ai" if int(piece_rows[0]["is_ai"]) else "human"
        cps = simple_changepoints(values, threshold=threshold, window=window)
        normalized = [cp / max(1, len(values) - 1) for cp in cps]
        rows.append(
            {
                "piece_id": piece_id,
                "label": label,
                "source": piece_rows[0]["source"],
                "events": len(values),
                "changepoint_count": len(cps),
                "changepoint_rate": len(cps) / len(values) if values else 0.0,
                "mean_changepoint_time": mean(normalized) if normalized else 0.0,
                "first_changepoint_time": min(normalized) if normalized else 0.0,
                "last_changepoint_time": max(normalized) if normalized else 0.0,
            }
        )
    return rows


def human_entropy_cutpoints(rows: list[dict], states: int) -> list[float]:
    if states < 2:
        raise ValueError("--entropy-states must be at least 2")
    values = sorted(
        float(row["surprisal_ngram"]) for row in rows if int(row["is_ai"]) == 0
    )
    return [percentile(values, index / states) for index in range(1, states)]


def sequence_dependency_features(
    by_piece: dict[str, list[dict]], cutpoints: list[float]
) -> list[dict]:
    rows: list[dict] = []
    for piece_id, piece_rows in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows]
        if len(values) < 4:
            continue
        states = [discretize(value, cutpoints) for value in values]
        transitions = list(zip(states, states[1:]))
        transition_counts = Counter(transitions)
        h0 = empirical_entropy(states)
        h1 = conditional_entropy(states, order=1)
        h2 = conditional_entropy(states, order=2)
        label = "ai" if int(piece_rows[0]["is_ai"]) else "human"
        rows.append(
            {
                "piece_id": piece_id,
                "label": label,
                "source": piece_rows[0]["source"],
                "events": len(values),
                "state_count": len(set(states)),
                "state_entropy": h0,
                "entropy_rate_order1": h1,
                "entropy_rate_order2": h2,
                "predictability_gain_order1": h0 - h1,
                "predictability_gain_order2": h1 - h2,
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


def sequence_dependency_feature_names() -> list[str]:
    return [
        "state_entropy",
        "entropy_rate_order1",
        "entropy_rate_order2",
        "predictability_gain_order1",
        "predictability_gain_order2",
        "same_state_transition_rate",
        "dominant_transition_rate",
    ]


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
    result = 0.0
    for next_counts in context_counts.values():
        context_total = sum(next_counts.values())
        result += context_total / total * entropy_from_counts(next_counts.values())
    return result


def entropy_from_counts(counts: object) -> float:
    values = [int(count) for count in counts if int(count) > 0]
    total = sum(values)
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in values)


def shape_distance_summary(profile_rows: list[dict]) -> list[dict]:
    by_label = {
        label: sorted(
            [row for row in profile_rows if row["label"] == label],
            key=lambda row: int(row["time_bin"]),
        )
        for label in ("human", "ai")
    }
    if not by_label["human"] or not by_label["ai"]:
        return []
    human = [float(row["mean_surprisal"]) for row in by_label["human"]]
    ai = [float(row["mean_surprisal"]) for row in by_label["ai"]]
    diff = [a - h for h, a in zip(human, ai)]
    max_idx = max(range(len(diff)), key=lambda index: diff[index])
    min_idx = min(range(len(diff)), key=lambda index: diff[index])
    return [
        {
            "metric": "mean_ai_minus_human",
            "value": mean(diff),
        },
        {
            "metric": "rms_curve_difference",
            "value": math.sqrt(mean(value**2 for value in diff)),
        },
        {
            "metric": "max_ai_excess",
            "value": diff[max_idx],
            "time_bin": max_idx,
            "normalized_time": max_idx / max(1, len(diff) - 1),
        },
        {
            "metric": "max_human_excess",
            "value": diff[min_idx],
            "time_bin": min_idx,
            "normalized_time": min_idx / max(1, len(diff) - 1),
        },
        {
            "metric": "signed_area_ai_minus_human",
            "value": sum(diff) / len(diff),
        },
    ]


def rolling_variance(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    half = max(1, window // 2)
    output = []
    for index in range(len(values)):
        chunk = values[max(0, index - half) : min(len(values), index + half + 1)]
        output.append(pstdev(chunk) ** 2 if len(chunk) > 1 else 0.0)
    return output


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


def draw_profile(rows: list[dict], output: Path, title: str, value_key: str, y_label: str) -> None:
    profiles = {
        label: sorted([row for row in rows if row["label"] == label], key=lambda row: int(row["time_bin"]))
        for label in ("human", "ai")
    }
    width, height = 980, 540
    left, right, top, bottom = 80, 120, 70, 80
    all_values = [float(row[value_key]) for row in rows]
    ymin, ymax = min(all_values) - 0.5, max(all_values) + 0.5
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
        '<text class="label" x="410" y="505">Normalized piece time</text>',
        f'<text class="label" transform="translate(24 330) rotate(-90)">{escape(y_label)}</text>',
    ]
    for label, profile_rows in profiles.items():
        points = " ".join(
            f"{sx(i, len(profile_rows), left, width-right):.1f},{sy(float(row[value_key]), ymin, ymax, top, height-bottom):.1f}"
            for i, row in enumerate(profile_rows)
        )
        body.append(f'<polyline points="{points}" fill="none" stroke="{color(label)}" stroke-width="4"/>')
    legend(body, width - right + 20, 100)
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_difference(rows: list[dict], output: Path, title: str, value_key: str) -> None:
    human = sorted([row for row in rows if row["label"] == "human"], key=lambda row: int(row["time_bin"]))
    ai = sorted([row for row in rows if row["label"] == "ai"], key=lambda row: int(row["time_bin"]))
    diff = [float(a[value_key]) - float(h[value_key]) for h, a in zip(human, ai)]
    width, height = 920, 500
    left, right, top, bottom = 80, 50, 70, 80
    ymin, ymax = min(min(diff) - 0.3, 0), max(max(diff) + 0.3, 0)
    zero = sy(0, ymin, ymax, top, height-bottom)
    points = " ".join(
        f"{sx(i, len(diff), left, width-right):.1f},{sy(value, ymin, ymax, top, height-bottom):.1f}"
        for i, value in enumerate(diff)
    )
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line x1="{left}" y1="{zero:.1f}" x2="{width-right}" y2="{zero:.1f}" stroke="#777" stroke-dasharray="5 5"/>',
        f'<polyline points="{points}" fill="none" stroke="#7a4fb3" stroke-width="3"/>',
        '<text class="label" x="360" y="465">Normalized piece time</text>',
        '<text class="label" transform="translate(24 315) rotate(-90)">AI minus human</text>',
    ]
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_effect_bars(rows: list[dict], output: Path, title: str) -> None:
    if not rows:
        output.write_text("", encoding="utf-8")
        return
    width, height = 980, max(360, 120 + len(rows) * 48)
    left, right, top, bottom = 270, 80, 70, 50
    values = [float(row["cohens_d_ai_minus_human"]) for row in rows]
    limit = max(0.25, max(abs(value) for value in values) * 1.15)
    zero = xscale(0, -limit, limit, left, width - right)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{height-bottom}"/>',
        f'<text class="small" x="{left}" y="{height-18}">human higher</text>',
        f'<text class="small" x="{width-right-60}" y="{height-18}">AI higher</text>',
    ]
    row_gap = (height - top - bottom) / max(1, len(rows))
    for index, row in enumerate(rows):
        y = top + row_gap * index + row_gap * 0.5
        value = float(row["cohens_d_ai_minus_human"])
        end = xscale(value, -limit, limit, left, width - right)
        x = min(zero, end)
        bar_width = max(1, abs(end - zero))
        fill = "#b84a6b" if value >= 0 else "#2f6f9f"
        body.append(f'<text class="small" x="30" y="{y+4:.1f}">{escape(row["feature"])}</text>')
        body.append(
            f'<rect x="{x:.1f}" y="{y-10:.1f}" width="{bar_width:.1f}" height="20" fill="{fill}" rx="2"/>'
        )
        body.append(
            f'<text class="small" x="{end + (8 if value >= 0 else -44):.1f}" y="{y+4:.1f}">{value:.2f}</text>'
        )
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_summary(
    output: Path,
    args: argparse.Namespace,
    threshold: float,
    shape_rows: list[dict],
    run_rows: list[dict],
    changepoint_rows: list[dict],
    sequence_effect_rows: list[dict],
) -> None:
    run_summary = summarize_piece_rows(run_rows, ["high_state_rate", "mean_high_run", "max_high_run", "mean_low_run"])
    cp_summary = summarize_piece_rows(changepoint_rows, ["changepoint_rate", "mean_changepoint_time"])
    lines = [
        f"# RQ4 Curve Shape Summary: {args.pair_name}",
        "",
        f"Human source: `{args.human_source}`",
        f"AI source: `{args.ai_source}`",
        f"Human high-surprisal threshold q={args.threshold_quantile}: `{threshold:.3f}`",
        "",
        "## Curve Shape Distance",
        "",
    ]
    for row in shape_rows:
        details = f"- `{row['metric']}`: {float(row['value']):.3f}"
        if "normalized_time" in row and row["normalized_time"] != "":
            details += f" at t={float(row['normalized_time']):.2f}"
        lines.append(details)
    lines.extend(["", "## Run-Length Summary", ""])
    for label, values in run_summary.items():
        lines.append(f"### {label}")
        for feature, value in values.items():
            lines.append(f"- `{feature}`: {value:.3f}")
    lines.extend(["", "## Changepoint Summary", ""])
    for label, values in cp_summary.items():
        lines.append(f"### {label}")
        for feature, value in values.items():
            lines.append(f"- `{feature}`: {value:.3f}")
    lines.extend(["", "## Sequence Dependency Summary", ""])
    for row in sequence_effect_rows:
        lines.append(
            f"- `{row['feature']}`: human={float(row['human_mean']):.3f}, "
            f"AI={float(row['ai_mean']):.3f}, "
            f"AI-human={float(row['ai_minus_human']):.3f}, "
            f"d={float(row['cohens_d_ai_minus_human']):.3f}"
        )
    output.write_text("\n".join(lines), encoding="utf-8")


def summarize_piece_rows(rows: list[dict], features: list[str]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["label"]].append(row)
    return {
        label: {feature: mean(float(row[feature]) for row in label_rows) for feature in features}
        for label, label_rows in grouped.items()
    }


def effect_summary_piece_rows(rows: list[dict], features: list[str]) -> list[dict]:
    human = [row for row in rows if row["label"] == "human"]
    ai = [row for row in rows if row["label"] == "ai"]
    output: list[dict] = []
    for feature in features:
        human_values = [float(row[feature]) for row in human]
        ai_values = [float(row[feature]) for row in ai]
        if not human_values or not ai_values:
            continue
        output.append(
            {
                "feature": feature,
                "human_mean": mean(human_values),
                "ai_mean": mean(ai_values),
                "ai_minus_human": mean(ai_values) - mean(human_values),
                "cohens_d_ai_minus_human": cohens_d(human_values, ai_values),
                "human_median": median(human_values),
                "ai_median": median(ai_values),
            }
        )
    return output


def cohens_d(human_values: list[float], ai_values: list[float]) -> float:
    if len(human_values) < 2 or len(ai_values) < 2:
        return 0.0
    human_sd = pstdev(human_values)
    ai_sd = pstdev(ai_values)
    pooled = math.sqrt((human_sd**2 + ai_sd**2) / 2)
    if pooled == 0:
        return 0.0
    return (mean(ai_values) - mean(human_values)) / pooled


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


def sx(index: int, n: int, left: float, right: float) -> float:
    return left + index / max(1, n - 1) * (right - left)


def xscale(value: float, xmin: float, xmax: float, left: float, right: float) -> float:
    return left + (value - xmin) / (xmax - xmin) * (right - left)


def sy(value: float, ymin: float, ymax: float, top: float, bottom: float) -> float:
    return top + (ymax - value) / (ymax - ymin) * (bottom - top)


def color(label: str) -> str:
    return "#2f6f9f" if label == "human" else "#b84a6b"


def legend(body: list[str], x: int, y: int) -> None:
    body.append(f'<line x1="{x}" y1="{y}" x2="{x+28}" y2="{y}" stroke="#2f6f9f" stroke-width="4"/>')
    body.append(f'<text class="small" x="{x+36}" y="{y+4}">human</text>')
    body.append(f'<line x1="{x}" y1="{y+24}" x2="{x+28}" y2="{y+24}" stroke="#b84a6b" stroke-width="4"/>')
    body.append(f'<text class="small" x="{x+36}" y="{y+28}">AI</text>')


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


if __name__ == "__main__":
    main()
