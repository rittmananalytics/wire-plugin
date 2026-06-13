# Feature: Personalisation Engine

## Overview

Personalise the shopping experience using a combination of explicit user data (self-segmentation profiles) and implicit behavioural signals (search history, product views, cart actions). This data feeds into AI recommendations, dynamic greetings, and contextual shortcuts.

## Architecture

```
┌──────────────────┐     ┌────────────────────┐
│  Self-Segment    │────▸│  Profile Database   │
│  (Modal Form)    │     │  (Supabase / DB)    │
└──────────────────┘     └────────┬───────────┘
                                  │
┌──────────────────┐              │
│  Event Tracking  │────▸┌───────▼────────────┐
│  (Analytics)     │     │  Personalisation    │
└──────────────────┘     │  Edge Function      │
                         └───────┬────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Greeting │ │ Shortcut │ │ Refined  │
              │ "Hi Ben" │ │ Pills    │ │ Search   │
              └──────────┘ └──────────┘ └──────────┘
```

## Implementation Steps

### 1. Self-Segmentation Profile

Create a modal or onboarding flow that captures user preferences:

```typescript
// Database schema
interface UserProfile {
  id: string;
  session_id: string;
  first_name: string;
  email: string;
  style_preferences: string[];  // ["casual", "sporty", "technical"]
  age_range: string;            // "25-34"
  size_info: {
    shirt: string;              // "M" or "15.5 collar"
    waist: string;              // "32"
  };
  photo_url?: string;           // For virtual try-on
}
```

```sql
CREATE TABLE self_segmentation_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  first_name TEXT NOT NULL,
  email TEXT NOT NULL,
  style_preferences TEXT[],
  age_range TEXT,
  shirt_collar_size TEXT,
  waist_size TEXT,
  photo_url TEXT,
  discount_code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 2. Event Tracking

Log user interactions to build a behavioural profile:

```typescript
// Client-side tracking
function trackEvent(eventType: string, payload: Record<string, any>) {
  const visitorId = getVisitorId(); // persistent localStorage ID

  supabase.functions.invoke("log-event", {
    body: {
      visitor_id: visitorId,
      event_type: eventType, // "search", "product_view", "add_to_cart"
      payload,
      timestamp: new Date().toISOString(),
    },
  });
}

// Usage
trackEvent("search", { query: "summer jersey", resultCount: 12 });
trackEvent("product_view", { handle: "pro-cycling-jersey", price: 45 });
trackEvent("add_to_cart", { handle: "pro-cycling-jersey", variant: "M" });
```

### 3. Behavioural Data Retrieval

Create an edge function that aggregates recent user behaviour:

```typescript
// /functions/user-recent-events
export async function handler(req) {
  const { visitorId } = await req.json();

  // Query event store (BigQuery, Supabase, or analytics DB)
  const recentSearches = await db.query(`
    SELECT payload->>'query' as query
    FROM events
    WHERE visitor_id = $1 AND event_type = 'search'
    ORDER BY timestamp DESC LIMIT 5
  `, [visitorId]);

  const recentViews = await db.query(`
    SELECT payload->>'handle' as handle
    FROM events
    WHERE visitor_id = $1 AND event_type = 'product_view'
    ORDER BY timestamp DESC LIMIT 10
  `, [visitorId]);

  return { recentSearches, recentViews };
}
```

### 4. Personalised Greetings

Use profile + behaviour data to create contextual greetings:

```typescript
function generateGreeting(profile, recentEvents) {
  if (profile?.first_name) {
    const lastSearch = recentEvents.recentSearches[0];
    if (lastSearch) {
      return `Welcome back, ${profile.first_name}! Still looking for ${lastSearch}?`;
    }
    return `Hey ${profile.first_name}, what are you in the mood for today?`;
  }
  return "Hi there! What can I help you find?";
}
```

### 5. Dynamic Shortcut Pills

Generate contextual quick-action buttons based on user data:

```typescript
function generateShortcuts(profile, recentEvents) {
  const shortcuts = [];

  // Based on recent searches
  if (recentEvents.recentSearches.length > 0) {
    shortcuts.push({
      label: `More like "${recentEvents.recentSearches[0]}"`,
      query: recentEvents.recentSearches[0],
    });
  }

  // Based on style preferences
  if (profile?.style_preferences?.includes("sporty")) {
    shortcuts.push({ label: "Performance gear", query: "high-performance athletic" });
  }

  // Based on season / weather
  const month = new Date().getMonth();
  if (month >= 5 && month <= 8) {
    shortcuts.push({ label: "Summer essentials", query: "lightweight breathable" });
  }

  return shortcuts.slice(0, 4);
}
```

### 6. Visitor Identity

Use a persistent visitor ID to link sessions:

```typescript
function getVisitorId(): string {
  const KEY = "visitor_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}
```

## Privacy Considerations

- **Transparency** — Tell users what data you collect and why
- **Opt-in** — Self-segmentation should be voluntary, incentivised with a discount
- **Data minimisation** — Only store what you actively use
- **Deletion** — Support data deletion requests
- **No PII in analytics** — Use anonymous visitor IDs, not emails

## Prompt for Claude Code

```
Add a personalisation engine to this React ecommerce site:

1. Create a self-segmentation modal that:
   - Asks for name, email, style preferences, and sizing
   - Stores data in a database table
   - Offers a discount code as incentive
   - Links to a persistent visitor ID

2. Add event tracking for:
   - Search queries (query text, result count)
   - Product views (handle, category, price)
   - Add-to-cart actions (handle, variant, quantity)
   - Store events via an edge function to [EVENT_STORE]

3. Create a /functions/user-recent-events endpoint that:
   - Accepts a visitor ID
   - Returns recent searches, views, and cart actions
   - Aggregates data for the personalisation layer

4. Integrate personalisation into the shopping assistant:
   - Personalised greeting using first name + recent activity
   - Dynamic shortcut pills based on preferences and history
   - Pass user context to the AI for refined recommendations
```
