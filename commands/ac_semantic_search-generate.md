---
description: Implement AI semantic search
argument-hint: <release-folder>
---

# Implement AI semantic search

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.9\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_semantic_search-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.9\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Implement AI semantic search feature in the ecommerce repo
argument-hint: <project-folder>
---

# Agentic Commerce — Semantic Search Generate Command

## Purpose

Implement AI-powered semantic search in the cloned GitHub repo. Replaces keyword search with natural language understanding, enabling users to describe what they want ("breathable jersey for hot summer rides") and receive contextually relevant results from Vertex AI, Algolia, or another AI search provider.

## Usage

```bash
/wire:ac_semantic_search-generate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.review: approved` in status.md
- GitHub repo cloned locally (URL in status.md)
- AI search provider account (Vertex AI Retail API, Algolia NeuralSearch, or equivalent)
- Supabase project configured

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Confirm `storefront.review == approved`
3. Confirm GitHub repo URL is recorded
4. Ask consultant which AI search provider they are using:
   - Google Vertex AI Retail API (best semantic understanding, requires GCP)
   - Algolia NeuralSearch (fastest setup, managed)
   - Supabase pgvector (embedded, no extra service)
   - OpenAI Embeddings + Pinecone (flexible)

### Step 2: Read Project Structure

1. Read the cloned repo at the path provided
2. Read `src/lib/shopify.ts` to understand the product data structure
3. Read `supabase/functions/` to understand existing edge functions
4. Read `src/integrations/supabase/client.ts` for the Supabase setup

### Step 3: Generate Catalog Sync Edge Function

Create `supabase/functions/sync-products/index.ts`:

```typescript
// Fetches all products from Shopify Storefront API and upserts them
// into the configured AI search index (Vertex AI / Algolia / pgvector)

import { createClient } from "@supabase/supabase-js";
import { storefrontApiRequest } from "../../src/lib/shopify.ts";

const ALL_PRODUCTS_QUERY = `
  query AllProducts($cursor: String) {
    products(first: 50, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      edges {
        node {
          id title description productType
          priceRange { minVariantPrice { amount currencyCode } }
          images(first: 1) { edges { node { url } } }
          handle tags
        }
      }
    }
  }
`;

Deno.serve(async (req) => {
  // Paginate through all products
  let cursor: string | null = null;
  const allProducts = [];
  do {
    const { data } = await storefrontApiRequest(ALL_PRODUCTS_QUERY, { cursor });
    const page = data.products;
    allProducts.push(...page.edges.map(e => ({
      id: e.node.id,
      title: e.node.title,
      description: e.node.description,
      productType: e.node.productType,
      price: e.node.priceRange.minVariantPrice.amount,
      currency: e.node.priceRange.minVariantPrice.currencyCode,
      imageUrl: e.node.images.edges[0]?.node.url,
      handle: e.node.handle,
      tags: e.node.tags,
    })));
    cursor = page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null;
  } while (cursor);

  // Upsert into search provider
  // [Provider-specific implementation here]

  return new Response(JSON.stringify({ synced: allProducts.length }));
});
```

The consultant should adapt the `// [Provider-specific implementation here]` section to their chosen provider. Provide the Claude Code prompt:

```
In supabase/functions/sync-products/index.ts, implement the catalog upsert for 
[PROVIDER]. After the allProducts array is populated:
- [Vertex AI]: Call the Retail API importProducts endpoint with the product array
- [Algolia]: Call algolia.saveObjects() with the product array
- [pgvector]: Generate embeddings for each product description and upsert into 
  a products table with a vector column
Read the existing shopify.ts to understand the product structure already in use.
```

### Step 4: Generate Semantic Search Edge Function

Create `supabase/functions/semantic-search/index.ts`:

```typescript
import { createClient } from "@supabase/supabase-js";

// Simple in-memory cache: Map<queryHash, { results, expires }>
const cache = new Map<string, { results: any[], expires: number }>();
const CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes

function hashQuery(query: string): string {
  // Normalise query for cache key
  return query.toLowerCase().trim().replace(/\s+/g, " ");
}

Deno.serve(async (req) => {
  const { query } = await req.json();
  if (!query?.trim()) {
    return new Response(JSON.stringify({ results: [] }), { status: 400 });
  }

  const cacheKey = hashQuery(query);
  const cached = cache.get(cacheKey);
  if (cached && cached.expires > Date.now()) {
    return new Response(JSON.stringify({ results: cached.results, cached: true }));
  }

  // 1. Call AI search provider
  const searchResults = await searchProvider(query);
  
  // 2. Enrich with live Shopify product data
  const enriched = await enrichWithShopifyData(searchResults);

  // 3. Cache results
  cache.set(cacheKey, { results: enriched, expires: Date.now() + CACHE_TTL_MS });

  return new Response(JSON.stringify({ results: enriched }));
});
```

