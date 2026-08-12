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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph
argument-hint: <release-folder> [--seed path] [--target-batches N]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Before the generic stale-artifact prompt, run the **Reviewed-Artifact Guard** below — a reviewed/adjudicated batching plan needs a stronger warning than "re-generate? yes/no".
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

## Reviewed-Artifact Guard

`/wire:migration-batching-review` rewrites `migration_batching.csv` rows in place — renames, merges, object moves, a human correcting a misclassification the graph got wrong — with nothing on disk to mark the file as adjudicated rather than generated. Left unguarded, re-running this command silently overwrites that human work with a fresh candidate partition, which can reintroduce exactly the defect a reviewer just fixed by hand (an orphan connector routed correctly to `NO-DEP` at review, for instance, landing back in wave 1 on the next run).

Read `artifacts.migration_batching.reviewed_checksum` from `status.md` before doing anything else:

- **Not set** — no review has run against this artifact yet (or this engagement predates the guard). Proceed straight to the generic `specs/utils/stale_artifact_check.md` prompt as today; this guard adds nothing here.
- **Set** — a review has recorded a checksum of the CSV at adjudication time. Compute the current on-disk `migration_batching.csv`'s checksum (e.g. `shasum -a 256 migration/migration_batching.csv`) and compare:
  - **Matches** — the reviewed CSV is sitting untouched since adjudication. Regenerating would discard a committed, client-facing schedule for a fresh unreviewed proposal. Warn explicitly, naming what's at stake — pull `reviewed_by`, `reviewed_date`, and the batch names/dates/owners from `migration_batching.md`'s Review — Adjudication section — and require the reviewer to type back a distinct confirmation (e.g. "overwrite reviewed plan") rather than a plain yes/no.
  - **Does not match** — the CSV was reviewed, then hand-edited again afterward outside the review flow. Those further edits are exactly as much at risk as an unmodified review. Warn explicitly that this CSV was reviewed on `reviewed_date` and has since changed by hand, so a regenerate would lose both the original adjudication and the untracked follow-up edit, and require the same explicit named confirmation.
  - Either way, do **not** fall through to the generic `stale_artifact_check.md` yes/no prompt — this guard's confirmation replaces it. Only proceed to Step 1 once the reviewer has typed the exact confirmation string.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md` — unified object catalog, dependency graph, per-object effort-hour estimates
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — per-model `batch_number`, `enabled`, `platform_macros`, layer/path (domain-grouping hints and the batch-zero dependency)
- `.wire/releases/$ARGUMENTS/status.md`
- **Optional seed**: if `status.md` carries a `sow.batch_allocation` path (or a similar hand-drafted batch plan reference), or `--seed <path>` was passed in `$ARGUMENTS`, read the referenced CSV/plan of human-assigned batch names and groupings as a **seed, not ground truth** — it is reconciled against the real graph in Step 3, never accepted or discarded silently. If no seed exists, proceed with pure graph-derived grouping.
- **Optional `--target-batches N`**: the number of waves to cut the model graph into if the build-ordered fallback fires (Step 4b/4c). Ignored in the default domain mode. If unset, defaults to the candidate domain-group count (Step 3), so wave granularity stays comparable to what the domain partition would have produced.

## Workflow

### Step 1: Load the inventory graph and per-model detail

Parse the dependency graph from `migration_inventory.md` (adjacency list; the Mermaid diagram is a rendering, the adjacency list is the source) and the unified object catalog with per-object effort estimates. Parse `dbt_audit.csv` for per-model `batch_number`, `enabled`, and `platform_macros`.

