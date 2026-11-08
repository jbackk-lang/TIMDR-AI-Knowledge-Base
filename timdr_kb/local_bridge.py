"""Bridge localhost embedding HTTP API to the existing protected Vectorize Worker.

No public endpoints, new Cloudflare deployments, or paid models required.
Uses TIMDR_SEARCH_TOKEN from the existing Windows DPAPI launcher.
"""
import argparse
import json
import os

import requests
from timdr_kb.vectorize_search import rank_matches

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LOCAL_URL = "http://127.0.0.1:8789/embed"
WORKER_URL = "https://timdr-vector-search.jbackk.workers.dev/search"


def search(question, limit=5, branch=None):
    if not 2 <= len(question.strip()) <= 180:
        raise ValueError("Question must be 2..180 characters")
    token = os.getenv("TIMDR_SEARCH_TOKEN")
    local_token = os.getenv("TIMDR_EMBEDDING_TOKEN")
    if not token:
        raise RuntimeError("Missing TIMDR_SEARCH_TOKEN; use start-timdr.ps1 -Bridge")
    if not local_token:
        raise RuntimeError("Missing TIMDR_EMBEDDING_TOKEN in this process")
    embedding_response = requests.post(
        LOCAL_URL,
        headers={"Authorization": "Bearer " + local_token},
        json={"text": question.strip(), "model": MODEL},
        timeout=60,
    )
    embedding_response.raise_for_status()
    vector = embedding_response.json().get("vector")
    if not isinstance(vector, list) or len(vector) != 384 or any(
        not isinstance(v, (float, int)) or isinstance(v, bool) for v in vector
    ):
        raise RuntimeError("Embedding API did not return a 384-dimensional vector")
    worker_response = requests.post(
        WORKER_URL,
        headers={"Authorization": "Bearer " + token},
        json={"vector": vector, "topK": 10, "filter": {"branch": branch} if branch else {}},
        timeout=60,
    )
    worker_response.raise_for_status()
    ranked = rank_matches(question, worker_response.json().get("matches", []))
    results = []
    seen = set()
    for _, similarity, _, match in ranked:
        metadata = match.get("metadata") or {}
        url = metadata.get("url") or ""
        excerpt = (metadata.get("excerpt") or "").strip()
        if not url.startswith("https://github.com/") or not excerpt or url in seen:
            continue
        seen.add(url)
        results.append({
            "source": "S" + str(len(results) + 1),
            "url": url,
            "score": round(similarity, 4),
            "branch": metadata.get("branch"),
            "excerpt": excerpt[:750],
        })
        if len(results) >= limit:
            break
    return results


def main():
    parser = argparse.ArgumentParser(description="Local embedding HTTP -> protected Cloudflare Vectorize")
    parser.add_argument("question")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--branch")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be 1..10")
    try:
        results = search(args.question, args.limit, args.branch)
    except requests.exceptions.ConnectionError:
        parser.exit(2, "Connection failed: ensure local embedding server is running on 127.0.0.1:8789.\n")
    except (requests.exceptions.RequestException, RuntimeError, ValueError) as exc:
        parser.exit(2, "Search failed: " + str(exc) + "\n")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
