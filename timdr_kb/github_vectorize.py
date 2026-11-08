"""Export an allowlisted public GitHub repository to Cloudflare Vectorize NDJSON.

Usage: python -m timdr_kb.github_vectorize jbackk-lang/GIA-TIMDR --limit 100
No credentials are written to disk. The existing Qdrant backend is untouched.
"""
import argparse
import hashlib
import json
from pathlib import Path

from timdr_kb.cli import chunks, embedding, github_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", help="Explicitly authorized public owner/repository")
    parser.add_argument("--limit", type=int, default=100, help="Maximum eligible files")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 3000:
        parser.error("--limit must be between 1 and 3000")
    out = Path(args.output or ("vectorize-" + args.repository.replace("/", "-") + ".ndjson"))
    count = 0
    batch = []

    def flush(destination):
        nonlocal count
        if not batch:
            return
        vectors = embedding([item[1] for item in batch])
        for (identity, part, record, index), vector in zip(batch, vectors):
            destination.write(json.dumps({
                "id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:48],
                "values": vector,
                "metadata": {
                    "branch": record.get("branch", "unclassified"),
                    "source_type": record.get("source_type", "github"),
                    "repo": record.get("repo", "")[:64],
                    "status": record.get("status", "source_unverified"),
                    "url": record["url"][:1000],
                    "chunk": index,
                    "excerpt": part[:1500],
                },
            }, ensure_ascii=False) + "\n")
            count += 1
        batch.clear()

    with out.open("w", encoding="utf-8") as destination:
        for record in github_records(args.repository, limit=args.limit):
            for index, part in enumerate(chunks(record["text"])):
                identity = record["url"] + ":" + str(index)
                batch.append((identity, part, record, index))
                if len(batch) == 32:
                    flush(destination)
        flush(destination)
    print(f"Exported {count} vectors to {out}")


if __name__ == "__main__":
    main()
