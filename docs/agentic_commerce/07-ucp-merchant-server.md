# Feature: Universal Commerce Protocol (UCP) Merchant Server

## Overview

Implement a merchant server that follows the Universal Commerce Protocol (UCP) specification, enabling external AI agents (like ChatGPT, Google Shopping, or any UCP-compatible agent) to discover, browse, and purchase products from your store through a standardised API.

## What is UCP?

UCP is a protocol that defines how AI shopping agents interact with merchant servers. It standardises:

- **Product Discovery** — Agents can search and browse your catalog
- **Checkout** — Agents can create and manage checkout sessions
- **Payment** — Agents can initiate and confirm payments
- **Order Management** — Agents can track order status

## Architecture

```
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  External AI     │────▸│  UCP Edge Functions   │────▸│  Commerce   │
│  Agent           │◂────│  /ucp-discovery       │◂────│  Platform   │
│  (ChatGPT etc)   │     │  /ucp-shopping        │     │  (Shopify)  │
└──────────────────┘     └──────────────────────┘     └─────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Checkout DB     │
                         │  (Orders table)  │
                         └──────────────────┘
```

## Implementation Steps

### 1. Discovery Endpoint

The discovery endpoint tells agents what products are available:

```typescript
// /functions/ucp-discovery
export async function handler(req) {
  const { query, category, page, pageSize } = await req.json();

  // Search products via your catalog
  const products = await searchCatalog({ query, category, page, pageSize });

  return {
    products: products.map(p => ({
      id: p.id,
      title: p.title,
      description: p.description,
      price: { amount: p.price, currency: p.currency },
      images: p.images,
      variants: p.variants.map(v => ({
        id: v.id,
        title: v.title,
        price: { amount: v.price, currency: v.currency },
        available: v.available,
      })),
      url: `https://your-store.com/products/${p.handle}`,
    })),
    pagination: {
      page,
      pageSize,
      total: products.totalCount,
    },
  };
}
```

### 2. Checkout Session Management

Create and manage checkout sessions for external agents:

```typescript
// /functions/ucp-shopping
export async function handler(req) {
  const { action, ...params } = await req.json();

  switch (action) {
    case "create_checkout":
      return createCheckout(params);
    case "update_checkout":
      return updateCheckout(params);
    case "confirm_checkout":
      return confirmCheckout(params);
    case "get_checkout":
      return getCheckout(params);
  }
}

async function createCheckout({ lineItems, customerInfo }) {
  const checkoutId = crypto.randomUUID();

  // Calculate totals
  const totals = calculateTotals(lineItems);

  // Store in database
  await db.insert("ucp_checkout_sessions", {
    id: checkoutId,
    line_items: lineItems,
    totals,
    status: "pending",
    platform_profile: customerInfo,
  });

  return {
    checkout_id: checkoutId,
    totals,
    status: "pending",
    payment_methods: ["card"],
  };
}
```

### 3. Database Schema

```sql
-- Checkout sessions
CREATE TABLE ucp_checkout_sessions (
  id TEXT PRIMARY KEY,
  line_items JSONB NOT NULL DEFAULT '[]',
  totals JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',
  payment JSONB,
  fulfillment JSONB,
  discount JSONB,
  platform_profile JSONB,
  idempotency_key TEXT,
  order_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Completed orders
CREATE TABLE ucp_orders (
  id TEXT PRIMARY KEY,
  checkout_id TEXT REFERENCES ucp_checkout_sessions(id),
  line_items JSONB NOT NULL DEFAULT '[]',
  totals JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'confirmed',
  stripe_payment_intent_id TEXT,
  fulfillment JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 4. Payment Integration

Integrate with Stripe for payment processing:

```typescript
async function confirmCheckout({ checkoutId, paymentMethodId }) {
  const checkout = await db.get("ucp_checkout_sessions", checkoutId);

  // Create Stripe PaymentIntent
  const paymentIntent = await stripe.paymentIntents.create({
    amount: Math.round(checkout.totals.total * 100),
    currency: checkout.totals.currency.toLowerCase(),
    payment_method: paymentMethodId,
    confirm: true,
    allow_redirects: "never", // Important for agent-based checkout
  });

  if (paymentIntent.status === "succeeded") {
    // Create order
    const orderId = crypto.randomUUID();
    await db.insert("ucp_orders", {
      id: orderId,
      checkout_id: checkoutId,
      line_items: checkout.line_items,
      totals: checkout.totals,
      status: "confirmed",
      stripe_payment_intent_id: paymentIntent.id,
    });

    // Update checkout
    await db.update("ucp_checkout_sessions", checkoutId, {
      status: "completed",
      order_id: orderId,
    });

    return { status: "completed", order_id: orderId };
  }

  return { status: "payment_failed" };
}
```

### 5. Idempotency

Protect against duplicate orders:

```typescript
async function createCheckout({ lineItems, idempotencyKey }) {
  // Check for existing checkout with same idempotency key
  if (idempotencyKey) {
    const existing = await db.findOne("ucp_checkout_sessions", {
      idempotency_key: idempotencyKey,
    });
    if (existing) return existing;
  }

  // Create new checkout...
}
```

## Security Considerations

- **Authentication** — Verify the identity of calling agents
- **Rate limiting** — Protect against abuse
- **Input validation** — Validate all line items against your real catalog
- **Price verification** — Always calculate prices server-side, never trust client prices
- **Idempotency** — Prevent duplicate charges

## Prompt for Claude Code

```
Implement a UCP merchant server for this React ecommerce site:

1. Create edge functions:
   - /functions/ucp-discovery: Product search and browsing for external agents
   - /functions/ucp-shopping: Checkout lifecycle (create, update, confirm, get)

2. Create database tables:
   - ucp_checkout_sessions: Stores checkout state with line_items, totals, status
   - ucp_orders: Completed orders linked to checkout sessions

3. Integrate Stripe for payment:
   - Create PaymentIntents with allow_redirects: "never"
   - Handle success/failure states
   - Create order records on successful payment

4. Add idempotency protection using an idempotency_key field.

5. Ensure all pricing is calculated server-side from the actual catalog.
```
