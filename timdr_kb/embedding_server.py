r"""Local-only compatible embedding API. No cloud costs; never expose directly to internet.

Usage:
  $env:TIMDR_EMBEDDING_TOKEN = Read-Host "Local API token"
  .\.venv312\Scripts\python.exe -m timdr_kb.embedding_server

POST http://127.0.0.1:8789/embed
Authorization: Bearer <token>
{"text":"chronoproces TIMDR","model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
"""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from timdr_kb.cli import MODEL, embedding

HOST = "127.0.0.1"
PORT = 8789
MAX_BODY = 2048


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/embed":
            return self.respond(404, {"error": "Not found"})
        token = os.environ["TIMDR_EMBEDDING_TOKEN"]
        provided = self.headers.get("Authorization", "")
        if not hmac.compare_digest(provided, "Bearer " + token):
            return self.respond(401, {"error": "Unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= MAX_BODY:
                return self.respond(413, {"error": "Invalid body size"})
            payload = json.loads(self.rfile.read(length))
            query = payload.get("text")
            if payload.get("model") != MODEL or not isinstance(query, str) or not 2 <= len(query.strip()) <= 180:
                return self.respond(400, {"error": "Invalid text or model"})
            vector = embedding([query.strip()])[0]
            if len(vector) != 384:
                return self.respond(500, {"error": "Embedding dimension mismatch"})
            return self.respond(200, {"vector": vector})
        except (ValueError, TypeError, json.JSONDecodeError):
            return self.respond(400, {"error": "Invalid JSON"})
        except Exception:
            return self.respond(500, {"error": "Embedding failed"})

    def respond(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        # Do not log authorization credentials or request bodies.
        return


def main():
    if len(os.environ.get("TIMDR_EMBEDDING_TOKEN", "")) < 24:
        raise SystemExit("Set TIMDR_EMBEDDING_TOKEN to a random secret (24+ chars).")
    print(f"Local TIMDR embedding service: http://{HOST}:{PORT}/embed (localhost only)")
    print("This does NOT make the service reachable by Cloudflare.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
