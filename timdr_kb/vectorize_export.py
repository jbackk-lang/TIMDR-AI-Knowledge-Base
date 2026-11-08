"""Export source corpus as Cloudflare Vectorize V2 NDJSON using the shared 384d model."""
import argparse
import hashlib
import json
from pathlib import Path
from timdr_kb.cli import chunks, embedding

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="knowledge/seed.jsonl")
    p.add_argument("--output", default="vectorize-seed.ndjson")
    args = p.parse_args()
    items = []
    with open(args.input, encoding="utf-8") as src:
        for line in src:
            if not line.strip():
                continue
            record = json.loads(line)
            for n, part in enumerate(chunks(record["text"])):
                identity = record["url"] + ":" + str(n)
                items.append((hashlib.sha256(identity.encode()).hexdigest()[:48], part, record, n))
    out = Path(args.output)
    with out.open("w", encoding="utf-8") as dst:
        for start in range(0, len(items), 32):
            batch = items[start:start + 32]
            vectors = embedding([x[1] for x in batch])
            for (id_, part, record, n), vector in zip(batch, vectors):
                obj = {
                    "id": id_,
                    "values": vector,
                    "metadata": {
                        "branch": record.get("branch", "unclassified"),
                        "source_type": record.get("source_type", "unknown"),
                        "repo": record.get("repo", "")[:64],
                        "status": record.get("status", "unverified"),
                        "url": record["url"][:1000],
                        "chunk": n,
                        "excerpt": part[:1500],
                    },
                }
                dst.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Exported {len(items)} vectors to {out}")

if __name__ == "__main__":
    main()
