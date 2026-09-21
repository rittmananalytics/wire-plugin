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
    'command': 'migration-batching-generate',
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

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: migration_batching
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: migration_inventory
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Partition the migration inventory into independently-schedulable domain batches, checked against the real dependency graph
argument-hint: <release-folder> [--seed path] [--target-batches N] [--partition-mode mode]
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

**Three partition modes.** The default output is one batch per domain group (`partition_mode: domain`). But some estates cross-reference in every direction — the domains form a single strongly-connected component (SCC), and no domain grouping can be both acyclic *and* declare every cross-batch edge (the two conditions `/wire:migration-batching-validate` enforces are mutually exclusive for an SCC). When Step 4b detects that, generate falls back automatically to **build-ordered waves** (`partition_mode: build_ordered_waves`): a topological sort of the model graph, cut into N waves, each depending on the full prefix of earlier waves. That is trivially acyclic and declares every edge, so it validates — and it reproduces from the command instead of a hand-rolled script. The domain tag is kept as a column for client/milestone rollup even when it can't be the build order.

The third mode is **readiness waves** (`partition_mode: readiness_waves`), selected automatically when status.md carries `migration.scope: tenant_carveout` and a non-null `migration.parent_release`. A tenant carve-out staged after a parent migration is not scheduled by domain or by build order alone: the schedule depends on which models are allowed to ship right now, and that is determined by three inputs the other two modes never read: the carve rule's state in `migration/tenant_predicate_registry.csv`, whether the model's parent-release translation is merged on the client's main, and which rule groups the client has approved. A domain cut of such an estate drifts as those states change (on the reference engagement 270 of 1,494 models reclassified within days of the domain cut being built, and the plan was replaced by a hand-run readiness partition under a documented deviation). Step 4d specifies the assignment. Wave-id tokens minted in this mode (`B00` for shipped history, `PEN-<NAME>` holding pens) extend the canonical set in `specs/utils/wave_resolution.md`.

**`--partition-mode <domain|build_ordered_waves|readiness_waves>`** overrides the automatic selection. `readiness_waves` requires `migration.scope: tenant_carveout` and the readiness inputs (abort with the missing input named if they are absent). `build_ordered_waves` skips the Step 4b decision and forces waves, including on a carve-out that would otherwise get readiness mode. `domain` forces the domain cut, but Step 4b's SCC test still runs: if the single-SCC condition holds, abort rather than emit a partition that cannot validate. Without the flag: readiness mode when the carve-out condition above holds; otherwise domain, with the Step 4b fallback.

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
- **Optional `--target-batches N`**: the number of waves to cut the model graph into if the build-ordered fallback fires (Step 4b/4c). In readiness mode (Step 4d) it caps the number of sub-waves the ready band is cut into. Ignored in the default domain mode. If unset, defaults to the candidate domain-group count (Step 3), so wave granularity stays comparable to what the domain partition would have produced.
- **Readiness-mode inputs** (only when `partition_mode: readiness_waves`, Step 4d): `migration/tenant_predicate_registry.csv` (per-item carve-rule state, per `specs/utils/tenant_predicate_registry.md`); `migration/region_tags_adjudicated.csv` (adjudicated rulings: `defer`/`split` rows are exclusion-pending); the parent register at `.wire/releases/<migration.parent_release>/migration/migration_register.csv` (`delivery_stage` per parent translation); this release's own `migration/migration_register.csv` (`delivery_stage` for shipped models); the prior `migration/migration_batching.csv` if one exists (`B00` preservation); and, when reachable, a live merge-state read against the client repo(s) (`migration.client_repos`), which wins over either register's `delivery_stage`, the same rule `migration_status.md` applies. Say in the narrative which source was used.

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

**Mode selection first.** If readiness mode applies (`migration.scope: tenant_carveout` and `migration.parent_release` set, or `--partition-mode readiness_waves`), skip Steps 4–4c and go to Step 4d; the domain tags from Step 3 are kept on every row for rollup, exactly as in build-ordered mode. Otherwise proceed below.

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

### Step 4d: Readiness waves (only when readiness mode was selected)

Assign every dbt model a readiness class from four inputs, then let the dependency closure sink each model to at least its inputs' wave. The wave ids extend the canonical set per `specs/utils/wave_resolution.md`: `B00` is shipped history, `PEN-<NAME>` ids are holding pens, and the schedulable waves are `B01` onward.

**1. Per-model rule state**, from `tenant_predicate_registry.csv` (vocabulary per `specs/utils/tenant_predicate_registry.md`):

