from __future__ import annotations

import argparse
import csv
import tarfile
import urllib.request
from pathlib import Path


BASE = "https://storage.googleapis.com/magentadata/datasets/cocochorales/cocochorales_full_v1_zipped/note_expression/{split}/{chunk}.tar.bz2"
DEFAULT_CHUNKS = {
    "train": [1],
    "valid": [1],
    "test": [1],
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download symbolic note_expression chunks from CocoChorales."
    )
    parser.add_argument("--output-dir", default="datasets/raw/cocochorales_note_expression")
    parser.add_argument(
        "--chunks",
        nargs="*",
        help="Optional split:chunk entries, e.g. train:1 valid:1 test:1.",
    )
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    output = Path(args.output_dir)
    archive_dir = output / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    chunks = parse_chunks(args.chunks)
    manifest_rows: list[dict] = []

    for split, split_chunks in chunks.items():
        for chunk in split_chunks:
            url = BASE.format(split=split, chunk=chunk)
            destination = archive_dir / split / f"{chunk}.tar.bz2"
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.stat().st_size == 0:
                print(f"Downloading CocoChorales note_expression {split}:{chunk}...")
                download(url, destination)
            if args.extract:
                extract_to = output / "extracted" / split / str(chunk)
                if not extract_to.exists():
                    print(f"Extracting {destination}...")
                    extract_to.mkdir(parents=True, exist_ok=True)
                    with tarfile.open(destination, "r:bz2") as tar:
                        tar.extractall(extract_to)
            manifest_rows.append(
                {
                    "split": split,
                    "chunk": chunk,
                    "url": url,
                    "path": str(destination),
                    "bytes": destination.stat().st_size,
                }
            )

    write_manifest(output / "manifest.csv", manifest_rows)
    print(f"Wrote CocoChorales note_expression chunks to {output}")


def parse_chunks(entries: list[str] | None) -> dict[str, list[int]]:
    if not entries:
        return DEFAULT_CHUNKS
    chunks: dict[str, list[int]] = {}
    for entry in entries:
        split, value = entry.split(":", 1)
        chunks.setdefault(split, []).append(int(value))
    return chunks


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "music-surprisal-pipeline"})
    tmp = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as handle:
        handle.write(response.read())
    tmp.replace(destination)


def write_manifest(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "chunk", "url", "path", "bytes"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
