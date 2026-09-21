---
description: Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)
argument-hint: <release-folder>
---

# Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)

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
    'command': 'migration-register-generate',
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
artifact: migration_register
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
  - artifact: dbt_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Build and maintain the per-model migration register — the source-of-truth state store for what has been migrated, from which source commit, to which BigQuery target, and how it last validated

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_register` and `artifact_file_path: migration/migration_register.csv` before proceeding.

---

# Migration Register — Generate

## Purpose

Maintains a **per-model migration register** — one row per in-scope model recording what was migrated, from which source commit, to which BigQuery target, its current state, and how it last validated. This is the queryable source of truth that the drift gate, the equivalency loop, and CI all read; it is distinct from the per-model transformation **log** (`migration.transformation_log_table`), which is an append-only audit trail, not current state.

The register is maintained **incrementally** by the migration commands (see the maintenance contract below). This command initialises it, and rebuilds/reconciles it on demand.

## Register schema

`.wire/releases/$ARGUMENTS/migration/migration_register.csv`:

| Column | Meaning |
|--------|---------|
| `model` | dbt model **or snapshot** name (unique key); for a `reverse_etl_sync` row, the normalised sync id (see Reverse-ETL sync rows below) |
| `object_type` | `model` (default), `snapshot` (an SCD-2 history object, tracked here so its migration strategy and state travel with everything else), `reverse_etl_sync` (a reverse-ETL sync, seeded from `audit/reverse_etl_audit.csv` per Reverse-ETL sync rows below, #191; its equivalence verdict comes from `reverse-etl-equivalency-validate`), `metabase_card` (a **native** Metabase card — MBQL cards are repoint-only and carried by the connection, not tracked as rows), or `metabase_dashboard` (state derives from its cards) — #184 |
| `source_path` | path to the model/snapshot in the source dbt project (e.g. `models/business/orders.sql`, `snapshots/orders_snapshot.sql`) |
| `source_layer` | source-project layer (e.g. `source_project`, `business_project`, `reporting`) |
| `last_migrated_commit` | source repo commit SHA the translated model was built from |
| `bq_target` | the **fully qualified physical target relation** (`project.dataset.table` on BigQuery; `database.schema.table` on Snowflake), resolved from the target-side manifest node's resolved config (`database`/`project`, `schema`, and `alias`; the model name only when no alias is set, dbt's own fallback), never composed from the model name (#201). For a snapshot, the fully qualified `target_schema` relation. For `metabase_card`/`metabase_dashboard` rows, the target connection + database (a reporting-layer reference, not a warehouse relation, exempt from the segment rule below). **Legacy form**: registers written before #201 carry a dbt-relative two-segment value (e.g. `de_source_project.orders`). Consumers distinguish by dot-separated segment count (three segments is a physical path, two is the legacy form) and must never guess a physical path from a legacy value: `/wire:upgrade` Step 6c re-resolves legacy rows from the manifest, and `equivalency-validate` Step 1g defines what a consumer does with a row it cannot resolve exactly (`unresolved_target`, never a guess) |
| `state` | `pending` \| `migrated` \| `drifted` \| `failed` \| `removed` \| `deferred` |
| `snapshot_strategy` | for `object_type = snapshot`: `copy_and_continue` (default) or `rebuild_from_T` — blank for models. `rebuild_from_T` is valid only with a sign-off recorded in `notes` (see below) |
| `last_equivalence_result` | `pass` \| `pass_qualified` \| `diff_vintage` \| `diff_availability` \| `diff_schema_type` \| `fail` \| `null` — the verdict of the last equivalency run for this object, per the verdict taxonomy in `specs/migration/equivalency/validate.md` (legacy registers may still carry `info`; treat it as `pass_qualified`) |
| `last_equivalence_t` | the baseline instant `T` of that equivalency run (UTC), or `null` for a live run |
| `last_validated_commit` | source commit at the last equivalency validation (lets the drift gate tell "validated-then-drifted" from "never validated") |
| `delivery_stage` | blank \| `in_pr` \| `merged` \| `production_verified` — how far past "migrated" the object has shipped. Orthogonal to `state`: `state` records translation lifecycle and health (a merged model can still go `drifted`), `delivery_stage` records delivery progress. Blank until the object enters a client PR |
| `pr_url` | URL of the client PR carrying this object (set with `delivery_stage: in_pr`; kept through `merged`/`production_verified`; cleared with `delivery_stage` if the PR closes unmerged) |
| `last_reverse_ported_commit` | The client-repo commit whose version of this model was last carried back into the delivery tree by `dbt-migration-reverse-port`. Blank means never swept: a `merged` row with a blank value is the standing reminder that the delivery tree may already be stale (wire#195) |
| `parent_release` | **Relocated rows only** (`origin: relocate` in `notes`): the parent migration release folder the model's translation came from (from `migration.parent_release`). Blank on every other row |
| `parent_model` | Relocated rows only: the model's name in the parent register (usually identical; recorded so a rename never breaks the link) |
| `parent_verdict_ref` | Relocated rows only: a reference to the parent verdict that proves the SQL being relocated — the parent register row's `last_equivalence_result` plus its evidence (`<parent_release>:<report_ref>`, e.g. `05-parent-migration:migration/equivalency_report_12.md#orders`). Blank when the parent register was unreachable at relocate time — an evidence gap the relocate-mode comparator treats as unproven (see `equivalency-validate`, Relocate-mode comparison) |
| `notes` | free text (e.g. reason for `deferred`/`failed`; for a `rebuild_from_T` snapshot, the required data-owner sign-off — name + date) |

