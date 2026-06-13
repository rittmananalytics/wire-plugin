# Prerequisites & Worked Examples

A comprehensive guide to everything you need to sign up for, configure, and have API keys ready before Claude Code (or any AI coding agent) can build the agentic commerce features described in these playbooks.

---

## Overview: What Services Does This Site Actually Use?

| Feature | External Service | Auth Method | Secret Name |
|---------|-----------------|-------------|-------------|
| Semantic Search | Google Cloud Retail API | GCP Service Account JWT | `BIGQUERY_SERVICE_ACCOUNT_KEY` |
| Conversational Shopping Assistant | Google Cloud Retail API (Conversational Search) | GCP Service Account JWT | `BIGQUERY_SERVICE_ACCOUNT_KEY` |
| Virtual Try-On | Lovable AI Gateway (Gemini Flash image model) | API Key (auto-provisioned) | `LOVABLE_API_KEY` |
| Visual Similarity | Lovable AI Gateway (Gemini multimodal) | API Key (auto-provisioned) | `LOVABLE_API_KEY` |
| LLM Chat with Tools | Lovable AI Gateway (Gemini 2.5 Flash) | API Key (auto-provisioned) | `LOVABLE_API_KEY` |
| Personalisation / Analytics | Google BigQuery | GCP Service Account JWT | `BIGQUERY_SERVICE_ACCOUNT_KEY` |
| Product Catalog Sync | Google BigQuery + Shopify Storefront API | GCP SA + Storefront Token | `BIGQUERY_SERVICE_ACCOUNT_KEY`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN` |
| UCP Merchant Server | Stripe (payments) | API Key | `STRIPE_SECRET_KEY` |
| Product Data | Shopify Storefront API | Access Token | `SHOPIFY_STOREFRONT_ACCESS_TOKEN` |

---

## Step 1: Google Cloud Platform Setup

Most of the AI and search features run on Google Cloud. You'll need:

### 1.1 Create a GCP Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `my-agentic-commerce`)
3. Note the **Project ID** — you'll use it in edge function code

### 1.2 Enable Required APIs

In the GCP Console → APIs & Services → Enable APIs:

- **Retail API** (`retail.googleapis.com`) — for semantic search and conversational shopping
- **BigQuery API** (`bigquery.googleapis.com`) — for analytics event logging, catalog storage, and personalisation

### 1.3 Create a Service Account

1. Go to **IAM & Admin → Service Accounts**
2. Create a service account (e.g. `lovable-bigquery@your-project.iam.gserviceaccount.com`)
3. Grant it these roles:
   - `Retail API Admin` (`roles/retail.admin`) — or `Retail API User` for read-only
   - `BigQuery Data Editor` (`roles/bigquery.dataEditor`) — for writing analytics events
   - `BigQuery Data Viewer` (`roles/bigquery.dataViewer`) — for reading catalog data
   - `BigQuery Job User` (`roles/bigquery.jobUser`) — for running queries
4. Create a **JSON key** for this service account
5. Store the entire JSON key as a backend secret called `BIGQUERY_SERVICE_ACCOUNT_KEY`

### 1.4 Set Up the Retail API Catalog

1. In GCP Console, go to **Retail → Catalogs**
2. Create a default catalog (or use the auto-created `default_catalog`)
3. Create a **Serving Config** (e.g. `default_search`) — this is what the search endpoint queries against
4. Note the full resource path: `projects/YOUR_PROJECT/locations/global/catalogs/default_catalog/servingConfigs/default_search`

### 1.5 Set Up BigQuery Dataset

1. In GCP Console, go to **BigQuery**
2. Create a dataset (e.g. `ecommerce_data`)
3. Create a products table — this is where the catalog sync will write to
4. Create an events table — for analytics event logging

---

## Step 2: Shopify Setup

### 2.1 Shopify Store

You need a Shopify store (free trial works) with products published to the **Headless** sales channel.

### 2.2 Storefront API Access Token

1. In Shopify Admin, go to **Settings → Apps and sales channels → Develop apps**
2. Create a new app
3. Configure **Storefront API** scopes: `unauthenticated_read_product_listings`, `unauthenticated_read_product_inventory`, `unauthenticated_write_checkouts`, `unauthenticated_read_checkouts`
4. Install the app and copy the **Storefront API access token**
5. Store as secret: `SHOPIFY_STOREFRONT_ACCESS_TOKEN`

### 2.3 Publish Products to Headless Channel

1. In Shopify Admin → **Settings → Apps and sales channels**
2. Find **Headless** (install it from the Shopify App Store if not present)
3. Go to **Products → All products**, select all, then **More actions → Make available on Headless channel**

---

## Step 3: Stripe Setup (for UCP Merchant Server only)

If you're implementing the Universal Commerce Protocol checkout:

1. Create a [Stripe account](https://dashboard.stripe.com)
2. Get your **Secret Key** from the Developers → API Keys section
3. Store as secret: `STRIPE_SECRET_KEY`

---

## Step 4: Lovable AI Gateway (Auto-Provisioned)

The Lovable AI Gateway provides access to Gemini and GPT models without needing your own API keys. The `LOVABLE_API_KEY` is automatically provisioned when you enable Lovable Cloud.

**No action needed** — just ensure Lovable Cloud is enabled on your project.

This powers: Virtual Try-On, Visual Similarity, LLM Chat with Tools, and any other LLM-driven feature.

---

## Step 5: Store All Secrets

In Lovable, use the secrets management to store these keys as backend secrets. They'll be available as environment variables in all edge functions:

| Secret Name | Where to Get It |
|-------------|----------------|
| `BIGQUERY_SERVICE_ACCOUNT_KEY` | GCP Console → IAM → Service Accounts → Keys → JSON |
| `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | Shopify Admin → Apps → Your app → Storefront API token |
| `STRIPE_SECRET_KEY` | Stripe Dashboard → Developers → API Keys |
| `LOVABLE_API_KEY` | Auto-provisioned (do not set manually) |

