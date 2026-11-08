"""Protected Cloudflare Vectorize search with optional lexical reranking.

Uses the same 384-dimensional embedding model as ingestion.
Hybrid mode reranks only the semantic candidates returned by Vectorize;
it is NOT a full-text search over the whole corpus.
"""
import argparse
import json
import os
import re
import unicodedata
from urllib.parse import unquote, urlsplit

import requests
from timdr_kb.cli import embedding

ALIASES = {
    "chronoproces": ("chronoprocess",),
    "chronoprocess": ("chronoproces",),
    "geometria": ("geometry",),
    "geometry": ("geometria",),
}

def tokens(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))

def lexical_score(query, metadata):
    terms = tokens(query)
    if not terms:
        return 0.0
    expanded = set(terms)
    for term in terms:
        expanded.update(ALIASES.get(term, ()))
    url = metadata.get("url") or ""
    filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    body = tokens(metadata.get("excerpt") or "")
    name = tokens(filename)
    # Normalize by query length; filename relevance gets an additional boost.
    hits = sum(any(t in body for t in (term, *ALIASES.get(term, ()))) for term in terms)
    name_hits = sum(any(t in name for t in (term, *ALIASES.get(term, ()))) for term in terms)
    return min(1.0, (hits + 2 * name_hits) / max(1, len(terms)))

def rank_matches(query, matches, hybrid=True):
    ranked = []
    for match in matches:
        meta = match.get("metadata") or {}
        similarity = float(match.get("score") or 0.0)
        lexical = lexical_score(query, meta) if hybrid else 0.0
        # Semantic similarity remains the main signal; bounded lexical bonus.
        rank = similarity + (0.12 * lexical if hybrid else 0.0)
        ranked.append((rank, similarity, lexical, match))
    return sorted(ranked, key=lambda item: item[0], reverse=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--branch")
    parser.add_argument("--source")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--semantic-only", action="store_true",
                        help="Disable local lexical reranking")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10 (Worker limit)")
    url = os.getenv("TIMDR_SEARCH_URL", "")
    token = os.getenv("TIMDR_SEARCH_TOKEN", "")
    if not url.startswith("https://") or not token:
        parser.error("Set TIMDR_SEARCH_URL (https://.../search) and TIMDR_SEARCH_TOKEN")
    filt = {}
    if args.branch: filt["branch"] = args.branch
    if args.source: filt["source_type"] = args.source
    response = requests.post(
        url, headers={"Authorization": "Bearer " + token},
        json={"vector": embedding([args.query])[0], "topK": 10, "filter": filt},
        timeout=45,
    )
    response.raise_for_status()
    matches = response.json().get("matches", [])
    for rank, similarity, lexical, match in rank_matches(
        args.query, matches, hybrid=not args.semantic_only
    )[:args.limit]:
        metadata = match.get("metadata") or {}
        print(json.dumps({
            "score": round(similarity, 4),
            "rank_score": round(rank, 4),
            "lexical_score": round(lexical, 4),
            "branch": metadata.get("branch"),
            "source_type": metadata.get("source_type"),
            "url": metadata.get("url"),
            "excerpt": (metadata.get("excerpt") or "")[:500],
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
