/**
 * TIMDR public semantic-search gateway.
 * Requires a dedicated Worker deployment, a secret and Cloudflare Rate Limiting binding.
 * Never expose TIMDR_SEARCH_TOKEN in GitHub Pages or browser JavaScript.
 */
const ORIGIN = "https://jbackk-lang.github.io";
const PAGE = "/TIMDR-AI-Knowledge-Base/";
const UPSTREAM = "https://timdr-vector-search.jbackk.workers.dev/search";
const headers = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Vary": "Origin",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff"
};
const reply = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { ...headers, "Content-Type": "application/json; charset=utf-8" }
});
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/search") return reply({ error: "Not found" }, 404);
    const origin = request.headers.get("Origin");
    if (origin !== ORIGIN) return reply({ error: "Origin not allowed" }, 403);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (request.method !== "POST") return reply({ error: "Method not allowed" }, 405);
    if (!env.TIMDR_SEARCH_TOKEN || !env.SEARCH_LIMITER) return reply({ error: "Gateway not configured" }, 503);
    if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json"))
      return reply({ error: "Expected JSON" }, 415);
    const size = Number(request.headers.get("content-length") || 0);
    if (size > 2048) return reply({ error: "Request too large" }, 413);
    const ip = request.headers.get("CF-Connecting-IP");
    if (!ip) return reply({ error: "Client IP unavailable" }, 403);
    // Cloudflare's rate limiter is shared across isolates; fail closed on errors.
    try {
      const limit = await env.SEARCH_LIMITER.limit({ key: ip });
      if (!limit.success) return reply({ error: "Rate limit exceeded" }, 429);
    } catch (_) { return reply({ error: "Rate limiting unavailable" }, 503); }
    let payload;
    try { payload = await request.json(); } catch (_) { return reply({ error: "Invalid JSON" }, 400); }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return reply({ error: "Invalid request" }, 400);
    const query = payload.query;
    if (typeof query !== "string" || query.trim().length < 2 || query.length > 180)
      return reply({ error: "Query must contain 2–180 characters" }, 400);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      // Fixed upstream; no user-supplied URL or arbitrary proxying.
      const upstream = await fetch(UPSTREAM, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + env.TIMDR_SEARCH_TOKEN },
        body: JSON.stringify({ query: query.trim(), limit: 5 }),
        signal: controller.signal
      });
      if (!upstream.ok) return reply({ error: "Search service unavailable" }, 502);
      const raw = await upstream.json();
      // Only return selected public metadata; never forward upstream headers or credentials.
      const items = Array.isArray(raw) ? raw : (raw.results || raw.matches || []);
      if (!Array.isArray(items)) return reply({ error: "Unexpected search response" }, 502);
      const results = items.slice(0, 5).map(item => {
        const m = item.metadata || item;
        const link = typeof m.url === "string" ? m.url : (typeof m.source_url === "string" ? m.source_url : "");
        let safeUrl = "";
        try {
          const parsed = new URL(link);
          if (parsed.protocol === "https:" && (parsed.hostname === "github.com" || parsed.hostname === "raw.githubusercontent.com"))
            safeUrl = parsed.href;
        } catch (_) {}
        return {
          title: String(m.title || m.path || m.repo || "Dokument TIMDR").slice(0, 180),
          excerpt: String(m.excerpt || m.text || "").slice(0, 900),
          url: safeUrl,
          score: Number.isFinite(item.score) ? item.score : null
        };
      }).filter(item => item.url);
      return reply({ results });
    } catch (_) { return reply({ error: "Search temporarily unavailable" }, 502); }
    finally { clearTimeout(timer); }
  }
};