---

## Worked Examples: Actual Code From This Site

Below are real, working code examples extracted from this project showing exactly how each service is called.

---

### Example 1: GCP Service Account Authentication (JWT Signing)

This pattern is reused across every function that calls Google Cloud APIs (Retail API, BigQuery). The service account JSON key is read from environment, a JWT is signed using the Web Crypto API, and exchanged for an OAuth2 access token.

```typescript
// Used in: semantic-search, shopping-assistant, sync-products-bq, log-event
import { encode as base64url } from "https://deno.land/std@0.168.0/encoding/base64url.ts";

async function importPKCS8Key(pem: string): Promise<CryptoKey> {
  const pemContents = pem
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s/g, "");
  const binaryDer = Uint8Array.from(atob(pemContents), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey(
    "pkcs8",
    binaryDer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

function textToBytes(s: string): Uint8Array {
  return new TextEncoder().encode(s);
}

async function createSignedJwt(
  serviceAccount: { client_email: string; private_key: string; token_uri: string }
): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: serviceAccount.client_email,
    // Adjust scope per use case:
    // Search/Retail: "https://www.googleapis.com/auth/cloud-platform"
    // BigQuery read: "https://www.googleapis.com/auth/bigquery.readonly https://www.googleapis.com/auth/cloud-platform"
    // BigQuery write: "https://www.googleapis.com/auth/bigquery.insertdata"
    scope: "https://www.googleapis.com/auth/cloud-platform",
    aud: serviceAccount.token_uri,
    iat: now,
    exp: now + 3600,
  };
  const enc = (obj: unknown) => base64url(textToBytes(JSON.stringify(obj)));
  const unsignedToken = `${enc(header)}.${enc(payload)}`;
  const key = await importPKCS8Key(serviceAccount.private_key);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, textToBytes(unsignedToken));
  return `${unsignedToken}.${base64url(new Uint8Array(sig))}`;
}

async function getAccessToken(serviceAccount: any): Promise<string> {
  const jwt = await createSignedJwt(serviceAccount);
  const res = await fetch(serviceAccount.token_uri, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=${jwt}`,
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${await res.text()}`);
  return (await res.json()).access_token;
}

// Usage in any edge function:
const saKey = JSON.parse(Deno.env.get("BIGQUERY_SERVICE_ACCOUNT_KEY")!);
const accessToken = await getAccessToken(saKey);
```