**Why `bq_target` is physical, not dbt-relative (#201).** A dbt-relative name forces every consumer to guess the physical `project.dataset.table`, and one wave-1 post-merge verification run (2026-08-20) showed guessing fail three ways: a model whose dbt `schema` + `alias` config produces a prefix-stripped physical name (`salesforce_case` materialises as `salesforce.case`; a name-equality guess finds nothing); the same table name under two datasets, where the wrong-dataset guess produced a false divergence of 70,229 rows that a manual trace showed was an exact match (23,298 = 23,298) in the right dataset; and the reverse case, a comparison against a non-existent table that returned a silent empty result. The command that builds the relation knows the exact physical path at build time: the register records it then, and consumers resolve from the register, never by guessing. This is the physical-side counterpart of the node-identity rule (`model.<package_name>.<model_name>`, `specs/utils/dbt_manifest_parse.md` Step 3): a model name is a join key, never a physical name.

## Maintenance contract (which command writes which columns)

- **`dbt-migration-generate`** — on a successful per-model migration, upserts the row: `source_path`, `source_layer`, `last_migrated_commit` (the source snapshot SHA, from `migration_sources.dbt.commit`), `bq_target` (the fully qualified relation the build just produced, from the target-side manifest node's resolved `database`/`project` + `schema` + `alias`; never recomposed from the model name, #201), `state = migrated` (or `failed` after 5 iterations, `deferred` if its source object isn't built on target). For a **snapshot** (`object_type = snapshot`), it upserts the same way after translating the inner SELECT and running the target `dbt snapshot` adopt-and-continue, leaving `snapshot_strategy` as seeded.
- **`migration-strategy-generate` / this command** — sets each snapshot row's `snapshot_strategy` (`copy_and_continue` default; `rebuild_from_T` only with the sign-off recorded in `notes`).
- **`equivalency-validate`** — on each run, writes `last_equivalence_result` (the taxonomy verdict), `last_equivalence_t` (the baseline `T` when in baseline mode, else `null`), and `last_validated_commit` for each model checked, and appends one row per verdict to the verdict log (below). It never touches `delivery_stage`.
- **`reverse-etl-equivalency-validate`**: writes `last_equivalence_result` and `last_equivalence_t` on `object_type = reverse_etl_sync` rows and appends each sync verdict to the verdict log, exactly as `equivalency-validate` does for models. It never touches `delivery_stage`. It updates rows; this command is what creates them (#191).
- **`migration-drift-generate`** — flips `state` to `drifted` (modified upstream) or `removed`, and records the drifting commit in `notes`. It never touches `delivery_stage` — a merged model that drifts keeps its delivery progress and gains a health flag.
- **`dbt-migration-batch-raise`** — sets `delivery_stage: in_pr` + `pr_url` when a model enters a client PR, advances to `merged` on merge detection, and clears both if the PR closes unmerged.
- **`equivalency-post-merge-verify`** — advances `delivery_stage` to `production_verified` when the post-merge production comparison returns `pass` or `pass_qualified`.
- **`dbt-carveout-relocate-generate`** — on relocated rows only, writes the cross-release linkage columns `parent_release` / `parent_model` / `parent_verdict_ref` (#180), alongside the upsert it already performs.
- **`dbt-migration-reverse-port`** — writes `last_reverse_ported_commit` on a ported model, and blanks `last_equivalence_result` with an audit note, since the verdict bound to the file version the port replaced. It writes nothing else: a port changes the authored file, not the model's delivery stage.
- **`metabase-migration-generate` / `metabase-carveout-generate`** — upsert `object_type: metabase_card` rows for native cards (and `metabase_dashboard` rows derived from their cards) as manifest rows are signed off and applied; `metabase-equivalency-validate` writes their `last_equivalence_*` via the standard merge (#184).
- **`equivalency-sweep`** — blanks a superseded `last_equivalence_result` (with an audit note in `notes` naming the sweep and pattern id) when a defect-class sweep invalidates a standing verdict; it never deletes rows or verdict-log history.

This command does not duplicate that logic — it seeds and reconciles the file.

## Companion verdict log (append-only history)

The register is **current-state**: one row per object, reconciled in place, so a re-validation overwrites the previous verdict and its date is lost. The companion file `migration/migration_verdict_log.csv` (seeded from `TEMPLATES/migration/migration_verdict_log.csv`) is the **append-only** verdict history: every equivalency verdict, at every run point (`standard`, `pre_raise`, `post_merge_prod`), appends one row and no row is ever rewritten or deleted. Columns: `model, object_type, run_point, verdict, divergence_mechanism, method_class, mode, baseline_t, file_version, lane_id, report_ref, written_at`. `equivalency-validate` is the only writer (via its single-writer merge step, `specs/migration/equivalency/verdict_schema.md`). Throughput reporting and reviews read the log, not the register, for anything dated.

**Snapshot rows.** Snapshots are seeded here as `object_type = snapshot` rows from `audit/dbt_snapshots.csv`, and their `snapshot_strategy` is set from the migration strategy's "Snapshot migration" section (`copy_and_continue` by default; `rebuild_from_T` only when the strategy records a data-owner sign-off, which this command copies into `notes`). If the strategy doc has not yet assigned a strategy, seed the snapshot `copy_and_continue` and leave a note — never default a snapshot to `rebuild_from_T`, since that silently discards history.

**Reverse-ETL sync rows (#191).** Where `audit/reverse_etl_audit.csv` exists, seed one `object_type = reverse_etl_sync` row per audit row: every approach, regardless of `include_in_migration`, per the routing table in `specs/utils/reverse_etl_approach.md` (a `decommission` sync is out of scope for migration and in scope for retirement, and its row is how that retirement is tracked rather than forgotten). Before this seeding existed, no command could create the row `reverse-etl-equivalency-validate` updates, and validate's Check 2 rejected any that appeared: on one engagement, 643 in-scope syncs produced 621 branch-copy compliance checks and 8 tier-1 verdicts in one day, none with a register row to land on. Per row:

- `model`: the **normalised sync id**, the audit's `sync_id` normalised per `reverse-etl-twin-generate`'s Step 0 rule (basename, extension stripped, trailing target-warehouse marker `-bq`/`_bq`/`-bigquery`/`_bigquery` stripped, lower-cased). The audit keys on the original id and authored twins carry the marker, which is why the raw string is not the key: a raw-string join matched 6 of 609 on one engagement, the normalised join 575 of 643, with the residual explained (`decommission` syncs never get twins). Where the raw `sync_id` differs from the normalised id, record `sync_id: <raw>` in `notes`. Two audit rows normalising to the same id is an error naming both original ids, never a silent merge into one row.
- `state`: `migrated` when the twin manifest (`migration/reverse_etl_twin_manifest.csv`, or its wave-labelled variants) records the sync's twin as `authored`, joined on the normalised sync id; `pending` otherwise, which covers every `decommission` and `rebuild` sync, since neither gets a twin.
- `notes`: `approach: <migration_approach>` exactly as the audit writes it, per the closed vocabulary in `specs/utils/reverse_etl_approach.md` (an approach outside the closed set is an error naming the value and the sync, never seeded); plus `wave: <batch_id>` where `migration/migration_batching.csv` assigns the sync a wave.
- `source_path`: the sync's source config path from the twin manifest where recorded; blank otherwise.
- `last_equivalence_result`, `last_equivalence_t`, `last_validated_commit`: `null` at seed. A real verdict comes only from `reverse-etl-equivalency-validate`.
- `delivery_stage`: blank at seed. Step 2b's `--ingest-merge-state` backfills `in_pr`/`merged` from live PR state for twin files exactly as it does for models, joined back to the sync row via the normalised twin filename.

## Prerequisites

- `audit/dbt_audit.csv` exists (the in-scope model list); `audit/dbt_snapshots.csv` too if the project defines snapshots — **or**, under `--from region-tagging`, `migration/region_tags_adjudicated.csv` exists instead
- `audit/reverse_etl_audit.csv`, where the release has reverse-ETL scope: sync rows are seeded from it (#191). Its absence means no sync rows, not an error
- `migration_sources.dbt` registered (so `last_migrated_commit` can be resolved)

## Flags (#180)

- `--from region-tagging` — **carve-out bootstrap.** Seed the register from the adjudicated region-tagging output instead of the dbt audit: one row per `region_tags_adjudicated.csv` item with `adjudicated_ruling: carve_in`, mapped by `item_type` (`dbt_model` → `object_type: model`; snapshot rows from `audit/dbt_snapshots.csv` where present), `state: pending`, and the item's separation mechanism from `migration/tenant_predicate_registry.csv` recorded in `notes` (`mechanism: <value>`). This is the natural seed for a carve-out that reached delivery before its register existed — the adjudication is already the locked ruling on what is in scope. Items ruled `exclude`/`defer` are not seeded. Requires `migration.scope == tenant_carveout`; abort otherwise with `[wire] --from region-tagging applies to tenant_carveout releases only.`
- `--ingest-merge-state` — **retroactive PR ingestion.** For a release whose models reached client PRs (or main) before the register tracked them, backfill `delivery_stage` and `pr_url` from **live** repo state, and record PR-body verdicts as dated verdict-log evidence. See Step 2b. Composable with `--from region-tagging` (bootstrap then ingest) or usable alone against an existing register.

## Workflow

### Step 1: Seed or reconcile

If the register does not exist, create it from `TEMPLATES/migration/migration_register.csv` and seed one row per in-scope model from `dbt_audit.csv` (`object_type = model`), plus one row per snapshot from `dbt_snapshots.csv` (`object_type = snapshot`, `snapshot_strategy` from the strategy doc as above), all with `state = pending` and all migration/validation columns `null`, plus one row per sync from `audit/reverse_etl_audit.csv` where it exists (`object_type = reverse_etl_sync`, per Reverse-ETL sync rows above, #191). Under `--from region-tagging`, the seed source is `migration/region_tags_adjudicated.csv` filtered to `carve_in` instead (see Flags) — the seeded set is the adjudicated carve-in set, and each row's `notes` records its predicate-registry mechanism.

If it exists, **reconcile** rather than overwrite: add rows for any new in-scope models or audit syncs (`state = pending`, or `migrated` for a sync already twinned); never clobber `last_migrated_commit` / `last_equivalence_*` / `last_validated_commit` already recorded; mark rows whose model no longer exists in the dbt audit, or whose sync no longer exists in the reverse-ETL audit, as `state = removed` (do not delete the row — the history matters). A register that predates the sync seeding gains its `reverse_etl_sync` rows on the first reconcile after the reverse-ETL audit exists; nothing needs a flag for that. Where a `model` or `snapshot` row carries a legacy two-segment `bq_target` (pre-#201), re-resolve it from the target-side manifest exactly as `/wire:upgrade` Step 6c does. Never overwrite a three-segment value, and never compose a path from the model name when the manifest has no node for it: leave the legacy value and report the row.

### Step 2: Backfill from existing artifacts (first run)

On first creation, backfill state from what already happened: read the batch acceptance packs and per-model `.diff.md` files to set `state` (`migrated`/`failed`) and `last_migrated_commit` where derivable; read the latest equivalency report to set `last_equivalence_result` / `last_equivalence_t` / `last_validated_commit`. Leave unknown fields `null` rather than guessing.

### Step 2b: Retroactive PR ingestion (`--ingest-merge-state`, #180)

For each configured client repo (`migration.client_repos`), read the **live** PR series — `gh pr list --state merged` plus open PRs, filtered to this release's branches/authors — and resolve which register models each PR carried (from the PR's changed files mapped back to model names). Where the release has reverse-ETL scope, do the same over the sync config repo's PRs: a PR's twin config files map back to `reverse_etl_sync` rows via the normalised twin filename (the Step 0 rule), and the same delivery-stage mapping below applies to them.

- **`delivery_stage` comes from live repo state, never from the release folder's own status records.** A model whose file is merged to the client's base branch: `delivery_stage: merged` (+ `pr_url`); in an open PR: `in_pr` (+ `pr_url`); in a PR closed unmerged, or nowhere: `delivery_stage` blank. Where the folder's prior notes disagree with `gh`, `gh` wins and the correction is reported — stale local status is exactly the failure this flag exists to repair. Set `state: migrated` for any ingested model still `pending` (its file demonstrably shipped).
- **PR-body verdicts are evidence, ingested but marked.** A PR body carrying verdict-grade comparison evidence (counts, checksums, windows argued per model) appends one row per model to `migration/migration_verdict_log.csv`: `verdict` as stated, `run_point: standard`, `lane_id: retro-ingest`, `method_class: pr_body_evidence`, `report_ref: <pr_url>`, `written_at` = the PR's merge (or last-update) instant. These rows are dated history, not fresh proof — every ingested model is flagged **re-verify: post_merge** in `notes`, and `equivalency-post-merge-verify` is the command that replaces the prose evidence with a real production comparison. A PR body with no verdict-grade evidence ingests delivery state only, no log row.
- The ingestion is idempotent: re-running re-reads live state and reconciles; it never duplicates verdict-log rows for the same (model, pr_url) pair.

### Step 3: Write the register and update status

Write `migration/migration_register.csv`. Update status.md:

```yaml
artifacts:
  migration_register:
    generate: complete
    file: migration/migration_register.csv
    generated_date: "{{TODAY}}"
    models_total: N
    migrated: N
    drifted: N
    pending: N
    failed: N
    snapshots_total: N            # object_type = snapshot rows; 0 if none
    snapshots_rebuild_from_t: N   # snapshots assigned rebuild_from_T (each requires a recorded sign-off)
    reverse_etl_syncs_total: N    # object_type = reverse_etl_sync rows (#191); 0 if none
```

### Step 4: Output next command

```
/wire:migration-register-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact_id, `Migration Register` as artifact_name, and the `file` value from `artifacts.migration_register` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_register` as artifact, `generate` as action.

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
