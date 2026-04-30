---
description: Sync a generated artifact to the document store
argument-hint: <project-folder> <artifact>
---

# Sync a generated artifact to the document store

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.16\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"utils-docstore-sync\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.16\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Sync a generated artifact to the configured document store
argument-hint: <project-folder> <artifact_id> <artifact_name> <file_path>
---

# Document Store Sync Utility

## Purpose

Publish or update a generated artifact in the configured external document store (Confluence, Notion, or both). Called at the end of every generate command, after the Jira sync step. Converts the canonical markdown file to the appropriate format for each provider and records the resulting page IDs and URLs back into `status.md` for future updates and for use by `docstore_fetch.md` during reviews.

## Usage

```bash
/wire:utils-docstore-sync YYYYMMDD_project_name requirements "Requirements Specification" .wire/releases/01-discovery/requirements/requirements_specification.md
```

Typically invoked automatically by generate commands. Inputs are passed by the calling spec:

| Input | Description | Example |
|-------|-------------|---------|
| `artifact_id` | Machine-readable artifact key | `requirements` |
| `artifact_name` | Human-readable display name | `Requirements Specification` |
| `file_path` | Path to generated markdown file | `.wire/releases/01-discovery/requirements/requirements_specification.md` |
| `project_id` | Release folder path | `releases/01-discovery` |

## Prerequisites

- Project must have a valid `status.md` with a `docstore` section (created by `docstore_setup.md`)
- For Confluence: Atlassian MCP server must be configured
- For Notion: Notion MCP server must be configured
- If `docstore.provider` is `null`, the utility exits immediately without error

---

## Workflow

### Step 1: Check Document Store Configuration

**Process**:
1. Read the project's `status.md`
2. Check `docstore.provider` in YAML frontmatter
3. If `provider` is `null`, absent, or the `docstore` section does not exist: **exit silently** — no output, no error. The generate command continues normally.
4. Otherwise, extract:
   - `docstore.provider` (`confluence`, `notion`, or `both`)
   - `docstore.confluence.cloud_id` (if Confluence)
   - `docstore.confluence.space_key` (if Confluence)
   - `docstore.confluence.parent_page_id` (if Confluence)
   - `docstore.confluence.artifacts.[artifact_id]` (if Confluence — check for existing page)
   - `docstore.notion.parent_page_id` (if Notion)
   - `docstore.notion.artifacts.[artifact_id]` (if Notion — check for existing page)

### Step 2: Read the Generated Markdown

Read the file at `file_path`. If the file cannot be read:
```
Note: Could not read [file_path] for document store sync. Skipping.
```
Exit without error.

Store the raw markdown content for conversion in subsequent steps.

---

### Step 3: Confluence Sync

*Run this step if `provider` is `confluence` or `both`.*

#### Step 3.1: Convert Markdown to Confluence Storage Format

Convert the markdown content to Confluence storage format (a subset of XHTML). Apply the following transformation rules:

**Headings**:
- `# Heading` → `<h1>Heading</h1>`
- `## Heading` → `<h2>Heading</h2>`
- `### Heading` → `<h3>Heading</h3>`
- `#### Heading` → `<h4>Heading</h4>`

**Text formatting**:
- `**bold**` → `<strong>bold</strong>`
- `*italic*` or `_italic_` → `<em>italic</em>`
- `~~strikethrough~~` → `<del>strikethrough</del>`
- `` `inline code` `` → `<code>inline code</code>`

**Paragraphs**:
- Blank-line-separated text blocks → `<p>paragraph text</p>`

**Code blocks**:
```
```language
code
```
```
→
```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">language</ac:parameter>
  <ac:plain-text-body><![CDATA[code]]></ac:plain-text-body>
</ac:structured-macro>
```
If no language is specified, omit the language parameter.

**Unordered lists**:
```
- item 1
- item 2
  - nested item
```
→
```xml
<ul>
  <li>item 1</li>
  <li>item 2
    <ul><li>nested item</li></ul>
  </li>
</ul>
```

**Ordered lists**:
```
1. item 1
2. item 2
```
→
```xml
<ol>
  <li>item 1</li>
  <li>item 2</li>
</ol>
```

**Tables**:
```
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```
→
```xml
<table>
  <thead>
    <tr>
      <th><p>Header 1</p></th>
      <th><p>Header 2</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>Cell 1</p></td>
      <td><p>Cell 2</p></td>
    </tr>
  </tbody>
</table>
```

**Horizontal rules**: `---` → `<hr/>`

**Blockquotes**: `> text` → `<blockquote><p>text</p></blockquote>`

**Links**: `[text](url)` → `<a href="url">text</a>`

**Images**: `![alt](url)` → `<ac:image><ri:url ri:value="url"/></ac:image>`

Store the converted content as `confluence_storage_body`.

