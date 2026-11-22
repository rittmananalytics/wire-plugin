---
wire_schema: "1.0"
command: utility
artifact: custom
domain: custom
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Define a custom release type by analysing SoW or project documents — map deliverables to Wire commands or generate bespoke specs
argument-hint: <release-folder>

---

# Wire Custom Release Define

## Purpose

When an engagement has bespoke deliverables that don't map to any standard Wire release type, this command analyses the provided source documents (SoW, kick-off notes, agreed delivery plan) and proposes a tailored release structure. Deliverables that match existing Wire commands use those commands directly. Deliverables with no standard equivalent get fully-generated project-scoped custom specs with their own generate/validate/review cycle.

This command is invoked automatically by `/wire:new` when the user selects "Custom" as the release type.

## Usage

```bash
/wire:custom-define <release-folder>
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

### Keeping Status Current

Custom releases often do substantial work conversationally, outside the
generated commands — and only command runs update status.md and the
execution log automatically. Any work done outside a command run must
reconcile the record before raising a PR:

   /wire:status-sync [release_folder]
```

---

## Edge Cases

**No documents provided**: ask once more, then offer to define deliverables manually (user types them as a numbered list).

**Deliverable with no acceptance criteria and very vague description**: flag in the proposal table as "⚠️ Vague — acceptance criteria will need to be confirmed before spec is generated." Ask the user to clarify before generating that deliverable's specs.

**Duplicate deliverable names**: append a numeric suffix (`-2`, `-3`) to disambiguate.

**Custom commands directory already exists**: check for existing specs before writing. If a spec with the same name already exists, ask whether to overwrite or keep the existing one.

**Standalone invocation (not via `/wire:new`)**: check that `.wire/releases/[release_folder]/` exists. If not, ask the user to run `/wire:new` first or create the folder manually.
