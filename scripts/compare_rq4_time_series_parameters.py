from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


FEATURE_GROUPS = {
    "level": ["mean", "p90", "p95", "max"],
    "volatility": ["variance", "sd", "cv", "range"],
    "peaks": ["peak_rate", "peak_mass"],
    "motion": ["mean_abs_diff", "diff_sd", "smoothness"],
    "autocorr": [
        "lag1_autocorr",
        "lag4_autocorr",
        "lag8_autocorr",
        "max_autocorr_lag2_16",
    ],
    "distribution": ["surprisal_entropy"],
}

DISPLAY_FEATURES = [
    "variance",
    "sd",
    "cv",
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
    parser = argparse.ArgumentParser(
        description="Compare RQ4 time-series parameters across AI-vs-human pairs."
    )
    parser.add_argument(
        "--pair-dirs",
        nargs="+",
        default=[
            "output/ai_symbolic_detection/jsb_vs_js_fake",
            "output/ai_symbolic_detection/jsb_vs_cocochorales_test1",
            "output/ai_symbolic_detection/maestro_vs_music_transformer_sample20",
        ],
    )
    parser.add_argument(
        "--output", default="output/ai_symbolic_detection/time_series_comparison"
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rows = collect_effect_rows([Path(path) for path in args.pair_dirs])
    write_csv(output / "rq4_time_series_parameter_comparison_long.csv", rows)
    write_csv(output / "rq4_time_series_effect_size_matrix.csv", effect_matrix(rows))
    write_csv(output / "rq4_time_series_direction_summary.csv", direction_summary(rows))
    draw_heatmap(rows, output / "rq4_time_series_effect_size_heatmap.svg")
    draw_grouped_bars(rows, output / "rq4_core_time_series_parameters.svg")
    write_markdown_summary(rows, output / "RQ4_TIME_SERIES_PARAMETER_SUMMARY.md")
    print(f"Wrote RQ4 time-series parameter comparison to {output}")


def collect_effect_rows(pair_dirs: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for pair_dir in pair_dirs:
        path = pair_dir / "rq4_human_ai_effects.csv"
        if not path.exists():
            print(f"Skipping missing pair effects: {path}")
            continue
        pair_name = pair_dir.name
        for row in read_csv(path):
            feature = row["feature"]
            group = next(
                (name for name, features in FEATURE_GROUPS.items() if feature in features),
                "other",
            )
            rows.append(
                {
                    "pair": pair_name,
                    "feature_group": group,
                    "feature": feature,
                    "human_mean": float(row["human_mean"]),
                    "ai_mean": float(row["ai_mean"]),
                    "ai_minus_human": float(row["ai_minus_human"]),
                    "cohens_d_ai_minus_human": float(row["cohens_d_ai_minus_human"]),
                    "human_median": float(row["human_median"]),
                    "ai_median": float(row["ai_median"]),
                }
            )
    return rows


def effect_matrix(rows: list[dict]) -> list[dict]:
    pairs = sorted({row["pair"] for row in rows})
    by_key = {(row["pair"], row["feature"]): row for row in rows}
    output: list[dict] = []
    for pair in pairs:
        result = {"pair": pair}
        for feature in DISPLAY_FEATURES:
            row = by_key.get((pair, feature))
            result[f"{feature}_d"] = (
                row["cohens_d_ai_minus_human"] if row else math.nan
            )
            result[f"{feature}_diff"] = row["ai_minus_human"] if row else math.nan
        output.append(result)
    return output


def direction_summary(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    for feature in DISPLAY_FEATURES:
        feature_rows = [row for row in rows if row["feature"] == feature]
        positive = sum(1 for row in feature_rows if row["ai_minus_human"] > 0)
        negative = sum(1 for row in feature_rows if row["ai_minus_human"] < 0)
        output.append(
            {
                "feature": feature,
                "pairs": len(feature_rows),
                "ai_higher_count": positive,
                "ai_lower_count": negative,
                "mean_cohens_d": mean(
                    row["cohens_d_ai_minus_human"] for row in feature_rows
                ),
                "mean_ai_minus_human": mean(row["ai_minus_human"] for row in feature_rows),
            }
        )
    return output


def draw_heatmap(rows: list[dict], output: Path) -> None:
    pairs = sorted({row["pair"] for row in rows})
    by_key = {(row["pair"], row["feature"]): row for row in rows}
    cell_w, cell_h = 112, 34
    left, top = 230, 70
    width = left + len(DISPLAY_FEATURES) * cell_w + 50
    height = top + len(pairs) * cell_h + 90
    body = [
        '<text class="title" x="55" y="36">RQ4 time-series parameter effect sizes</text>',
        '<text class="small" x="55" y="56">Cells show Cohen&apos;s d for AI minus human. Purple = higher in AI, red = lower in AI.</text>',
    ]
    for j, feature in enumerate(DISPLAY_FEATURES):
        x = left + j * cell_w + 8
        body.append(
            f'<text class="small" transform="translate({x} {top-12}) rotate(-35)">'
            f'{feature}</text>'
        )
    for i, pair in enumerate(pairs):
        y = top + i * cell_h
        body.append(f'<text class="label" x="55" y="{y+22}">{short_pair(pair)}</text>')
        for j, feature in enumerate(DISPLAY_FEATURES):
            x = left + j * cell_w
            row = by_key.get((pair, feature))
            value = row["cohens_d_ai_minus_human"] if row else 0.0
            color = diverging_color(value, limit=4.5)
            body.append(
                f'<rect x="{x}" y="{y}" width="{cell_w-3}" height="{cell_h-3}" '
                f'fill="{color}" stroke="#ffffff"/>'
            )
            body.append(
                f'<text class="cell" x="{x+cell_w/2-14:.1f}" y="{y+21}">{value:.1f}</text>'
            )
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def draw_grouped_bars(rows: list[dict], output: Path) -> None:
    core = [
        "variance",
        "peak_rate",
        "peak_mass",
        "smoothness",
        "lag1_autocorr",
        "max_autocorr_lag2_16",
    ]
    pairs = sorted({row["pair"] for row in rows})
    by_key = {(row["pair"], row["feature"]): row for row in rows}
    width, height = 1120, 560
    zero_y = 280
    left, slot = 80, 160
    values = [
        by_key[(pair, feature)]["cohens_d_ai_minus_human"]
        for pair in pairs
        for feature in core
        if (pair, feature) in by_key
    ]
    max_abs = max(abs(value) for value in values) or 1.0
    body = [
        '<text class="title" x="70" y="38">Core RQ4 time-series parameters by pair</text>',
        f'<line class="axis" x1="{left}" y1="{zero_y}" x2="{width-50}" y2="{zero_y}"/>',
        '<text class="small" x="70" y="58">Bars show Cohen&apos;s d for AI minus human.</text>',
    ]
    colors = ["#2f6f9f", "#c46a32", "#7a4fb3"]
    for i, feature in enumerate(core):
        gx = left + i * slot
        body.append(
            f'<text class="small" transform="translate({gx+5} 505) rotate(35)">'
            f'{feature}</text>'
        )
        for j, pair in enumerate(pairs):
            value = by_key[(pair, feature)]["cohens_d_ai_minus_human"]
            h = abs(value) / max_abs * 180
            x = gx + 10 + j * 36
            y = zero_y - h if value >= 0 else zero_y
            body.append(
                f'<rect x="{x}" y="{y:.1f}" width="28" height="{h:.1f}" '
                f'fill="{colors[j % len(colors)]}"/>'
            )
    legend_x, legend_y = 845, 85
    for j, pair in enumerate(pairs):
        y = legend_y + j * 22
        body.append(
            f'<rect x="{legend_x}" y="{y-11}" width="12" height="12" '
            f'fill="{colors[j % len(colors)]}"/>'
        )
        body.append(f'<text class="small" x="{legend_x+18}" y="{y}">{short_pair(pair)}</text>')
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_markdown_summary(rows: list[dict], output: Path) -> None:
    matrix = effect_matrix(rows)
    directions = direction_summary(rows)
    lines = [
        "# RQ4 Time-Series Parameter Comparison",
        "",
        "This comparison aggregates the interpretable surprisal time-series parameters",
        "across available AI-vs-human pairs. Effect sizes are Cohen's d for AI minus",
        "human within each matched pair, which is safer than comparing raw values",
        "across different musical styles.",
        "",
        "## Main Pattern",
        "",
    ]
    for row in directions:
        lines.append(
            f"- `{row['feature']}`: AI higher in {row['ai_higher_count']}/{row['pairs']} "
            f"pairs; mean d = {row['mean_cohens_d']:.2f}."
        )
    lines.extend(["", "## Pair Matrix", ""])
    for row in matrix:
        lines.append(f"### {row['pair']}")
        for feature in DISPLAY_FEATURES:
            lines.append(
                f"- `{feature}`: d = {row[f'{feature}_d']:.2f}, "
                f"AI-human = {row[f'{feature}_diff']:.3f}"
            )
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else math.nan


def diverging_color(value: float, limit: float) -> str:
    value = max(-limit, min(limit, value)) / limit
    if value >= 0:
        base = (122, 79, 179)
    else:
        base = (184, 74, 74)
    alpha = abs(value)
    white = (248, 246, 241)
    rgb = tuple(round(white[i] * (1 - alpha) + base[i] * alpha) for i in range(3))
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def short_pair(pair: str) -> str:
    return (
        pair.replace("jsb_vs_", "")
        .replace("maestro_vs_", "")
        .replace("_sample20", "")
        .replace("_test1", "")
    )


def svg_wrap(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fbfaf7"/>
  <style>
    text {{ font-family: Arial, Helvetica, sans-serif; fill: #1d252c; }}
    .title {{ font-size: 22px; font-weight: 700; }}
    .label {{ font-size: 13px; }}
    .small {{ font-size: 11px; fill: #52606d; }}
    .cell {{ font-size: 11px; fill: #1d252c; font-weight: 700; }}
    .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
  </style>
{body}
</svg>
"""


if __name__ == "__main__":
    main()
