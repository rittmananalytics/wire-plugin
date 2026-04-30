---
description: Pre-flight checklist verification for base storefront
argument-hint: <release-folder>
---

# Pre-flight checklist verification for base storefront

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.15\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_storefront-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.15\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate base e-commerce storefront against pre-flight checklist
argument-hint: <project-folder>
---

# Agentic Commerce Storefront Validate Command

## Purpose

Run automated and manual checks against the generated storefront to confirm it meets the requirements for agentic feature development. Produces a PASS/FAIL report with actionable remediation steps for any failures.

## Usage

```bash
/wire:ac_storefront-validate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.generate: complete` in status.md
- GitHub repo URL recorded in status.md
- Local clone of the repo available (or repo URL accessible)

## Workflow

### Step 1: Verify Generate is Complete

1. Read `.wire/<project_id>/status.md`
2. Check `storefront.generate == complete`

If not:
```
Error: Storefront not yet generated.
Run: /wire:ac_storefront-generate <project_id>
```

### Step 2: Read Project State

1. Read the GitHub repo URL from status.md
2. Ask the consultant to confirm local dev server is running (`npm run dev`)
3. Identify the local URL (typically `http://localhost:5173`)

### Step 3: Run Validation Checks

Work through each check with the consultant. For each item, mark PASS, FAIL, or SKIP (if feature not included in scope).

#### 3A — Shopify Integration Checks

| Check | Criteria | Severity |
|-------|----------|----------|
| Products load from Shopify | Product grid shows real products with images, titles, prices | Critical |
| Product detail pages render | `/product/:handle` shows gallery, variants, price, description | Critical |
| Variant selector works | Selecting different options updates price and stock status | Critical |
| Out-of-stock variants disabled | Add to Cart button is disabled for unavailable variants | Major |
| Category filtering works | Category nav links filter the product grid correctly | Major |

#### 3B — Cart & Checkout Checks

| Check | Criteria | Severity |
|-------|----------|----------|
| Add to cart works | Clicking "Add to Cart" adds item to cart state | Critical |
| Cart drawer opens | Cart icon opens slide-out drawer with items | Critical |
| Quantity update works | +/- buttons update line item quantities via Shopify API | Critical |
| Remove item works | Remove button removes item from cart via Shopify API | Critical |
| Cart persists across refresh | Reload page — cart items remain | Critical |
| Checkout opens Shopify checkout | "Checkout with Shopify" button opens checkout in new tab | Critical |
| Cart clears after checkout | Returning from checkout, cart is empty | Major |
| Checkout URL correct | URL contains `?channel=online_store` | Major |

#### 3C — Infrastructure Checks

| Check | Criteria | Severity |
|-------|----------|----------|
| Supabase client configured | `src/integrations/supabase/client.ts` exists and connects | Critical |
| Edge functions directory exists | `supabase/functions/` directory present in repo | Critical |
| GitHub repo synced | Latest Lovable changes reflected in GitHub | Critical |
| `.claude/CLAUDE.md` present | Project instructions file exists in repo root | Major |
| Environment variables documented | `.env.example` or README lists required env vars | Major |

#### 3D — Frontend Quality Checks

| Check | Criteria | Severity |
|-------|----------|----------|
| Mobile responsive layout | 1-col mobile, 2-col tablet, 3-4-col desktop grid | Major |
| Dark mode support | Site looks correct in dark mode (if configured) | Minor |
| No console errors on load | Browser console shows no errors on homepage | Major |
| Images have alt text | Product images include descriptive alt attributes | Minor |
| SEO meta tags present | Title, description, H1 on all key pages | Minor |
| Product JSON-LD present | Product detail pages include structured data | Minor |

#### 3E — Code Quality Checks

Ask the consultant to run these in the cloned repo:

```bash
npm run build     # Must succeed with no errors
npm run lint      # Zero errors (warnings acceptable)
```

| Check | Criteria | Severity |
|-------|----------|----------|
| Build succeeds | `npm run build` exits 0 | Critical |
| No TypeScript errors | `tsc --noEmit` exits 0 | Critical |
| Lint passes | `npm run lint` exits 0 | Major |

### Step 4: Produce Validation Report

Generate a report in `.wire/<project_id>/storefront/validation_report.md`:

```markdown
# Storefront Validation Report

**Project:** [project_id]
**Date:** YYYY-MM-DD
**Validated by:** [consultant name]

## Result: PASS / FAIL

## Critical Checks

| Check | Result | Notes |
|-------|--------|-------|
| Products load from Shopify | PASS | |
| Cart add/update/remove | PASS | |
| Checkout opens Shopify | PASS | |
| Cart persists across refresh | PASS | |
| Supabase client configured | PASS | |
| GitHub repo synced | PASS | |
| Build succeeds | PASS | |

## Major Checks

| Check | Result | Notes |
|-------|--------|-------|
| ... | | |

## Minor Checks

| Check | Result | Notes |
|-------|--------|-------|
| ... | | |

## Failures Requiring Remediation

### [Check Name]
**Issue:** [description]
**Fix:** [specific corrective action]
**Lovable prompt to fix:**
```
[paste corrective Lovable prompt here]
```
```

### Step 5: Update Status

```yaml
storefront:
  generate: complete
  validate: pass   # or fail
  review: not_started
  validation_report: storefront/validation_report.md
  validated_date: YYYY-MM-DD
```

### Step 6: Confirm and Suggest Next Steps

**If PASS:**
```
## Storefront Validation: PASS ✓

All critical and major checks passed. The storefront is ready for stakeholder review.

### Next Steps
1. **Review storefront**: `/wire:ac_storefront-review <project>`
2. Or proceed directly to feature development if review is deferred.
```

**If FAIL:**
```
## Storefront Validation: FAIL ✗

[N] critical / [N] major issues found. Remediation required before review.

### Issues to Fix
[list each failure with corrective Lovable prompt]

Re-run validation after fixes: `/wire:ac_storefront-validate <project>`
```

## Edge Cases

### Build Errors

If `npm run build` fails:
1. Read the error output
2. Identify the failing file and error type
3. Provide the corrective Claude Code prompt to fix it:
   ```
   Fix the TypeScript error in [file]: [error message].
   Do not change any other files.
   ```

### Shopify API Not Returning Products

Check:
- Products are published to the **Headless** sales channel (not just Online Store)
- Storefront API token is in the correct environment variable
- Token has `unauthenticated_read_product_listings` scope

## Output

This command produces:
- `.wire/<project_id>/storefront/validation_report.md`
- Updated `status.md` with `validate: pass` or `validate: fail`

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