#### Step 3.2: Check for Existing Page

Inspect `docstore.confluence.artifacts.[artifact_id]` in `status.md`:
- If `page_id` is present and non-null: proceed to **Step 3.3** (update existing page)
- If `page_id` is absent or null: proceed to **Step 3.4** (create new page)

#### Step 3.3: Update Existing Confluence Page

Fetch the current page version number (required for updates):

```
getConfluencePage:
  cloudId: "[cloud_id]"
  pageId: "[existing_page_id]"
```

Extract `version.number` from the response. Increment by 1 for the update.

Then update the page:

```
updateConfluencePage:
  cloudId: "[cloud_id]"
  pageId: "[existing_page_id]"
  title: "[artifact_name]"
  version: [current_version + 1]
  body: "[confluence_storage_body]"
  representation: "storage"
```

On success: record `last_synced` timestamp (current ISO datetime) in `status.md` under `docstore.confluence.artifacts.[artifact_id].last_synced`. The `page_id` and `page_url` remain unchanged.

On failure: log and continue (see Step 5 for error handling).

Proceed to **Step 3.5** to update the index page.

#### Step 3.4: Create New Confluence Page

Create a new page as a child of the engagement's parent page:

```
createConfluencePage:
  cloudId: "[cloud_id]"
  spaceKey: "[space_key]"
  parentId: "[docstore.confluence.parent_page_id]"
  title: "[artifact_name]"
  body: "[confluence_storage_body]"
  representation: "storage"
```

On success: extract the returned `id` and `_links.webui` (page URL). Write to `status.md`:

```yaml
docstore:
  confluence:
    artifacts:
      [artifact_id]:
        page_id: "[returned_page_id]"
        page_url: "[returned_page_url]"
        last_synced: "[current ISO datetime]"
```

On failure: log and continue.

Proceed to **Step 3.5** to update the index page.

#### Step 3.5: Update Confluence Index Page

After every successful create or update, rebuild the "Wire Documents" index page so that its artifact table reflects the current state of all synced artifacts.

**Process**:

1. Build the artifact map from two sources merged together:
   - Read `docstore.confluence.artifacts` from `status.md` (previously persisted entries)
   - Overlay any `page_id`, `page_url`, and `last_synced` values produced **in the current run** (Steps 3.3/3.4) — these may not yet be written to disk, but must be included so the newly synced artifact appears as a live link rather than "Pending generation"

2. Fetch the current version of the parent index page (needed for the update call):
   ```
   getConfluencePage:
     cloudId: "[cloud_id]"
     pageId: "[docstore.confluence.parent_page_id]"
   ```
   Extract `version.number`.

3. Rebuild the index table body. For each artifact in the standard artifact order (requirements, workshops, conceptual_model, pipeline_design, data_model, mockups, pipeline, dbt, semantic_layer, dashboards, data_quality, uat, deployment, training, documentation — plus discovery artifacts: problem_definition, pitch, release_brief, sprint_plan):
   - If the artifact has a `page_id` in the merged artifact map: render as a linked row using the Confluence internal page link macro (do NOT use `<a href>` — the `page_url` field from the API is a relative path that will not render as a clickable link)
   - If not yet synced: render the artifact name as plain text with "Pending generation"
   - Only include rows for artifacts that are in-scope for this release (i.e. present in `status.md`)

   Table structure (use `<ac:link>` with `ri:page-id` for internal Confluence links):
   ```xml
   <table>
     <thead>
       <tr>
         <th><p>Artifact</p></th>
         <th><p>Status</p></th>
         <th><p>Last Synced</p></th>
       </tr>
     </thead>
     <tbody>
       <!-- Row for a synced artifact — note: ac:link not href -->
       <tr>
         <td><p>
           <ac:link>
             <ri:page ri:page-id="[page_id]"/>
             <ac:plain-text-link-body><![CDATA[[artifact display name]]]></ac:plain-text-link-body>
           </ac:link>
         </p></td>
         <td><p>Published</p></td>
         <td><p>[last_synced date]</p></td>
       </tr>
       <!-- Row for an artifact not yet synced -->
       <tr>
         <td><p>[artifact display name]</p></td>
         <td><p>Pending generation</p></td>
         <td><p>—</p></td>
       </tr>
     </tbody>
   </table>
   ```

4. Update the parent index page with the rebuilt table:
   ```
   updateConfluencePage:
     cloudId: "[cloud_id]"
     pageId: "[docstore.confluence.parent_page_id]"
     title: "[existing title — do not change]"
     version: [current_version + 1]
     body: "[introductory paragraph] + [rebuilt table]"
     representation: "storage"
   ```

On failure: log `Note: Could not update Confluence index page. Child page was still created/updated successfully.` and continue — do not block.

---

### Step 4: Notion Sync

