---
description: Build base e-commerce storefront via Lovable and sync to GitHub
argument-hint: <release-folder>
---

# Build base e-commerce storefront via Lovable and sync to GitHub

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.7\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_storefront-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.7\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Build base e-commerce storefront via Lovable and sync to GitHub
argument-hint: <project-folder>
---

# Agentic Commerce Storefront Generate Command

## Purpose

Guide the consultant through building a production-ready e-commerce storefront using Lovable's chat interface, wiring it to Shopify's Storefront API, and syncing the resulting codebase to GitHub — ready for agentic feature development. This is the prerequisite for all subsequent `/wire:ac_*` commands.

## Usage

```bash
/wire:ac_storefront-generate YYYYMMDD_project_name
```

## Prerequisites

- Active Lovable account with a new project created
- Shopify store with Storefront API access token (products published to Headless channel)
- GitHub account with Lovable GitHub App authorised
- Supabase project enabled in Lovable (Lovable Cloud)

Read `.wire/<project_id>/artifacts/` for any SOW, brand brief, or Shopify store details.

## Workflow

### Step 1: Verify Prerequisites and Read Inputs

1. Read `.wire/<project_id>/status.md`
2. Confirm `project_type: agentic_commerce` in frontmatter
3. Read any brand briefs or Shopify credentials in `.wire/<project_id>/artifacts/`
4. If prerequisites are missing, output:
   ```
   Missing prerequisite: [item]
   
   Please provide: [specific detail needed]
   ```

### Step 2: Phase 1 — Project Creation & Brand Foundation

Present the following Lovable prompts in sequence. After each prompt, wait for the consultant to confirm Lovable has rendered the output before proceeding.

**Prompt 2.1 — Initial scaffold:**

```
Create a modern e-commerce storefront for [Brand Name], a [industry] brand. The design 
should be [aesthetic description — e.g. minimal, editorial, bold]. Use a serif/display 
font for headings and a clean sans-serif for body text. The colour palette should be 
[describe palette or reference]. Include a navbar with the brand name, category 
navigation, and a cart icon. Add a hero section with a tagline and a product grid 
below it. No mock products yet — just the empty grid with a "No products found" message.
```

**Prompt 2.2 — Design system refinement:**

```
Update the design system: set the primary colour to [HSL values], add a muted 
background tone, and ensure all colours use CSS custom properties via index.css. 
The navbar should have a subtle bottom border, and product cards should have hover 
elevation. Make sure the site looks good in both light and dark modes.
```

Key requirements to verify after this step:
- All colours defined as HSL CSS variables in `index.css`
- Tailwind config references semantic tokens (`--primary`, `--background`, etc.)
- Typography uses `font-display` for headings and sans for body

**Prompt 2.3 — Core pages:**

```
Add the following pages with proper routing: a product detail page at /product/:handle, 
a contact page, and policy pages for shipping, refunds, and terms of service. The 
product detail page should show a large image gallery, title, price, variant selector, 
description, and an Add to Cart button. Use placeholder content for now.
```

### Step 3: Phase 2 — Shopify Integration

**Prompt 3.1 — Storefront API connection:**

```
Connect this site to my Shopify store. Use the Shopify Storefront API to fetch and 
display real products. Replace the empty product grid with live product data showing 
images, titles, prices, and product types. Each product card should link to its 
detail page at /product/[handle].
```

Confirm Lovable creates:
- `src/lib/shopify.ts` with Storefront API client
- GraphQL queries for product listing and individual product fetch
- `useShopifyProducts` hook

**Prompt 3.2 — Category filtering:**

```
Add category filtering to the product grid. Create navigation links for 
[your categories]. Each category should filter products using a Shopify query 
parameter. Show all products by default. Make sure the grid is responsive — 
1 column on mobile, 2 on tablet, 3-4 on desktop.
```

**Prompt 3.3 — Cart & checkout:**

```
Implement a full shopping cart using Zustand for state management. The cart should 
persist across page refreshes using localStorage. When items are added, create a 
Shopify cart via the Storefront API cartCreate mutation. Include a slide-out cart 
drawer accessible from the navbar cart icon, showing item thumbnails, quantities 
with +/- controls, a remove button, line totals, and a "Checkout with Shopify" 
button that opens the Shopify checkout URL in a new tab.
```

