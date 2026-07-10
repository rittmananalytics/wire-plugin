---
description: Define a custom release type from SoW or project documents — map deliverables to Wire commands or generate bespoke specs
argument-hint: <release-folder>
---

# Define a custom release type from SoW or project documents — map deliverables to Wire commands or generate bespoke specs

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
description: Define a custom release type by analysing SoW or project documents — map deliverables to Wire commands or generate bespoke specs
argument-hint: <release-folder>
---

# Wire Custom Release Define

## Purpose

When an engagement has bespoke deliverables that don't map to any standard Wire release type, this command analyses the provided source documents (SoW, kick-off notes, agreed delivery plan) and proposes a tailored release structure. Deliverables that match existing Wire commands use those commands directly. Deliverables with no standard equivalent get fully-generated project-scoped custom specs with their own generate/validate/review cycle.

This command is invoked automatically by `/wire:new` when the user selects "Custom" as the release type.

## Usage

```bash
/wire:custom-release-define <release-folder>
```

The `release-folder` argument is the `.wire/releases/` subfolder that `/wire:new` has already created (e.g. `01-poc-productionisation`). If invoked standalone (not via `/wire:new`), the release folder must already exist.

---

## Workflow

### Phase 1: Document Ingestion

Ask in chat:

```
To define a custom release structure, I need to read the engagement documents.

Provide one or more of the following (file paths, Google Drive URLs, or Confluence URLs):
- Statement of Work (SoW)
- Kick-off meeting notes
- Agreed delivery plan
- Project proposal or scope document

Paste paths or URLs, or type "paste" to paste the content directly.
```

For each provided source, call `utils/doc_analyze` to extract the `DeliverableList` object. If multiple documents are provided, merge their deliverable lists (deduplicate by name similarity — a deliverable mentioned in both the SoW and the kick-off notes is one deliverable, not two; use the SoW description as authoritative and kick-off notes for additional acceptance criteria).

Store: `deliverable_list` (merged `DeliverableList`), `source_documents` (list of all sources).

---

### Phase 2: Mapping and Proposal

For each extracted deliverable, determine the proposed handling based on the `wire_artifact_match` score:

**Score ≥ 0.70 (Strong match)**: Use the standard Wire command.
- Map to the matched `artifact` (e.g. `dbt` → `/wire:dbt-generate`, `/wire:dbt-validate`, `/wire:dbt-review`)
- Record as `type: standard`

**Score 0.40–0.69 (Approximate match, no workflow mismatch)**: Propose the standard command as approximate.
- Present a workflow comparison note (see format below)
- Ask user to confirm or choose custom instead
- Record as `type: approximate` pending user confirmation

**Score 0.40–0.69 with `workflow_mismatch: true`**: Default to custom despite the mid-band score.
- Show the mismatch note from `doc_analyze`
- Recommend custom; user can override to standard if they prefer
- Record as `type: custom` (unless user overrides)

**Score < 0.40 (No match)**: Generate a custom spec.
- Record as `type: custom`

Assemble the proposed release table:

```markdown
## Proposed Release Structure — [release_folder]

| # | Deliverable | Handling | Command / Spec Name | Notes |
|---|-------------|----------|---------------------|-------|
| 1 | [name] | Standard ✅ | `/wire:[artifact]-generate` | Matched: [artifact] (score [N]) |
| 2 | [name] | Approximate ⚠️ | `/wire:[artifact]-generate` | Workflow note: [mismatch_note] |
| 3 | [name] | Custom 🔧 | `/wire:[kebab-name]-generate` | No standard match (score [N]) |
```

**Workflow comparison note format** (for approximate matches):
```
⚠️ Approximate match: "[deliverable name]" → /wire:[artifact]-generate (score 0.NN)
   Standard command workflow: [one-line description of what Wire's standard command does]
   This deliverable requires: [one-line description from SoW]
   Recommend: [Custom (workflow differs) | Standard (workflow acceptable)]
```

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Review the proposed release structure. Would you like to proceed with this, or make changes?",
    "header": "Proposal",
    "options": [
      {"label": "Accept this structure", "description": "Proceed with the proposed mapping and generate custom specs as listed"},
      {"label": "Make changes", "description": "Swap or rename individual items before generating — I'll walk through each one"}
    ],
    "multiSelect": false
  }]
}
```

**If "Make changes"**: for each deliverable marked `approximate` or `custom`, ask in sequence:
```
Deliverable: "[name]"
Proposed: [Custom spec | /wire:[artifact]-generate (approximate)]

