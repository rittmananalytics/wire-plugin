---
description: Migrate pre-v3.4.0 flat .wire/ layout to two-tier engagement/releases structure
argument-hint: (no arguments — auto-detects the .wire/ layout)
---

# Migrate pre-v3.4.0 flat .wire/ layout to two-tier engagement/releases structure

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

## Workflow Specification

---
description: Migrate an engagement repository to the current Wire v3.4+ structure, auto-detecting the source layout
argument-hint: (no arguments — auto-detects the layout)
---

# Wire Migrate Command

## Purpose

Migrate an engagement repository to the **Wire v3.4+ two-tier layout** (`.wire/engagement/` + `.wire/releases/`), regardless of the source layout. Two migration paths are supported:

| Case | Source layout | Description |
|------|--------------|-------------|
| **Case A** | Pre-v3.4 flat `.wire/` | Old layout with project folders directly under `.wire/` |
| **Case B** | Near-wire root-level structure | Repos with `releases/`, `context/`, `artifacts/` at the repo root — no `.wire/` directory — that evolved organically alongside the Wire framework |
| **Case C** | v3.4+ layout with legacy `release_type: "discovery"` | Already on the two-tier layout but the release type is the now-renamed `discovery` — rewrite to `shape_up_discovery` and update any internal references |
| **Case D** | Custom commands in wrong namespace | Wire custom command wrappers written to `.claude/commands/` directly (pre-v3.5.7 behaviour) instead of `.claude/commands/wire/`, causing them to appear without the `/wire:` prefix |

This command is safe to re-run. For Case B, the migration runs on a **new git branch** and raises a **PR** so changes can be reviewed before merging. Case C is a small in-place edit and does not need its own branch.

---

## Layout Reference

### Case A — Pre-v3.4.0 flat `.wire/` (source)

```
.wire/
  20260202_barton_peveril_live_pastoral/
    status.md
    artifacts/
      sow.pdf
      kickoff_notes.md
    requirements/
    design/
    dev/
    test/
    deploy/
    enablement/
  20260310_acme_marketing_analytics/
    status.md
    artifacts/
      proposal.pdf
      2026-03-01-discovery-call.md
    requirements/
    ...
```

### Case B — Near-wire root-level structure (source)

```
releases/
  01-discovery/
    brief.md
    plan.md
    status.md           ← deliverable table format (D01, D02, …)
    deliverables/
      d01-business-structure-review.md
      ...
context/
  engagement.md         ← YAML frontmatter + rich engagement content
  stakeholders.md
  decisions.md
  glossary.md
  references/
    sow.pdf
    requirements-specification.md
artifacts/
  meetings/
    raw/                ← Fathom API JSON
    processed/          ← structured markdown transcripts and summaries
  notion/
  slack/
utils/
  script_*.py
.claude/
  commands/
    engagement/
    release/
    session/
  settings.json
CLAUDE.md
```

### v3.4+ target layout (both cases)

```
.wire/
  engagement/
    context.md          ← synthesised from context/engagement.md (Case B) or generated (Case A)
    stakeholders.md     ← moved from context/ (Case B)
    decisions.md        ← moved from context/ (Case B)
    glossary.md         ← moved from context/ (Case B)
    sow.pdf / sow.md    ← moved from context/references/ or artifacts/
    calls/              ← meeting transcripts and summaries
    org/                ← empty, ready for org charts
    references/         ← moved from context/references/ (Case B)
  releases/
    01-discovery/
      status.md         ← wire YAML frontmatter format
      deliverables/     ← preserved
      brief.md          ← preserved
      plan.md           ← preserved
    02-build-sprint-1/
      status.md
      ...
  research/
    sessions/           ← auto-populated by research skill

artifacts/              ← NON-meeting reference materials stay at root (Case B)
  notion/
  slack/
utils/                  ← utility scripts stay at root (Case B)
CLAUDE.md               ← updated to Wire framework conventions
```

---

## Workflow

### Step 1: Detect the current layout

Inspect the repository root:

```bash
ls -la
ls -la .wire/ 2>/dev/null || echo "no .wire"
```

Determine which case applies:

| Condition | Result |
|-----------|--------|
| `.wire/engagement/` exists, no stray project folders at `.wire/` root, and no `release_type: "shape_up_discovery"` strings | Already migrated — check for Case D then stop |
| `.wire/engagement/` exists AND any `.wire/releases/*/status.md` contains `release_type: "shape_up_discovery"` (the briefly-used identifier, reverted to `discovery` in v3.5.1) | **Case C** — release-type normalise |
| `.wire/` exists with project folders directly under it (no `engagement/` or `releases/` subdirs) | **Case A** |
| No `.wire/` directory; root contains `releases/` dir and `context/engagement.md` | **Case B** |
| Neither `.wire/` nor `releases/context/` found | Error: nothing to migrate — suggest `/wire:new` |

