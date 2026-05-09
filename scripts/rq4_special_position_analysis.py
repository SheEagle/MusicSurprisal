from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.rq4_ai_detection_analysis import build_human_trained_surprisal_rows
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RQ4 relation between surprisal time series and special musical positions."
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--human-source", required=True)
    parser.add_argument("--ai-source", required=True)
    parser.add_argument("--pair-name", required=True)
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--boundary-window", type=int, default=4)
    parser.add_argument("--local-window", type=int, default=16)
    parser.add_argument("--threshold-quantile", type=float, default=0.90)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.human_source} and {args.ai_source}...")
    events = load_events(args.events, sources={args.human_source, args.ai_source})
    print("Computing human-trained raw surprisal rows...")
    rows = build_human_trained_surprisal_rows(
        events,
        human_source=args.human_source,
        order=args.order,
        token_kind=args.token_kind,
    )
    threshold = human_threshold(rows, args.threshold_quantile)
    print(f"Human high-surprisal threshold q={args.threshold_quantile}: {threshold:.3f}")

    by_piece = group_by_piece(rows)
    event_rows, piece_rows = analyze_special_positions(
        by_piece,
        threshold=threshold,
        boundary_window=args.boundary_window,
        local_window=args.local_window,
    )
    position_summary = summarize_position_events(event_rows)
    position_effects = position_effect_summary(position_summary)
    alignment_summary = summarize_piece_rows(piece_rows, alignment_feature_names())
    alignment_effects = piece_effect_summary(piece_rows, alignment_feature_names())

    write_csv(output / "rq4_special_position_events.csv", event_rows)
    write_csv(output / "rq4_special_position_event_summary.csv", position_summary)
    write_csv(output / "rq4_special_position_effects.csv", position_effects)
    write_csv(output / "rq4_special_position_alignment_by_piece.csv", piece_rows)
    write_csv(output / "rq4_special_position_alignment_summary.csv", alignment_summary)
    write_csv(output / "rq4_special_position_alignment_effects.csv", alignment_effects)

    draw_position_effects(
        position_effects,
        output / "rq4_special_position_mean_surprisal_effects.svg",
        f"{args.pair_name}: AI-human surprisal by special position",
    )
    draw_alignment_effects(
        alignment_effects,
        output / "rq4_special_position_alignment_effects.svg",
        f"{args.pair_name}: special-position alignment effects",
    )
    write_summary(
        output / "RQ4_SPECIAL_POSITION_SUMMARY.md",
        args,
        threshold,
        position_summary,
        position_effects,
        alignment_summary,
        alignment_effects,
    )
    print(f"Wrote special-position analysis to {output}")


def group_by_piece(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["piece_id"]].append(row)
    for piece_rows in grouped.values():
        piece_rows.sort(key=lambda row: int(row["event_index"]))
    return dict(grouped)


def analyze_special_positions(
    by_piece: dict[str, list[dict]],
    *,
    threshold: float,
    boundary_window: int,
    local_window: int,
) -> tuple[list[dict], list[dict]]:
    event_rows: list[dict] = []
    piece_rows: list[dict] = []
    for piece_id, piece_rows_raw in by_piece.items():
        values = [float(row["surprisal_ngram"]) for row in piece_rows_raw]
        if len(values) < 4:
            continue
        label = "ai" if int(piece_rows_raw[0]["is_ai"]) else "human"
        boundaries = [
            index
            for index, row in enumerate(piece_rows_raw)
            if int(row["boundary"]) == 1 and 0 < index < len(piece_rows_raw) - 1
        ]
        boundary_zone = indices_near(boundaries, len(values), boundary_window)
        peaks = set(local_peaks(values, threshold))
        changepoints = set(simple_changepoints(values, threshold, local_window))
        high = {index for index, value in enumerate(values) if value >= threshold}
        local_var = rolling_variance(values, local_window)

        piece_rows.append(
            piece_alignment_row(
                piece_id,
                piece_rows_raw,
                label,
                values,
                boundaries,
                boundary_zone,
                high,
                peaks,
                changepoints,
            )
        )

        for index, row in enumerate(piece_rows_raw):
            ntime = index / max(1, len(piece_rows_raw) - 1)
            for position_type in position_types_for_index(
                index, ntime, boundaries, boundary_zone, len(piece_rows_raw), boundary_window
            ):
                event_rows.append(
                    {
                        "piece_id": piece_id,
                        "source": row["source"],
                        "label": label,
                        "position_type": position_type,
                        "event_index": index,
                        "normalized_time": ntime,
                        "surprisal": values[index],
                        "local_variance": local_var[index],
                        "is_high_surprisal": int(index in high),
                        "is_local_peak": int(index in peaks),
                        "is_changepoint": int(index in changepoints),
                    }
                )
    return event_rows, piece_rows