Options:
  a) Use proposed
  b) Use standard /wire:[artifact]-generate
  c) Use a different existing command — type the command name
  d) Custom spec with a different name — type the name

Your choice (a/b/c/d):
```

Require explicit confirmation before writing anything. Do not proceed to Phase 3 until the user has approved the final structure.

---

### Phase 3: Custom Spec Generation

For each deliverable with `type: custom`, generate three fully-detailed specs:

**`[artifact-kebab-name]-generate.md`**

Structure each custom generate spec as:

```markdown
---
description: [one-line description derived from SoW]
argument-hint: <release-folder>
---

# [Deliverable Name] — Generate

## Purpose

[One paragraph from deliverable description in the DeliverableList, written as a Wire spec purpose.]

## Prerequisites

- `.wire/releases/[release_folder]/status.md` exists with this artifact registered
- Source documents: [list the source_doc values from DeliverableList]
- [Any dependencies from deliverable.dependencies]

## Inputs

[List the input files/sources the consultant will need. Derived from the SoW description and acceptance criteria.]

## Workflow

### Step 1: Review Source Materials

Read the following to understand the current state and constraints:
[Generated from the deliverable's context in the SoW — e.g. existing codebase, prior decisions, stakeholder preferences extracted from kick-off notes]

### Step 2–N: [Steps derived from acceptance criteria]

[Each acceptance criterion from the DeliverableList becomes one or more workflow steps.
For example: acceptance criterion "covers storage tier, transformation tier, semantic layer, AI/presentation layer"
→ Step 2: Document storage tier decision and rationale
→ Step 3: Document transformation approach
→ Step 4: Document semantic layer recommendation
→ Step 5: Document AI/MCP integration pattern]

### Final Step: Update Status and Log Session

Update `.wire/releases/[release_folder]/status.md`:
```yaml
[artifact-key]:
  generate: complete
  file: "[output file path]"
  generated_date: "[today]"
```

Log this session in the Session History table.
```

**`[artifact-kebab-name]-validate.md`**

```markdown
---
description: Validate [deliverable name] against SoW acceptance criteria
argument-hint: <release-folder>
---

# [Deliverable Name] — Validate

## Purpose

Run automated checks to confirm the generated [deliverable] meets all acceptance criteria defined in the SoW before it proceeds to stakeholder review.

## Workflow

### Step 1: Read the Artifact

Read the file path recorded in `status.md` under `[artifact-key].file`.

### Step 2: Check Each Acceptance Criterion

[One check per acceptance criterion from DeliverableList. Format as PASS/FAIL.]

| Criterion | Check | Result |
|-----------|-------|--------|
| [criterion 1] | [how to check it] | PASS / FAIL |
| [criterion 2] | [how to check it] | PASS / FAIL |

### Step 3: Report

If all criteria pass: update `status.md` `[artifact-key].validate: complete`.
If any fail: update `status.md` `[artifact-key].validate: fail`, list failures.

Output validation report to terminal.
```

**`[artifact-kebab-name]-review.md`**

```markdown
---
description: Present [deliverable name] for stakeholder review and approval
argument-hint: <release-folder>
---

# [Deliverable Name] — Review

## Purpose

Present the [deliverable] to stakeholders for approval. Gather structured feedback and record the verdict in status.md.

## Workflow

### Step 1: Retrieve Meeting Context

Call `utils/meeting_context` to search Fathom for any prior discussions about this deliverable.

### Step 2: Present for Review

[Stakeholders from DeliverableList — present the artifact summary and key decisions.]

### Step 3: Gather Feedback

Ask the reviewer:
1. Do you approve this deliverable as meeting the SoW requirements?
2. Are there specific sections that need changes?
3. Any blocking concerns before sign-off?

### Step 4: Record Verdict

- **Approved**: update `status.md` `[artifact-key].review: approved`
- **Changes requested**: update `status.md` `[artifact-key].review: changes_requested`, record feedback
- **Blocked**: update `status.md` `[artifact-key].review: blocked`, note blocker

Log in Session History.
```

**Spec naming**: convert the deliverable name to kebab-case for the spec filename and command name. Examples:
- "Target State Architecture Document" → `target-state-architecture-doc`
- "Decision Log" → `decision-log`
- "MCP / AI Integration Roadmap" → `mcp-ai-integration-roadmap`

---

### Phase 4: Scaffolding

Write all files in this order:

**4a. Custom command specs** (for `type: custom` deliverables):
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-generate.md`
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-validate.md`
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-review.md`

Create the directory first:
```bash
mkdir -p .wire/releases/[release_folder]/custom-commands
```

**4b. `.claude/commands/wire/` wrappers** (for each custom spec):

Write a thin wrapper to `.claude/commands/wire/[artifact-kebab-name]-generate.md`:
```markdown
---
description: [same description as the custom spec]
argument-hint: <release-folder>
---

Read the spec at `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-generate.md` and execute it for the provided release folder.
```

Write equivalent wrappers for `-validate.md` and `-review.md`.

The subdirectory `wire/` gives these commands the `wire:` namespace prefix, so they are invoked as `/wire:[artifact-kebab-name]-generate` — consistent with standard Wire commands.

Create the directory first:
```bash
mkdir -p .claude/commands/wire
```

**4c. Update `status.md`**:

Open the existing `.wire/releases/[release_folder]/status.md` and append custom artifact entries to the `artifacts:` YAML section for each deliverable:

For `type: custom` deliverables:
```yaml
[artifact-key]:
  custom: true
  source_document: "[source_doc from DeliverableList]"
  generate: not_started
  validate: not_started
  review: not_started
  file: null
  generated_date: null
  generated_files: []
  revision_history: []
```

For `type: standard` or `type: approximate` deliverables (confirmed), add the matching artifact entry from `status-template.md`.

**4d. Seed Session History from timeline milestones**:

If `deliverable_list.timeline.milestones` contains entries, append a pre-populated session history skeleton to the Session History table in `status.md`:

```markdown
## Session History — Planned Milestones

| Week / Phase | Target Date | Focus | Accomplished | Next |
|---|---|---|---|---|
| [milestone.name] | [milestone.date or TBC] | [milestone.focus] | | |
```

This gives the consultant a ready-made progress tracking structure from day one.

**4e. Patch `engagement/context.md`**:

Add or update the `custom_commands_path` field in the engagement context:
```yaml
custom_commands_path: ".wire/releases/[release_folder]/custom-commands"
```

---

### Phase 5: Activation Notice

Print to terminal:

```
## Custom Release Ready ✅

Folder: .wire/releases/[release_folder]/

### Deliverables and Commands

| Deliverable | Type | Generate | Validate | Review |
|-------------|------|----------|----------|--------|
[one row per deliverable]

### Invocation

All commands use the `/wire:` prefix — custom and standard are consistent:
[list each /wire:[artifact-kebab-name]-generate, -validate, -review]

Standard commands work as usual:
[list each /wire:[artifact]-generate etc. for standard deliverables]

### Suggested First Step

/wire:[first-custom-artifact]-generate [release_folder]
```

---

## Edge Cases

**No documents provided**: ask once more, then offer to define deliverables manually (user types them as a numbered list).

**Deliverable with no acceptance criteria and very vague description**: flag in the proposal table as "⚠️ Vague — acceptance criteria will need to be confirmed before spec is generated." Ask the user to clarify before generating that deliverable's specs.

**Duplicate deliverable names**: append a numeric suffix (`-2`, `-3`) to disambiguate.

**Custom commands directory already exists**: check for existing specs before writing. If a spec with the same name already exists, ask whether to overwrite or keep the existing one.

**Standalone invocation (not via `/wire:new`)**: check that `.wire/releases/[release_folder]/` exists. If not, ask the user to run `/wire:new` first or create the folder manually.

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
