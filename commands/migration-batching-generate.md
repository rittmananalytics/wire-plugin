---
description: Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph
argument-hint: <release-folder> [--seed <path>]
---

# Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph

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
description: Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph
argument-hint: <release-folder> [--seed path] [--target-batches N]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_batching` and `artifact_file_path: migration/migration_batching.md` before proceeding.

---

# Migration Batching — Generate

## Purpose

Partitions the approved migration inventory into named **domain batches** — independently-implementable, schedulable slices of the migration scope, each spanning every layer it touches (ingestion, warehouse objects, dbt models, orchestration, reverse ETL) — and derives the dependency ordering between batches from the real dependency graph.

This replaces the hand-drafted batch spreadsheet. It is re-runnable whenever the inventory or dbt audit changes, specifically so a domain-batch plan cannot silently drift out of sync with the real dependency graph — a hand-drawn plan on a past engagement scheduled batches in parallel that the graph, once known, showed could not build in parallel, and nothing was responsible for catching it.

**Two partition modes.** The default output is one batch per domain group (`partition_mode: domain`). But some estates cross-reference in every direction — the domains form a single strongly-connected component (SCC), and no domain grouping can be both acyclic *and* declare every cross-batch edge (the two conditions `/wire:migration-batching-validate` enforces are mutually exclusive for an SCC). When Step 4b detects that, generate falls back automatically to **build-ordered waves** (`partition_mode: build_ordered_waves`): a topological sort of the model graph, cut into N waves, each depending on the full prefix of earlier waves. That is trivially acyclic and declares every edge, so it validates — and it reproduces from the command instead of a hand-rolled script. The domain tag is kept as a column for client/milestone rollup even when it can't be the build order.

**Domain batches are not translation batches.** `dbt_audit.csv`'s `batch_number` is a translation batch — a group of ≤20 models sequenced for `/wire:dbt-migration-generate` runs. A domain batch is a business-scoped, multi-layer slice delivered as its own release or sprint. Do not conflate them.

**This command produces CANDIDATES, not decisions.** It proposes a partition and a dependency ordering. `/wire:migration-batching-review` is where a human/client adjusts and signs off on batch composition and schedule. Generate never marks a batch "approved" or "final", and never assigns a committed date or owner.

State this posture at the top of the generated artifact so no downstream reader treats the partition as a committed schedule.

## Prerequisites

- `migration/migration_inventory.md` with `review: approved`

If the inventory is not approved, stop: "Approve the migration inventory before batching — run /wire:migration-inventory-review $ARGUMENTS."

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md` — unified object catalog, dependency graph, per-object effort-hour estimates
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — per-model `batch_number`, `enabled`, `platform_macros`, layer/path (domain-grouping hints and the batch-zero dependency)
- `.wire/releases/$ARGUMENTS/status.md`
- **Optional seed**: if `status.md` carries a `sow.batch_allocation` path (or a similar hand-drafted batch plan reference), or `--seed <path>` was passed in `$ARGUMENTS`, read the referenced CSV/plan of human-assigned batch names and groupings as a **seed, not ground truth** — it is reconciled against the real graph in Step 3, never accepted or discarded silently. If no seed exists, proceed with pure graph-derived grouping.
- **Optional `--target-batches N`**: the number of waves to cut the model graph into if the build-ordered fallback fires (Step 4b/4c). Ignored in the default domain mode. If unset, defaults to the candidate domain-group count (Step 3), so wave granularity stays comparable to what the domain partition would have produced.

## Workflow

### Step 1: Load the inventory graph and per-model detail

Parse the dependency graph from `migration_inventory.md` (adjacency list; the Mermaid diagram is a rendering, the adjacency list is the source) and the unified object catalog with per-object effort estimates. Parse `dbt_audit.csv` for per-model `batch_number`, `enabled`, and `platform_macros`.

### Step 2: Load the optional seed plan

If a seed exists (Step 0 of Inputs), extract its batch names and object→batch groupings. This is a starting hint for naming and grouping preference, to be reconciled against the graph in Step 3 — not accepted as-is. Record the seed path used, or "no seed provided".

### Step 3: Determine domain groupings

