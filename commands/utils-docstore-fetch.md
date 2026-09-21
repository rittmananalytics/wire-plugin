---
description: Fetch document store content and comments for review
argument-hint: <project-folder> <artifact>
---

# Fetch document store content and comments for review

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'utils-docstore-fetch',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Fetch document store content and reviewer comments for a review command
argument-hint: <project-folder> <artifact_id> <artifact_name> <file_path>

---

# Document Store Fetch Utility

## Purpose

Retrieve the external document store version of an artifact and any reviewer comments left since the last sync. Called at the start of every review command as part of the "Retrieve External Context" step, alongside `meeting_context.md` and `atlassian_search.md`. Surfaces reviewer edits and comments to enrich the review session — reviewers may have annotated or modified the Confluence or Notion page directly rather than providing feedback through the Wire review workflow.

## Usage

```bash
/wire:utils-docstore-fetch YYYYMMDD_project_name requirements "Requirements Specification" .wire/releases/01-discovery/requirements/requirements_specification.md
```

Typically invoked automatically at the start of review commands. Inputs are passed by the calling spec:

| Input | Description | Example |
|-------|-------------|---------|
| `artifact_id` | Machine-readable artifact key | `requirements` |
| `artifact_name` | Human-readable display name | `Requirements Specification` |
| `file_path` | Path to canonical .md file in repo | `.wire/releases/01-discovery/requirements/requirements_specification.md` |
| `project_id` | Release folder path | `releases/01-discovery` |

## Prerequisites

- Project must have a valid `status.md` with a `docstore` section
- For Confluence: Atlassian MCP server must be configured
- For Notion: Notion MCP server must be configured
- If `docstore.provider` is `null`, the utility returns empty — no error, no output

---

## Workflow

### Step 1: Check Document Store Configuration

**Process**:
1. Read the project's `status.md`
2. Check `docstore.provider` in YAML frontmatter
3. If `provider` is `null`, absent, or the `docstore` section does not exist: **return empty** — output nothing, return no context block. The review command continues with only the meeting and Jira context.
4. Otherwise, extract:
   - `docstore.provider` (`confluence`, `notion`, or `both`)
   - `docstore.confluence.artifacts.[artifact_id]` — specifically `page_id` and `page_url` (if Confluence)
   - `docstore.notion.artifacts.[artifact_id]` — specifically `page_id` and `page_url` (if Notion)

### Step 2: Read the Canonical File

Read the file at `file_path`. Store its content as `canonical_content`.

If the file cannot be read, log a note and continue — the fetch can still retrieve comments even if the canonical file is unavailable:
```
Note: Could not read canonical file [file_path]. Diff comparison will be skipped.
```

---

### Step 3: Confluence Fetch

*Run this step if `provider` is `confluence` or `both`, and `docstore.confluence.artifacts.[artifact_id].page_id` is non-null.*

If `page_id` is null or absent, skip this step and note: `"[artifact_name] has not yet been synced to Confluence."`

#### Step 3.1: Fetch Page Content

```
getConfluencePage:
  cloudId: "[docstore.confluence.cloud_id]"
  pageId: "[confluence_page_id]"
```

Extract:
- `body.storage.value` — the page content in Confluence storage format (XHTML)
- `version.number` — current version
- `version.by.displayName` — last editor name
- `version.when` — last edited timestamp
- `_links.webui` — page URL (may differ from the stored URL if the page was moved)

Convert the Confluence storage format body back to plain text for comparison with the canonical markdown (rough conversion — strip all XML tags, decode HTML entities, normalise whitespace). Store as `confluence_plain_text`.

On failure:
```
Note: Could not fetch Confluence page for [artifact_name]. Error: [error]. Skipping Confluence context.
```
Skip Steps 3.2–3.4 for Confluence; continue with other providers.

#### Step 3.2: Fetch Inline Comments

```
getConfluencePageInlineComments:
  cloudId: "[docstore.confluence.cloud_id]"
  pageId: "[confluence_page_id]"
```