| Registry row | Rule state |
|---|---|
| `resolved_by` is `adjudication` or `manual` (a ruling), any of the five mechanisms | **ruled**: batches forward |
| `mechanism: inherited`, not ruled | **rider**: takes its `resolving_node`'s rule state (follow the chain; it terminates in a resolved row per the registry-wide checks. A chain ending in an unresolved or missing row is a registry defect: pen the model and report it) |
| Any other mechanism with `resolved_by` in `global_default`, `object_signal`, `alias_resolution`, `row_distribution_probe` | **candidate**: batches behind its approval gate. `verified_date` never promotes a candidate; verification confirms the mechanism against data, not client sign-off |
| `mechanism: unresolved`, or no registry row | **unresolved**: routes to `PEN-UNRESOLVED` |

An item whose adjudicated ruling in `region_tags_adjudicated.csv` is `defer` or `split` routes to `PEN-EXCLUSION-PENDING` regardless of its registry row: it is ruled out of (or partially out of) the current carve scope pending a rescope. If the adjudicated file is absent, skip this route and say so in the narrative.

**2. Approval groups.** Approvals arrive per rule, not per model: the client approves "filter this feed by `ad_account_id IN (...)`" once, and every model carrying that rule unlocks together. Group candidate rows by the distinct (`mechanism`, `tenant_column`, `expression`) triple. Each group is **one wave of its own**, so a client answer flips a whole wave to shippable without re-partitioning. A group is approved when every row in it is ruled; recording the approval (via `region-tagging-review`, or a hand edit with `resolved_by: manual`) is what moves its models forward on the next run.

**3. Parent-release delivery state.** A model whose parent-release translation is not yet on the client's main parks in the waiting-on-parent wave. Merged means the parent register row's `delivery_stage` is `merged` or `production_verified`; blank or `in_pr` is not merged. Use a live repo read when the client repo is reachable, the register otherwise, and say which. A model with **no parent register row** has no parent translation to wait for (authored in this release): it is not parent-gated, but list it in the narrative under "no parent row" for review.

**4. Shipped history (`B00`).** `B00` is the union of (a) models whose own register row in this release carries `delivery_stage: merged` or `production_verified`, and (b) rows the prior `migration_batching.csv` already carried as `B00`. History survives re-runs: a shipped model is never re-partitioned into a future wave, and a prior `B00` row missing from the current shipped set stays `B00` and is reported as a register discrepancy, never silently demoted. `B00` wins over every other class.