Assign every inventory object to exactly one candidate domain group:

- Where the seed plan assigns an object to a named domain group, start from that assignment.
- Where no seed exists, or for objects the seed doesn't cover, group by structural signal: schema/dataset name for db objects, top-level model folder or tag for dbt models, connector→destination pairing for ingestion and reverse ETL objects.
- **Merge rule**: merge two candidate groups if the edge density between them is high enough that separating them would force most objects in one group to declare a dependency on the other — they aren't really separable. State each merge and why in the narrative's seed-reconciliation note.

### Step 4: Build the batch-level dependency DAG

For every pair of domain groups with at least one graph edge crossing between them (from the inventory graph, dependency→dependent direction), record a directed batch-dependency edge from the prerequisite batch to the dependent batch.

If edges run in **both** directions between the same two groups, they are not actually separable — merge them into one batch rather than record a cyclic edge.

**The output DAG must be acyclic. This is a hard requirement — verify it before writing anything.** If a cycle survives the merge rule, keep merging along the cycle until it is gone, and record every merge in the narrative.

### Step 4b: Detect the single-SCC condition

The merge rule in Step 4 removes cycles by collapsing bidirectionally-linked groups. When the whole estate cross-references in every direction, that collapsing runs all the way to **one group** — the domain partition degenerates to a single batch, which is no partition at all. A domain plan can never both stay acyclic and declare every cross-batch edge in that case; the two are mutually exclusive, so `/wire:migration-batching-validate` C2 and C3 can never both pass.

Test for it. Build the domain-level directed graph (a node per candidate domain group from Step 3; an edge A→B for any object edge crossing from A to B), then compute its strongly-connected components (Tarjan's or Kosaraju's):

- **More than one SCC, and the condensation is a non-trivial DAG** → the domain partition is viable. Continue in **domain mode** (Steps 5–10 as written).
- **A single SCC spanning all (or effectively all) domains** — equivalently, Step 4's merge rule collapses everything to one batch → the domain partition is not viable. Switch to **build-ordered waves** per Step 4c.

Record which mode was chosen and the evidence (SCC count, the size of the largest SCC vs the domain count) — it goes in the narrative and the status block. Never silently emit a single-batch domain partition.

### Step 4c: Build-ordered waves (fallback — only when Step 4b selects it)

Replace the domain partition with waves cut from the model-level build order:

1. **Topologically sort the full buildable model graph** (the same graph the dbt audit's batch ordering uses — every model's `ref()`/`source()` parents sort before it, 0 forward references). Break ties by domain priority (so a wave stays as domain-coherent as the build order allows), then by name.
2. **Coarsen into `--target-batches N` waves** (default: the candidate domain-group count from Step 3), preserving the topological order — wave 1 is the earliest slice of the sort, wave N the latest. Balance the waves by the inventory's per-object effort hours (Step 6) without ever reordering across the topological cut.
3. **Set each wave's `depends_on_batches` to the full prefix** `B01..B(k-1)`. This declares every possible cross-wave edge by construction, so C3 holds, and a strict prefix is trivially acyclic, so C2 holds.
4. **Keep the domain tag** on every object's CSV row (the `domain` column) so the still-meaningful domain grouping survives for client/milestone/billing rollup — it just isn't the build order.

Non-dbt inventory objects (ingestion, warehouse objects, reverse ETL) that have no place in the model graph attach to the wave of the earliest model that depends on them, or to wave 1 if nothing does; note the rule applied. In build-ordered mode there are no parallel-safe wave pairs — the full-prefix dependency makes every wave depend on all earlier ones — so Step 7 emits an empty parallel-safe set with that explanation rather than searching for one.

### Step 5: Fold in the batch-zero macro dependency

Any batch containing a model with a non-empty `platform_macros` value (from `dbt_audit.csv`) has an implicit prerequisite on the dbt-audit **batch-zero macro translation pass** (`audit/batch_zero_plan.json`) completing first. Record this explicitly per affected batch in the narrative's batch summary table and batch-zero callout — do not let it get lost among the domain-to-domain edges. This prerequisite lives in the narrative only; the CSV's `depends_on_batches` column carries domain batch ids, not the batch-zero pass.