Run the Case D check as follows:

```bash
grep -rl 'Read the spec at .wire/releases/' .claude/commands/ 2>/dev/null \
  | grep -v '/.claude/commands/wire/'
```

If any files match, **Case D applies** — chain it in after whichever primary case runs (or run it standalone if the repo is already on the current layout). Case D is always checked last, regardless of which other cases ran.

If **Case A**: proceed to [Case A Workflow](#case-a-workflow).
If **Case B**: proceed to [Case B Workflow](#case-b-workflow).
If **Case C**: proceed to [Case C Workflow](#case-c-workflow).
After any case (or if the layout is already current): check and run **Case D** if the grep above returns results.

Case A and Case B may **also** require Case C steps if the migrated releases use the briefly-used `shape_up_discovery` identifier — after completing the primary case, re-check for `release_type: "shape_up_discovery"` and chain into Case C if found.

---

## Case A Workflow

*(Pre-v3.4.0 flat `.wire/` layout → v3.4+ two-tier layout)*

### A1: Identify old project folders

Scan `.wire/` for directories that:
- Are NOT named `engagement`, `releases`, or `research`
- Contain a `status.md` file

Display the proposed migration to the user and ask for confirmation before proceeding.

```
Found N project folder(s) in the old layout:
  .wire/20260202_barton_peveril_live_pastoral/
  .wire/20260310_acme_marketing_analytics/

These will be migrated to:
  .wire/releases/01-barton-peveril-live-pastoral/
  .wire/releases/02-acme-marketing-analytics/

Engagement-level files found:
  sow.pdf → .wire/engagement/sow.pdf
  kickoff_notes.md → .wire/engagement/calls/migrated-kickoff_notes.md

Continue? (yes/no)
```

### A2: Determine release folder names

For each old project folder:
1. Strip the date prefix (`20260202_`) if present
2. Replace underscores with hyphens
3. Assign sequential numbering (`01-`, `02-`, …) oldest first
4. Allow user to override names before proceeding

### A3: Find engagement-level files

Scan each project folder's `artifacts/` directory for:

- **SOW/proposal**: filenames matching `sow`, `statement-of-work`, `proposal`, `contract`, `scope`
- **Meeting notes**: filenames or content matching `call`, `transcript`, `meeting`, `notes`, `kickoff`, `review`, `standup`, `sync`

### A4: Create new directory structure

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
mkdir -p .wire/releases
mkdir -p .wire/research/sessions
```

### A5: Move project folders to `.wire/releases/`

```bash
mv .wire/<old-folder>/ .wire/releases/<new-release-name>/
```

If a target name already exists under `.wire/releases/`, append `-2` and warn.

### A6: Move engagement-level files

- SOW files → `.wire/engagement/`
- Meeting notes → `.wire/engagement/calls/`
  - If filename lacks `YYYY-MM-DD-` prefix, prepend `migrated-`

### A7: Generate `.wire/engagement/context.md`

Synthesise from available metadata in the releases' `status.md` YAML frontmatter:

```markdown
---
engagement_name: "<derived from project folder names>"
client_name: "<extracted from status.md YAML or folder name>"
repo_mode: combined
client_repo: null
created_date: "<oldest release creation date>"
migrated_from_version: "pre-v3.4.0"
---

# Engagement: <Client Name>

> **Migrated** from pre-v3.4.0 flat layout on <today's date> by `/wire:migrate`.
> Review and update the fields below.

## Objectives
[Add engagement objectives here]

## Key Stakeholders
| Name | Role | Organisation | Contact |
|------|------|-------------|---------|

## Current-State Architecture
[Add description here]

## Working Agreements
- Branch naming: `feature/<release-name>`
- Review process: [add details]

## Releases in This Engagement
| Release Folder | Release Type | Status |
|----------------|-------------|--------|
```

For each release, add a row using the `release_type` from its `status.md` YAML.

### A8: Update release status files

For each migrated release, add a `session_history` entry if it does not exist:

```markdown
## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
| <today> | Migrated from pre-v3.4.0 layout | Release moved to .wire/releases/<folder>/ | Resume from last completed artifact |
```

Also update the `project_id` field in the frontmatter if it changed.

### A9: Print migration report

```
╔══════════════════════════════════════════════════════════╗
║  WIRE MIGRATION COMPLETE (Case A)                         ║
╚══════════════════════════════════════════════════════════╝

Releases migrated:
  .wire/20260202_barton_peveril_live_pastoral/
    → .wire/releases/01-barton-peveril-live-pastoral/

  .wire/20260310_acme_marketing_analytics/
    → .wire/releases/02-acme-marketing-analytics/

Engagement files:
  .wire/.../artifacts/sow.pdf → .wire/engagement/sow.pdf
  .wire/.../artifacts/kickoff_notes.md → .wire/engagement/calls/migrated-kickoff_notes.md

Created:
  .wire/engagement/context.md        ← review and fill in details
  .wire/engagement/calls/
  .wire/engagement/org/
  .wire/research/sessions/

Next steps:
  1. Review .wire/engagement/context.md
  2. Run /wire:session-start <release-folder> to resume work
```

---

## Case B Workflow

*(Near-wire root-level structure → v3.4+ `.wire/` layout)*

This workflow creates a **new git branch**, performs the migration, commits and pushes, then **opens a PR** so the team can review before merging.

### B1: Pre-flight checks

**Check for uncommitted changes:**

```bash
git status --short
```

If uncommitted changes exist, warn:
```
Warning: uncommitted changes detected. The migration moves files — git will track these as renames.
Recommend committing or stashing current changes first.
Proceed anyway? (yes/no)
```

**Identify available content:**

Read the following files to understand what exists:
- `context/engagement.md` — engagement metadata (YAML frontmatter + content)
- `context/stakeholders.md` — stakeholder list
- `context/decisions.md` — decisions log
- `context/glossary.md` — domain glossary (if present)
- `context/references/` — SOW PDFs, requirements specs, etc.
- `releases/*/status.md` — one per release (deliverable table format)
- `artifacts/meetings/processed/` — meeting transcripts and summaries
- `CLAUDE.md` — existing repo instructions

Display a preview of what will happen and ask for confirmation:

```
Detected: near-wire root-level layout

What will be moved into .wire/:
  context/engagement.md     → .wire/engagement/context.md (reformatted)
  context/stakeholders.md   → .wire/engagement/stakeholders.md
  context/decisions.md      → .wire/engagement/decisions.md
  context/glossary.md       → .wire/engagement/glossary.md
  context/references/       → .wire/engagement/references/
  releases/01-discovery/    → .wire/releases/01-discovery/ (status.md reformatted)
  artifacts/meetings/processed/  → .wire/engagement/calls/

Left at root (not moved):
  artifacts/notion/         ← reference materials, not engagement files
  artifacts/slack/          ← reference materials, not engagement files
  utils/                    ← utility scripts
  .claude/commands/         ← preserved (see CLAUDE.md for wire command notes)

New branch: wire/migrate-<YYYYMMDD>
PR will be opened after migration.

Continue? (yes/no)
```

Wait for user confirmation.

### B2: Create the migration branch

```bash
git checkout -b wire/migrate-<YYYYMMDD>
```

Use today's date in `YYYYMMDD` format (e.g. `wire/migrate-20260327`).

### B3: Create the `.wire/` directory structure

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
mkdir -p .wire/engagement/references
mkdir -p .wire/releases
mkdir -p .wire/research/sessions
```

### B4: Generate `.wire/engagement/context.md`

Read `context/engagement.md` in full. It contains a YAML frontmatter block and rich markdown content (overview, timeline, team, tooling, commercial notes, etc.).

Create `.wire/engagement/context.md` by:

1. **Translating the YAML frontmatter** to the wire engagement context schema:

```yaml
---
engagement_name: "<client_name from context/engagement.md> Data & Analytics"
client_name: "<client field from context/engagement.md>"
created_date: "<start_date from context/engagement.md>"
engagement_lead: "<first RA team member listed as Principal or lead>"
repo_mode: "dedicated_delivery"
migrated_from: "near-wire root-level layout"
migrated_on: "<today's date>"

client_repo:
  github_url: null
  local_path: null
  default_branch: "main"
---
```

2. **Preserving all rich content** from `context/engagement.md` verbatim below the frontmatter — overview, timeline, team table, tooling table, Jira links, commercial notes, etc. This is valuable engagement context; do not discard it.

3. **Appending an Engagement Releases table** at the end, populated from the existing `releases/` directory:

```markdown
## Engagement Releases

| # | Release Name | Type | Status | Start | End |
|---|-------------|------|--------|-------|-----|
```

For each release folder under `releases/`, add a row. Read each release's `status.md` frontmatter to populate Type and Status. Use `created` from the release status frontmatter for Start.

### B5: Move engagement-level context files

```bash
git mv context/stakeholders.md .wire/engagement/stakeholders.md
git mv context/decisions.md .wire/engagement/decisions.md
```

If `context/glossary.md` exists:
```bash
git mv context/glossary.md .wire/engagement/glossary.md
```

Move the entire `context/references/` directory:
```bash
git mv context/references/ .wire/engagement/references/
```

Within `references/`, identify the primary SOW/contract file (matches `sow`, `msa`, `statement-of-work`, `contract` — case insensitive). Also create a top-level symlink or note in context.md pointing to it:

In `.wire/engagement/context.md`, add or update:
```markdown
## SOW Reference

Primary contract: `.wire/engagement/references/<sow-filename>`
```

After all files from `context/` are moved, remove the now-empty `context/` directory:
```bash
rmdir context
```

### B6: Move releases to `.wire/releases/`

For each directory found under `releases/`:

```bash
git mv releases/<release-folder>/ .wire/releases/<release-folder>/
```

Preserve the folder name exactly (e.g. `01-discovery` stays `01-discovery`).

After all releases are moved:
```bash
rmdir releases
```

### B7: Reformat release status files to wire YAML frontmatter

For each release, read the existing `status.md` at `.wire/releases/<folder>/status.md`. The old format has a simple YAML frontmatter block and a deliverable table. Replace it with the full wire-format status file:

**Determine the release type**: read the release name and the deliverable table. If the release is named `discovery` or its deliverables match discovery-phase work (business structure review, stakeholder interviews, solution definition), classify as a discovery release. Otherwise classify as `delivery`.

For a discovery release, pick the discovery **flavour**:

- If deliverables include a Shape Up sequence (problem definition → pitch → release brief → sprint plan) and there is no Findings Playback deck artefact, classify as `shape_up_discovery`.
- If deliverables include stakeholder interview write-ups, a Requirements Matrix, the three analyses, or a Findings Playback slide deck, classify as `sop_discovery`.
- If neither pattern is obvious, default to `shape_up_discovery` (the historical default that this migration replaces) and note in `migrated_from` that the flavour was inferred.

**For `shape_up_discovery` releases**, generate a status.md using the shape-up discovery template schema, mapping existing deliverable statuses:

```yaml
---
release_id: "<release-folder-name>"
release_name: "<human-readable from brief.md title or folder name>"
release_type: "shape_up_discovery"
client_name: "<client_name from .wire/engagement/context.md>"
engagement_name: "<engagement_name from .wire/engagement/context.md>"
created_date: "<created from old frontmatter>"
last_updated: "<today's date>"
current_phase: "discovery"
spawned_from: null
migrated_from: "near-wire root-level layout"

jira:
  project_key: null
  epic_key: null
  artifacts:
    problem_definition:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    pitch:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    release_brief:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    sprint_plan:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

artifacts:
  problem_definition:
    generate: <see mapping table below>
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  pitch:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  release_brief:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  sprint_plan:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

notes:
  - "Migrated from near-wire root-level layout on <today's date>"
  - "Original deliverable table preserved below"

blockers: []
---
```

**For `sop_discovery` releases**, the schema is materially different (interviews array, sponsor_validation block). Generate the status.md from `TEMPLATES/sop-discovery-status-template.md` instead of inlining the schema here. Map each existing deliverable to one of the SOP artifact names (engagement_brief, stakeholder_map, stakeholder_interview, requirements_matrix, discovery_analyses, findings_playback, delivery_roadmap) using best-effort keyword matching:

| Old deliverable (by keyword) | Mapped SOP artifact |
|---|---|
| Engagement brief, project brief, scoping doc | `engagement_brief` |
| Stakeholder map, interview list | `stakeholder_map` |
| Stakeholder interview, discovery interview, write-up | `stakeholder_interview` (aggregate state; per-stakeholder files go in `planning/interviews/`) |
| Requirements matrix, consolidated requirements | `requirements_matrix` |
| Hierarchy of Needs, PPT analysis, Maturity Curve, three analyses | `discovery_analyses` |
| Findings playback, playback deck, discovery readout | `findings_playback` |
| Delivery roadmap, programme plan, Build/Pair/Coach | `delivery_roadmap` |

If migrating per-stakeholder interview files, write each to `.wire/releases/<folder>/planning/interviews/<slug>.md` and append a corresponding entry to `interviews:` in the new status.md. **Tag completeness on legacy interviews must be checked manually** — the v3.4+ four-tag rule was not enforced before, so `validate: not_started` is the safe default until the consultant re-tags.

**Deliverable status → wire artifact state mapping**:

| Old deliverable status | wire generate state | wire validate state | wire review state |
|------------------------|--------------------|--------------------|------------------|
| `--` (not started) | `not_started` | `not_started` | `not_started` |
| `draft` | `complete` | `not_started` | `not_started` |
| `review` | `complete` | `complete` | `in_progress` |
| `approved` | `complete` | `complete` | `complete` |
| `n/a` or `out of scope` | `not_started` | `not_started` | `not_started` |

**Discovery deliverable → wire artifact mapping** (best-effort; used to infer artifact states):

| Old deliverable (by keyword) | Mapped wire artifact |
|-----------------------------|---------------------|
| Business structure review, org structure, stakeholder analysis | `problem_definition` |
| Pitch, proposal, business case | `pitch` |
| Solution definition, discovery document, final discovery report | `release_brief` |
| Delivery roadmap, sprint plan, release plan | `sprint_plan` |

For deliverables that don't clearly map to a wire artifact, record them as notes in the `notes:` array.

**For delivery releases**, use the standard wire status template schema with all artifact fields (`requirements`, `conceptual_model`, `data_model`, etc.), inferring states from any existing status table using the same mapping.

**After the YAML frontmatter**, include the full human-readable status content:

```markdown
# Release Status: <Release Name>

**Client**: <client_name>
**Release ID**: <release_id>
**Type**: Discovery
**Created**: <created_date>
**Last Updated**: <today>

## Artifact Status

| Artifact | Generate | Validate | Review | Ready |
|----------|----------|----------|--------|-------|
| problem_definition | <emoji> | <emoji> | <emoji> | <emoji> |
| pitch | <emoji> | <emoji> | <emoji> | <emoji> |
| release_brief | <emoji> | <emoji> | <emoji> | <emoji> |
| sprint_plan | <emoji> | <emoji> | <emoji> | <emoji> |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Not Started | ⚠️ Blocked

## Migrated Deliverables

> The following deliverable table was carried over from the pre-migration status.md.
> It reflects actual work completed during discovery and is the authoritative record of deliverable status.
> Wire artifact states above are inferred from it.

<paste the original deliverable table verbatim here>

## Session History

<migrate all rows from the old session history table verbatim>
| <today> | Migrated to Wire v3.4+ structure | Repository restructured by /wire:migrate | Resume with /wire:session-start |

## Blockers

<migrate any rows from the old blockers table>
```

### B8: Move meeting transcripts to `.wire/engagement/calls/`

```bash
git mv artifacts/meetings/processed/* .wire/engagement/calls/
git mv artifacts/meetings/raw/ .wire/engagement/calls/raw/
rmdir artifacts/meetings/processed
rmdir artifacts/meetings
```

Files in `calls/` should use the `YYYY-MM-DD__topic__id__type.md` naming convention already used. No renaming needed if existing files already follow this convention.

If `artifacts/` becomes empty after removing `meetings/`, do not remove it — non-meeting artifact directories (`notion/`, `slack/`, etc.) remain there as reference material.

### B9: Update `CLAUDE.md`

Replace the existing `CLAUDE.md` with a new one that reflects the wire v3.4+ structure. Preserve important engagement-specific content (tooling, conventions, current state summary) but update the structural descriptions and command table.

The new `CLAUDE.md` should follow this structure:

```markdown
# <Client Name> Delivery — Claude Instructions

This is the delivery repository for the <Client Name> engagement. It is a **planning-only** repo — no code lives here.

> **Migrated to Wire v3.4+** on <today's date>. Engagement files now live under `.wire/`.
> Previous custom commands (`.claude/commands/`) are preserved but superseded by wire plugin commands.

## Repository Structure

\`\`\`
.wire/
  engagement/          Engagement-level context (persists across releases)
    context.md         Client, team, dates, commercial terms, tooling
    stakeholders.md    People, roles, relationships, preferences
    decisions.md       Append-only log of key decisions
    glossary.md        Domain terminology
    calls/             Meeting transcripts and summaries (from Fathom)
    references/        Source documents (SOW, contracts, org charts)
  releases/            Time-boxed work cycles
    NN-name/
      status.md        Wire YAML frontmatter + deliverable tracking
      deliverables/    Actual work products
      brief.md         Release brief (problem, appetite, solution)
      plan.md          Execution plan
  research/
    sessions/          Research session persistence (auto-managed)

artifacts/             Shared reference materials (not engagement management files)
  notion/              Notion exports
  slack/               Slack exports

utils/                 Utility scripts (Fathom fetch, process, etc.)
\`\`\`

---

## Case C Workflow

Engagements using the **briefly-used `release_type: "shape_up_discovery"`** identifier (from the Wire v3.5.0 window before the rename was reverted in v3.5.1) need to be normalised back to `discovery`. The `discovery` identifier is canonical for the Shape Up flow — the rename to `shape_up_discovery` was reversed for backwards compatibility.

Case C is an **in-place edit** — it does not move any files or restructure the repo. It is also idempotent: re-running on an already-normalised repo is a no-op.

### C1: Identify affected releases

```bash
grep -l 'release_type: "shape_up_discovery"' .wire/releases/*/status.md 2>/dev/null
```

For each matching file, report the path before editing.

### C2: Rewrite `release_type`

For each affected `status.md`:

1. Replace `release_type: "shape_up_discovery"` with `release_type: "discovery"`.
2. Append a one-line note to `notes:` recording the migration:

   ```yaml
   notes:
     - "Normalised release_type shape_up_discovery → discovery on <today's date> by /wire:migrate Case C"
   ```

### C3: Update other in-repo references

Search for any other files that reference the literal release type:

```bash
grep -rln 'release_type: "shape_up_discovery"' .wire/ 2>/dev/null
grep -rln 'release_type: shape_up_discovery$' .wire/ 2>/dev/null
```

Update any matches to `discovery`. Likely candidates: legacy session-history snapshots, exported status copies.

**Do not** mass-rename the word `discovery` — it is a valid phase name, folder name, and search keyword. Only the **release type identifier value** changes.

### C4: Validate

After rewriting, run `/wire:status` to confirm each affected release is recognised under `discovery` and that artifact lifecycle states are unchanged.

### C5: Report

```
## Case C migration complete

| Release | Before | After |
|---|---|---|
| 01-discovery | release_type: "shape_up_discovery" | release_type: "discovery" |

Files updated: <N>
No file moves, no schema changes.
```

---

## Commands

### Wire Plugin Commands (primary)

| Command | Purpose |
|---------|---------|
| `/wire:status` | Show status across all releases with Jira sync |
| `/wire:session-start` | Begin a work session |
| `/wire:session-end` | End session, update tracking |
| `/wire:requirements-generate` | Generate requirements artifact |
| `/wire:<artifact>-generate` | Generate any wire artifact |
| `/wire:<artifact>-validate` | Validate an artifact |
| `/wire:<artifact>-review` | Stakeholder review flow |

### Legacy Commands (preserved, may overlap)

The `.claude/commands/` directory contains previous engagement/release/session commands.
These still work but use the old root-level `releases/` and `context/` paths which no longer exist.
**Prefer wire plugin commands** for new work. The legacy commands are kept for reference.

## Conventions

### Deliverable Lifecycle

\`\`\`
not_started → in_progress → complete
\`\`\`

Wire tracks generate / validate / review states per artifact. The status.md YAML frontmatter is the source of truth.

### Wire Integration

Wire commands output to `.wire/releases/<release>/` as their working directory.
Deliverables live in `.wire/releases/<release>/deliverables/`.

### Branching

Use feature branches for deliverable work: `feat/d<NN>-<kebab-name>/0.0.1`

## Current State

### Active Releases

<list releases from .wire/releases/ with current status>

### Key Context

- Read `.wire/engagement/context.md` for timeline, team, commercial terms
- Read `.wire/engagement/stakeholders.md` for who's who at <client>
- Read `.wire/engagement/decisions.md` for accumulated decisions
- Read `.wire/engagement/glossary.md` for domain terminology
```

Populate the **Current State** section from the releases' status.md frontmatter.

### B10: Commit the migration

Stage all changes:

```bash
git add .wire/
git add CLAUDE.md
git add -u  # stage all renames/deletions (moved context/, releases/, artifacts/meetings/)
```

Commit:

```bash
git commit -m "feat: migrate to Wire v3.4+ .wire/ structure

- Move context/ → .wire/engagement/ (preserving all files)
- Move releases/ → .wire/releases/ (preserving all deliverables)
- Move artifacts/meetings/ → .wire/engagement/calls/
- Reformat status.md files to wire YAML frontmatter
- Generate .wire/engagement/context.md from context/engagement.md
- Update CLAUDE.md to wire v3.4+ conventions
- Preserve artifacts/notion/, artifacts/slack/, utils/ at root

Migrated by /wire:migrate on <today's date>"
```

### B11: Push the branch and create a PR

```bash
git push -u origin wire/migrate-<YYYYMMDD>
```

Create a PR using `gh pr create`:

```bash
gh pr create \
  --title "feat: migrate to Wire v3.4+ structure" \
  --body "$(cat <<'EOF'
## Summary

This PR migrates the delivery repository from the near-wire root-level layout to the standard Wire v3.4+ `.wire/` structure, enabling full compatibility with wire plugin commands.

## What Changed

### Files Moved

| From | To |
|------|----|
| `context/engagement.md` | `.wire/engagement/context.md` (reformatted) |
| `context/stakeholders.md` | `.wire/engagement/stakeholders.md` |
| `context/decisions.md` | `.wire/engagement/decisions.md` |
| `context/glossary.md` | `.wire/engagement/glossary.md` |
| `context/references/` | `.wire/engagement/references/` |
| `releases/01-discovery/` | `.wire/releases/01-discovery/` |
| `artifacts/meetings/processed/` | `.wire/engagement/calls/` |
| `artifacts/meetings/raw/` | `.wire/engagement/calls/raw/` |

### Files Modified

- `releases/01-discovery/status.md` → reformatted to wire YAML frontmatter; original deliverable table preserved in body
- `CLAUDE.md` → updated to wire v3.4+ structure; legacy commands noted

### Files Created

- `.wire/research/sessions/` (empty directory, ready for research skill)

### Not Changed

- `artifacts/notion/` — reference materials, stays at root
- `artifacts/slack/` — reference materials, stays at root
- `utils/` — utility scripts, stays at root
- `.claude/commands/` — preserved for reference (wire plugin commands are now primary)

## Why

Wire plugin commands read engagement and release state from `.wire/`. Moving files into this structure makes all wire plugin commands immediately usable without manual path adjustments.

## Review Checklist

- [ ] `.wire/engagement/context.md` — review and fill in any fields left as placeholders
- [ ] `.wire/releases/01-discovery/status.md` — verify artifact state mapping is correct
- [ ] `CLAUDE.md` — confirm the current state section is accurate
- [ ] Run `/wire:status` to confirm Wire reads the engagement correctly

🤖 Migrated by `/wire:migrate`
EOF
)"
```

After the PR is created, print the PR URL and the next steps.

### B12: Print migration report

```
╔══════════════════════════════════════════════════════════╗
║  WIRE MIGRATION COMPLETE (Case B)                         ║
╚══════════════════════════════════════════════════════════╝

Branch created: wire/migrate-<YYYYMMDD>
PR: <PR URL>

Moved into .wire/:
  context/               → .wire/engagement/
  releases/01-discovery/ → .wire/releases/01-discovery/
  artifacts/meetings/    → .wire/engagement/calls/

Status files reformatted:
  .wire/releases/01-discovery/status.md   ← wire YAML frontmatter added
                                             original deliverable table preserved

CLAUDE.md updated to Wire v3.4+ conventions.

Left at root (unchanged):
  artifacts/notion/, artifacts/slack/    ← reference materials
  utils/                                 ← utility scripts
  .claude/commands/                      ← legacy commands preserved

Next steps:
  1. Review the PR: <PR URL>
  2. Open .wire/engagement/context.md and fill in any placeholder fields
  3. Verify .wire/releases/01-discovery/status.md artifact states are correct
  4. Merge the PR when satisfied
  5. After merging, run /wire:status to confirm Wire reads the engagement
```

---

## Case D Workflow

*(Custom command wrappers in wrong namespace → `.claude/commands/wire/`)*

Custom commands generated by `/wire:custom-define` before v3.5.7 were written to `.claude/commands/[name].md` directly, which makes them available as `/[name]-generate` rather than `/wire:[name]-generate`. This case moves them into the `wire/` subdirectory so they pick up the correct namespace prefix.

Case D is an **in-place edit** — no new branch or PR needed. The file moves are tracked by git as renames.

### D1: Find misplaced custom command wrappers

```bash
grep -rl 'Read the spec at .wire/releases/' .claude/commands/ 2>/dev/null \
  | grep -v '/.claude/commands/wire/'
```

This matches any wrapper file that delegates to a `.wire/releases/*/custom-commands/` spec but is not already inside `.claude/commands/wire/`.

If no files match, print:
```
No misplaced custom command wrappers found — already on the current layout.
```
and stop.

### D2: Display what will move and confirm

List each file with its current and target path:

```
Found N custom command wrapper(s) in the wrong location:

  .claude/commands/target-state-architecture-doc-generate.md
    → .claude/commands/wire/target-state-architecture-doc-generate.md
  .claude/commands/target-state-architecture-doc-validate.md
    → .claude/commands/wire/target-state-architecture-doc-validate.md
  .claude/commands/target-state-architecture-doc-review.md
    → .claude/commands/wire/target-state-architecture-doc-review.md
  [... etc]

After this move, these commands will be invoked as:
  /wire:target-state-architecture-doc-generate
  /wire:target-state-architecture-doc-validate
  /wire:target-state-architecture-doc-review

They previously had no prefix (e.g. /target-state-architecture-doc-generate).

Move them now? (yes/no)
```

Wait for confirmation. If no, stop and note that commands will continue to work without the prefix until manually moved.

### D3: Create the target directory if needed

```bash
mkdir -p .claude/commands/wire
```

### D4: Move each file

For each misplaced wrapper:

```bash
git mv .claude/commands/[name].md .claude/commands/wire/[name].md
```

Use `git mv` so the rename is tracked. If git is not initialised in this repo (unusual), fall back to `mv`.

### D5: Commit

```bash
git add .claude/commands/
git commit -m "fix: move custom Wire command wrappers to .claude/commands/wire/

Wrappers written by /wire:custom-define before v3.5.7 were placed in
.claude/commands/ directly, giving them no namespace prefix. Moving them
to .claude/commands/wire/ restores the /wire: prefix.

Migrated by /wire:migrate Case D on <today's date>"
```

### D6: Report

```
╔══════════════════════════════════════════════════════════════╗
║  WIRE MIGRATION COMPLETE (Case D)                             ║
╚══════════════════════════════════════════════════════════════╝

Moved N wrapper file(s) to .claude/commands/wire/:

  [list each file moved]

These commands are now available as:
  /wire:[name]-generate
  /wire:[name]-validate
  /wire:[name]-review

If you had bookmarked or shared the old command names (without /wire:),
update any references — the old names are no longer available.
```

---

## Edge Cases

### Both cases

**Already fully migrated** (`.wire/engagement/` and `.wire/releases/` both exist, no stray folders):
```
Already on Wire v3.4+ layout — nothing to migrate.
Run /wire:status to see current engagement state.
```

**`.wire/` exists but is empty or has unknown structure**:
- Ask the user to describe what they expect and suggest `/wire:new` if starting fresh.

### Case A specific

**`.wire/` has no project folders** (nothing to migrate):
```
No Wire project folders found in .wire/ — nothing to migrate.
Run /wire:new to start a new engagement.
```

**Partial migration** (`.wire/engagement/` exists but some old-layout folders remain at `.wire/` root):
- Skip creating `engagement/` directories
- Only move folders still at `.wire/` root level
- Report what was already migrated vs newly migrated

**Project folder has no `artifacts/`**: proceed with folder move only; note in report.

**Multiple projects share the same SOW filename**: move the first to `engagement/sow.md`, log a warning.

### Case B specific

**`context/` exists but `releases/` is empty or absent**:
- Still migrate `context/` to `.wire/engagement/`
- Create `.wire/releases/` (empty, ready for `/wire:start`)
- Note in migration report that no releases were found

**Release has no `brief.md` or `plan.md`** (only `status.md` and `deliverables/`):
- Proceed; note in PR description that brief/plan are absent

**Multiple releases** (e.g. `01-discovery/` and `02-build-sprint-1/`):
- Migrate all releases to `.wire/releases/`
- Reformat all `status.md` files
- Include all releases in the PR body's change table

**`artifacts/meetings/` does not exist** (meetings stored elsewhere):
- Skip that move step; note in report

**No `.claude/commands/`** (custom commands were never created):
- Skip the legacy commands section in CLAUDE.md
- Proceed normally

### Case D specific

**`.claude/commands/` does not exist**: no custom commands were ever created — skip silently.

**Some wrappers already in `wire/`, some not**: only move the ones outside `wire/`. Report both sets in the summary (already correct vs moved).

**A file with the same name already exists in `.claude/commands/wire/`**: do not overwrite. Warn the user, show both file contents side by side, and ask which to keep. Default is to keep the existing one in `wire/` and leave the stale root-level file in place for manual review.

**Non-Wire project commands also in `.claude/commands/`**: the grep for `Read the spec at .wire/releases/` is specific enough to avoid matching project commands that happen to live in `.claude/commands/`. Do not move files that don't match the grep — they are not Wire custom command wrappers.

**Git remote not configured** (no `origin`):
```
Warning: no git remote found. Cannot push branch or create PR.
Migration completed locally on branch wire/migrate-<date>.
Push manually when ready: git push -u origin wire/migrate-<date>
```

**`gh` CLI not installed or not authenticated**:
```
Warning: gh CLI not available. Cannot create PR automatically.
Branch pushed to origin. Create the PR manually at: <remote URL>/compare/wire/migrate-<date>
```

---

## Output Files Created or Modified

### Case A

- `.wire/engagement/context.md` — created
- `.wire/engagement/calls/` — created
- `.wire/engagement/org/` — created
- `.wire/releases/<new-name>/` — moved from old location
- `.wire/releases/<new-name>/status.md` — session_history section added
- `.wire/research/sessions/` — created
- SOW files → `.wire/engagement/`
- Meeting notes → `.wire/engagement/calls/`

### Case B

- `.wire/engagement/context.md` — created (from `context/engagement.md`)
- `.wire/engagement/stakeholders.md` — moved from `context/`
- `.wire/engagement/decisions.md` — moved from `context/`
- `.wire/engagement/glossary.md` — moved from `context/` (if present)
- `.wire/engagement/references/` — moved from `context/references/`
- `.wire/engagement/calls/` — moved from `artifacts/meetings/processed/`
- `.wire/engagement/calls/raw/` — moved from `artifacts/meetings/raw/`
- `.wire/engagement/org/` — created (empty)
- `.wire/releases/<folder>/` — moved from root `releases/<folder>/`
- `.wire/releases/<folder>/status.md` — reformatted to wire YAML frontmatter
- `.wire/research/sessions/` — created (empty)
- `CLAUDE.md` — updated to wire v3.4+ conventions
- `context/` — removed (emptied by moves)
- `releases/` — removed (emptied by moves)
- `artifacts/meetings/` — removed (emptied by moves); `artifacts/` stays if non-meeting dirs remain

### Case D

- `.claude/commands/wire/` — created (if not already present)
- `.claude/commands/[name]-generate.md` → `.claude/commands/wire/[name]-generate.md` — moved (one per custom artifact)
- `.claude/commands/[name]-validate.md` → `.claude/commands/wire/[name]-validate.md` — moved
- `.claude/commands/[name]-review.md` → `.claude/commands/wire/[name]-review.md` — moved

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
