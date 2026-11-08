# Public semantic search gateway — deployment checklist

**Status: source code committed, NOT deployed.** The existing protected Vectorize Worker is unchanged. The GitHub Pages site continues to offer public lexical search until this gateway is deployed and tested.

## Why an embedding service is required

The existing protected endpoint expects a JSON payload of `{"vector":[384 numbers],"topK":5,"filter":{}}`, not a text query. All 738 indexed vectors use **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2**. A different 384D model is NOT compatible, even if dimensions match. Cloudflare Workers AI embeddings are not automatically interchangeable.

This gateway calls a **separate private embedding endpoint** configured with `EMBEDDING_URL` and `EMBEDDING_TOKEN`. It must accept `POST {"text":"...","model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}` with a bearer token and respond `{"vector":[...384 finite numbers...]}` using exactly the original model and preprocessing. Such a service is **not included or deployed** here. Without it the gateway intentionally returns 503. Do not point the gateway at an arbitrary model provider.

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