### Step 6: Balance batch sizes

**Domain mode.** Using the inventory's per-object effort-hour estimates, aim for roughly even hours per batch — without breaking a domain grouping and without violating the Step 4 dependency order. Note any batch that is a clear size outlier and why. A shared foundational layer that many batches depend on is often small in object count but blocks everything — its position in the DAG matters more for scheduling than its own hours; say so in the narrative.

**Build-ordered mode.** Balancing already happened inside the Step 4c coarsening — cut the topological order into waves of roughly even effort hours, never reordering across the cut. Note any wave that is a size outlier and why (a dense foundational layer early in the sort often makes wave 1 heavier).

### Step 7: Identify parallel-safe batch groups

**Domain mode.** Any set of batches with **zero** dependency edges (either direction) between their members, per the Step 4 DAG, can be scheduled in parallel. Produce this list explicitly — it is the deliverable that directly answers "which of these batches can actually run at the same time", which is exactly what a hand-drawn plan gets wrong.

**Build-ordered mode.** There are none by construction — every wave depends on the full prefix of earlier waves. Emit an empty parallel-safe set and state that build-ordered waves are strictly sequential (the domain tag, not the wave, is what rolls up for parallel client-facing planning).

### Step 8: Emit the CSV

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_batching.csv`

Columns:
```
object_id,object_type,source_audit,domain,batch_id,batch_name,depends_on_batches
```

One row per migration_inventory object, classified into exactly one batch. `batch_id` is zero-padded (`B01`, `B02`, …). `depends_on_batches` is a semicolon-separated list of `batch_id`s this object's batch depends on (may be empty; identical for every row in the same batch).

The columns are the same in both modes. In **build-ordered mode**, `batch_id` is the wave id, `batch_name` is the wave label (`Wave 1`, `Wave 2`, …), `domain` still carries the object's domain tag (retained for rollup, not used as the build order), and `depends_on_batches` is the full prefix `B01;…;B(k-1)`.

### Step 9: Emit the narrative

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_batching.md`

Use the template at `TEMPLATES/migration/migration_batching.md`. Include:

- The CANDIDATES-not-decisions posture statement (from Purpose) at the top
- **The partition-mode note**: `domain` or `build_ordered_waves`, and — when the fallback fired — the Step 4b evidence (the domains form a single SCC, so no domain grouping can be acyclic *and* declare every cross-batch edge), stated plainly so no reader wonders why the output isn't domain-grouped
- The seed-reconciliation note: what was kept from the seed, what changed and why (including every Step 3/4 merge), or "no seed provided"
- Batch summary table: `batch_id`, name, domain, object count, effort hours, `depends_on_batches`, batch-zero prerequisite (yes/no). In build-ordered mode the `domain` column shows the wave's dominant domain tag(s) for rollup
- A Mermaid DAG at batch granularity — nodes are batches, edges are dependencies (in build-ordered mode, the prefix chain B01→B02→…→BN)
- The parallel-safe groupings table (empty, with the by-construction explanation, in build-ordered mode)
- The batch-zero macro dependency callout: which batches require the batch-zero pass first, and why
- A note that this artifact is not authoritative for scheduling or dates until `/wire:migration-batching-review` runs

### Step 10: Update status

```yaml
artifacts:
  migration_batching:
    generate: complete
    file: migration/migration_batching.md
    data_file: migration/migration_batching.csv
    generated_date: "{{TODAY}}"
    partition_mode: domain | build_ordered_waves
    scc_fallback: true | false          # true when Step 4b forced build-ordered waves
    batch_count: N
    objects_classified: N
    seed_used: true | false
```

`partition_mode` is what `/wire:migration-batching-validate` reads to pick the right checks. When `scc_fallback` is true, `partition_mode` is `build_ordered_waves` and `batch_count` is the wave count (from `--target-batches` or the default).

### Step 11: Output summary

Print: partition mode (and, if the SCC fallback fired, a one-line reason), batch/wave count, object count, parallel-safe groupings found (none in build-ordered mode), and next command:

```
/wire:migration-batching-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `generate` as action.

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
