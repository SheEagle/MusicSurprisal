from __future__ import annotations

import argparse
from pathlib import Path

from .analysis import run_pipeline
from .data import read_events
from .midi_io import convert_midi_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run music n-gram surprisal analyses.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run on a normalized event CSV.")
    run.add_argument("--events", required=True, help="Path to event CSV.")
    run.add_argument("--output", required=True, help="Output directory.")
    run.add_argument("--order", type=int, default=3, help="N-gram order.")
    run.add_argument(
        "--token-kind",
        default="pitch",
        choices=["pitch", "pitch_duration", "pitch_chord"],
    )
    run.add_argument("--pre-window", type=int, default=3)
    run.add_argument("--permutations", type=int, default=1000)
    run.add_argument(
        "--rq123-genres",
        nargs="*",
        default=["classical", "jazz"],
        help="Genres to include in RQ1-RQ3 outputs. Defaults to classical jazz.",
    )
    run.add_argument(
        "--rq4-sources",
        nargs="*",
        help="Optional source names to include in RQ4 classification, e.g. jsb js_fake.",
    )

    demo = subparsers.add_parser("run-demo", help="Run on the bundled demo table.")
    demo.add_argument("--output", required=True, help="Output directory.")
    demo.add_argument("--order", type=int, default=3)
    demo.add_argument(
        "--token-kind",
        default="pitch",
        choices=["pitch", "pitch_duration", "pitch_chord"],
    )
    demo.add_argument("--pre-window", type=int, default=3)
    demo.add_argument("--permutations", type=int, default=200)
    demo.add_argument(
        "--rq123-genres",
        nargs="*",
        default=["classical", "jazz"],
        help="Genres to include in RQ1-RQ3 outputs.",
    )
    demo.add_argument(
        "--rq4-sources",
        nargs="*",
        help="Optional source names to include in RQ4 classification.",
    )

    convert = subparsers.add_parser(
        "convert-midi", help="Convert a MIDI directory into the normalized event CSV."
    )
    convert.add_argument("--midi-dir", required=True)
    convert.add_argument("--output-events", required=True)
    convert.add_argument("--source", required=True)
    convert.add_argument("--genre", required=True)
    convert.add_argument("--split", default="train")
    convert.add_argument("--is-ai", action="store_true")
    convert.add_argument(
        "--boundary-mode",
        default="measure",
        choices=["measure", "none"],
        help="Use measure-start boundaries or no boundaries.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "convert-midi":
        path = convert_midi_directory(
            args.midi_dir,
            args.output_events,
            source=args.source,
            genre=args.genre,
            split=args.split,
            is_ai=args.is_ai,
            boundary_mode=args.boundary_mode,
        )
        print(f"Wrote: {path}")
        return

    if args.command == "run-demo":
        events_path = Path(__file__).resolve().parent.parent / "examples" / "demo_events.csv"
    else:
        events_path = Path(args.events)

    events = read_events(events_path)
    paths = run_pipeline(
        events,
        args.output,
        order=args.order,
        token_kind=args.token_kind,
        pre_window=args.pre_window,
        permutations=args.permutations,
        rq123_genres=set(args.rq123_genres) if args.rq123_genres else None,
        rq4_sources=set(args.rq4_sources) if args.rq4_sources else None,
    )
    print("Wrote:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
