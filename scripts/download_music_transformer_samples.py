from __future__ import annotations

import argparse
import csv
import random
import urllib.request
from pathlib import Path


BASE_URL = "https://magentadata.storage.googleapis.com/piano_transformer/midi/a1/{index}.mid"
MAX_INDEX = 99974


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Music Transformer MIDI samples.")
    parser.add_argument("--output-dir", default="datasets/raw/music_transformer/a1")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--indices", nargs="*", type=int, help="Explicit sample indices.")
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    indices = args.indices or random_indices(args.count, args.seed)
    manifest_rows: list[dict] = []

    for index in indices:
        if index < 0 or index > MAX_INDEX:
            raise ValueError(f"Music Transformer index out of range: {index}")
        url = BASE_URL.format(index=index)
        destination = output / f"{index}.mid"
        if not destination.exists() or destination.stat().st_size == 0:
            print(f"Downloading {index}...")
            download(url, destination)
        manifest_rows.append(
            {
                "index": index,
                "url": url,
                "path": str(destination),
                "bytes": destination.stat().st_size,
            }
        )

    write_manifest(output / "manifest.csv", manifest_rows)
    print(f"Wrote {len(manifest_rows)} Music Transformer samples to {output}")


def random_indices(count: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    return sorted(rng.sample(range(MAX_INDEX + 1), count))


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "music-surprisal-pipeline"})
    tmp = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as handle:
        handle.write(response.read())
    tmp.replace(destination)


def write_manifest(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["index", "url", "path", "bytes"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