def piece_alignment_row(
    piece_id: str,
    raw_rows: list[dict],
    label: str,
    values: list[float],
    boundaries: list[int],
    boundary_zone: set[int],
    high: set[int],
    peaks: set[int],
    changepoints: set[int],
) -> dict:
    zone_values = [values[index] for index in boundary_zone]
    far_values = [value for index, value in enumerate(values) if index not in boundary_zone]
    return {
        "piece_id": piece_id,
        "source": raw_rows[0]["source"],
        "label": label,
        "events": len(values),
        "boundary_count": len(boundaries),
        "boundary_zone_event_rate": len(boundary_zone) / len(values),
        "boundary_zone_mean_surprisal": mean(zone_values) if zone_values else 0.0,
        "far_from_boundary_mean_surprisal": mean(far_values) if far_values else 0.0,
        "boundary_zone_surprisal_lift": (
            mean(zone_values) - mean(far_values) if zone_values and far_values else 0.0
        ),
        "high_event_count": len(high),
        "high_event_boundary_zone_rate": overlap_rate(high, boundary_zone),
        "high_event_boundary_enrichment": enrichment(high, boundary_zone, len(values)),
        "peak_count": len(peaks),
        "peak_boundary_zone_rate": overlap_rate(peaks, boundary_zone),
        "peak_boundary_enrichment": enrichment(peaks, boundary_zone, len(values)),
        "changepoint_count": len(changepoints),
        "changepoint_boundary_zone_rate": overlap_rate(changepoints, boundary_zone),
        "changepoint_boundary_enrichment": enrichment(changepoints, boundary_zone, len(values)),
        "opening_mean_surprisal": zone_mean(values, lambda ntime: ntime <= 0.10),
        "middle_mean_surprisal": zone_mean(values, lambda ntime: 0.45 <= ntime <= 0.55),
        "closing_mean_surprisal": zone_mean(values, lambda ntime: ntime >= 0.90),
        "closing_minus_opening_surprisal": zone_mean(
            values, lambda ntime: ntime >= 0.90
        )
        - zone_mean(values, lambda ntime: ntime <= 0.10),
    }


def position_types_for_index(
    index: int,
    ntime: float,
    boundaries: list[int],
    boundary_zone: set[int],
    length: int,
    boundary_window: int,
) -> list[str]:
    types = ["all_events"]
    if ntime <= 0.10:
        types.append("opening_10pct")
    if 0.45 <= ntime <= 0.55:
        types.append("middle_10pct")
    if ntime >= 0.90:
        types.append("closing_10pct")
    if index in boundaries:
        types.append("annotated_boundary_exact")
    if index in boundary_zone:
        types.append(f"annotated_boundary_zone_pm{boundary_window}")
    else:
        types.append("far_from_annotated_boundary")
    if any(0 < boundary - index <= boundary_window for boundary in boundaries):
        types.append(f"pre_boundary_{boundary_window}")
    if any(0 <= index - boundary <= boundary_window for boundary in boundaries):
        types.append(f"post_boundary_{boundary_window}")
    if index == 0:
        types.append("first_event")
    if index == length - 1:
        types.append("last_event")
    return types


def summarize_position_events(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["label"], row["position_type"])].append(row)
    output: list[dict] = []
    for (label, position_type), items in sorted(grouped.items()):
        output.append(
            {
                "label": label,
                "position_type": position_type,
                "events": len(items),
                "pieces": len({row["piece_id"] for row in items}),
                "mean_normalized_time": mean(float(row["normalized_time"]) for row in items),
                "mean_surprisal": mean(float(row["surprisal"]) for row in items),
                "median_surprisal": median(float(row["surprisal"]) for row in items),
                "mean_local_variance": mean(float(row["local_variance"]) for row in items),
                "high_surprisal_rate": mean(float(row["is_high_surprisal"]) for row in items),
                "local_peak_rate": mean(float(row["is_local_peak"]) for row in items),
                "changepoint_rate": mean(float(row["is_changepoint"]) for row in items),
            }
        )
    return output