---

### Example 2: Google Cloud Retail API — Semantic Search

This is the actual search call used in the `semantic-search` edge function. It calls the Retail Search endpoint with query expansion and spell correction enabled.

```typescript
const GCP_PROJECT = "YOUR_GCP_PROJECT_ID";
const RETAIL_SEARCH_ENDPOINT = 
  `https://retail.googleapis.com/v2/projects/${GCP_PROJECT}/locations/global/catalogs/default_catalog/servingConfigs/default_search:search`;
const RETAIL_BRANCH = 
  `projects/${GCP_PROJECT}/locations/global/catalogs/default_catalog/branches/default_branch`;

async function retailSearch(query: string, visitorId: string, accessToken: string) {
  const res = await fetch(RETAIL_SEARCH_ENDPOINT, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      visitorId,
      branch: RETAIL_BRANCH,
      pageSize: 20,
      queryExpansionSpec: { condition: "AUTO" },
      spellCorrectionSpec: { mode: "AUTO" },
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Retail API Search failed: ${res.status} - ${errText}`);
  }

  const data = await res.json();
  if (!data.results) return [];

  // Extract product handles from results
  return data.results.map((r: any) => {
    const product = r.product || {};
    const title = product.title || "";
    const id = r.id || "";
    const handle = id || title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    return { handle, title };
  });
}
```

**Then enrich with Shopify data** — the Retail API returns handles/titles, but you fetch images, prices, and variants from Shopify:

```typescript
const SHOPIFY_STOREFRONT_URL = "https://YOUR-STORE.myshopify.com/api/2025-07/graphql.json";
const storefrontToken = Deno.env.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN")!;

// Fetch all products from Shopify, then match by handle
const shopifyRes = await fetch(SHOPIFY_STOREFRONT_URL, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Shopify-Storefront-Access-Token": storefrontToken,
  },
  body: JSON.stringify({
    query: `query { products(first: 100) { edges { node { 
      handle title description productType tags
      priceRange { minVariantPrice { amount currencyCode } }
      images(first: 1) { edges { node { url altText } } }
      variants(first: 20) { edges { node { id title price { amount currencyCode } availableForSale selectedOptions { name value } } } }
      options { name values }
    } } } }`,
  }),
});

const shopifyData = await shopifyRes.json();
const allProducts = shopifyData.data.products.edges;

// Match retail search handles to Shopify products
const enriched = retailResults.map((r) => {
  const match = allProducts.find((p) => p.node.handle === r.handle);
  return match || null;
}).filter(Boolean);
```

---

### Example 3: Lovable AI Gateway — LLM Chat with Tool Calling

This is the actual two-call pattern used in the `gemini-chat` edge function. The LLM decides when to search via tool calling.

```typescript
const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY")!;

const SYSTEM_PROMPT = `You are a friendly shopping assistant for [STORE_NAME].
Your capabilities:
- Search for products using the search_products tool
- Have general conversations about products, fabrics, and fit
- Understand context: "something for hot summer rides" means breathable jerseys

Guidelines:
- Only search when the user expresses intent to find or buy products
- When you search, explain WHY you chose those products
- Keep responses concise but warm`;

const TOOLS = [
  {
    type: "function",
    function: {
      name: "search_products",
      description: "Search the product catalog using semantic search.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "A descriptive search query for finding products.",
          },
        },
        required: ["query"],
      },
    },
  },
];

// --- First LLM call: may include tool calls ---
const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${LOVABLE_API_KEY}`,
  },
  body: JSON.stringify({
    model: "google/gemini-2.5-flash",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      ...userMessages,
    ],
    tools: TOOLS,
    tool_choice: "auto",
    max_tokens: 1024,
  }),
});

