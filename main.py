#!/usr/bin/env python3
import argparse
import csv
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main_loop")


def read_urls(csv_path: str) -> list[str]:
    path = Path(csv_path)
    if not path.exists():
        log.error("CSV file not found: %s", path)
        sys.exit(1)

    urls = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "URL" not in reader.fieldnames:
            log.error("CSV missing 'URL' column. Found: %s", reader.fieldnames)
            sys.exit(1)
        for row in reader:
            url = row["URL"].strip()
            if url:
                urls.append(url)
    log.info("Loaded %d URLs from %s", len(urls), path)
    return urls


def main():
    parser = argparse.ArgumentParser(
        description="Queue superscrape jobs from a CSV file."
    )
    parser.add_argument(
        "--csv",
        default="dataset/species.csv",
        help="Path to CSV file with URL column (default: dataset/species.csv)",
    )
    parser.add_argument(
        "--schema",
        default="species.schema.json",
        help="JSON Schema file (default: species.schema.json)",
    )
    parser.add_argument(
        "--table",
        help="Supabase table name",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "groq", "nvidia"],
        default="ollama",
        help="LLM provider (default: ollama)",
    )
    parser.add_argument(
        "--skip",
        help="Comma-separated column names to skip",
    )
    args = parser.parse_args()

    urls = read_urls(args.csv)

    for i, url in enumerate(urls, 1):
        cmd = ["python", "superscrape.py", url]

        if args.schema:
            cmd.append(args.schema)
        if args.table:
            cmd.extend(["--table", args.table])
        if args.provider:
            cmd.extend(["--provider", args.provider])
        if args.skip:
            cmd.extend(["--skip", args.skip])

        log.info("[%d/%d] Processing %s", i, len(urls), url)
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            log.error("[%d/%d] Failed: %s", i, len(urls), url)
            continue

    log.info("All done.")


if __name__ == "__main__":
    main()
