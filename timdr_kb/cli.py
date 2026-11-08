"""Unified TIMDR vector index: GitHub + arXiv metadata."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests
from qdrant_client import QdrantClient, models

COLLECTION = "timdr_unified_v1"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
ALLOWED = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".tex", ".rst"}


def client():
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY") or None,
    )


def embedding(texts):
    from fastembed import TextEmbedding
    global _embedder
    if "_embedder" not in globals():
        _embedder = TextEmbedding(model_name=MODEL)
    return [v.tolist() for v in _embedder.embed(texts)]


def chunks(text, size=1700, overlap=250):
    if not text.strip():
        return
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", pos + size // 2, end)
            if boundary > pos:
                end = boundary + 1
        yield text[pos:end]
        if end == len(text):
            break
        pos = max(pos + 1, end - overlap)


def setup(db):
    if not db.collection_exists(COLLECTION):
        db.create_collection(
            COLLECTION,
            vectors_config=models.VectorParams(
                size=DIM, distance=models.Distance.COSINE, on_disk=True
            ),
            on_disk_payload=True,
        )
    for field in ("source_type", "branch", "repo", "status"):
        try:
            db.create_payload_index(
                COLLECTION, field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def flush(db, batch):
    vectors = embedding([item[2] for item in batch])
    points = [
        models.PointStruct(id=pid, vector=vector, payload=payload)
        for (pid, payload, _), vector in zip(batch, vectors)
    ]
    db.upsert(collection_name=COLLECTION, points=points, wait=True)
    return len(points)


def ingest(db, records):
    import uuid
    setup(db)
    count = 0
    batch = []
    for record in records:
        for index, part in enumerate(chunks(record["text"])):
            metadata = {k: v for k, v in record.items() if k != "text"}
            metadata["text"] = part
            metadata["chunk"] = index
            identity = metadata["url"] + ":" + str(index)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
            batch.append((point_id, metadata, part))
            if len(batch) >= 32:
                count += flush(db, batch)
                batch.clear()
    if batch:
        count += flush(db, batch)
    return count


def guess_branch(path):
    p = path.lower()
    if "meta" in p:
        return "META"
    if any(w in p for w in ("geometry", "weingarten", "curvature", "axioms_g")):
        return "G"
    if any(w in p for w in ("modal", "phase", "axioms_k")):
        return "K"
    if any(w in p for w in ("signal", "resonance", "axioms_s")):
        return "M/S"
    return "unclassified"


def github_records(repo, limit=3000):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "TIMDR-KB/0.1",
    }
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    api = "https://api.github.com/repos/" + repo
    response = requests.get(api, headers=headers, timeout=30)
    response.raise_for_status()
    default_branch = response.json()["default_branch"]
    branch = requests.get(
        api + "/branches/" + quote(default_branch), headers=headers, timeout=30
    )
    branch.raise_for_status()
    sha = branch.json()["commit"]["sha"]
    tree = requests.get(
        api + "/git/trees/" + sha,
        params={"recursive": "1"},
        headers=headers, timeout=60,
    )
    tree.raise_for_status()
    data = tree.json()
    if data.get("truncated"):
        raise RuntimeError("GitHub tree truncated: use per-directory ingestion")
    selected = [
        entry for entry in data.get("tree", [])
        if entry["type"] == "blob"
        and Path(entry["path"]).suffix.lower() in ALLOWED
        and entry.get("size", 0) <= 250_000
    ][:limit]
    for entry in selected:
        path = entry["path"]
        raw_url = (
            f"https://raw.githubusercontent.com/{repo}/{sha}/{quote(path)}"
        )
        response = requests.get(
            raw_url, headers={"User-Agent": "TIMDR-KB/0.1"}, timeout=30
        )
        if response.status_code != 200:
            continue
        yield {
            "url": f"https://github.com/{repo}/blob/{sha}/{quote(path)}",
            "text": response.text,
            "repo": repo,
            "commit": sha,
            "path": path,
            "branch": guess_branch(path),
            "source_type": "github",
            "status": "source_unverified",
        }


def arxiv_records(query, maximum=30):
    import feedparser
    response = requests.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": query,
            "start": 0,
            "max_results": maximum,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
        headers={"User-Agent": "TIMDR-KB/0.1 (research indexing)"},
        timeout=45,
    )
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    for entry in feed.entries:
        yield {
            "url": entry.link,
            "text": entry.title + "\n" + entry.summary,
            "title": entry.title,
            "published": entry.get("published", ""),
            "source_type": "arxiv_metadata",
            "branch": "external",
            "status": "preprint_not_validated",
            "repo": "",
        }


def search(db, query, branch=None, source=None, limit=8):
    setup(db)
    conditions = []
    if branch:
        conditions.append(
            models.FieldCondition(
                key="branch", match=models.MatchValue(value=branch)
            )
        )
    if source:
        conditions.append(
            models.FieldCondition(
                key="source_type", match=models.MatchValue(value=source)
            )
        )
    result = db.query_points(
        collection_name=COLLECTION,
        query=embedding([query])[0],
        query_filter=models.Filter(must=conditions) if conditions else None,
        limit=limit,
        with_payload=True,
    )
    for point in result.points:
        payload = point.payload or {}
        print(json.dumps({
            "score": round(point.score, 4),
            "url": payload.get("url"),
            "branch": payload.get("branch"),
            "source_type": payload.get("source_type"),
            "status": payload.get("status"),
            "excerpt": payload.get("text", "")[:500],
        }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("github")
    g.add_argument("repo")
    g.add_argument("--limit", type=int, default=3000)
    a = sub.add_parser("arxiv")
    a.add_argument("--query", default="all:quantum gravity")
    a.add_argument("--limit", type=int, default=30)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--branch")
    s.add_argument("--source")
    s.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    db = client()
    if args.command == "github":
        print("Indexed chunks:", ingest(db, github_records(args.repo, args.limit)))
    elif args.command == "arxiv":
        print("Indexed chunks:", ingest(db, arxiv_records(args.query, args.limit)))
    else:
        search(db, args.query, args.branch, args.source, args.limit)


if __name__ == "__main__":
    main()