For each returned comment, extract:
- `author.displayName`
- `created` (ISO timestamp)
- `body.storage.value` — strip XML tags to get plain text
- `resolvedAt` — if present, the comment has been resolved

Collect all comments into a list. Note the resolved/unresolved state.

On failure: set inline comments to empty list and continue.

#### Step 3.3: Fetch Footer Comments

```
getConfluencePageFooterComments:
  cloudId: "[docstore.confluence.cloud_id]"
  pageId: "[confluence_page_id]"
```

For each returned comment, extract:
- `author.displayName`
- `created` (ISO timestamp)
- `body.storage.value` — strip XML tags for plain text

Collect into a separate list from inline comments.

On failure: set footer comments to empty list and continue.

#### Step 3.4: Diff Page Content Against Canonical

Compare `confluence_plain_text` with `canonical_content` (after stripping markdown syntax for a fair comparison). Use a line-by-line diff approach:

1. Normalise both texts: lowercase, collapse whitespace, strip punctuation — this avoids false positives from formatting differences introduced by the markdown → storage format → plain text round-trip
2. Split each into sections based on heading patterns
3. For each section present in both:
   - If the section text is substantially different (more than ~15% of words changed): flag as "edited"
   - If a section exists in the Confluence version but not in the canonical: flag as "added by reviewer"
   - If a section exists in the canonical but not in the Confluence version: flag as "removed by reviewer"

Store the diff findings as a list of `confluence_diffs`:
```
[
  {"section": "Section 3.2: Data Sources", "type": "edited", "canonical_excerpt": "...", "docstore_excerpt": "..."},
  {"section": "Section 5: Appendix", "type": "added_by_reviewer", "docstore_excerpt": "..."},
  ...
]
```

If no differences are detected: `confluence_diffs = []`

If `canonical_content` was unavailable (Step 2 failed): `confluence_diffs = null` (skip diff, cannot compare)

---

### Step 4: Notion Fetch

*Run this step if `provider` is `notion` or `both`, and `docstore.notion.artifacts.[artifact_id].page_id` is non-null.*

Run independently of Step 3 — a Confluence failure does not skip Notion.

If `page_id` is null or absent, skip this step and note: `"[artifact_name] has not yet been synced to Notion."`

#### Step 4.1: Fetch Page Content and Metadata

```
notion_get_page:
  page_id: "[notion_page_id]"
```

Extract:
- `last_edited_time` — last edited timestamp
- `last_edited_by.name` — last editor name
- `url` — canonical Notion URL

Then retrieve the page's block children to reconstruct the content:

```
notion_get_block_children:
  block_id: "[notion_page_id]"
```

Convert the returned blocks to plain text for comparison:
- `heading_1` / `heading_2` / `heading_3` blocks → extract `rich_text[].plain_text`, prefix with `#`/`##`/`###`
- `paragraph` blocks → extract `rich_text[].plain_text`
- `bulleted_list_item` → prefix with `-`
- `numbered_list_item` → prefix with `1.`
- `code` blocks → extract `rich_text[].plain_text`
- `quote` blocks → prefix with `>`
- Concatenate all into a plain text string

Store as `notion_plain_text`.

On failure:
```
Note: Could not fetch Notion page for [artifact_name]. Error: [error]. Skipping Notion context.
```
Skip Steps 4.2–4.3 for Notion; continue.

#### Step 4.2: Fetch Page Comments

```
notion_get_comments:
  block_id: "[notion_page_id]"
```

For each returned comment, extract:
- `created_by.name`
- `created_time` (ISO timestamp)
- `rich_text[].plain_text` — concatenate for comment body

On failure: set comments to empty list and continue.

#### Step 4.3: Diff Page Content Against Canonical

Apply the same section-based diff approach as Step 3.4, comparing `notion_plain_text` against `canonical_content`.

Store the diff findings as `notion_diffs` using the same structure as `confluence_diffs`.

---

### Step 5: Assemble and Return Context Block

Combine all findings into a structured context block. The calling review command will surface this to the reviewer.

**Template**:

