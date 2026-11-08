# Cloudflare Vectorize deployment (no shop changes)

This deployment is **not yet live**. The connected GitHub integration cannot administer the user's Cloudflare account. No DNS, Tunnel, or shop settings are modified.

## Prerequisites

Node.js, npm, Python 3.10+, Cloudflare login with Vectorize write permission. Never commit credentials.

```bash
npm install -g wrangler
npx wrangler login
npx wrangler vectorize create timdr-unified-v1 --dimensions=384 --metric=cosine
```

Create filtering indexes **before inserting vectors**:

```bash
npx wrangler vectorize create-metadata-index timdr-unified-v1 --property-name=branch --type=string
npx wrangler vectorize create-metadata-index timdr-unified-v1 --property-name=source_type --type=string
npx wrangler vectorize create-metadata-index timdr-unified-v1 --property-name=repo --type=string
npx wrangler vectorize create-metadata-index timdr-unified-v1 --property-name=status --type=string
npx wrangler vectorize list-metadata-index timdr-unified-v1
```

Prepare and upload vectors using the same multilingual model as the original Qdrant CLI:

```bash
pip install -r requirements.txt
python -m timdr_kb.vectorize_export --input knowledge/seed.jsonl --output vectorize-seed.ndjson
npx wrangler vectorize insert timdr-unified-v1 --file=vectorize-seed.ndjson
npx wrangler vectorize info timdr-unified-v1
```

**Privacy and quality:** Source snapshots contain unverified repository text; no claims of independent scientific validation. Never upload private repositories, customer data, tokens or credentials without authorization. Indexing additional data should use an allowlist, stable document IDs, license review, and rate limiting. Do not commit generated NDJSON (large embedding data).

**Free-tier:** Check current Vectorize limits and usage in your Cloudflare dashboard before large imports. 384 dimensions means 384 stored dimensions per vector. Index capacity is separate from GitHub repository capacity.

**Next:** A protected Cloudflare Worker query endpoint with consistent query embeddings and authenticated access. Do not expose raw Vectorize publicly.
