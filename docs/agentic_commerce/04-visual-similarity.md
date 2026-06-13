# Feature: Visual Similarity Discovery

## Overview

Enable users to find visually similar products by clicking a "Find Similar" button on any product card. The system uses multimodal AI to analyse the product image and return items with similar visual characteristics — colour, pattern, style, and silhouette.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Product Card│────▸│  Edge Function   │────▸│  Multimodal AI      │
│  [Find ≈]    │◂────│  /find-similar   │◂────│  (Gemini / GPT-4V)  │
└──────────────┘     └──────────────────┘     └─────────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  Product Catalog │
                     │  (All products)  │
                     └──────────────────┘
```

## Implementation Steps

### 1. Similarity Edge Function

Create a backend function that compares a source product's image against the catalog using a multimodal AI model.

```typescript
// /functions/find-similar
export async function handler(req) {
  const { productHandle, imageUrl } = await req.json();

  // 1. Fetch all products from the catalog
  const allProducts = await commercePlatform.getProducts({ limit: 50 });

  // 2. Filter out the source product
  const candidates = allProducts.filter(p => p.handle !== productHandle);

  // 3. Build a multimodal prompt
  const prompt = `
    Analyse the source product image and compare it visually to each candidate product.
    For each candidate, score visual similarity (0-100) based on:
    - Colour palette and pattern
    - Silhouette and shape
    - Style category and aesthetic
    - Material appearance

    Return the top 6 most visually similar products with scores and explanations.
  `;

  // 4. Call multimodal AI with all images
  const result = await model.generateContent({
    prompt,
    images: [
      { url: imageUrl, label: "source" },
      ...candidates.map(p => ({ url: p.imageUrl, label: p.handle })),
    ],
  });

  // 5. Parse and return ranked results
  return {
    similar: result.rankings.map(r => ({
      ...candidates.find(p => p.handle === r.handle),
      similarity_score: r.score,
      similarity_reason: r.explanation,
    })),
  };
}
```

### 2. Alternative: Embedding-Based Approach

For larger catalogs, pre-compute image embeddings instead of real-time comparison:

```typescript
// Pre-compute (run once, or on product change)
async function indexProductImages() {
  const products = await getProducts();
  for (const product of products) {
    const embedding = await model.embedImage(product.imageUrl);
    await db.upsert("product_embeddings", {
      product_id: product.id,
      embedding: embedding.vector,
    });
  }
}

// At query time — fast vector similarity search
async function findSimilar(productId: string) {
  const sourceEmbedding = await db.select("product_embeddings", { product_id: productId });
  const results = await db.query(`
    SELECT *, 1 - (embedding <=> $1) AS similarity
    FROM product_embeddings
    WHERE product_id != $2
    ORDER BY similarity DESC
    LIMIT 6
  `, [sourceEmbedding, productId]);
  return results;
}
```

### 3. React Component

```tsx
function SimilarProducts({ product }) {
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(false);

  const findSimilar = async () => {
    setLoading(true);
    try {
      const { data } = await supabase.functions.invoke("find-similar", {
        body: { productHandle: product.handle, imageUrl: product.imageUrl },
      });
      setSimilar(data.similar || []);
    } catch (err) {
      console.error("Find similar failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={findSimilar} disabled={loading}>
        {loading ? "Analysing..." : "Find Similar"}
      </button>
      {similar.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {similar.map(p => (
            <ProductCard key={p.id} product={p} badge={p.similarity_reason} />
          ))}
        </div>
      )}
    </div>
  );
}
```

## Performance Considerations

- **Catalog size limit** — Real-time multimodal comparison works for ~25-50 products. For larger catalogs, use the embedding approach.
- **Latency** — Multimodal AI comparison takes 10-15 seconds. Show a loading state and consider pre-computing results.
- **Caching** — Cache similarity results per product for 24 hours.
- **Cost** — Each comparison involves sending multiple images to an AI model. Budget accordingly.

## Prompt for Claude Code

```
Add visual similarity discovery to this React ecommerce site:

1. Create an edge function at /functions/find-similar that:
   - Accepts { productHandle, imageUrl }
   - Fetches the product catalog (limit to first 25-50 products)
   - Uses [MULTIMODAL_MODEL] to compare images visually
   - Returns top 6 similar products with scores and explanations
   - Implements caching to avoid repeated comparisons

2. Create a SimilarProducts component that:
   - Shows a "Find Similar" button on each product card
   - Displays a loading spinner (expect 10-15s latency)
   - Renders similar products in a grid with similarity badges
   - Handles errors gracefully

3. Add the component to the product detail page and
   optionally to the product grid cards.
```
