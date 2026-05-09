from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, group_by_piece, token_function
from music_surprisal.ngram import NGramModel
from scripts.run_formal_experiment import load_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bidirectional RQ4 expectation analysis: human-trained vs AI-trained n-gram models."
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--human-source", required=True)
    parser.add_argument("--ai-source", required=True)
    parser.add_argument("--pair-name", required=True)
    parser.add_argument("--order", type=int, default=3)
    parser.add_argument("--token-kind", default="pitch_duration")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    events = load_events(args.events, sources={args.human_source, args.ai_source})
    splits = {
        "human": split_source_events(
            [event for event in events if event.source == args.human_source],
            train_frac=args.train_frac,
            seed=args.seed,
        ),
        "ai": split_source_events(
            [event for event in events if event.source == args.ai_source],
            train_frac=args.train_frac,
            seed=args.seed + 1,
        ),
    }
    models = {
        label: train_model(
            split["train"],
            order=args.order,
            token_kind=args.token_kind,
        )
        for label, split in splits.items()
    }

    rows: list[dict] = []
    for model_label, model in models.items():
        for eval_label, split in splits.items():
            rows.extend(
                score_pieces(
                    split["eval"],
                    model=model,
                    model_label=model_label,
                    eval_label=eval_label,
                    token_kind=args.token_kind,
                )
            )

    cell_summary = summarize_cells(rows)
    direction_summary = summarize_directions(cell_summary)

    write_csv(output / "rq4_bidirectional_piece_surprisal.csv", rows)
    write_csv(output / "rq4_bidirectional_cell_summary.csv", cell_summary)
    write_csv(output / "rq4_bidirectional_direction_summary.csv", direction_summary)
    draw_direction_summary(
        direction_summary,
        output / "rq4_bidirectional_expectation_effects.svg",
        f"{args.pair_name}: bidirectional expectation effects",
    )
    write_summary(
        output / "RQ4_BIDIRECTIONAL_EXPECTATION_SUMMARY.md",
        args,
        splits,
        cell_summary,
        direction_summary,
    )
    print(f"Wrote bidirectional expectation analysis to {output}")


def split_source_events(
    events: list[Event], *, train_frac: float, seed: int
) -> dict[str, list[Event]]:
    by_piece = group_by_piece(events)
    explicit_train = [
        piece_id
        for piece_id, piece_events in by_piece.items()
        if all(event.split == "train" for event in piece_events)
    ]
    explicit_eval = [
        piece_id
        for piece_id, piece_events in by_piece.items()
        if all(event.split != "train" for event in piece_events)
    ]
    if explicit_train and explicit_eval:
        train_ids = set(explicit_train)
        eval_ids = set(explicit_eval)
    else:
        piece_ids = sorted(by_piece)
        rng = random.Random(seed)
        rng.shuffle(piece_ids)
        split_at = max(1, min(len(piece_ids) - 1, round(len(piece_ids) * train_frac)))
        train_ids = set(piece_ids[:split_at])
        eval_ids = set(piece_ids[split_at:])

    train = [event for piece_id in sorted(train_ids) for event in by_piece[piece_id]]
    eval_events = [event for piece_id in sorted(eval_ids) for event in by_piece[piece_id]]
    if not train or not eval_events:
        raise ValueError("Each source needs non-empty train and eval events")
    return {"train": train, "eval": eval_events}


def train_model(events: list[Event], *, order: int, token_kind: str) -> NGramModel:
    to_token = token_function(token_kind)
    sequences = [
        [to_token(event) for event in piece]
        for piece in group_by_piece(events).values()
        if piece
    ]
    if not sequences:
        raise ValueError("No training sequences")
    return NGramModel(order=order).fit(sequences)


def score_pieces(
    events: list[Event],
    *,
    model: NGramModel,
    model_label: str,
    eval_label: str,
    token_kind: str,
) -> list[dict]:
    to_token = token_function(token_kind)
    rows: list[dict] = []
    for piece_id, piece_events in sorted(group_by_piece(events).items()):
        tokens = [to_token(event) for event in piece_events]
        values = model.sequence_surprisal(tokens)
        if not values:
            continue
        rows.append(
            {
                "piece_id": piece_id,
                "source": piece_events[0].source,
                "model_label": model_label,
                "eval_label": eval_label,
                "events": len(values),
                "mean_surprisal": mean(values),
                "median_surprisal": median(values),
                "sd_surprisal": pstdev(values) if len(values) > 1 else 0.0,
                "p90_surprisal": percentile(sorted(values), 0.90),
                "max_surprisal": max(values),
            }
        )
    return rows