Provide the Claude Code prompt:

```
In supabase/functions/semantic-search/index.ts, implement:

1. The searchProvider(query) function that calls [SEARCH_PROVIDER] with:
   - The natural language query string
   - pageSize: 20
   - queryExpansion: "AUTO" (or provider equivalent)
   - spellCorrection: "AUTO" (or provider equivalent)
   - Returns array of { productId, score, explanation }

2. The enrichWithShopifyData(searchResults) function that:
   - Takes the array of product IDs/handles from search results
   - Fetches live product data (images, prices, availability) from Shopify Storefront API
   - Merges relevance_reason and score from search results onto each product
   - Returns merged array

3. Add rate limiting: return 429 if >100 requests/minute from the same IP.

Read the existing shopify.ts and supabase client setup for reference.
```

### Step 5: Generate React SemanticSearch Component

Create `src/components/SemanticSearch.tsx`:

Provide the Claude Code prompt:

```
Create a SemanticSearch React component at src/components/SemanticSearch.tsx that:

1. Has a full-width search input with:
   - Placeholder: "Describe what you're looking for…"
   - A search button (or search icon)
   - A clear button when a query is active
   - Loading spinner during search
   - Keyboard shortcut: Enter to search

2. Shows example query pills below the input when no query is active:
   - Use 3-4 queries relevant to the product catalog
   - Clicking a pill populates and submits the query

3. On search:
   - Calls supabase.functions.invoke("semantic-search", { body: { query } })
   - Passes results up via an onResults(results, query) callback
   - Shows an "active query" label with a clear button after search

4. Shows a relevance_reason badge on each result when available:
   - Small italic text below the product price explaining why it matched

5. Tracks search analytics:
   - On each search, call a trackEvent("search", { query, resultCount }) function
   - (We will implement trackEvent in the personalisation feature later — 
     for now create a stub that logs to console)

Add the SemanticSearch component to the top of the product listing page, 
replacing or enhancing the existing search bar.
```

### Step 6: Add Search Analytics Tracking (Stub)

Create `src/lib/analytics.ts` as a stub:

```typescript
// Analytics stub — full implementation in personalisation feature
export function trackEvent(eventType: string, payload: Record<string, unknown>) {
  console.log("[Analytics]", eventType, payload);
  // TODO: implement in ac_personalisation-generate
}
```

### Step 7: Update Status

```yaml
semantic_search:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  files:
    - supabase/functions/sync-products/index.ts
    - supabase/functions/semantic-search/index.ts
    - src/components/SemanticSearch.tsx
    - src/lib/analytics.ts
```

### Step 8: Confirm and Suggest Next Steps

```
## Semantic Search Generated

**Files created:**
- supabase/functions/sync-products/index.ts
- supabase/functions/semantic-search/index.ts  
- src/components/SemanticSearch.tsx
- src/lib/analytics.ts (stub)

### Next Steps

1. Configure your search provider credentials as Supabase secrets:
   - Vertex AI: GOOGLE_APPLICATION_CREDENTIALS_JSON, GCP_PROJECT_ID, RETAIL_LOCATION
   - Algolia: ALGOLIA_APP_ID, ALGOLIA_API_KEY, ALGOLIA_INDEX_NAME
   
2. Sync your product catalog:
   ```bash
   supabase functions serve sync-products
   curl -X POST http://localhost:54321/functions/v1/sync-products
   ```

3. **Validate**: `/wire:ac_semantic_search-validate <project>`
```

## Edge Cases

### No Search Provider Configured

If the consultant hasn't chosen a provider, present the comparison table:

| Provider | Strengths | Setup Complexity |
|----------|-----------|-----------------|
| Vertex AI Retail | Best semantic understanding | Medium (requires GCP) |
| Algolia NeuralSearch | Fast, great DX | Low (SDK-based) |
| Supabase pgvector | Integrated with your DB | Medium (need embeddings) |
| OpenAI + Pinecone | Flexible, strong embeddings | Medium (two services) |

## Output

This command produces:
- `supabase/functions/sync-products/index.ts`
- `supabase/functions/semantic-search/index.ts`
- `src/components/SemanticSearch.tsx`
- `src/lib/analytics.ts` (stub)
- Updated `status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