**5. Dependency closure (fixpoint).** For every model outside `B00` and the pens, compute three transitive properties over its upstream closure: `gates` (the union of pending approval groups on its own rule and every upstream's), `parent_blocked` (itself or any upstream waits on parent), `reads_pen` (any upstream sits in a pen). Propagation **stops at `B00`**: a shipped model is a satisfied input, so its own upstreams' states do not pass through it. Assign the band, first match wins:

| Condition | Band |
|---|---|
| `reads_pen`, or two or more pending groups in `gates` | **residue** (the sink band: pen readers and mixed-gate closures) |
| `parent_blocked` | **waiting on parent** |
| exactly one pending group in `gates` | **gated**, in that group's wave |
| `gates` empty | **ready** (self-ruled models and riders on ruled rules; report the two separately: approved self-contained vs no-approval riders) |

Because the three properties are transitive, every model lands at or after its inputs' wave; the bands are the fixpoint. A ready model with one gated upstream sinks to that group's wave; one spanning two pending groups sinks to residue.

**6. Wave numbering.** Number the non-empty bands consecutively: `B00` (when non-empty), then the ready band as `B01` onward (one wave, or up to `--target-batches` effort-balanced sub-waves preserving topological order, per the Step 4c coarsening rule), then one wave per approval group in lexicographic order of the group triple, then the waiting-on-parent wave, then the residue wave. Residue is last because it is the dependency sink. Pens are unnumbered and unscheduled. `depends_on_batches` for wave `Bk` is the full prefix of numbered waves including `B00`; empty for `B00`, pens, and `NO-DEP`.

**Non-dbt objects** attach to the lowest-numbered wave among their model consumers, as in Step 4c. An object whose only consumers sit in pens parks in the same pen (in `PEN-UNRESOLVED` if its consumers span both pens, the stronger hold). An object with no model consumer goes to `NO-DEP`, unchanged. Exclude pens from effort balancing, the parallel-safe set (empty in this mode, as in build-ordered mode), and the wave DAG, exactly as `NO-DEP` is excluded.

**Domain tags stay on every row** for client rollup, as in build-ordered mode.

### Step 5: Fold in the batch-zero macro dependency

Any batch containing a model with a non-empty `platform_macros` value (from `dbt_audit.csv`) has an implicit prerequisite on the dbt-audit **batch-zero macro translation pass** (`audit/batch_zero_plan.json`) completing first. Record this explicitly per affected batch in the narrative's batch summary table and batch-zero callout — do not let it get lost among the domain-to-domain edges. This prerequisite lives in the narrative only; the CSV's `depends_on_batches` column carries domain batch ids, not the batch-zero pass.

### Step 6: Balance batch sizes

**Domain mode.** Using the inventory's per-object effort-hour estimates, aim for roughly even hours per batch — without breaking a domain grouping and without violating the Step 4 dependency order. Note any batch that is a clear size outlier and why. A shared foundational layer that many batches depend on is often small in object count but blocks everything — its position in the DAG matters more for scheduling than its own hours; say so in the narrative.

**Build-ordered mode.** Balancing already happened inside the Step 4c coarsening — cut the topological order into waves of roughly even effort hours, never reordering across the cut. Note any wave that is a size outlier and why (a dense foundational layer early in the sort often makes wave 1 heavier).

**Readiness mode.** Only the ready band is balance-cut (Step 4d.6). Every other wave's membership is determined by readiness state, not effort: a gated wave is exactly its approval group, however large. Note the outliers; they tell the client which approvals unblock the most work.

**All modes.** Exclude `NO-DEP` objects, and in readiness mode pen and `B00` objects, from these hour totals entirely. They aren't schedulable work, so they can't be balanced into a wave.

### Step 7: Identify parallel-safe batch groups

**Domain mode.** Any set of batches with **zero** dependency edges (either direction) between their members, per the Step 4 DAG, can be scheduled in parallel. Produce this list explicitly — it is the deliverable that directly answers "which of these batches can actually run at the same time", which is exactly what a hand-drawn plan gets wrong.

**Build-ordered mode.** There are none by construction — every wave depends on the full prefix of earlier waves. Emit an empty parallel-safe set and state that build-ordered waves are strictly sequential (the domain tag, not the wave, is what rolls up for parallel client-facing planning).

**Readiness mode.** Same as build-ordered mode: the full-prefix dependency makes the set empty by construction.

**All modes.** `NO-DEP` is not a batch — exclude it from parallel-safe grouping in every mode, and exclude readiness-mode pens on the same grounds. Zero edges to everything is an artifact of having no consumer yet, not evidence it's safe to schedule alongside anything.

### Step 8: Emit the CSV

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_batching.csv`

Columns:
```
object_id,object_type,source_audit,domain,batch_id,batch_name,depends_on_batches
```

One row per migration_inventory object, classified into exactly one batch. `batch_id` is zero-padded (`B01`, `B02`, …). `depends_on_batches` is a semicolon-separated list of `batch_id`s this object's batch depends on (may be empty; identical for every row in the same batch).

The columns are the same in all modes. In **build-ordered mode**, `batch_id` is the wave id, `batch_name` is the wave label (`Wave 1`, `Wave 2`, …), `domain` still carries the object's domain tag (retained for rollup, not used as the build order), and `depends_on_batches` is the full prefix `B01;…;B(k-1)`.

In **readiness mode**, `batch_id` is the readiness wave or pen id from Step 4d. `batch_name` states what the wave is waiting on: `Shipped` for `B00`; `Ready` (or `Ready N`) for the ready band; `Awaiting approval: <mechanism> on <tenant_column>` for a gated wave; `Waiting on parent release`; `Residue: mixed gates or pen reads`; `Holding pen: unresolved carve rule` and `Holding pen: exclusion pending` for the pens. Pen rows follow the same completeness rules as `NO-DEP` rows: every column non-empty except `depends_on_batches`, which is empty.

**`NO-DEP` is a valid classification, not an anomaly.** An object routed to `NO-DEP` per Step 3 or Step 4c gets `batch_id: NO-DEP`, `batch_name: "No model dependency — review"`, `depends_on_batches` empty, and its best-effort `domain` tag (structural signal if one exists, otherwise the tag it would have inferred with — never left blank; Check 6 still requires every column non-empty). A `NO-DEP` row satisfies "every object classified exactly once" (validate's Check 1) and "every row complete" (Check 6) exactly as any other row does — it is a deliberate, named holding pen for human triage, not a gap in the partition, and validate must not flag it as one.

### Step 9: Emit the narrative

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_batching.md`

Use the template at `TEMPLATES/migration/migration_batching.md`. Include:

- The CANDIDATES-not-decisions posture statement (from Purpose) at the top
- **The partition-mode note**: `domain`, `build_ordered_waves`, or `readiness_waves`. When the SCC fallback fired: the Step 4b evidence (the domains form a single SCC, so no domain grouping can be acyclic *and* declare every cross-batch edge), stated plainly so no reader wonders why the output isn't domain-grouped. When readiness mode was selected: the selection basis (`migration.scope: tenant_carveout` plus `migration.parent_release`, or the `--partition-mode` override)
- **Readiness sections** (readiness mode only): the band summary (`B00` / ready / per-group gated / waiting on parent / residue / pens, with counts, and ready split into approved self-contained vs no-approval riders); one row per approval group with the rule text, its models, and what recording the approval unlocks; the waiting-on-parent list with the parent evidence used (live read or register); the "no parent row" list; any prior-`B00` register discrepancies and pen-terminating rider chains from Step 4d; and a note that shipped waves are preserved as `B00` across re-runs
- The seed-reconciliation note: what was kept from the seed, what changed and why (including every Step 3/4 merge), or "no seed provided"
- Batch summary table: `batch_id`, name, domain, object count, effort hours, `depends_on_batches`, batch-zero prerequisite (yes/no). In build-ordered mode the `domain` column shows the wave's dominant domain tag(s) for rollup
- A Mermaid DAG at batch granularity — nodes are batches, edges are dependencies (in build-ordered mode, the prefix chain B01→B02→…→BN)
- The parallel-safe groupings table (empty, with the by-construction explanation, in build-ordered mode)
- The batch-zero macro dependency callout: which batches require the batch-zero pass first, and why
- **The `NO-DEP` callout**: the count of objects routed to `NO-DEP` and the list of them (object_id, object_type, source_audit) — surfaced explicitly as a named section for human triage, never folded into the object-count totals or left implicit in the CSV. Zero is fine and should still be stated ("0 objects with no model consumer"); a non-zero count is the number one thing a reviewer should not have to go digging in the CSV to find
- **`### Cutover partition (secondary view)`** — wave modes only (`build_ordered_waves` and `readiness_waves`). The Step 4c.5 domain-grouped rollup: one row per domain, listing which wave(s) its objects landed in. State plainly that **build order and cutover/domain order diverge** (in build-ordered mode because the SCC fallback fired; in readiness mode because waves are readiness bands, not domains) and name specifically which domains end up spread across which waves, so no reader mistakes a wave number for a domain or milestone grouping. Explicitly flag this partition as not required to be acyclic or edge-complete, unlike the wave partition it sits alongside — it's for talking to the client about milestones, not for sequencing builds
- A note that this artifact is not authoritative for scheduling or dates until `/wire:migration-batching-review` runs

### Step 10: Update status

```yaml
artifacts:
  migration_batching:
    generate: complete
    file: migration/migration_batching.md
    data_file: migration/migration_batching.csv
    generated_date: "{{TODAY}}"
    partition_mode: domain | build_ordered_waves | readiness_waves
    scc_fallback: true | false          # true when Step 4b forced build-ordered waves
    batch_count: N
    objects_classified: N
    no_dep_count: N                     # objects routed to the NO-DEP bucket — 0 if none
    shipped_count: N                    # readiness mode only: B00 rows
    pen_count: N                        # readiness mode only: rows in PEN-* holding pens
    seed_used: true | false
```

`partition_mode` is what `/wire:migration-batching-validate` reads to pick the right checks. When `scc_fallback` is true, `partition_mode` is `build_ordered_waves` and `batch_count` is the wave count (from `--target-batches` or the default). In readiness mode, `batch_count` is the numbered-wave count (`B00` included when non-empty; pens excluded), and `shipped_count`/`pen_count` are set (0 when empty); omit both keys in the other modes.

### Step 11: Output summary

Print: partition mode (and, if the SCC fallback fired, a one-line reason; if readiness mode, the selection basis), batch/wave count, object count, `NO-DEP` count (state it even when 0), readiness band counts when in readiness mode (shipped / ready / gated groups / waiting on parent / residue / pens), parallel-safe groupings found (none in the wave modes), and next command:

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
