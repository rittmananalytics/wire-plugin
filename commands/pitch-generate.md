---
description: Generate a Shape Up pitch document from the approved problem definition
argument-hint: <release-folder>
---

# Generate a Shape Up pitch document from the approved problem definition

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
description: Generate a Shape Up pitch document from the approved problem definition
---

# Pitch Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a 10-section Shape Up pitch document from the approved problem definition. The pitch is the core planning artefact of a discovery release — it frames the problem, proposes a shaped (rough but solved) solution, defines the appetite, identifies rabbit holes to avoid, and makes the case for why this is worth betting on now.

A pitch is NOT a requirements specification. It uses fat-marker sketches and rough concepts, not pixel-perfect designs. It leaves room for implementation decisions. It is meant to be good enough to bet on — not complete enough to build from.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/problem_definition.md` — must be reviewed and approved

**Helpful**:
- `engagement/context.md` — client background, engagement objectives
- `engagement/sow.md` — budget context, appetite clues

## Workflow

### Step 1: Locate the Release and Read Problem Definition

1. Resolve release folder from `$ARGUMENTS`
2. Read `planning/problem_definition.md` — verify it exists and has been through review (check status.md)
3. If problem definition is not yet approved, output:
   ```
   Problem definition must be reviewed before generating a pitch.
   Run /wire:problem-definition-review [folder] first.
   ```

### Step 2: Determine Appetite

The appetite is the most important constraint in the pitch. It defines the time budget — and therefore shapes what solution is worth building.

Ask directly in chat:
```
What is the appetite for this release?
- Small batch (1–2 weeks): tight scope, a quick win or focused improvement
- Big batch (6 weeks): significant new capability or complex problem

Which fits? (small/big)
```

Wait for user response.

If the SOW or engagement context has a timeline, suggest that as the default.

### Step 3: Facilitate Solution Shaping

The pitch must contain a shaped solution — rough but solved. Guide the user through the key shaping decisions:

**Q1:**
```
What is the core element of the solution — the one thing that, if done, solves the problem?
(Describe it in 2–3 sentences. No need for technical specifics — sketch the idea.)
```

**Q2:**
```
What is the simplest version of this that would still solve the problem?
(The "fat marker" version — what gets cut to the bone but still works?)
```

**Q3:**
```
What are the rabbit holes — the parts that look straightforward but could take forever?
(List 2–3 specific things you want to explicitly avoid or timebox.)
```

**Q4:**
```
What are the hard no-gos — things this solution will NOT do?
(Boundaries that must not move, even if stakeholders ask for them.)
```

If source material already answers some of these, pre-populate and ask for confirmation.

### Step 4: Generate the Pitch Document

**Output location**: `.wire/releases/$ARGUMENTS/planning/pitch.md`

**Document structure**:

```markdown
# Pitch: [Engagement Name / Release Name]

**Release**: [release_folder]
**Client**: [client_name]
**Date**: [generation_date]
**Appetite**: [Small batch — 1–2 weeks | Big batch — 6 weeks]
**Version**: 1.0

---

## 1. Problem

[2–3 paragraph summary of the problem from the problem definition. Written for a decision-maker who hasn't read the full problem definition. Include who has the problem, what they can't do today, and what it costs them.]

## 2. Appetite

**[Small batch — 1–2 weeks | Big batch — 6 weeks]**

[Why this appetite is appropriate. What it means for scope. What is explicitly NOT included because of the appetite constraint.]

## 3. Solution Sketch

[2–4 paragraphs describing the shaped solution. Fat-marker level — not implementation design. Describe the key user-facing behaviour or system behaviour that solves the problem. Use simple diagrams (ASCII or Mermaid) where helpful.]

**Core interaction / key behaviour**:
[One concrete example of how the solution works for the user. A scenario or story.]

## 4. Rabbit Holes

[Specific things that look simple but could expand indefinitely. Name them explicitly so the team knows to timebox or cut them.]

- **[Rabbit hole 1]**: [Why it's dangerous and what the boundary is]
- **[Rabbit hole 2]**: [Why it's dangerous and what the boundary is]

## 5. No-gos

Things this release will NOT do:

- [Hard no-go 1]
- [Hard no-go 2]
- [Hard no-go 3]

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [risk] | High/Med/Low | High/Med/Low | [mitigation] |

## 7. Success Criteria

How we will know this release has solved the problem:

- [ ] [Measurable outcome 1 — tied directly to the problem definition]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## 8. Downstream Releases

[If this discovery release will spawn delivery releases, list the likely release types and names here. These will be formalised in the release brief.]

| Likely Release | Type | Rough Scope |
|----------------|------|-------------|
| [name] | [full_platform / pipeline_only / dbt_development / etc.] | [1-line description] |

## 9. Timeline

| Milestone | Target |
|-----------|--------|
| Problem definition approved | [date] |
| Pitch approved | [date] |
| Release brief signed off | [date] |
| Sprint plan confirmed | [date] |
| First delivery release start | [date] |

## 10. The Bet

[1–2 paragraphs: why this is worth betting [appetite] on now. What is the cost of NOT doing it. What opportunity or risk it addresses. This is the closing argument for the pitch — it should make the decision feel obvious.]
```

### Step 5: Update Release Status

```yaml
pitch:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "planning/pitch.md"
  generated_date: [today's date]
```

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `pitch`
- `artifact_name`: `Shape Up Pitch`
- `file_path`: `.wire/releases/[release_folder]/artifacts/pitch.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Pitch Generated

File: .wire/releases/[folder]/planning/pitch.md
Appetite: [Small batch / Big batch]

### Next Steps

1. Validate the pitch:
   /wire:pitch-validate [folder]

2. Review with stakeholders (decision-makers who will approve the bet):
   /wire:pitch-review [folder]

3. When approved, formalise as a release brief:
   /wire:release-brief-generate [folder]
```

## Output Files

- `.wire/releases/[folder]/planning/pitch.md`
- Updated `.wire/releases/[folder]/status.md`

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