const completion = await response.json();
const choice = completion.choices?.[0];

// If no tool calls → return text directly
if (!choice.message.tool_calls?.length) {
  return { type: "text", content: choice.message.content };
}

// --- Execute the tool call ---
const toolCall = choice.message.tool_calls[0];
const args = JSON.parse(toolCall.function.arguments);
const searchResults = await searchProducts(args.query); // calls your semantic-search function

// --- Second LLM call: with tool results ---
const followUp = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${LOVABLE_API_KEY}`,
  },
  body: JSON.stringify({
    model: "google/gemini-2.5-flash",
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      ...userMessages,
      choice.message, // includes tool_calls
      {
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify({
          result_count: searchResults.length,
          products: searchResults.slice(0, 6).map((p) => ({
            title: p.node.title,
            price: p.node.priceRange.minVariantPrice.amount,
            type: p.node.productType,
          })),
        }),
      },
    ],
    max_tokens: 1024,
  }),
});

const followUpData = await followUp.json();
return {
  type: "products",
  content: followUpData.choices[0].message.content,
  products: searchResults,
};
```

---

### Example 4: Lovable AI Gateway — Virtual Try-On (Image Generation)

This uses Gemini's multimodal image generation to composite a person photo with a garment.

```typescript
const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY")!;

const prompt = `Generate an image of the person in the first image naturally wearing 
the garment shown in the second image (${garmentTitle}). Keep the person's face, body 
type, skin tone, and hair exactly the same. Only change their clothing to match the 
garment. The result should look like a natural, well-lit fashion photo.`;

const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${LOVABLE_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "google/gemini-3.1-flash-image-preview",
    modalities: ["image", "text"],
    messages: [
      {
        role: "user",
        content: [
          { type: "text", text: prompt },
          { type: "image_url", image_url: { url: personImageUrl } },
          { type: "image_url", image_url: { url: garmentImageUrl } },
        ],
      },
    ],
  }),
});

const data = await response.json();
const choice = data.choices?.[0]?.message;

// Extract the generated image from the response
let resultImageUrl = null;
if (choice?.images?.length > 0) {
  resultImageUrl = choice.images[0]?.image_url?.url;
}
```

**Rate limit handling** — the actual implementation includes retry logic:

```typescript
const MAX_RETRIES = 3;
let response: Response | null = null;

for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
  response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${LOVABLE_API_KEY}`, "Content-Type": "application/json" },
    body: requestBody,
  });

  if (response.status === 429 && attempt < MAX_RETRIES - 1) {
    const delay = (attempt + 1) * 3000; // 3s, 6s backoff
    await new Promise((r) => setTimeout(r, delay));
    continue;
  }
  break;
}

// Surface specific errors to the client
if (response?.status === 429) return { error: "Rate limited. Try again shortly." };
if (response?.status === 402) return { error: "Usage limit reached. Add credits." };
```

---

### Example 5: BigQuery — Event Logging for Personalisation

This writes user interaction events (search queries, product views, cart actions) to BigQuery for the personalisation engine.

```typescript
const GCP_PROJECT = "YOUR_GCP_PROJECT_ID";
const BQ_DATASET = "ecommerce_data";
const BQ_TABLE = "user_events";

const saKey = JSON.parse(Deno.env.get("BIGQUERY_SERVICE_ACCOUNT_KEY")!);
const accessToken = await getAccessToken(saKey); // reuse JWT helper from Example 1

const event = {
  event_type: "product_view",      // or "search", "add_to_cart", "purchase"
  visitor_id: visitorId,
  session_id: sessionId,
  product_handle: "summer-jersey",
  query: null,
  metadata: JSON.stringify({ source: "recommendation" }),
  timestamp: new Date().toISOString(),
};