*Run this step if `provider` is `notion` or `both`. Run independently of Step 3 — a Confluence failure does not skip Notion.*

#### Step 4.1: Convert Markdown to Notion Blocks

Convert the markdown content to a Notion `children` block array. Apply the following rules:

**Headings**:
- `# Heading` → `{"type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": "Heading"}}]}}`
- `## Heading` → `{"type": "heading_2", ...}`
- `### Heading` → `{"type": "heading_3", ...}`
- `#### Heading` and deeper → treat as `heading_3` (Notion maximum)

**Paragraphs** (plain text between blank lines):
```json
{"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "paragraph text"}, "annotations": {}}]}}
```

Apply inline annotations within rich_text arrays:
- `**bold**` → `"annotations": {"bold": true}`
- `*italic*` → `"annotations": {"italic": true}`
- `` `code` `` → `"annotations": {"code": true}`
- Combined: `**_bold italic_**` → `"annotations": {"bold": true, "italic": true}`

**Code blocks**:
```json
{
  "type": "code",
  "code": {
    "language": "[language or 'plain text']",
    "rich_text": [{"type": "text", "text": {"content": "code content"}}]
  }
}
```

**Unordered list items**: Each `- item` → `{"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [...]}}`

Nested list items: add as `children` on the parent list item block.

**Ordered list items**: Each `1. item` → `{"type": "numbered_list_item", "numbered_list_item": {"rich_text": [...]}}`

**Blockquotes**: `> text` → `{"type": "quote", "quote": {"rich_text": [...]}}`

**Horizontal rules**: `---` → `{"type": "divider", "divider": {}}`

**Tables**: Notion table blocks via API are complex. Convert markdown tables to a readable paragraph block instead:
- Use the table heading row as bold text
- Follow with each data row as a plain paragraph with pipe-separated values
- Prefix the block with a note: `[Table: [table heading if discernible]]`

Example output for a table:
```json
[
  {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "[Table]"}, "annotations": {"bold": true}}]}},
  {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Header 1 | Header 2"}, "annotations": {"bold": true}}]}},
  {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Cell 1 | Cell 2"}}]}}
]
```

**Block limit**: Notion's API accepts a maximum of 100 blocks per request. If the converted content exceeds 100 blocks, split into multiple append calls (see Step 4.3).

Store the converted block array as `notion_blocks`.

#### Step 4.2: Check for Existing Page

Inspect `docstore.notion.artifacts.[artifact_id]` in `status.md`:
- If `page_id` is present and non-null: proceed to **Step 4.3** (update existing page)
- If `page_id` is absent or null: proceed to **Step 4.4** (create new page)

#### Step 4.3: Update Existing Notion Page

Updating a Notion page's content requires clearing existing blocks and re-appending. Use the following sequence:

1. Retrieve existing block children to get their IDs:
   ```
   notion_get_block_children:
     block_id: "[existing_page_id]"
   ```

2. Delete each existing block:
   ```
   notion_delete_block:
     block_id: "[block_id]"
   ```
   Repeat for each block returned. If there are many blocks, delete in batches of 10 to avoid rate limits.

3. Append the new content blocks (in batches of 100 if needed):
   ```
   notion_append_block_children:
     block_id: "[existing_page_id]"
     children: [first 100 notion_blocks]
   ```
   Repeat for subsequent batches of 100 blocks.

On success: record `last_synced` timestamp in `status.md` under `docstore.notion.artifacts.[artifact_id].last_synced`.

On failure: log and continue.

Proceed to **Step 4.5** to update the index page.

#### Step 4.4: Create New Notion Page

Create a new page as a child of the engagement parent page:

```
notion_create_page:
  parent:
    page_id: "[docstore.notion.parent_page_id]"
  properties:
    title:
      title:
        - text:
            content: "[artifact_name]"
  children: [first 100 notion_blocks]
```

If `notion_blocks` has more than 100 items, append the remaining blocks after creation using `notion_append_block_children` on the returned `id`.

On success: extract `id` and `url` from the response. Write to `status.md`:

```yaml
docstore:
  notion:
    artifacts:
      [artifact_id]:
        page_id: "[returned_page_id]"
        page_url: "[returned_url]"
        last_synced: "[current ISO datetime]"
```

On failure: log and continue.

Proceed to **Step 4.5** to update the index page.

#### Step 4.5: Update Notion Index Page

After every successful create or update, rebuild the "Wire Documents" index page so its artifact list reflects the current state of all synced artifacts.

**Process**:

1. Build the artifact map from two sources merged together:
   - Read `docstore.notion.artifacts` from `status.md` (previously persisted entries)
   - Overlay any `page_id`, `page_url`, and `last_synced` values produced **in the current run** (Steps 4.3/4.4) — these may not yet be written to disk, but must be included so the newly synced artifact appears as a live link rather than "Pending generation"

