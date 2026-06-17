---
description: Implement Universal Commerce Protocol merchant server
argument-hint: <release-folder>
---

# Implement Universal Commerce Protocol merchant server

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Implement Universal Commerce Protocol merchant server for external AI agent access
argument-hint: <project-folder>
---

# Agentic Commerce — UCP Server Generate Command

## Purpose

Build a Universal Commerce Protocol (UCP) compliant merchant server that allows external AI agents (ChatGPT shopping, Google Shopping AI, or any UCP-compatible agent) to discover products, create checkout sessions, and confirm orders through a standardised API. All pricing is server-side calculated; idempotency protects against duplicate orders; Stripe PaymentIntents use `allow_redirects: "never"` for agent-compatible non-redirect checkout.

## Usage

```bash
/wire:ac_ucp_server-generate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.review: approved` in status.md
- GitHub repo cloned locally (URL in status.md)
- Stripe account with API keys (test mode)
- Supabase project configured

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Confirm `storefront.review == approved`
3. Confirm the consultant has:
   - Stripe secret key (`STRIPE_SECRET_KEY` for Supabase secrets)
   - Stripe test mode active (use `sk_test_` prefix keys for development)

### Step 2: Read Project Structure

1. Read `src/lib/shopify.ts` to understand how to fetch product and pricing data
2. Read `supabase/functions/` to understand existing edge functions
3. Read `src/integrations/supabase/client.ts` for the Supabase client setup

### Step 3: Create Database Schema

Provide the following Claude Code prompt:

```
Create a Supabase database migration at supabase/migrations/[timestamp]_ucp_schema.sql:

-- UCP checkout sessions: state machine for external agent checkouts
CREATE TABLE IF NOT EXISTS ucp_checkout_sessions (
  id TEXT PRIMARY KEY,                    -- UUID, server-generated
  line_items JSONB NOT NULL DEFAULT '[]', -- [{ product_id, variant_id, quantity, title, price }]
  totals JSONB NOT NULL DEFAULT '{}',     -- { subtotal, tax, shipping, total, currency }
  status TEXT NOT NULL DEFAULT 'pending', -- pending | confirmed | completed | cancelled
  payment JSONB,                          -- Stripe payment details on confirm
  fulfillment JSONB,                      -- shipping address and method
  discount JSONB,                         -- discount code if applied
  platform_profile JSONB,                 -- customer info from the calling agent
  idempotency_key TEXT,                   -- prevents duplicate checkouts
  order_id TEXT,                          -- set when status = completed
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX ON ucp_checkout_sessions (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- Completed orders
CREATE TABLE IF NOT EXISTS ucp_orders (
  id TEXT PRIMARY KEY,                      -- UUID, server-generated
  checkout_id TEXT REFERENCES ucp_checkout_sessions(id),
  line_items JSONB NOT NULL DEFAULT '[]',
  totals JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'confirmed', -- confirmed | fulfilled | cancelled
  stripe_payment_intent_id TEXT,
  fulfillment JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: service role only (these endpoints are for external agents, not browser clients)
ALTER TABLE ucp_checkout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ucp_orders ENABLE ROW LEVEL SECURITY;
-- No anon policies — all access via edge functions using service role client
```

### Step 4: Generate UCP Discovery Edge Function

Create `supabase/functions/ucp-discovery/index.ts`.

Provide the following Claude Code prompt:

```
Create a Supabase edge function at supabase/functions/ucp-discovery/index.ts that:

1. Accepts a JSON body with:
   { query?: string, category?: string, page?: number, pageSize?: number }
   Defaults: page=1, pageSize=20

2. Searches the Shopify Storefront API for products matching the query.
   Use the storefrontApiRequest helper from ../../src/lib/shopify.ts.
   If no query is provided, return all products (paginated).

3. Returns a standard UCP-format product list:
   {
     products: [
       {
         id: string,              // Shopify product GID
         title: string,
         description: string,
         price: { amount: number, currency: string },
         images: [{ url: string, alt: string }],
         variants: [
           {
             id: string,          // Shopify variant GID
             title: string,
             price: { amount: number, currency: string },
             available: boolean
           }
         ],
         url: string,             // https://[store-domain]/products/[handle]
         handle: string,
         productType: string
       }
     ],
     pagination: { page: number, pageSize: number, total: number }
   }

4. Validates the request:
   - pageSize must be ≤ 50 (return 400 if exceeded)
   - query must be a string if provided

5. Handles CORS headers for external agent calls:
   - Access-Control-Allow-Origin: *
   - Access-Control-Allow-Methods: POST, OPTIONS
   - Access-Control-Allow-Headers: Content-Type, Authorization
   - Handle OPTIONS preflight requests

6. Does NOT require authentication for product discovery
   (products are publicly available) — but does rate limit:
   - Track request count by IP using an in-memory Map
   - Return 429 if > 60 requests/minute from the same IP

Read src/lib/shopify.ts to use the existing storefrontApiRequest helper.
```

### Step 5: Generate UCP Shopping (Checkout Lifecycle) Edge Function

Create `supabase/functions/ucp-shopping/index.ts`.

Provide the following Claude Code prompt:

```
Create a Supabase edge function at supabase/functions/ucp-shopping/index.ts that
implements the UCP checkout lifecycle. Use a Supabase service role client.

1. Accepts a JSON body with: { action: string, ...params }
   Route to the appropriate handler based on action:
   - "create_checkout" → createCheckout(params)
   - "update_checkout" → updateCheckout(params)
   - "confirm_checkout" → confirmCheckout(params)
   - "get_checkout"    → getCheckout(params)
   - Any other action  → 400 Bad Request

2. Implement createCheckout({ lineItems, customerInfo, idempotencyKey? }):
   a. If idempotencyKey is provided:
      - Check if a checkout already exists with that key
      - If found, return the existing checkout (idempotency — no duplicate)
   b. Fetch real pricing from Shopify Storefront API for each line item:
      - Never trust client-supplied prices
      - Get price from the variant's actual Shopify price
   c. Calculate totals server-side:
      - subtotal: sum(variant.price * quantity)
      - tax: subtotal * taxRate (use 0.20 as default, or fetch from Shopify)
      - shipping: flat rate or fetched from Shopify
      - total: subtotal + tax + shipping
      - currency: from Shopify (e.g. "GBP")
   d. Insert into ucp_checkout_sessions with status="pending"
   e. Return the full checkout object

3. Implement updateCheckout({ checkoutId, lineItems?, fulfillment? }):
   a. Fetch existing checkout — return 404 if not found
   b. If status is "completed" or "cancelled", return 409 Conflict
   c. If lineItems provided, recalculate totals from Shopify prices
   d. Update fulfillment details if provided
   e. Update the session and return updated checkout

4. Implement confirmCheckout({ checkoutId, paymentMethodId }):
   a. Fetch checkout — return 404 if not found
   b. Verify status is "pending" — return 409 if already confirmed/completed
   c. Create a Stripe PaymentIntent:
      stripe.paymentIntents.create({
        amount: Math.round(checkout.totals.total * 100),  // pence/cents
        currency: checkout.totals.currency.toLowerCase(),
        payment_method: paymentMethodId,
        confirm: true,
        allow_redirects: "never",  // Critical: agent-compatible checkout
      })
   d. If payment succeeds (status === "succeeded"):
      - Generate orderId = crypto.randomUUID()
      - Insert into ucp_orders
      - Update checkout status to "completed", set order_id
      - Return { status: "completed", order_id: orderId }
   e. If payment fails:
      - Update checkout status to "confirmed" (awaiting payment retry)
      - Return { status: "payment_failed", error: paymentIntent.last_payment_error?.message }

5. Implement getCheckout({ checkoutId }):
   - Fetch and return the checkout session — 404 if not found

6. All API keys from Deno.env.get(): STRIPE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY

7. CORS headers same as ucp-discovery (external agents must be able to call this)

CRITICAL SECURITY RULES:
- Never accept client-supplied prices — always fetch from Shopify
- Never create an order without a successful Stripe PaymentIntent
- Always validate checkoutId exists before any mutation
- Idempotency key uniqueness must be enforced at the database level
```

### Step 6: Update Status

```yaml
ucp_server:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  files:
    - supabase/migrations/[timestamp]_ucp_schema.sql
    - supabase/functions/ucp-discovery/index.ts
    - supabase/functions/ucp-shopping/index.ts
```

### Step 7: Confirm and Suggest Next Steps

```
## UCP Server Generated

**Files created:**
- supabase/migrations/[timestamp]_ucp_schema.sql
- supabase/functions/ucp-discovery/index.ts
- supabase/functions/ucp-shopping/index.ts

### Next Steps

1. Add secrets to Supabase:
   - STRIPE_SECRET_KEY (use sk_test_... for now)

2. Apply the migration:
   ```bash
   supabase db push
   ```

3. Deploy edge functions:
   ```bash
   supabase functions deploy ucp-discovery
   supabase functions deploy ucp-shopping
   ```

4. **Validate**: `/wire:ac_ucp_server-validate <project>`
```

## Edge Cases

### Shopify Price Fetch Fails During Create

If Shopify is unavailable when creating a checkout, return a 503 Service Unavailable
rather than proceeding with potentially incorrect pricing. Never fall back to
client-supplied prices.

### Stripe PaymentIntent Requires Action (3DS)

With `allow_redirects: "never"`, Stripe will decline 3DS-required cards rather than
redirect. This is by design for agent-based checkout. Log the declined payment and
return `{ status: "payment_failed", error: "Card requires authentication not supported in this flow" }`.
The external agent can retry with a different payment method.

### Duplicate idempotency_key Race Condition

If two requests with the same `idempotency_key` arrive simultaneously, the unique index
on `ucp_checkout_sessions(idempotency_key)` will cause one to fail with a unique
constraint error. Catch this PostgreSQL error (code 23505) and return the existing
checkout instead of a 500.

## Output

This command produces:
- `supabase/migrations/[timestamp]_ucp_schema.sql`
- `supabase/functions/ucp-discovery/index.ts`
- `supabase/functions/ucp-shopping/index.ts`
- Updated `.wire/<project_id>/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

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
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
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