def summarize_cells(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["model_label"], row["eval_label"])].append(row)
    output: list[dict] = []
    for (model_label, eval_label), items in sorted(grouped.items()):
        summary = {
            "model_label": model_label,
            "eval_label": eval_label,
            "pieces": len(items),
            "events": sum(int(row["events"]) for row in items),
        }
        for feature in feature_names():
            values = [float(row[feature]) for row in items]
            summary[f"{feature}_mean"] = mean(values)
            summary[f"{feature}_median"] = median(values)
            summary[f"{feature}_sd"] = pstdev(values) if len(values) > 1 else 0.0
        output.append(summary)
    return output


def summarize_directions(cell_summary: list[dict]) -> list[dict]:
    cells = {
        (row["model_label"], row["eval_label"]): row for row in cell_summary
    }
    output: list[dict] = []
    human_model_within = cells.get(("human", "human"))
    human_model_cross = cells.get(("human", "ai"))
    ai_model_within = cells.get(("ai", "ai"))
    ai_model_cross = cells.get(("ai", "human"))
    if human_model_within and human_model_cross:
        output.append(
            direction_row(
                "human_model_ai_minus_human",
                "human",
                human_model_within,
                human_model_cross,
            )
        )
    if ai_model_within and ai_model_cross:
        output.append(
            direction_row(
                "ai_model_human_minus_ai",
                "ai",
                ai_model_within,
                ai_model_cross,
            )
        )
    return output


def direction_row(name: str, model_label: str, within: dict, cross: dict) -> dict:
    return {
        "direction": name,
        "model_label": model_label,
        "within_eval_label": within["eval_label"],
        "cross_eval_label": cross["eval_label"],
        "within_mean_surprisal": within["mean_surprisal_mean"],
        "cross_mean_surprisal": cross["mean_surprisal_mean"],
        "cross_minus_within": cross["mean_surprisal_mean"] - within["mean_surprisal_mean"],
        "within_p90_surprisal": within["p90_surprisal_mean"],
        "cross_p90_surprisal": cross["p90_surprisal_mean"],
        "p90_cross_minus_within": cross["p90_surprisal_mean"] - within["p90_surprisal_mean"],
    }


def feature_names() -> list[str]:
    return [
        "mean_surprisal",
        "median_surprisal",
        "sd_surprisal",
        "p90_surprisal",
        "max_surprisal",
    ]


def draw_direction_summary(rows: list[dict], output: Path, title: str) -> None:
    width, height = 920, 320
    left, right, top, bottom = 260, 80, 70, 60
    values = [(row["direction"], float(row["cross_minus_within"])) for row in rows]
    if not values:
        output.write_text("", encoding="utf-8")
        return
    limit = max(0.25, max(abs(value) for _, value in values) * 1.2)
    zero = xscale(0, -limit, limit, left, width - right)
    body = [
        f'<text class="title" x="70" y="38">{escape(title)}</text>',
        f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
        f'<line class="axis" x1="{zero:.1f}" y1="{top}" x2="{zero:.1f}" y2="{height-bottom}"/>',
        f'<text class="label" x="{left+160}" y="{height-18}">cross minus within surprisal</text>',
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
            f'<rect x="{x:.1f}" y="{y-12:.1f}" width="{bar_width:.1f}" height="24" fill="{fill}" rx="2"/>'
        )
        body.append(
            f'<text class="small" x="{end + (8 if value >= 0 else -44):.1f}" y="{y+4:.1f}">{value:.2f}</text>'
        )
    output.write_text(svg_wrap(width, height, "\n".join(body)), encoding="utf-8")


def write_summary(
    output: Path,
    args: argparse.Namespace,
    splits: dict[str, dict[str, list[Event]]],
    cell_summary: list[dict],
    direction_summary: list[dict],
) -> None:
    lines = [
        f"# RQ4 Bidirectional Expectation Summary: {args.pair_name}",
        "",
        f"Human source: `{args.human_source}`",
        f"AI source: `{args.ai_source}`",
        "",
        "## Train/Eval Splits",
        "",
    ]
    for label, split in splits.items():
        lines.append(
            f"- `{label}` train: {len(group_by_piece(split['train']))} pieces, "
            f"{len(split['train'])} events; eval: {len(group_by_piece(split['eval']))} "
            f"pieces, {len(split['eval'])} events"
        )
    lines.extend(["", "## Cell Means", ""])
    for row in cell_summary:
        lines.append(
            f"- model=`{row['model_label']}`, eval=`{row['eval_label']}`: "
            f"mean={float(row['mean_surprisal_mean']):.3f}, "
            f"p90={float(row['p90_surprisal_mean']):.3f}, "
            f"pieces={row['pieces']}"
        )
    lines.extend(["", "## Direction Tests", ""])
    for row in direction_summary:
        lines.append(
            f"- `{row['direction']}`: within={float(row['within_mean_surprisal']):.3f}, "
            f"cross={float(row['cross_mean_surprisal']):.3f}, "
            f"cross-within={float(row['cross_minus_within']):.3f}; "
            f"p90 diff={float(row['p90_cross_minus_within']):.3f}"
        )
    output.write_text("\n".join(lines), encoding="utf-8")


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