```markdown
## Document Store Context — [artifact_name]

### Reviewer Comments ([N] total)

[If no comments from any provider:]
No reviewer comments found in the document store.

[If comments exist, list each in chronological order, grouped by provider if both:]

**Confluence** ([N] inline + [N] footer comments):
- **[Author]** ([date]): [comment text] _(inline, [resolved/unresolved])_
- **[Author]** ([date]): [comment text] _(footer)_

**Notion** ([N] comments):
- **[Author]** ([date]): [comment text]

---

### Document Edits Since Last Sync

[If confluence_diffs is null and notion_diffs is null:]
Could not compare — canonical file was unavailable.

[If confluence_diffs = [] and notion_diffs = []:]
No edits — document store matches the canonical version.

[If diffs exist:]
The following differences were detected between the document store and the canonical repo file.
These may reflect direct reviewer edits made after the last generate.

**Confluence edits** (last edited by [last_editor] on [last_edited_date]):
[For each diff:]
- **[section title]** — [type: edited / added by reviewer / removed by reviewer]
  - Canonical: "[canonical_excerpt (first 120 chars)]..."
  - Confluence: "[docstore_excerpt (first 120 chars)]..."

[If confluence_diffs is empty but notion has diffs:]
Confluence: No edits detected.

**Notion edits** (last edited by [last_editor] on [last_edited_date]):
[Same format as Confluence diffs]

[If notion_diffs is empty but Confluence has diffs:]
Notion: No edits detected.

---

### Links
[If Confluence configured:]
- **Confluence**: [page_url]
[If Notion configured:]
- **Notion**: [page_url]
```

#### Guidance for the calling review spec

After surfacing this context block, instruct the reviewer:

```
Review the document store activity above before gathering feedback.

If reviewers have edited the Confluence or Notion page directly, consider whether those
edits should be incorporated into the canonical repo file before or after this review.

If there are unresolved inline comments in Confluence, address them as part of the
review feedback.
```

**Minimal output case** — if there are no comments and no diffs, output the short form instead:

```
Document Store Context — [artifact_name]: No activity since generation.
[Confluence: [page_url]] [Notion: [page_url]]
```

---

### Step 6: Handle Edge Cases

**Atlassian MCP not available:**
- Skip all Confluence steps silently
- If Confluence is configured: note `"Note: Could not reach Atlassian MCP. Confluence context unavailable."`
- Return whatever Notion context is available (or empty if Notion also unavailable)

**Notion MCP not available:**
- Skip all Notion steps silently
- If Notion is configured: note `"Note: Could not reach Notion MCP. Notion context unavailable."`
- Return whatever Confluence context is available

**Both providers unavailable:**
- Return: `"Document store context unavailable (MCP servers unreachable). Review proceeding without external context."`

**Page has not been synced yet (page_id is null):**
- Note: `"[artifact_name] has not yet been synced to [provider]. No document store context available."`
- This is expected if the artifact was just generated and `docstore_sync.md` failed or was skipped

**Very large page (>50 comments or >200 blocks):**
- For comments: summarise — `"[N] comments found. Showing the [10] most recent."`
- For blocks: process in batches using the `start_cursor` pagination parameter of `notion_get_block_children`

**Comment author is unknown or anonymous:**
- Display as `"Unknown reviewer"` in the context block

**Diff produces too many sections flagged as different (>10):**
- Summarise: `"[N] sections differ significantly between the document store and canonical file. This may indicate a major revision was made externally. Review the [provider] page directly before proceeding."`
- Provide the page link

**Provider is `both` but one provider has no page_id:**
- Fetch whichever provider has a page_id; skip the other with a note

In all failure cases, the calling review command is never blocked. This utility is additive context only.

## Output

This utility returns a structured context block containing:
- All reviewer comments from Confluence (inline and footer) and/or Notion, with author, date, and text
- A section-by-section diff between the document store version and the canonical repo file, identifying reviewer edits made directly in the document store
- Page URLs for quick navigation
- A brief "no activity" message if there are no comments and no edits
- Graceful degradation per provider — Confluence and Notion failures are independent
- Empty output if no document store is configured (`provider: null`)

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
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
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
