"""Query the protected Cloudflare Worker using the SAME embedding model as ingestion.

Environment:
 TIMDR_SEARCH_URL=https://...workers.dev/search
 TIMDR_SEARCH_TOKEN=<secret>
"""
import argparse
import json
import os
import requests
from timdr_kb.cli import embedding

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--branch")
    parser.add_argument("--source")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    url = os.getenv("TIMDR_SEARCH_URL", "")
    token = os.getenv("TIMDR_SEARCH_TOKEN", "")
    if not url.startswith("https://") or not token:
        parser.error("Set TIMDR_SEARCH_URL (https://.../search) and TIMDR_SEARCH_TOKEN")
    filt = {}
    if args.branch: filt["branch"] = args.branch
    if args.source: filt["source_type"] = args.source
    response = requests.post(url, headers={"Authorization": "Bearer " + token},
        json={"vector": embedding([args.query])[0], "topK": args.limit, "filter": filt},
        timeout=45)
    response.raise_for_status()
    for match in response.json().get("matches", []):
        metadata = match.get("metadata") or {}
        print(json.dumps({
            "score": round(match.get("score", 0), 4),
            "branch": metadata.get("branch"),
            "source_type": metadata.get("source_type"),
            "url": metadata.get("url"),
            "excerpt": metadata.get("excerpt", "")[:500],
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
