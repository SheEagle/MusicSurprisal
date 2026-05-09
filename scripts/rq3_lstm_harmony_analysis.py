from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music_surprisal.data import Event, group_by_piece
from music_surprisal.harmony_labels import simplify_chord
from scripts.dcml_period_time_series_analysis import attach_periods, load_period_metadata
from scripts.run_formal_experiment import load_events


PITCH_START = 12
CHORDS = ["T", "D", "S", "other"]
CHORD_TO_ID = {label: index for index, label in enumerate(CHORDS)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RQ3 LSTM test: does harmonic function improve long-context melody prediction?"
    )
    parser.add_argument("--events", default="data/events_dcml_classical.csv")
    parser.add_argument(
        "--metadata",
        default="datasets/raw/dcml/dcml_corpora/dcml_corpora.metadata.tsv",
    )
    parser.add_argument(
        "--output",
        default="output/formal_dcml_jtc_all_rq/dcml_period_rq3_lstm",
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--embedding-size", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--chunk-len", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    torch = import_torch()
    set_seed(args.seed, torch)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    period_meta = load_period_metadata(Path(args.metadata))
    events = attach_periods(load_events(args.events, sources={"dcml"}), period_meta)
    scoped_events = [
        event
        for event in events
        if event.genre in {"classical_period", "romantic_period"}
    ]
    train_pieces = encode_pieces([event for event in scoped_events if event.split == "train"])
    eval_pieces = encode_pieces([event for event in scoped_events if event.split != "train"])
    if not train_pieces or not eval_pieces:
        raise ValueError("Need train and held-out pieces for LSTM RQ3.")

    melody_model = PitchLSTM(
        torch=torch,
        model_kind="melody_only",
        embedding_size=args.embedding_size,
        hidden_size=args.hidden_size,
    )
    current_harmony_model = PitchLSTM(
        torch=torch,
        model_kind="current_harmony",
        embedding_size=args.embedding_size,
        hidden_size=args.hidden_size,
    )
    harmony_history_model = PitchLSTM(
        torch=torch,
        model_kind="harmony_history",
        embedding_size=args.embedding_size,
        hidden_size=args.hidden_size,
    )
    melody_history = train_model(torch, melody_model, train_pieces, args)
    current_harmony_history = train_model(torch, current_harmony_model, train_pieces, args)
    harmony_history_history = train_model(torch, harmony_history_model, train_pieces, args)

    rows = evaluate_models(
        torch, melody_model, current_harmony_model, harmony_history_model, eval_pieces
    )
    summary = summarize_periods(rows)
    effects = period_effects(rows)

    write_csv(output / "rq3_lstm_event_surprisal_sample.csv", rows[:100000])
    write_csv(output / "rq3_lstm_period_summary.csv", summary)
    write_csv(output / "rq3_lstm_period_effects.csv", effects)
    (output / "rq3_lstm_training_history.json").write_text(
        json.dumps(
            {
                "model_a_melody_only": melody_history,
                "model_b_current_harmony": current_harmony_history,
                "model_c_harmony_history": harmony_history_history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_summary(output / "RQ3_LSTM_HARMONY_SUMMARY.md", args, summary, effects)
    print(f"Wrote RQ3 LSTM harmony analysis to {output}")


def import_torch():
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        raise SystemExit(
            "PyTorch is required for this optional LSTM analysis. Install it first, "
            "for example: python -m pip install torch"
        ) from exc
    return torch


def set_seed(seed: int, torch) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def encode_pieces(events: list[Event]) -> list[dict]:
    pieces = []
    for piece_id, piece_events in group_by_piece(events).items():
        if len(piece_events) < 2:
            continue
        pieces.append(
            {
                "piece_id": piece_id,
                "period": piece_events[0].genre,
                "pitches": [event.pitch % 12 for event in piece_events],
                "chords": [
                    CHORD_TO_ID.get(simplify_chord(event.chord, "function"), CHORD_TO_ID["other"])
                    for event in piece_events
                ],
                "onsets": [event.onset for event in piece_events],
                "raw_chords": [event.chord for event in piece_events],
                "boundaries": [int(event.boundary) for event in piece_events],
            }
        )
    return pieces


class PitchLSTM:
    def __init__(self, *, torch, model_kind: str, embedding_size: int, hidden_size: int):
        import torch.nn as nn

        if model_kind not in {"melody_only", "current_harmony", "harmony_history"}:
            raise ValueError(f"Unknown model kind: {model_kind}")

        class Module(nn.Module):
            def __init__(self):
                super().__init__()
                self.model_kind = model_kind
                self.pitch_embedding = nn.Embedding(13, embedding_size)
                self.chord_embedding = nn.Embedding(len(CHORDS), embedding_size)
                if model_kind == "harmony_history":
                    lstm_input_size = embedding_size * 2
                    output_input_size = hidden_size
                elif model_kind == "current_harmony":
                    lstm_input_size = embedding_size
                    output_input_size = hidden_size + embedding_size
                else:
                    lstm_input_size = embedding_size
                    output_input_size = hidden_size
                self.lstm = nn.LSTM(lstm_input_size, hidden_size, batch_first=True)
                self.output = nn.Linear(output_input_size, 12)

            def forward(self, pitch_input, chord_input):
                pitch_emb = self.pitch_embedding(pitch_input)
                chord_emb = self.chord_embedding(chord_input)
                if self.model_kind == "harmony_history":
                    features = torch.cat([pitch_emb, chord_emb], dim=-1)
                    states, _ = self.lstm(features)
                    output_features = states
                elif self.model_kind == "current_harmony":
                    states, _ = self.lstm(pitch_emb)
                    output_features = torch.cat([states, chord_emb], dim=-1)
                else:
                    states, _ = self.lstm(pitch_emb)
                    output_features = states
                return self.output(output_features)

        self.module = Module()
        self.model_kind = model_kind


def train_model(torch, model: PitchLSTM, pieces: list[dict], args) -> list[dict]:
    import torch.nn.functional as F

    module = model.module
    optimizer = torch.optim.Adam(module.parameters(), lr=args.learning_rate)
    chunks = make_chunks(pieces, chunk_len=args.chunk_len)
    history = []
    for epoch in range(args.epochs):
        random.shuffle(chunks)
        losses = []
        for batch in batched(chunks, args.batch_size):
            pitch_input, chord_input, targets = tensorize_batch(torch, batch)
            logits = module(pitch_input, chord_input)
            loss = F.cross_entropy(logits.reshape(-1, 12), targets.reshape(-1))
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        history.append({"epoch": epoch + 1, "mean_loss_nats": mean(losses)})
    return history


def make_chunks(pieces: list[dict], chunk_len: int) -> list[dict]:
    chunks = []
    for piece in pieces:
        pitches = piece["pitches"]
        chords = piece["chords"]
        for start in range(0, len(pitches), chunk_len):
            target = pitches[start : start + chunk_len]
            chord_chunk = chords[start : start + chunk_len]
            if len(target) < 2:
                continue
            prev = [PITCH_START if start == 0 else pitches[start - 1]] + target[:-1]
            chunks.append({"pitch_input": prev, "chord_input": chord_chunk, "target": target})
    return chunks


def batched(items: list[dict], batch_size: int):
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def tensorize_batch(torch, batch: list[dict]):
    max_len = max(len(item["target"]) for item in batch)
    pitch_rows, chord_rows, target_rows = [], [], []
    for item in batch:
        pad = max_len - len(item["target"])
        pitch_rows.append(item["pitch_input"] + [PITCH_START] * pad)
        chord_rows.append(item["chord_input"] + [CHORD_TO_ID["other"]] * pad)
        target_rows.append(item["target"] + [0] * pad)
    return (
        torch.tensor(pitch_rows, dtype=torch.long),
        torch.tensor(chord_rows, dtype=torch.long),
        torch.tensor(target_rows, dtype=torch.long),
    )


def evaluate_models(
    torch,
    melody_model: PitchLSTM,
    current_harmony_model: PitchLSTM,
    harmony_history_model: PitchLSTM,
    pieces: list[dict],
) -> list[dict]:
    import torch.nn.functional as F

    rows = []
    melody_model.module.eval()
    current_harmony_model.module.eval()
    harmony_history_model.module.eval()
    with torch.no_grad():
        for piece in pieces:
            targets = piece["pitches"]
            pitch_input = [PITCH_START] + targets[:-1]
            chord_input = piece["chords"]
            pitch_tensor = torch.tensor([pitch_input], dtype=torch.long)
            chord_tensor = torch.tensor([chord_input], dtype=torch.long)
            target_tensor = torch.tensor([targets], dtype=torch.long)
            melody_logits = melody_model.module(pitch_tensor, chord_tensor)
            current_harmony_logits = current_harmony_model.module(pitch_tensor, chord_tensor)
            harmony_history_logits = harmony_history_model.module(pitch_tensor, chord_tensor)
            melody_logp = F.log_softmax(melody_logits, dim=-1)
            current_harmony_logp = F.log_softmax(current_harmony_logits, dim=-1)
            harmony_history_logp = F.log_softmax(harmony_history_logits, dim=-1)
            for index, pitch in enumerate(targets):
                melody_surprisal = -float(melody_logp[0, index, pitch]) / math.log(2)
                current_harmony_surprisal = (
                    -float(current_harmony_logp[0, index, pitch]) / math.log(2)
                )
                harmony_history_surprisal = (
                    -float(harmony_history_logp[0, index, pitch]) / math.log(2)
                )
                rows.append(
                    {
                        "piece_id": piece["piece_id"],
                        "period": piece["period"],
                        "event_index": index,
                        "onset": piece["onsets"][index],
                        "pitch_class": pitch,
                        "raw_chord": piece["raw_chords"][index],
                        "chord_function": CHORDS[piece["chords"][index]],
                        "boundary": piece["boundaries"][index],
                        "surprisal_model_a_melody_only": melody_surprisal,
                        "surprisal_model_b_current_harmony": current_harmony_surprisal,
                        "surprisal_model_c_harmony_history": harmony_history_surprisal,
                        "gain_a_to_b_current_harmony": melody_surprisal
                        - current_harmony_surprisal,
                        "gain_a_to_c_harmony_history": melody_surprisal
                        - harmony_history_surprisal,
                        "gain_b_to_c_history_over_current": current_harmony_surprisal
                        - harmony_history_surprisal,
                    }
                )
    return rows


def summarize_periods(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["period"]].append(row)
    output = []
    for period, period_rows in sorted(grouped.items()):
        gain_ab = [float(row["gain_a_to_b_current_harmony"]) for row in period_rows]
        gain_ac = [float(row["gain_a_to_c_harmony_history"]) for row in period_rows]
        gain_bc = [
            float(row["gain_b_to_c_history_over_current"]) for row in period_rows
        ]
        melody = [float(row["surprisal_model_a_melody_only"]) for row in period_rows]
        current = [
            float(row["surprisal_model_b_current_harmony"]) for row in period_rows
        ]
        history = [
            float(row["surprisal_model_c_harmony_history"]) for row in period_rows
        ]
        output.append(
            {
                "period": period,
                "events": len(period_rows),
                "pieces": len({row["piece_id"] for row in period_rows}),
                "mean_surprisal_a_melody_only": mean(melody),
                "mean_surprisal_b_current_harmony": mean(current),
                "mean_surprisal_c_harmony_history": mean(history),
                "mean_gain_a_to_b": mean(gain_ab),
                "mean_gain_a_to_c": mean(gain_ac),
                "mean_gain_b_to_c": mean(gain_bc),
                "median_gain_a_to_b": median(gain_ab),
                "median_gain_a_to_c": median(gain_ac),
                "median_gain_b_to_c": median(gain_bc),
                "positive_rate_a_to_b": sum(1 for value in gain_ab if value > 0)
                / len(gain_ab),
                "positive_rate_a_to_c": sum(1 for value in gain_ac if value > 0)
                / len(gain_ac),
                "positive_rate_b_to_c": sum(1 for value in gain_bc if value > 0)
                / len(gain_bc),
                "sd_gain_a_to_c": pstdev(gain_ac) if len(gain_ac) > 1 else 0.0,
            }
        )
    return output


def period_effects(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["period"], row["chord_function"])].append(row)
    output = []
    for (period, chord), group_rows in sorted(grouped.items()):
        gain_ab = [float(row["gain_a_to_b_current_harmony"]) for row in group_rows]
        gain_ac = [float(row["gain_a_to_c_harmony_history"]) for row in group_rows]
        gain_bc = [
            float(row["gain_b_to_c_history_over_current"]) for row in group_rows
        ]
        output.append(
            {
                "period": period,
                "chord_function": chord,
                "events": len(group_rows),
                "mean_gain_a_to_b": mean(gain_ab),
                "mean_gain_a_to_c": mean(gain_ac),
                "mean_gain_b_to_c": mean(gain_bc),
                "positive_rate_a_to_b": sum(1 for value in gain_ab if value > 0)
                / len(gain_ab),
                "positive_rate_a_to_c": sum(1 for value in gain_ac if value > 0)
                / len(gain_ac),
                "positive_rate_b_to_c": sum(1 for value in gain_bc if value > 0)
                / len(gain_bc),
            }
        )
    return output


def write_summary(output: Path, args, summary: list[dict], effects: list[dict]) -> None:
    lines = [
        "# RQ3 LSTM Harmony Summary",
        "",
        "This optional analysis compares three long-context neural sequence models:",
        "",
        "- Model A: melody-only LSTM. Previous pitch classes -> current pitch class.",
        "- Model B: melody + current harmony. Pitch-history LSTM plus current T/D/S/other at the output layer.",
        "- Model C: melody + harmony history sequence. Pitch and T/D/S/other are both recurrent inputs, so the hidden state can encode harmonic progression.",
        "",
        "Gain A->B = Model A surprisal minus Model B surprisal.",
        "Gain A->C = Model A surprisal minus Model C surprisal.",
        "Gain B->C = Model B surprisal minus Model C surprisal.",
        "Positive gain means the richer harmony model improved prediction.",
        "",
        f"Training: epochs={args.epochs}, hidden_size={args.hidden_size}, chunk_len={args.chunk_len}.",
        "",
        "## Period Summary",
        "",
    ]
    for row in summary:
        lines.append(
            f"- `{row['period']}`: "
            f"A={float(row['mean_surprisal_a_melody_only']):.4f}, "
            f"B={float(row['mean_surprisal_b_current_harmony']):.4f}, "
            f"C={float(row['mean_surprisal_c_harmony_history']):.4f}, "
            f"A->B={float(row['mean_gain_a_to_b']):.4f}, "
            f"A->C={float(row['mean_gain_a_to_c']):.4f}, "
            f"B->C={float(row['mean_gain_b_to_c']):.4f}"
        )
    lines.extend(["", "## By Harmonic Function", ""])
    for row in effects:
        lines.append(
            f"- `{row['period']}` / `{row['chord_function']}`: "
            f"A->B={float(row['mean_gain_a_to_b']):.4f}, "
            f"A->C={float(row['mean_gain_a_to_c']):.4f}, "
            f"B->C={float(row['mean_gain_b_to_c']):.4f}, "
            f"events={row['events']}"
        )
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


if __name__ == "__main__":
    main()