def position_effect_summary(summary_rows: list[dict]) -> list[dict]:
    by_position: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in summary_rows:
        by_position[row["position_type"]][row["label"]] = row
    output: list[dict] = []
    for position_type, labels in sorted(by_position.items()):
        if "human" not in labels or "ai" not in labels:
            continue
        for metric in position_metric_names():
            human_value = float(labels["human"][metric])
            ai_value = float(labels["ai"][metric])
            output.append(
                {
                    "position_type": position_type,
                    "metric": metric,
                    "human_mean": human_value,
                    "ai_mean": ai_value,
                    "ai_minus_human": ai_value - human_value,
                }
            )
    return output


def summarize_piece_rows(rows: list[dict], features: list[str]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["label"]].append(row)
    output: list[dict] = []
    for label, items in sorted(grouped.items()):
        summary = {"label": label, "pieces": len(items)}
        for feature in features:
            values = [float(row[feature]) for row in items]
            summary[f"{feature}_mean"] = mean(values)
            summary[f"{feature}_median"] = median(values)
            summary[f"{feature}_sd"] = pstdev(values) if len(values) > 1 else 0.0
        output.append(summary)
    return output


def piece_effect_summary(rows: list[dict], features: list[str]) -> list[dict]:
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


def position_metric_names() -> list[str]:
    return [
        "mean_surprisal",
        "mean_local_variance",
        "high_surprisal_rate",
        "local_peak_rate",
        "changepoint_rate",
    ]


def alignment_feature_names() -> list[str]:
    return [
        "boundary_zone_event_rate",
        "boundary_zone_surprisal_lift",
        "high_event_boundary_zone_rate",
        "high_event_boundary_enrichment",
        "peak_boundary_zone_rate",
        "peak_boundary_enrichment",
        "changepoint_boundary_zone_rate",
        "changepoint_boundary_enrichment",
        "opening_mean_surprisal",
        "middle_mean_surprisal",
        "closing_mean_surprisal",
        "closing_minus_opening_surprisal",
    ]


def human_threshold(rows: list[dict], q: float) -> float:
    values = sorted(
        float(row["surprisal_ngram"]) for row in rows if int(row["is_ai"]) == 0
    )
    return percentile(values, q)


def indices_near(indices: list[int], length: int, window: int) -> set[int]:
    output: set[int] = set()
    for index in indices:
        for candidate in range(max(0, index - window), min(length, index + window + 1)):
            output.add(candidate)
    return output


def overlap_rate(items: set[int], zone: set[int]) -> float:
    if not items:
        return 0.0
    return len(items & zone) / len(items)


def enrichment(items: set[int], zone: set[int], length: int) -> float:
    exposure = len(zone) / length if length else 0.0
    if not items or exposure == 0:
        return 0.0
    return overlap_rate(items, zone) / exposure


def zone_mean(values: list[float], predicate) -> float:
    selected = [
        value
        for index, value in enumerate(values)
        if predicate(index / max(1, len(values) - 1))
    ]
    return mean(selected) if selected else 0.0


def rolling_variance(values: list[float], window: int) -> list[float]:
    if not values:
        return []
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
        and values[index] >= values[index - 1]
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


def cohens_d(human_values: list[float], ai_values: list[float]) -> float:
    if len(human_values) < 2 or len(ai_values) < 2:
        return 0.0
    pooled = math.sqrt((pstdev(human_values) ** 2 + pstdev(ai_values) ** 2) / 2)
    if pooled == 0:
        return 0.0
    return (mean(ai_values) - mean(human_values)) / pooled


def draw_position_effects(rows: list[dict], output: Path, title: str) -> None:
    filtered = [
        row
        for row in rows
        if row["metric"] == "mean_surprisal"
        and row["position_type"]
        in {
            "opening_10pct",
            "middle_10pct",
            "closing_10pct",
            "annotated_boundary_exact",
            "annotated_boundary_zone_pm4",
            "pre_boundary_4",
            "post_boundary_4",
            "far_from_annotated_boundary",
        }
    ]
    draw_horizontal_bars(
        [(row["position_type"], float(row["ai_minus_human"])) for row in filtered],
        output,
        title,
        "AI minus human surprisal",
    )


