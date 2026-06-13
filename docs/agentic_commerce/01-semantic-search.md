# Feature: AI Semantic Search

## Overview

Replace traditional keyword-based product search with natural language understanding. Users describe what they want in plain English ("breathable jersey for hot summer rides") and the system returns contextually relevant results — even when no keywords match.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  React UI    │────▸│  Edge Function   │────▸│  AI Search Engine   │
│  (SearchBar) │◂────│  /semantic-search │◂────│  (Vertex AI / etc)  │
└──────────────┘     └──────────────────┘     └─────────────────────┘
                              │                         │
                              ▼                         ▼
                     ┌──────────────────┐     ┌─────────────────────┐
                     │  Product API     │     │  Product Catalog    │
                     │  (Shopify / etc) │     │  (BigQuery / DB)    │
                     └──────────────────┘     └─────────────────────┘
```

## Implementation Steps

### 1. Catalog Ingestion

Before semantic search works, your product catalog must be indexed in your AI search engine.

```
Edge Function: /sync-products
  1. Fetch all products from your commerce platform API
  2. Transform into a standardised schema:
     {
       id, title, description, productType,
       price, currency, imageUrl, handle, tags
     }
  3. Upsert into your search datastore (BigQuery, Algolia, Vertex AI, etc.)
  4. Trigger re-indexing if required by your search provider
```

**Key decisions:**
- **Full refresh vs incremental sync** — Start with full refresh; add webhook-based incremental sync later
- **Sync frequency** — After every product change, or on a schedule (e.g. nightly)
- **Which products** — Only those published to the relevant sales channel

### 2. Search Edge Function

Create a backend function that accepts a natural language query and returns ranked results.

```typescript
// Pseudocode: /functions/semantic-search
export async function handler(req) {
  const { query } = await req.json();

  // 1. Call your AI search provider
  const searchResults = await searchProvider.search({
    query,
    pageSize: 20,
    queryExpansion: "AUTO",    // let the engine expand intent
    spellCorrection: "AUTO",   // handle typos gracefully
  });

  // 2. Extract product IDs/handles from results
  const productIds = searchResults.map(r => r.productId);

  // 3. Enrich with live product data (images, prices, stock)
  const products = await commercePlatform.getProducts(productIds);

  // 4. Merge relevance metadata with product data
  return products.map((p, i) => ({
    ...p,
    relevance_reason: searchResults[i].explanation,
    score: searchResults[i].score,
  }));
}
```

**Important considerations:**
- **Caching** — Hash queries and cache results for 15-60 minutes to reduce API costs
- **Fallback** — If the AI search engine is down, fall back to keyword search on your commerce platform
- **Rate limiting** — Protect the endpoint from abuse

### 3. React Search Component

Build a search bar that sends natural language queries and renders results.

```tsx
function SemanticSearch({ onResults, onClear }) {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (q: string) => {
    setIsSearching(true);
    try {
      const { data } = await supabase.functions.invoke("semantic-search", {
        body: { query: q },
      });
      onResults(data.results, q);
    } catch (err) {
      console.error("Search failed:", err);
      onResults([], q);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSearch(query)}
        placeholder="Describe what you're looking for…"
      />
      <button onClick={() => handleSearch(query)} disabled={isSearching}>
        Search
      </button>
    </div>
  );
}
```

### 4. Suggested Queries

Provide clickable example queries to reduce friction and demonstrate capability:

```tsx
const EXAMPLE_QUERIES = [
  "Lightweight jersey for summer rides",
  "Warm thermal gear for winter",
  "Complete cycling outfit set",
];
```

### 5. Result Cards with Relevance Explanation

Display **why** each result matched the query using the `relevance_reason` from the search engine:

```tsx
function SearchResultCard({ product }) {
  return (
    <div>
      <img src={product.imageUrl} alt={product.title} />
      <h3>{product.title}</h3>
      <p>{product.price}</p>
      {product.relevance_reason && (
        <span className="text-sm text-muted-foreground">
          {product.relevance_reason}
        </span>
      )}
    </div>
  );
}
```

## Search Provider Options

| Provider | Strengths | Setup Complexity |
|----------|-----------|-----------------|
| Google Vertex AI Search (Retail API) | Best-in-class semantic understanding, built-in query expansion | Medium — requires GCP project + catalog import |
| Algolia NeuralSearch | Fast, great DX, managed infrastructure | Low — SDK-based, good docs |
| Typesense | Open source, self-hostable, vector search | Medium — requires server |
| Supabase pgvector | Integrated with your DB, embedding-based | Medium — need to generate embeddings |
| OpenAI Embeddings + Pinecone | Flexible, state-of-the-art embeddings | Medium — two services to manage |

## Prompt for Claude Code

```
Add AI-powered semantic search to this React ecommerce site:

1. Create a backend edge function at /functions/semantic-search that:
   - Accepts a { query } JSON body
   - Calls [YOUR_SEARCH_PROVIDER] with the query
   - Enriches results with product data from the commerce platform API
   - Returns ranked results with relevance explanations
   - Implements query caching using a hash of the normalised query

2. Create a SemanticSearch React component that:
   - Has a styled search input with loading states
   - Shows example query pills below the search bar
   - Sends queries to the edge function on Enter or button click
   - Passes results up via onResults callback
   - Shows an active query label with a clear button

3. Update the product grid to accept search results and display
   relevance_reason badges on each card when available.

4. Add search analytics tracking (query, result count, timestamp).
```
