"""Load committed source corpus into the unified Qdrant vector index."""
import json
from pathlib import Path
from timdr_kb.cli import client, ingest

def main():
    path = Path(__file__).resolve().parent.parent / "knowledge" / "seed.jsonl"
    with path.open(encoding="utf-8") as f:
        records = (json.loads(line) for line in f if line.strip())
        print("Indexed seed chunks:", ingest(client(), records))

if __name__ == "__main__":
    main()
