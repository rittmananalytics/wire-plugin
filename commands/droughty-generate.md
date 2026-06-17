---
description: Run full Droughty phase in sequence (discovery, post-dbt, or full)
argument-hint: <release-folder> [--mode discovery
---

# Run full Droughty phase in sequence (discovery, post-dbt, or full)

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
description: Run the full Droughty phase in sequence — setup, introspect, dbml, docs, qa, stage, dbt-tests, lookml
argument-hint: <release-folder>
---

# Droughty Generate Command

Follow `specs/utils/dbt_developer_delegate.md` before executing the workflow below.

## Purpose

Orchestrate all Droughty commands in the correct sequence for the current engagement context. Skips commands that are already complete and commands that are not applicable (e.g. `lookml` when no LookML project is configured, `stage` when warehouse is Snowflake).

Two modes:

- **Discovery/audit mode** (default for `droughty` release type): runs setup → introspect → dbml → docs → qa. Used when the primary goal is mapping and assessing an existing warehouse. Does not require dbt to have been deployed.
- **Post-dbt mode**: runs setup → dbt-tests → stage → lookml → docs → qa. Used after `dbt run` within a `full_platform` or `dbt_development` release. Droughty reads the deployed schema to generate the base layer for the semantic layer phase.

## Usage

```bash
/wire:droughty-generate <release-folder>
```

Pass `--mode discovery` or `--mode post-dbt` to force a specific mode. Without the flag, the command determines mode from context.

## Prerequisites

Varies by mode — see individual command specs. Minimum: `.wire/engagement/context.md` exists and the warehouse is accessible.

## Workflow

### Step 1: Determine Mode

Read `.wire/releases/[release]/status.md`.

**If `project_type: droughty`** or `droughty.context: discovery` in status.md:
- Default to **discovery mode**

**If called within another release type** (e.g. `full_platform`, `dbt_development`):
- Ask in chat:
  ```
  What context is this Droughty run for?
  ```
  Use `AskUserQuestion`:
  ```json
  {
    "questions": [{
      "question": "What is the Droughty phase context?",
      "header": "Mode",
      "options": [
        {"label": "Discovery / audit", "description": "Map and assess an existing warehouse — no dbt deployment needed. Runs: introspect, dbml, docs, qa."},
        {"label": "Post-dbt deploy", "description": "Generate base layer from deployed dbt models. Runs: dbt-tests, stage (BigQuery), lookml, docs, qa."},
        {"label": "Full sequence", "description": "Run everything in order — setup, introspect, dbml, dbt-tests, stage, lookml, docs, qa. Requires dbt to be deployed."}
      ],
      "multiSelect": false
    }]
  }
  ```

### Step 2: Check What Is Already Complete

Read `droughty.*` blocks in `status.md`. Skip any step with `status: complete` unless `--force` is passed.

Show the planned sequence:

```
Droughty phase plan — [mode]:

  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-setup
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-introspect
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-dbml
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-docs
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-qa
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-stage
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-dbt-tests
  [✅ complete | ▷ will run | ⏭ skipping (not applicable)] droughty-lookml

Proceed? (yes/no)
```

### Step 3: Execute Sequence

Run each planned step in order by invoking the corresponding spec:

**Discovery mode sequence:**
1. `specs/droughty/setup.md` (if not complete)
2. `specs/droughty/introspect.md`
3. `specs/droughty/dbml.md`
4. `specs/droughty/docs.md` (if OpenAI key available — skip with warning if not)
5. `specs/droughty/qa.md` (if OpenAI key available — skip with warning if not)

**Post-dbt mode sequence:**
1. `specs/droughty/setup.md` (if not complete)
2. `specs/droughty/dbt_tests.md`
3. `specs/droughty/stage.md` (BigQuery only — skip with note if Snowflake)
4. `specs/droughty/lookml.md` (if LookML project configured — skip with note if not)
5. `specs/droughty/docs.md` (if OpenAI key available)
6. `specs/droughty/qa.md` (if OpenAI key available)

**Full sequence:**
1–8 in the order listed above.

If any step fails, stop and surface the error. Do not proceed to the next step — partial completion is tracked in `status.md` so the sequence can be resumed.

### Step 4: Final Summary

After all planned steps complete:

```
## Droughty Phase Complete ✅

[mode] mode — [release]

Artifacts generated:
  [✅] schema_inventory.md       — [n] tables, [n] columns
  [✅] [schema].dbml             — [n] tables, [n] relationships
  [✅] field_descriptions/       — [n] columns documented
  [✅] qa_report.md              — [n] checks, [n] issues flagged
  [✅] stg_*.sql + sources.yml   — [n] staging models
  [✅] views/generated/*.lkml    — [n] base LookML views

All artifacts: .wire/releases/[release]/artifacts/droughty/

### Next Steps

[If discovery mode]:
  /wire:problem-definition-generate [release]   — Generate problem definition from Droughty evidence
  /wire:pitch-generate [release]                — Shape the engagement as a pitch

[If post-dbt mode]:
  /wire:semantic_layer-generate [release]       — Extend Droughty base views with business logic
  /wire:semantic_layer-validate [release]
  /wire:semantic_layer-review [release]

[If within a full_platform or dbt_development release]:
  Continue with the semantic layer phase — Droughty artifacts are available to the AI context.
```

## Output

This command invokes each sub-command in sequence, with all outputs as documented in the individual command specs.

Execute the complete workflow as specified above.