def draw_alignment_effects(rows: list[dict], output: Path, title: str) -> None:
    wanted = [
        "boundary_zone_surprisal_lift",
        "high_event_boundary_enrichment",
        "peak_boundary_enrichment",
        "changepoint_boundary_enrichment",
        "closing_minus_opening_surprisal",
    ]
    draw_horizontal_bars(
        [
            (row["feature"], float(row["cohens_d_ai_minus_human"]))
            for row in rows
            if row["feature"] in wanted
        ],
        output,
        title,
        "Cohen's d (AI minus human)",
    )


def draw_horizontal_bars(
    values: list[tuple[str, float]], output: Path, title: str, x_label: str
) -> None:
    if not values:
        output.write_text("", encoding="utf-8")
        return
    width, height = 980, max(360, 110 + len(values) * 48)
    left, right, top, bottom = 300, 80, 65, 60
    limit = max(0.25, max(abs(value) for _, value in values) * 1.15)
    zero = xscale(0, -limit, limit, left, width - right)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{height-bottom}"/>',
        f'<text class="label" x="{left+190}" y="{height-20}">{escape(x_label)}</text>',
    ]
    row_gap = (height - top - bottom) / max(1, len(values))
    for index, (name, value) in enumerate(values):
        y = top + row_gap * index + row_gap * 0.5
        end = xscale(value, -limit, limit, left, width - right)
        x = min(zero, end)
        bar_width = max(1, abs(end - zero))
        fill = "#b84a6b" if value >= 0 else "#2f6f9f"
        body.append(f'<text class="small" x="28" y="{y+4:.1f}">{escape(name)}</text>')
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
    position_summary: list[dict],
    position_effects: list[dict],
    alignment_summary: list[dict],
    alignment_effects: list[dict],
) -> None:
    mean_effects = [
        row for row in position_effects if row["metric"] == "mean_surprisal"
    ]
    important_positions = [
        "opening_10pct",
        "middle_10pct",
        "closing_10pct",
        "annotated_boundary_exact",
        f"annotated_boundary_zone_pm{args.boundary_window}",
        f"pre_boundary_{args.boundary_window}",
        f"post_boundary_{args.boundary_window}",
        "far_from_annotated_boundary",
    ]
    summary_by_label = {row["label"]: row for row in alignment_summary}
    lines = [
        f"# RQ4 Special Position Summary: {args.pair_name}",
        "",
        f"Human source: `{args.human_source}`",
        f"AI source: `{args.ai_source}`",
        f"Human high-surprisal threshold q={args.threshold_quantile}: `{threshold:.3f}`",
        f"Boundary window: `+/-{args.boundary_window}` events",
        "",
        "## Mean Surprisal by Special Position",
        "",
    ]
    for position in important_positions:
        row = next((item for item in mean_effects if item["position_type"] == position), None)
        if row:
            lines.append(
                f"- `{position}`: human={float(row['human_mean']):.3f}, "
                f"AI={float(row['ai_mean']):.3f}, "
                f"AI-human={float(row['ai_minus_human']):.3f}"
            )
    lines.extend(["", "## Alignment Effects", ""])
    for row in alignment_effects:
        if row["feature"] in {
            "boundary_zone_surprisal_lift",
            "high_event_boundary_enrichment",
            "peak_boundary_enrichment",
            "changepoint_boundary_enrichment",
            "closing_minus_opening_surprisal",
        }:
            lines.append(
                f"- `{row['feature']}`: human={float(row['human_mean']):.3f}, "
                f"AI={float(row['ai_mean']):.3f}, "
                f"AI-human={float(row['ai_minus_human']):.3f}, "
                f"d={float(row['cohens_d_ai_minus_human']):.3f}"
            )
    lines.extend(["", "## Label-Level Alignment Means", ""])
    for label in ("human", "ai"):
        row = summary_by_label.get(label)
        if not row:
            continue
        lines.append(f"### {label}")
        for feature in [
            "boundary_zone_event_rate",
            "boundary_zone_surprisal_lift",
            "high_event_boundary_enrichment",
            "peak_boundary_enrichment",
            "changepoint_boundary_enrichment",
            "closing_minus_opening_surprisal",
        ]:
            lines.append(f"- `{feature}`: {float(row[f'{feature}_mean']):.3f}")
    output.write_text("\n".join(lines), encoding="utf-8")


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


def xscale(value: float, xmin: float, xmax: float, left: float, right: float) -> float:
    return left + (value - xmin) / (xmax - xmin) * (right - left)


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