Critical requirements:
- Cart uses Shopify mutations: `cartCreate`, `cartLinesAdd`, `cartLinesUpdate`, `cartLinesRemove`
- Checkout URL includes `?channel=online_store`
- Checkout opens in new tab via `window.open(url, '_blank')`
- Cart syncs on tab visibility change

**Prompt 3.4 — Product detail page:**

```
Make the product detail page fully functional. Fetch the product by handle from the 
Shopify Storefront API. Show all product images in a gallery, display all variant 
options as selectable buttons, update the displayed price when variants change, and 
disable the Add to Cart button for out-of-stock variants. Include the full product 
description below.
```

### Step 4: Phase 3 — Backend & Infrastructure

**Prompt 4.1 — Supabase backend:**

```
Set up the backend for this project. I'll need a database for caching search results 
and storing user interaction data later. For now, just ensure the Supabase client is 
configured and working.
```

Confirm:
- `src/integrations/supabase/client.ts` exists (auto-generated)
- `supabase/functions/` directory created
- Database accessible

**Prompt 4.2 — Authentication (optional):**

```
Add a sign-in/sign-up page at /auth using email and password authentication. Show a 
user avatar in the navbar when signed in, with a dropdown for sign-out. Don't enable 
auto-confirm — users should verify their email.
```

**Prompt 4.3 — SEO & meta:**

```
Add proper SEO to all pages. Each page should have a unique title tag under 60 
characters and a meta description under 160 characters. The homepage should have a 
single H1. Product detail pages should use the product title as the H1 and include 
structured data (JSON-LD) for Product schema. Add a robots.txt and ensure images 
have alt text.
```

### Step 5: Phase 4 — GitHub Sync & Handoff

Guide the consultant through:

1. In Lovable editor → **Project Settings → GitHub → Connect project**
2. Authorise the Lovable GitHub App
3. Select GitHub account/organisation
4. Click **Create Repository**

Then clone and verify locally:

```bash
git clone https://github.com/[your-org]/[your-repo].git
cd [your-repo]
npm install
npm run dev
```

### Step 6: Create Claude Code Project Instructions

Generate a `.claude/CLAUDE.md` file in the cloned repo:

```markdown
# Project Context

This is a React 18 + Vite + Tailwind CSS + TypeScript e-commerce storefront.

## Key Architecture
- **Product data**: Shopify Storefront API (see src/lib/shopify.ts)
- **State management**: Zustand (see src/stores/)
- **Backend**: Supabase via Lovable Cloud (see src/integrations/supabase/)
- **Edge functions**: supabase/functions/ (auto-deployed)
- **Styling**: Tailwind with CSS custom properties (see src/index.css)

## Environment Variables
- VITE_SUPABASE_URL — Supabase project URL
- VITE_SUPABASE_PUBLISHABLE_KEY — Supabase anon key

## Adding New Features
- Edge functions go in supabase/functions/[name]/index.ts
- New pages go in src/pages/ and must be added to the router in App.tsx
- All API keys for external services should be stored as Supabase secrets
- Use the existing storefrontApiRequest() helper for Shopify API calls
```

### Step 7: Update Status

1. Read `.wire/<project_id>/status.md`
2. Update the `storefront` section:
   ```yaml
   storefront:
     generate: complete
     validate: not_started
     review: not_started
     github_repo: https://github.com/[org]/[repo]
     lovable_url: https://lovable.dev/projects/[project-id]
     generated_date: YYYY-MM-DD
   ```
3. Record the GitHub repo URL and Lovable project URL in the status file

### Step 8: Confirm and Suggest Next Steps

```
## Storefront Generated

**Lovable project:** [URL]
**GitHub repo:** [URL]

### Next Steps

1. **Validate the storefront**: `/wire:ac_storefront-validate <project>`
2. After validation passes: `/wire:ac_storefront-review <project>`
3. Once approved, begin feature development:
   - `/wire:ac_semantic_search-generate <project>`
   - `/wire:ac_conversational_assistant-generate <project>`
```

## Edge Cases

### Lovable Generation Fails

If Lovable produces an incorrect component, provide a corrective prompt:
```
The [component] has an issue: [description]. Please fix it by [specific instruction].
Do not change anything else.
```

### Shopify API Authentication Fails

Check:
- Storefront API token is for the correct store
- Products are published to the Headless sales channel
- Token has `unauthenticated_read_product_listings` scope

## Output

This command produces:
- A live Lovable-hosted storefront preview
- A GitHub repository with the full React/Vite/TypeScript codebase
- `.claude/CLAUDE.md` project instructions in the repo
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