const bqRes = await fetch(
  `https://bigquery.googleapis.com/bigquery/v2/projects/${GCP_PROJECT}/datasets/${BQ_DATASET}/tables/${BQ_TABLE}/insertAll`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      rows: [{ insertId: crypto.randomUUID(), json: event }],
    }),
  }
);
```

---

### Example 6: Shopify Storefront API — Product Catalog Sync to BigQuery

This syncs all products from Shopify to BigQuery so the Retail API and personalisation engine have catalog data to work with.

```typescript
const SHOPIFY_STOREFRONT_URL = "https://YOUR-STORE.myshopify.com/api/2025-07/graphql.json";
const storefrontToken = Deno.env.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN")!;

// Fetch all products from Shopify
const shopifyRes = await fetch(SHOPIFY_STOREFRONT_URL, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Shopify-Storefront-Access-Token": storefrontToken,
  },
  body: JSON.stringify({
    query: `query { products(first: 250) { edges { node {
      id handle title description productType tags
      priceRange { minVariantPrice { amount currencyCode } }
      images(first: 1) { edges { node { url } } }
    } } } }`,
  }),
});

const products = (await shopifyRes.json()).data.products.edges;

// Transform to BigQuery rows
const rows = products.map((p) => ({
  insertId: p.node.handle,
  json: {
    product_id: p.node.id,
    handle: p.node.handle,
    title: p.node.title,
    description: p.node.description,
    product_type: p.node.productType,
    tags: p.node.tags.join(","),
    price: parseFloat(p.node.priceRange.minVariantPrice.amount),
    currency: p.node.priceRange.minVariantPrice.currencyCode,
    image_url: p.node.images.edges[0]?.node?.url || "",
    synced_at: new Date().toISOString(),
  },
}));

// Write to BigQuery (uses same auth pattern as Example 1)
const accessToken = await getAccessToken(saKey);
await fetch(
  `https://bigquery.googleapis.com/bigquery/v2/projects/${GCP_PROJECT}/datasets/${BQ_DATASET}/tables/products/insertAll`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ rows }),
  }
);
```

---

## Quick-Start Checklist

Before handing this codebase to Claude Code for agentic feature development, verify:

| Prerequisite | Done? |
|-------------|-------|
| GCP project created | ☐ |
| Retail API enabled in GCP | ☐ |
| BigQuery API enabled in GCP | ☐ |
| Service account created with Retail Admin + BigQuery roles | ☐ |
| Service account JSON key stored as `BIGQUERY_SERVICE_ACCOUNT_KEY` | ☐ |
| Retail API catalog & serving config created | ☐ |
| BigQuery dataset and tables created | ☐ |
| Shopify store with products published to Headless channel | ☐ |
| Shopify Storefront API token stored as `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | ☐ |
| Lovable Cloud enabled (auto-provisions `LOVABLE_API_KEY`) | ☐ |
| Stripe secret key stored as `STRIPE_SECRET_KEY` (if using UCP) | ☐ |
| Product catalog synced to BigQuery via `sync-products-bq` function | ☐ |
| Retail API datastore re-indexed after catalog sync | ☐ |

---

## Common Pitfalls

1. **403 on Retail API calls** — The service account needs `roles/retail.admin` or `roles/retail.user` in GCP IAM. The Retail API must also be explicitly enabled.

2. **No search results** — Products must be synced to BigQuery AND the Retail API datastore must be re-indexed in GCP Console after sync. This is a manual step.

3. **Shopify products not showing** — Products must be published to the **Headless** sales channel, not just the Online Store channel.

4. **JWT signing fails** — The `BIGQUERY_SERVICE_ACCOUNT_KEY` secret must contain the complete JSON key file contents (not just the private key).

5. **Rate limits on Lovable AI Gateway** — The gateway has per-workspace rate limits. Implement exponential backoff (see Example 4). For higher limits, upgrade your plan or contact support.

6. **BigQuery `insertAll` silently fails** — Always check `response.insertErrors` in the BigQuery response. Rows can fail individually even if the HTTP status is 200.