2. Retrieve the existing blocks of the parent index page:
   ```
   notion_get_block_children:
     block_id: "[docstore.notion.parent_page_id]"
   ```

3. Delete all existing blocks (the introductory paragraph and the artifacts section will be rebuilt in full):
   ```
   notion_delete_block:
     block_id: "[block_id]"
   ```
   Repeat for each block. Delete in batches of 10 to avoid rate limits.

4. Rebuild and append the full index content. For each in-scope artifact (only those present in `status.md`), in the standard artifact order:
   - If the artifact has a `page_url`: include as a linked mention with last_synced date
   - If not yet synced: list as plain text with "Pending generation"

   Block structure to append:
   ```json
   [
     {
       "type": "paragraph",
       "paragraph": {
         "rich_text": [{"type": "text", "text": {"content": "This page is the central index for all Wire Framework artifacts generated during this engagement. Artifacts are published automatically each time a generate command completes."}}]
       }
     },
     {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Artifacts"}}]}},
     // For each synced artifact:
     {
       "type": "bulleted_list_item",
       "bulleted_list_item": {
         "rich_text": [
           {"type": "text", "text": {"content": "[Artifact Display Name] — "}, "annotations": {"bold": true}},
           {"type": "text", "text": {"content": "Published", "link": {"url": "[page_url]"}}, "annotations": {"color": "green"}},
           {"type": "text", "text": {"content": " (last synced: [last_synced date])"}}
         ]
       }
     },
     // For each not-yet-synced artifact:
     {
       "type": "bulleted_list_item",
       "bulleted_list_item": {
         "rich_text": [
           {"type": "text", "text": {"content": "[Artifact Display Name] — "}, "annotations": {"bold": true}},
           {"type": "text", "text": {"content": "Pending generation"}, "annotations": {"color": "gray"}}
         ]
       }
     }
   ]
   ```

   Append in batches of 100 blocks if needed.

On failure: log `Note: Could not update Notion index page. Child page was still created/updated successfully.` and continue — do not block.

---

### Step 5: Update status.md

After all provider steps complete, write all changes to `status.md` in a single update:
- Page IDs and URLs for any newly created pages
- `last_synced` timestamps for any successfully updated or created pages

Do not update `status.md` for any provider that failed — leave those fields as-is so a future sync attempt can retry.

### Step 6: Output Confirmation

Output a brief, single-line confirmation per successfully synced provider:

**Created (new page)**:
```
✓ Synced [artifact_name] to Confluence (new page) — [page_url]
✓ Synced [artifact_name] to Notion (new page) — [page_url]
```

**Updated (existing page)**:
```
✓ Synced [artifact_name] to Confluence (updated) — [page_url]
✓ Synced [artifact_name] to Notion (updated) — [page_url]
```

**Both providers**:
```
✓ Synced [artifact_name] to Confluence and Notion — [confluence_url] | [notion_url]
```

If a provider was skipped (not configured) or failed silently, omit it from the output.

### Step 7: Handle Edge Cases

**Atlassian MCP not available:**
- Skip Confluence sync silently
- Do not log an error unless the user has explicitly configured Confluence as their provider
- If configured: `Note: Could not reach Atlassian MCP. Confluence sync skipped for [artifact_name].`

**Notion MCP not available:**
- Skip Notion sync silently
- If configured: `Note: Could not reach Notion MCP. Notion sync skipped for [artifact_name].`

**Page update fails with version conflict (Confluence):**
- Re-fetch the page to get the latest version number and retry once
- If the retry also fails: log `Note: Confluence version conflict for [artifact_name]. Sync skipped.` and continue

**Page not found (Confluence or Notion — page_id recorded but page deleted externally):**
- Treat as a new page: clear the stored `page_id` and `page_url` and proceed with creation (Step 3.4 or 4.4)
- Log: `Note: [Provider] page for [artifact_name] was not found (may have been deleted). Re-creating.`

**Markdown file is empty:**
- Log: `Note: [file_path] is empty. Skipping document store sync for [artifact_name].`
- Exit without updating status.md

**generate command invoked without docstore configured:**
- Exit silently at Step 1 — no output, no side effects

**Rate limiting (Notion API):**
- If a 429 response is received when appending blocks, wait 2 seconds and retry once
- If the retry also fails, log the error and mark the sync as incomplete

In all failure cases, the calling generate command is never blocked. Document store sync is additive and best-effort.

## Output

This utility:
- Converts the generated markdown artifact to Confluence storage format and/or Notion block format
- Creates a new page if none exists for this artifact, or updates the existing page
- Records `page_id`, `page_url`, and `last_synced` in `status.md` for each configured provider
- Outputs a one-line confirmation per provider on success
- Fails gracefully per provider — Confluence and Notion failures are independent
- Exits silently if no document store is configured

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
