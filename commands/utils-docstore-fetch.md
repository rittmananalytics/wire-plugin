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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.9\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"utils-docstore-fetch\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.9\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
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
