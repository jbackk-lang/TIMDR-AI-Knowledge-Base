# Public semantic search gateway — deployment checklist

**Status: source code committed, NOT deployed.** The existing protected Vectorize Worker is unchanged. The GitHub Pages site continues to offer public lexical search until this gateway is deployed and tested.

## Why an embedding service is required

The existing protected endpoint expects a JSON payload of `{"vector":[384 numbers],"topK":5,"filter":{}}`, not a text query. All 738 indexed vectors use **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2**. A different 384D model is NOT compatible, even if dimensions match. Cloudflare Workers AI embeddings are not automatically interchangeable.

This gateway calls a **separate private embedding endpoint** configured with `EMBEDDING_URL` and `EMBEDDING_TOKEN`. It must accept `POST {"text":"...","model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}` with a bearer token and respond `{"vector":[...384 finite numbers...]}` using exactly the original model and preprocessing. A compatible **localhost-only** implementation is now included as `timdr_kb/embedding_server.py`; it is **not deployed publicly** and cannot be reached by Cloudflare without additional secure hosting. Without it the gateway intentionally returns 503. Do not point the gateway at an arbitrary model provider.

## Deployment once compatible embedding service exists

From `cloudflare/public-search`:

```powershell
npx wrangler login
npx wrangler secret put TIMDR_SEARCH_TOKEN
npx wrangler secret put EMBEDDING_TOKEN
npx wrangler secret put EMBEDDING_URL
npx wrangler deploy
```

The search token is the existing private Worker token; do not paste it into GitHub or public JavaScript. Verify your Cloudflare plan supports the `ratelimit` binding in `wrangler.toml`, and set limits within plan quotas. Public rate limiting and Origin checks reduce casual abuse but do not constitute user authentication; requests can spoof Origin outside browsers. A public endpoint remains publicly callable and may incur costs. Monitor usage, set limits, and disable if abused.

Test the gateway from the browser with the exact GitHub Pages origin. Verify the returned results contain correct source URLs and excerpts before changing `docs/search.js` to call the new endpoint. The frontend is deliberately NOT wired to an unverified URL.

No DNS records, Cloudflare Tunnel or ecommerce configuration need changing. Never publish API secrets.

## Free local embedding test (Windows)

From the repository root, with Python 3.12 and the existing virtual environment:

```powershell
$env:TIMDR_EMBEDDING_TOKEN = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
.\.venv312\Scripts\python.exe -m timdr_kb.embedding_server
```

In a **second** PowerShell window (the secret is process-local, so supply the same token in that window securely):

```powershell
$env:TIMDR_EMBEDDING_TOKEN = Read-Host "Enter the same local test token"
$headers = @{ Authorization = "Bearer $env:TIMDR_EMBEDDING_TOKEN" }
$body = @{ text = "chronoproces TIMDR"; model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" } | ConvertTo-Json
$result = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8789/embed" -Headers $headers -ContentType "application/json" -Body $body
$result.vector.Count # expected: 384
```

The local service listens on **127.0.0.1 only**, uses the already-installed FastEmbed dependency, and requires no paid API. It is intentionally NOT a public endpoint. Do not expose it with port forwarding or the existing ecommerce Cloudflare Tunnel. Public deployment needs a separately approved secure hosting arrangement with usage controls and may involve costs.