The inventory graph already reflects connector/object alias normalization (regionalized or multi-tenant naming — see `migration_inventory/generate.md` Step 2's `migration.connector_alias_patterns` handling): a regional connector alias is already resolved to its canonical object and edge there. This command consumes that graph as-is and does not re-normalize.

### Step 2: Load the optional seed plan

If a seed exists (Step 0 of Inputs), extract its batch names and object→batch groupings. This is a starting hint for naming and grouping preference, to be reconciled against the graph in Step 3 — not accepted as-is. Record the seed path used, or "no seed provided".

### Step 3: Determine domain groupings

Assign every inventory object to exactly one candidate domain group:

- Where the seed plan assigns an object to a named domain group, start from that assignment.
- Where no seed exists, or for objects the seed doesn't cover, group by structural signal: schema/dataset name for db objects, top-level model folder or tag for dbt models, connector→destination pairing for ingestion and reverse ETL objects.
- **Merge rule**: merge two candidate groups if the edge density between them is high enough that separating them would force most objects in one group to declare a dependency on the other — they aren't really separable. State each merge and why in the narrative's seed-reconciliation note.
- **No silent default.** A non-dbt inventory object (Fivetran connector, warehouse object, reverse-ETL sync) with no structural grouping signal and no graph edge to any other object must never be forced into a default or nearest domain group just to keep the partition complete. Route it instead to the **`NO-DEP`** bucket — `batch_id: NO-DEP`, `batch_name: "No model dependency — review"` — for human triage at `/wire:migration-batching-review` (decommission, assign once its real consumer surfaces, or confirm it as genuinely foundational and hand-place it). This is the same rule Step 4c applies in build-ordered mode; a domain plan that quietly folds an orphan connector into whichever domain group happens to come first is the same defect by another name, just less visible because domain mode usually has a structural signal (schema, folder, connector→destination pairing) to fall back on. Use `NO-DEP` only when that structural signal is genuinely absent, not as a substitute for doing the structural grouping.

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

1. **Topologically sort the full buildable model graph** (the same graph the dbt audit's batch ordering uses — every model's `ref()`/`source()` parents sort before it, 0 forward references). Node identity must be the project-qualified node ID (`model.<package_name>.<model_name>`, per `specs/utils/dbt_manifest_parse.md` Step 3), not the bare model name — the dbt audit CSV only carries `model_name`, so if this step is joining against the CSV rather than re-deriving the graph via the manifest-parse utility, re-qualify by project first in a multi-project estate to avoid silently merging two same-named models from different projects into one node.

   **Metabase cards order after their models (#184).** A `metabase_card` node attaches after every warehouse model it reads (the inventory's model→card edges) — a card cannot be repointed or compared until its models exist on target — and a `metabase_dashboard` after its cards. Cards are wave members like connectors and syncs: scheduled, reported, and accepted with their wave.

   **Snapshots are buildable nodes in this sort.** Include every snapshot (the `snapshot` object type) as a node with its **upstream→snapshot** edge (from the ref/source it reads) and its **snapshot→dependent** edges (to each downstream model). A snapshot is a dbt build target, not a passive non-dbt object — do **not** treat it like a connector or warehouse object that "attaches to the wave of the earliest model that references it". Sorting it as a real node with real edges is what guarantees each snapshot lands after its upstream ref model and **before** every model that reads it, so no downstream model is ever deferred into a later wave solely because its snapshot upstream was skipped or placed after it.

   Break ties, in this order:
   1. **Shared-reference priority** — an object depended on by consumers spanning **N or more** distinct domains (default `N = 3`, or "more than half the candidate domain count from Step 3" if that's larger — state whichever threshold was used, and treat it as tunable per engagement) is a shared/foundational object. Among topologically-tied candidates, pull it to the earlier position regardless of where the other tie-break rules would otherwise place it — it blocks the most downstream work, so building it early matters more than keeping any one wave domain-coherent.
   2. **Domain priority** (so a wave stays as domain-coherent as the build order allows beyond rule 1).
   3. **Name**.
2. **Coarsen into `--target-batches N` waves** (default: the candidate domain-group count from Step 3), preserving the topological order — wave 1 is the earliest slice of the sort, wave N the latest. Balance the waves by the inventory's per-object effort hours (Step 6) without ever reordering across the topological cut.
3. **Set each wave's `depends_on_batches` to the full prefix** `B01..B(k-1)`. This declares every possible cross-wave edge by construction, so C3 holds, and a strict prefix is trivially acyclic, so C2 holds.
4. **Keep the domain tag** on every object's CSV row (the `domain` column) so the still-meaningful domain grouping survives for client/milestone/billing rollup — it just isn't the build order.
5. **Compute the cutover partition (secondary view).** Group every object by its `domain` tag alone, purely for client communication and milestone/cutover-rollup purposes. Unlike the wave partition above, this grouping is **not required to be acyclic or edge-complete** — it doesn't feed `depends_on_batches`, Step 6 balancing, or Step 7's parallel-safe analysis, and it can perfectly well contain a cycle or split a single dependency across two of its groups. It exists purely to answer "which domains does the client see progress in during which waves", not "what can build in parallel". For each domain, record which wave(s) its member objects actually landed in.

Non-dbt inventory objects (ingestion, warehouse objects, reverse ETL) attach to the wave of the earliest model that has a real graph edge to them — a model that `source()`s the object, or otherwise references it directly in the inventory graph. **Never default an object with no such edge into wave 1, or into any other wave.** An object with no model consumer anywhere in the graph goes into the **`NO-DEP`** bucket instead — `batch_id: NO-DEP`, `batch_name: "No model dependency — review"`, `depends_on_batches` empty — for human triage at `/wire:migration-batching-review`: decommission it, place it once its real consumer surfaces in a later audit pass, or confirm it as genuinely foundational and hand-assign it to a wave. Note the rule applied and the `NO-DEP` count in the narrative. This is not a hypothetical: on one engagement, "attach to wave 1 if nothing does" put 105 of a client's 168 Fivetran connectors into wave 1 against an intended 31 — and wave 1 is what the client authenticates first, so the defaulting was directly client-facing. In build-ordered mode there are no parallel-safe wave pairs — the full-prefix dependency makes every wave depend on all earlier ones — so Step 7 emits an empty parallel-safe set with that explanation rather than searching for one. Exclude `NO-DEP` objects from Step 6's effort-hour balancing, Step 7's parallel-safe grouping, and the wave/batch DAG itself in both modes — `NO-DEP` is a holding pen for human triage, not a schedulable batch.

### Step 5: Fold in the batch-zero macro dependency

Any batch containing a model with a non-empty `platform_macros` value (from `dbt_audit.csv`) has an implicit prerequisite on the dbt-audit **batch-zero macro translation pass** (`audit/batch_zero_plan.json`) completing first. Record this explicitly per affected batch in the narrative's batch summary table and batch-zero callout — do not let it get lost among the domain-to-domain edges. This prerequisite lives in the narrative only; the CSV's `depends_on_batches` column carries domain batch ids, not the batch-zero pass.

### Step 6: Balance batch sizes

**Domain mode.** Using the inventory's per-object effort-hour estimates, aim for roughly even hours per batch — without breaking a domain grouping and without violating the Step 4 dependency order. Note any batch that is a clear size outlier and why. A shared foundational layer that many batches depend on is often small in object count but blocks everything — its position in the DAG matters more for scheduling than its own hours; say so in the narrative.

**Build-ordered mode.** Balancing already happened inside the Step 4c coarsening — cut the topological order into waves of roughly even effort hours, never reordering across the cut. Note any wave that is a size outlier and why (a dense foundational layer early in the sort often makes wave 1 heavier).

**Both modes.** Exclude `NO-DEP` objects from these hour totals entirely — they aren't in any batch or wave yet, so they can't be balanced into one.

### Step 7: Identify parallel-safe batch groups

**Domain mode.** Any set of batches with **zero** dependency edges (either direction) between their members, per the Step 4 DAG, can be scheduled in parallel. Produce this list explicitly — it is the deliverable that directly answers "which of these batches can actually run at the same time", which is exactly what a hand-drawn plan gets wrong.

**Build-ordered mode.** There are none by construction — every wave depends on the full prefix of earlier waves. Emit an empty parallel-safe set and state that build-ordered waves are strictly sequential (the domain tag, not the wave, is what rolls up for parallel client-facing planning).

**Both modes.** `NO-DEP` is not a batch — exclude it from parallel-safe grouping in either mode. Zero edges to everything is an artifact of having no consumer yet, not evidence it's safe to schedule alongside anything.

### Step 8: Emit the CSV

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_batching.csv`

Columns:
```
object_id,object_type,source_audit,domain,batch_id,batch_name,depends_on_batches
```

One row per migration_inventory object, classified into exactly one batch. `batch_id` is zero-padded (`B01`, `B02`, …). `depends_on_batches` is a semicolon-separated list of `batch_id`s this object's batch depends on (may be empty; identical for every row in the same batch).

The columns are the same in both modes. In **build-ordered mode**, `batch_id` is the wave id, `batch_name` is the wave label (`Wave 1`, `Wave 2`, …), `domain` still carries the object's domain tag (retained for rollup, not used as the build order), and `depends_on_batches` is the full prefix `B01;…;B(k-1)`.

**`NO-DEP` is a valid classification, not an anomaly.** An object routed to `NO-DEP` per Step 3 or Step 4c gets `batch_id: NO-DEP`, `batch_name: "No model dependency — review"`, `depends_on_batches` empty, and its best-effort `domain` tag (structural signal if one exists, otherwise the tag it would have inferred with — never left blank; Check 6 still requires every column non-empty). A `NO-DEP` row satisfies "every object classified exactly once" (validate's Check 1) and "every row complete" (Check 6) exactly as any other row does — it is a deliberate, named holding pen for human triage, not a gap in the partition, and validate must not flag it as one.

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
- **The `NO-DEP` callout**: the count of objects routed to `NO-DEP` and the list of them (object_id, object_type, source_audit) — surfaced explicitly as a named section for human triage, never folded into the object-count totals or left implicit in the CSV. Zero is fine and should still be stated ("0 objects with no model consumer"); a non-zero count is the number one thing a reviewer should not have to go digging in the CSV to find
- **`### Cutover partition (secondary view)`** — build-ordered mode only. The Step 4c.5 domain-grouped rollup: one row per domain, listing which wave(s) its objects landed in. State plainly that **build order and cutover/domain order diverge whenever the SCC fallback has fired** — that's the entire reason the fallback exists — and name specifically which domains end up spread across which waves, so no reader mistakes a wave number for a domain or milestone grouping. Explicitly flag this partition as not required to be acyclic or edge-complete, unlike the wave partition it sits alongside — it's for talking to the client about milestones, not for sequencing builds
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
    no_dep_count: N                     # objects routed to the NO-DEP bucket — 0 if none
    seed_used: true | false
```

`partition_mode` is what `/wire:migration-batching-validate` reads to pick the right checks. When `scc_fallback` is true, `partition_mode` is `build_ordered_waves` and `batch_count` is the wave count (from `--target-batches` or the default).

### Step 11: Output summary

Print: partition mode (and, if the SCC fallback fired, a one-line reason), batch/wave count, object count, `NO-DEP` count (state it even when 0), parallel-safe groupings found (none in build-ordered mode), and next command:

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
