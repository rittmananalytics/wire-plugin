---
description: Build personalisation engine with profiles and event tracking
argument-hint: <release-folder>
---

# Build personalisation engine with profiles and event tracking

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.17\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_personalisation-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.17\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Implement personalisation engine with behavioural tracking, user profiles, and dynamic recommendations
argument-hint: <project-folder>
---

# Agentic Commerce — Personalisation Generate Command

## Purpose

Build a personalisation layer that combines explicit user data (self-segmentation profile: name, style preferences, sizing) with implicit behavioural signals (search history, product views, add-to-cart events) to deliver personalised greetings, dynamic shortcut pills, and enriched AI recommendations. Event tracking uses anonymous visitor IDs — no PII is stored in the events table.

## Usage

```bash
/wire:ac_personalisation-generate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.review: approved` in status.md
- GitHub repo cloned locally (URL in status.md)
- Supabase project configured
- `src/lib/analytics.ts` stub exists (created during semantic search feature, or create fresh)

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Confirm `storefront.review == approved`
3. Check if `src/lib/analytics.ts` exists — if so, read it to understand the existing stub
4. Check if `src/stores/` contains a cart store — read it for the Zustand pattern to follow

### Step 2: Read Project Structure

1. Read `supabase/functions/` to understand existing edge functions
2. Read `src/integrations/supabase/client.ts` for the Supabase client setup
3. Read `src/components/ShoppingAssistant.tsx` (if it exists) to understand
   where personalised greetings and shortcuts need to be injected

### Step 3: Create Database Schema

Provide the following Claude Code prompt:

```
Create a Supabase database migration at supabase/migrations/[timestamp]_personalisation.sql:

-- User self-segmentation profiles (stores explicit user preferences)
CREATE TABLE IF NOT EXISTS self_segmentation_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  first_name TEXT NOT NULL,
  email TEXT NOT NULL,
  style_preferences TEXT[] DEFAULT '{}',
  age_range TEXT,
  shirt_collar_size TEXT,
  waist_size TEXT,
  photo_url TEXT,
  discount_code TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON self_segmentation_profiles (session_id);

-- Behavioural event log (no PII — uses visitor_id only, not email)
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visitor_id TEXT NOT NULL,   -- anonymous localStorage ID, never the user's email
  event_type TEXT NOT NULL,   -- 'search' | 'product_view' | 'add_to_cart'
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON events (visitor_id, event_type);
CREATE INDEX ON events (created_at);

-- Row-level security: service role can write, anon can insert their own events
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous event inserts" ON events
  FOR INSERT TO anon WITH CHECK (true);
ALTER TABLE self_segmentation_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow profile inserts" ON self_segmentation_profiles
  FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow profile reads by session_id" ON self_segmentation_profiles
  FOR SELECT TO anon USING (true);
```

### Step 4: Generate Event Logging Edge Function

Create `supabase/functions/log-event/index.ts`.

Provide the following Claude Code prompt:

```
Create a Supabase edge function at supabase/functions/log-event/index.ts that:

1. Accepts a JSON body with:
   {
     visitor_id: string,     // anonymous ID from localStorage
     event_type: string,     // "search" | "product_view" | "add_to_cart"
     payload: object,        // event-specific data (see below)
     timestamp: string       // ISO 8601 timestamp
   }

2. Validates:
   - visitor_id is present and non-empty
   - event_type is one of the allowed values
   - payload is an object

3. Strips any PII from the payload before saving:
   - If payload contains "email", remove it
   - If payload contains "name", remove it
   - Log a warning if PII fields were present

4. Inserts into the events table using the Supabase service role client
   (so it bypasses RLS for the insert — the anon policy is still there as a fallback)

5. Returns { success: true } on success, { error: "..." } on failure

Expected payload shapes by event_type:
- "search": { query: string, resultCount: number }
- "product_view": { handle: string, title: string, price: number, productType: string }
- "add_to_cart": { handle: string, title: string, variant: string, quantity: number, price: number }

This function should fire-and-forget — the client should not wait for it.
```

### Step 5: Generate User Recent Events Edge Function

Create `supabase/functions/user-recent-events/index.ts`.

Provide the following Claude Code prompt:

```
Create a Supabase edge function at supabase/functions/user-recent-events/index.ts that:

1. Accepts a JSON body with: { visitorId: string }

2. Queries the events table for the visitor's recent activity:

   Recent searches (last 5):
   SELECT payload->>'query' as query, created_at
   FROM events
   WHERE visitor_id = $1 AND event_type = 'search'
   ORDER BY created_at DESC LIMIT 5

   Recent product views (last 10):
   SELECT payload->>'handle' as handle,
          payload->>'title' as title,
          payload->>'productType' as product_type,
          created_at
   FROM events
   WHERE visitor_id = $1 AND event_type = 'product_view'
   ORDER BY created_at DESC LIMIT 10

   Recent cart adds (last 5):
   SELECT payload->>'handle' as handle,
          payload->>'title' as title,
          created_at
   FROM events
   WHERE visitor_id = $1 AND event_type = 'add_to_cart'
   ORDER BY created_at DESC LIMIT 5

3. Returns:
   {
     recentSearches: Array<{ query: string, created_at: string }>,
     recentViews: Array<{ handle: string, title: string, product_type: string }>,
     recentCartAdds: Array<{ handle: string, title: string }>
   }

4. Returns empty arrays if no data found — never null
```

### Step 6: Implement Real trackEvent in analytics.ts

Provide the following Claude Code prompt:

```
Update src/lib/analytics.ts to implement real event tracking:

1. Add a getVisitorId() function:
   - Reads from localStorage key "visitor_id"
   - If not found, generates a new UUID with crypto.randomUUID()
   - Saves to localStorage and returns it
   - Never stores or returns the user's email

2. Update the trackEvent function:
   - Get the visitorId from getVisitorId()
   - Call supabase.functions.invoke("log-event", { body: { visitor_id, event_type, payload, timestamp } })
   - Fire-and-forget: do NOT await — use .catch(console.error) but don't block the caller
   - Also console.log in development (check import.meta.env.DEV)

3. Wire up trackEvent calls at key events:
   - In SemanticSearch component: trackEvent("search", { query, resultCount })
   - In the product detail page: trackEvent("product_view", { handle, title, price, productType })
     on component mount
   - In the cart store: trackEvent("add_to_cart", { handle, title, variant, quantity, price })
     when addToCart is called

Export: trackEvent, getVisitorId
```

### Step 7: Generate Self-Segmentation Modal

Create `src/components/SelfSegmentationModal.tsx`.

Provide the following Claude Code prompt:

```
Create a SelfSegmentationModal React component at src/components/SelfSegmentationModal.tsx that:

1. Renders as a centered modal with a friendly headline:
   "Tell us about yourself and get 10% off your first order"

2. Has a multi-step form (3 steps):

   Step 1 — About you:
   - First name (text input, required)
   - Email (email input, required) — explain this is for the discount code only
   - Age range (radio buttons: Under 25 / 25-34 / 35-44 / 45+)

   Step 2 — Your style:
   - Style preferences (multi-select chips): Casual / Performance / Technical / Commuter / Touring
   - Allow selecting multiple

   Step 3 — Your sizing (optional):
   - Shirt/collar size (select: XS / S / M / L / XL / XXL)
   - Waist size (text input, placeholder "e.g. 32")
   - Photo upload (optional — link to PhotoUpload component if available)
   - Discount code preview: "Your code: SUMMER10"

3. On submission:
   - Get the visitor_id from getVisitorId() in src/lib/analytics.ts
   - Get or generate a session_id from localStorage "session_id"
   - Insert into self_segmentation_profiles via Supabase client directly
   - Save the profile to localStorage as "user_profile" (JSON)
   - Save first_name to localStorage as "user_first_name"
   - Close the modal and call onComplete(profile) callback

4. Shows automatically:
   - 30 seconds after first visit (if no profile in localStorage)
   - Never shows again once a profile is saved

5. Has a "No thanks" dismiss option that sets a "profile_dismissed" flag in localStorage
   (prevents the modal from re-appearing for 30 days)

Export: SelfSegmentationModal (named export)
```

### Step 8: Generate Personalised Greeting and Shortcuts Utility

Provide the following Claude Code prompt:

```
Create src/lib/personalisation.ts with utilities for personalised UI:

1. generateGreeting(profile, recentEvents):
   - If profile?.first_name and recentEvents.recentSearches[0]:
     return `Welcome back, ${firstName}! Still looking for ${lastSearch}?`
   - If profile?.first_name:
     return `Hey ${firstName}, what are you in the mood for today?`
   - Default: "Hi there! What can I help you find today?"

2. generateShortcuts(profile, recentEvents) → Array<{ label: string, query: string }>:
   - From recent searches: { label: `More like "${search}"`, query: search }
   - From style preferences (sporty): { label: "Performance gear", query: "high-performance athletic" }
   - From style preferences (casual): { label: "Everyday rides", query: "casual comfortable cycling" }
   - Seasonal (months 5-8): { label: "Summer essentials", query: "lightweight breathable summer" }
   - Seasonal (months 11-2): { label: "Winter kit", query: "thermal insulated cold weather" }
   - Always add: { label: "Best sellers", query: "popular best sellers" }
   - Return first 4 results only

3. getStoredProfile() → UserProfile | null:
   - Read from localStorage "user_profile"
   - Parse JSON, return null if not found or invalid

4. Export: generateGreeting, generateShortcuts, getStoredProfile

Integrate personalisation into the ShoppingAssistant component:
- On mount, call getStoredProfile() and supabase.functions.invoke("user-recent-events",
  { body: { visitorId: getVisitorId() } })
- Use generateGreeting() for the initial assistant message
- Use generateShortcuts() to populate the shortcut pills
```

### Step 9: Update Status

```yaml
personalisation:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  files:
    - supabase/migrations/[timestamp]_personalisation.sql
    - supabase/functions/log-event/index.ts
    - supabase/functions/user-recent-events/index.ts
    - src/lib/analytics.ts (updated)
    - src/lib/personalisation.ts
    - src/components/SelfSegmentationModal.tsx
```

### Step 10: Confirm and Suggest Next Steps

```
## Personalisation Engine Generated

### Next Steps

1. Apply the database migration:
   ```bash
   supabase db push
   ```

2. Deploy the edge functions:
   ```bash
   supabase functions deploy log-event
   supabase functions deploy user-recent-events
   ```

3. **Validate**: `/wire:ac_personalisation-validate <project>`
```

## Edge Cases

### Profile Already Exists in Database

If a visitor returns to the site, check localStorage for the saved profile before
querying the database. The modal should never show again once a profile is saved.

### PII in Event Payloads

If any component mistakenly passes `email` or `name` in a `trackEvent` payload,
the `log-event` edge function strips those fields before saving. The events table
must never contain email addresses or full names.

## Output

This command produces:
- `supabase/migrations/[timestamp]_personalisation.sql`
- `supabase/functions/log-event/index.ts`
- `supabase/functions/user-recent-events/index.ts`
- `src/lib/analytics.ts` (upgraded from stub to real implementation)
- `src/lib/personalisation.ts`
- `src/components/SelfSegmentationModal.tsx`
- Updated `.wire/<project_id>/status.md`

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
