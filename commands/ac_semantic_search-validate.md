---
description: Functional and performance tests for semantic search
argument-hint: <release-folder>
---

# Functional and performance tests for semantic search

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_semantic_search-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.7\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate AI semantic search feature — functional, performance, and resilience tests
argument-hint: <project-folder>
---

# Agentic Commerce — Semantic Search Validate Command

## Purpose

Verify that the semantic search feature works correctly — natural language queries return relevant results, caching is active, error handling is robust, and the React component integrates correctly into the storefront.

## Usage

```bash
/wire:ac_semantic_search-validate YYYYMMDD_project_name
```

## Prerequisites

- `semantic_search.generate: complete` in status.md
- Search provider credentials configured as Supabase secrets
- Product catalog synced via the `sync-products` edge function

## Workflow

### Step 1: Verify Generate is Complete

1. Read `.wire/<project_id>/status.md`
2. Check `semantic_search.generate == complete`
3. Confirm all expected files exist:
   - `supabase/functions/sync-products/index.ts`
   - `supabase/functions/semantic-search/index.ts`
   - `src/components/SemanticSearch.tsx`

### Step 2: Catalog Sync Check

Ask the consultant to run the sync function and verify:

```bash
# Option A: Deployed function
curl -X POST https://[project].supabase.co/functions/v1/sync-products \
  -H "Authorization: Bearer [anon-key]"

# Option B: Local dev
supabase functions serve sync-products &
curl -X POST http://localhost:54321/functions/v1/sync-products
```

Expected response:
```json
{ "synced": [N] }
```

| Check | Criteria | Severity |
|-------|----------|----------|
| Sync returns product count | Response contains `synced: N` where N > 0 | Critical |
| All products synced | N matches actual Shopify product count (within 5%) | Critical |
| No auth errors | No 401/403 from search provider | Critical |

### Step 3: Semantic Search Functional Tests

Test a range of query types. For each, ask the consultant to submit the query in the UI or via curl and verify results:

```bash
curl -X POST https://[project].supabase.co/functions/v1/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "breathable jersey for hot weather"}'
```

#### Functional Checks

| Check | Test Query | Expected Behaviour | Severity |
|-------|-----------|-------------------|----------|
| Natural language match | "breathable jersey for hot weather" | Returns jerseys tagged light/summer/breathable | Critical |
| Intent expansion | "something warm for cold morning rides" | Returns thermal/winter products | Critical |
| No exact keyword match | A concept with no exact keyword in product titles | Still returns relevant results | Critical |
| Typo tolerance | "cyclng glvoes" | Returns cycling gloves despite typos | Major |
| Empty query | `{"query": ""}` | Returns 400 error, not a crash | Major |
| Very long query | 500+ character string | Handled gracefully, no 500 error | Major |
| Results include relevance_reason | Any query | Each result has `relevance_reason` field | Major |
| Results include score | Any query | Each result has `score` field | Minor |

#### Performance Checks

| Check | Criteria | Severity |
|-------|----------|----------|
| First search response time | < 3 seconds (uncached) | Major |
| Cached search response time | < 300ms for repeated identical query | Major |
| Cache hit indicator | `cached: true` in response on repeat query | Minor |
| Result count | Returns 5-20 results per query | Minor |

### Step 4: React Component Tests

Ask the consultant to test the UI in the local dev server:

| Check | Test Action | Expected Behaviour | Severity |
|-------|------------|-------------------|----------|
| Example pills visible | Load homepage | 3-4 example query pills shown below search bar | Major |
| Pill click searches | Click an example pill | Pill query appears in input, search fires | Major |
| Loading state shown | Submit a query | Spinner/loading indicator visible while waiting | Major |
| Results appear | After search | Product grid updates with semantic results | Critical |
| Relevance badges shown | Inspect result cards | `relevance_reason` text visible under price | Major |
| Active query label | After search | "Searching for: [query]" label with clear button | Major |
| Clear button works | Click clear | Input cleared, original product grid restored | Major |
| Enter key searches | Type query, press Enter | Search fires without clicking button | Major |
| Console no errors | Open browser console | No errors on page load or after search | Major |

### Step 5: Resilience Tests

| Check | Test Method | Expected Behaviour | Severity |
|-------|------------|-------------------|----------|
| Search provider down | Temporarily break the API key, run a query | Falls back gracefully (empty results, no crash) | Critical |
| Edge function 500 | Call with malformed body | Returns error message in UI, not blank page | Critical |
| Network timeout | Throttle network in DevTools, run long query | Shows timeout/error message after timeout | Major |

### Step 6: Analytics Tracking Check

Verify the analytics stub fires:

| Check | Test | Expected | Severity |
|-------|------|----------|----------|
| trackEvent called on search | Open browser console, run a search | `[Analytics] search {query: "...", resultCount: N}` logged | Minor |

### Step 7: Build Check

```bash
npm run build
tsc --noEmit
```

| Check | Criteria | Severity |
|-------|----------|----------|
| Build succeeds | Exits 0 with no errors | Critical |
| No TypeScript errors | `tsc --noEmit` exits 0 | Critical |

### Step 8: Produce Validation Report

Save to `.wire/<project_id>/semantic_search/validation_report.md`:

```markdown
# Semantic Search Validation Report

**Date:** YYYY-MM-DD
**Provider:** [Vertex AI / Algolia / pgvector / other]
**Products synced:** [N]

## Result: PASS / FAIL

## Critical Checks
| Check | Result | Notes |
...

## Issues Requiring Remediation
[list any FAIL items with suggested fixes]
```

### Step 9: Update Status

```yaml
semantic_search:
  generate: complete
  validate: pass   # or fail
  review: not_started
  validation_report: semantic_search/validation_report.md
  validated_date: YYYY-MM-DD
```

### Step 10: Confirm and Suggest Next Steps

**If PASS:**
```
## Semantic Search Validation: PASS ✓

### Next Steps
1. Review with stakeholders: `/wire:ac_semantic_search-review <project>`
2. Or proceed to next feature: `/wire:ac_conversational_assistant-generate <project>`
```

**If FAIL:**
```
## Semantic Search Validation: FAIL ✗

[N] issues found. See validation report for remediation steps.
Re-run: `/wire:ac_semantic_search-validate <project>`
```

## Output

- `.wire/<project_id>/semantic_search/validation_report.md`
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
