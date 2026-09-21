---
description: Generate Snowflake→BigQuery bulk copy runbook (tenant carve-out, two-stage with equivalency gate)
argument-hint: <release-folder> [--wave id]
---

# Generate Snowflake→BigQuery bulk copy runbook (tenant carve-out, two-stage with equivalency gate)

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
    'command': 'bulk-copy-migration-generate',
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
artifact: bulk_copy_migration
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
  - artifact: target_setup
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate a Snowflake→BigQuery bulk historical copy runbook — tenant carve-out two-stage copy with an equivalency gate, plus a bring-in mode for source-platform-only history in any scope
argument-hint: <release-folder> [--wave id] [--snapshots [names]] [--mode bring-in [--dry-run]]

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: bulk_copy_migration` and `artifact_file_path: migration/bulk_copy_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before generating any copy steps, read `data_safety`, `migration.scope`, and `migration.tenant_predicate` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform (snowflake): READ ONLY.
  The bulk copy issues SELECT / COPY INTO (export) against the source only.
  Do NOT run INSERT, UPDATE, DELETE, or any DDL against the source.

[If migration.scope == tenant_carveout:]
Tenant carve-out scope — this copy moves ONE tenant's data only:
  Every extract is filtered by its object's resolved tenant filter, from
  migration/tenant_predicate_registry.csv (Step 2a). An object whose
  mechanism is object_carve is copied whole, by design.
  A copy step that omits its object's resolved filter, or whose filter does
  not match the registry row, MUST NOT run. An object with no resolved
  mechanism is NOT copied at all.

[If migration.scope is full_migration/absent (snapshot-history copy only):]
Full-migration snapshot-history copy — unfiltered:
  Only snapshot histories are copied (raw tables re-land via ingestion).
  The whole history is copied — no tenant predicate is applied or required.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (never a copy destination):
  [list each production project ID]
```

If any generated copy step would write to a source platform, target a production project listed in `data_safety.production_projects`, or write anywhere other than the designated target, stop immediately and report the conflict before proceeding. Under carve-out, a copy step that omits the tenant predicate (or uses one that does not match `migration.tenant_predicate`) must not run either.

---

# Bulk Copy Migration — Generate

## Purpose

Generates the runbook for a one-off **bulk historical copy of a single tenant's data from Snowflake to BigQuery**, using the **BigQuery Data Transfer Service** (managed Snowflake connector) or a **GCS-staged** path (Snowflake `COPY INTO` an external GCS stage → BigQuery load from GCS). This is the carve-out alternative to re-ingestion: it moves the existing historical rows in bulk rather than re-running Fivetran/connector ingestion against the target.

This command has three copy paths, gated separately (see Step 1):

- **Raw-table / connector copy** (ingestion-replacement) — carve-out-only. It runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`). For a full migration, raw tables re-land via `/wire:ingestion-migration-generate` instead, so bulk-copy must not copy raw/connector tables outside carve-out.
- **Snapshot-history copy** — runs in **any** scope. A dbt snapshot's SCD-2 history cannot be reconstructed from the current source, so it is copied rather than re-ingested regardless of scope. Under carve-out it is tenant-filtered like every other extract; in a full migration it copies the **whole** history, unfiltered. The `--snapshots` scope runs this path on its own.
- **History bring-in** (`--mode bring-in`, #179) — runs in **any** scope. For **source-platform-only history**: tables whose data exists nowhere upstream to re-ingest from — ML inference outputs, event history predating the current connectors, billion-row archives whose upstream is gone. A sizing pass classifies each table COPYABLE / EXPORT / CONNECTOR-ONLY against a configurable gate, the copyable path is a chunked, ledgered, resumable copy with a verification battery, and the over-gate path emits a client-run execute-pack — RA never runs writes on the source platform. See "Bring-in mode" below.

**Always a runbook/script.** Native SQL and the BigQuery Storage Write / load path are always available — there is no MCP-server dependency and no execution-vs-runbook branching. `method` is always `runbook`.

**Two-stage copy with a validation gate.** A pilot partition is copied first and verified with equivalency checks before the remainder is copied. The first copy execution is a safety gate requiring written approval — see `review.md`.

## Prerequisites

- `target_setup review: approved`
- For the **raw-table / connector copy** path: `migration.scope == tenant_carveout` and `migration.tenant_predicate` is set. For a **snapshot-history copy** in a full migration (`--snapshots`), neither is required — see Step 1.
- Target warehouse schemas exist (target_setup scripts executed)
- `migration/migration_batching.csv` exists — required only when running with `--wave`

## Flags

- `--wave <id>` — restrict this run to the tables `migration/migration_batching.csv` assigns to this wave. Resolution is identical to `dbt-migration-generate`'s Step 1w: normalise the wave id, load `migration_batching. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).csv` (abort if missing), filter to rows where `batch_id` matches **and** `object_type == "connector"`, then cross-reference each matched `object_id` against `ingestion_audit.md`'s connector identifiers for the landed tables to copy. Print the mandatory resolved-table preview before proceeding. If rows match the wave but none are `connector` rows, print `[wire] Wave <id> has no connector/table objects — nothing to copy for this command.` and stop cleanly.
- `--snapshots` — **targeted snapshot-history-copy scope.** Restrict the run to copying the selected snapshot histories only (the snapshot-history-copy path in Step 3), skipping the raw-table / connector copy entirely. `--snapshots` (bare) copies every `copy_and_continue` snapshot history in the release (`object_type = snapshot` in the migration register / `audit/dbt_snapshots.csv`; `rebuild_from_T` snapshots are correctly skipped — they start fresh at `T`); `--snapshots name1,name2` copies only the named snapshots. Selection resolves against the snapshot object-type rows, never a connector/table list. This is the path that runs in a **full migration** — where raw tables re-land via ingestion, but snapshot history still has to be copied. Under carve-out it stays tenant-filtered; in a full migration it copies the whole history, unfiltered (see Step 1). Standalone scope — abort if combined with `--batch`, `--wave`, `--model`, `--models`, `--select`, `--exclude`, or `--macros`: `[wire] --snapshots is a standalone scope. Run it on its own; do not combine with --batch/--wave/--model/--models/--select/--exclude/--macros.`
- `--mode bring-in` — the history bring-in path (see the "Bring-in mode" section below). Standalone: abort if combined with `--wave` or `--snapshots`. `--dry-run` stops after the sizing pass and classification, writing nothing and running no copy.
- No flag — process every landed table for connectors with `include_in_migration: true`, plus every `copy_and_continue` snapshot history (today's behaviour, unchanged; carve-out only).

When `--wave` is supplied, the runbook is wave-labelled (`migration/bulk_copy_migration_runbook_{wave_id}.md`) and status.md tracks the wave under `wave` / `waves_complete`.

## Bring-in mode (`--mode bring-in`, #179)

**Scope of the mode.** The in-scope table list is the migration inventory's source-platform-only history set: tables flagged as having no re-ingestion path (no live connector upstream), plus any table the consultant names explicitly. Under `tenant_carveout` every extract still resolves its filter from the tenant predicate registry (Step 2a rules apply unchanged — an unresolved object gets no copy step); in a full migration extracts are unfiltered.

**Step B1 — Sizing pass (read-only, always first).** For every candidate table, read row count and stored bytes from the source platform's metadata (`INFORMATION_SCHEMA` / `SHOW TABLES` — SELECT/SHOW only, never a data scan), and record the source's current high-water mark (max load timestamp or key) as the **vintage pin** for everything downstream. Write the sizing table into the runbook: table, rows, GB, classification.

**Step B2 — Classification (deterministic — tests mirror it: `wire/tests/platform_migration/validate_bring_in_classification.py`).** Read the gate from `migration.bring_in.copy_gate` in status.md (defaults `max_rows: 10000000`, `max_gb: 3`):

| Condition | Classification | Path |
|---|---|---|
| A live connector still serves the table | **CONNECTOR-ONLY** | No copy step — it re-lands via ingestion; listed with the serving connector |
| Rows ≤ `max_rows` AND GB ≤ `max_gb` | **COPYABLE** | Chunked copy (Step B3) |
| Over either limit | **EXPORT** | Client-run execute-pack (Step B4) |

**Step B3 — COPYABLE path: chunked, ledgered, resumable copy.** Per table:

- **Pinned vintage**: every chunk's extract is bounded by the Step B1 vintage pin, so a moving source never smears the copy.
- **Boundary-keyed chunks**: chunks cut on a monotonic key or partition column, each chunk's boundaries recorded before it runs.
- **Chunk ledger**: `migration/bring_in/<table>_ledger.csv` — one row per chunk: boundary keys, row count, load-job id, state (`pending`/`loaded`/`verified`). Rewritten after each chunk, per the fleet resume contract (`specs/utils/migration_fleet.md`).
- **Deterministic load-job ids**: derived from release + table + chunk floor (e.g. `wire_<release>_<table>_<chunk_floor>`), never timestamps — a re-run re-submitting a completed chunk is rejected by the warehouse as a duplicate job instead of double-loading. **A killed copy resumes mid-table from the ledger**, skipping every `loaded`/`verified` chunk.
- **Verification battery** per table once all chunks load: exact row count, numeric column sums, key min/max, all at the pinned vintage on both sides. Exactness, not tolerance — a bring-in is a copy, not a translation.

**Step B4 — EXPORT path: the client-run execute-pack.** For each over-gate table, emit `migration/bring_in/export_pack_<table>.md` as a client-handoff artifact: the storage-integration setup, the `COPY INTO` parquet unload statements (vintage-pinned, chunk-bounded), the target load or BigLake external-table DDL, and the same verification battery as B3 for the client to run and return. **RA never executes writes on the source platform** — the pack is prepared, reviewed at `bulk-copy-migration-review`, and handed over.

**Step B5 — Register rows.** Each brought-in table upserts a register row whose `notes` carry the **vintage pin** (`vintage: <instant-or-key>` — this is a pinned snapshot of a moving source, and the note is what stops it being mistaken for a live feed) and the **production-promotion route** (`promotion: weekly_copy_dag | client_pipe | frozen` — how, if at all, the table stays current after the one-off bring-in).

Bring-in runbook: `migration/bulk_copy_migration_runbook_bring_in.md`. The review gate (`bulk-copy-migration-review`) covers the first COPYABLE execution and every EXPORT pack handoff.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md` — the in-scope source datasets/tables (connectors with `include_in_migration: true` identify the landed tables to copy)
- `.wire/releases/$ARGUMENTS/audit/dbt_snapshots.csv` — the snapshot catalog (strategy, `target_schema`, meta-column set); identifies the built snapshot histories to copy for `copy_and_continue` snapshots
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` — each snapshot's assigned `snapshot_strategy` (`copy_and_continue` vs `rebuild_from_T`)
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md` — copy mechanism decision (BQ Data Transfer Service vs GCS-staged), per-table tolerances, and the tenant-scoped IAM model
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` — per-object tenant filter, resolved at Step 2a under carve-out (`specs/utils/tenant_predicate_registry.md`)
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`, `data_safety`, target platform/project

## Workflow

### Step 1: Confirm prerequisites and gate the copy path

1. Confirm `target_setup review: approved` in status.md. If not, stop with message.

2. **Determine the copy path(s) this run will generate:**
   - **Raw-table / connector copy** — copying landed raw/connector tables (the ingestion-replacement path). In scope for a bare run or a `--wave` run.
   - **Snapshot-history copy** — copying built `copy_and_continue` snapshot histories. In scope for a bare run (alongside the raw-table copy), a `--wave` run, or — on its own — a `--snapshots` run.

3. **Gate each path against `migration.scope`** (the guard is a function of scope × copy path):
   - If `migration.scope == tenant_carveout`: **both** paths are allowed and **both** are tenant-filtered. Confirm `migration.tenant_predicate` is set — if null, stop: "migration.tenant_predicate is required to scope the carve-out copy." Every extract (raw-table and snapshot-history alike) carries a tenant filter — from v3.11.3 **resolved per object from the tenant predicate registry**, not the global string applied to everything (see Step 2a).
   - If `migration.scope` is `full_migration` or absent:
     - The **raw-table / connector copy path is blocked.** If this run would copy raw/connector tables (a bare run, or a `--wave` run), stop: "Bulk copy of raw/connector tables runs in tenant carve-out scope only. For a full migration, raw tables re-land via /wire:ingestion-migration-generate; bulk-copy in a full migration copies snapshot histories only — run with --snapshots."
     - The **snapshot-history copy path is allowed** (run with `--snapshots`). It copies the **whole** snapshot history **unfiltered** — no tenant predicate is applied, and `migration.tenant_predicate` is **not** required (do not stop on a null predicate for this path). Only `copy_and_continue` snapshots are copied; `rebuild_from_T` snapshots start fresh at `T` and are skipped.

   In short: raw-table copy needs carve-out; snapshot-history copy runs in any scope. Tenant-filtering of the unload applies **only** under carve-out — a full-migration snapshot-history copy is unfiltered.

### Step 1w: Resolve `--wave` (only when `--wave` is used)

Resolve the in-scope table set per the **Flags** section above. This replaces "each in-scope source dataset/table" in Step 3 with the wave-resolved subset. A `--wave` run copies raw/connector tables, so it takes the raw-table path and is gated carve-out-only per Step 1.

### Step 1s: Resolve `--snapshots` (only when `--snapshots` is used)

Resolve the selected snapshots against the **snapshot object-type nodes** only — the `object_type = snapshot` rows in `migration/migration_register.csv`, cross-referenced to `audit/dbt_snapshots.csv` for each snapshot's `snapshot_strategy`, `target_schema`, and meta-column set. Never resolve against the connector/table list. Bare `--snapshots` selects every `copy_and_continue` snapshot; `--snapshots name1,name2` selects only the named ones (a name that resolves to a model, an unknown snapshot, or a `rebuild_from_T` snapshot is reported: `[wire] --snapshots: "<name>" is not a copy_and_continue snapshot object-type node — check audit/dbt_snapshots.csv.`). Abort with `[wire] No copy_and_continue snapshots matched --snapshots. Aborting.` if the resolved set is empty. Print the resolved-snapshot preview before proceeding. This run generates **only** the snapshot-history-copy steps (Step 3's snapshot section) — the raw-table / connector copy is skipped entirely — and is gated per Step 1 (allowed in any scope; unfiltered outside carve-out).

### Step 2: Pre-flight — scoped service account and tenant guard

There is no MCP probe. Instead, verify the safety posture for a pilot export before generating any copy step:

1. **Scoped service account** — confirm the migration strategy designates a service account scoped to *only* the target project/dataset (under carve-out, only the extracted tenant's; and, for the GCS-staged path, only the dedicated staging bucket). Record its identity in the runbook. The copy must not run under a broad/admin credential.
2. **Copy guard** — confirm a guard is in place so a misconfigured copy cannot write outside the designated target:
   - the destination resolves to `migration.target_project` and is not in `data_safety.production_projects`;
   - for GCS-staged, the staging bucket is dedicated to this run and the service account has no access to other tenants' buckets.
   - **Under carve-out only:** additionally confirm every source extract carries its object's resolved tenant filter (Step 2a) so a misconfigured copy cannot touch another tenant's data. A **full-migration snapshot-history copy** (`--snapshots`) is unfiltered by design — there is no tenant filter to check; confirm instead that the run copies only snapshot histories (no raw/connector tables).
3. Output the pre-flight table before generating the runbook:

```
Bulk Copy Pre-flight Check
════════════════════════════════════════════════════════════════

  Copy mechanism      : BigQuery Data Transfer Service | GCS-staged
  Scope               : tenant_carveout | full_migration (snapshots only)
  Tenant filters      : resolved per object from the registry (Step 2a); N unresolved → not copied
                        (n/a — unfiltered full-migration snapshot copy)
  Scoped SA           : [service account identity]
  Target destination  : [migration.target_project] / [dataset]
  Copy guard          : ✅ destination verified · [carve-out: resolved filter on every extract]
  Objects in scope    : N

```

If the scoped service account or the copy guard cannot be confirmed, stop and report — do not generate copy steps that could run without them.

### Step 2a: Resolve each object's tenant filter from the registry (v3.11.3, carve-out only)

Read `migration/tenant_predicate_registry.csv` and resolve one filter per in-scope object, applying the read contract in `specs/utils/tenant_predicate_registry.md`:

| Registry `mechanism` | Extract filter |
|---|---|
| `row_predicate`, `derived_expr`, `account_cascade` | `WHERE <expression>` from the row |
| `object_carve` | None — the whole object is inside the carve-out by name or schema convention, so copy it whole. Record `object_carve` against the step so a reader does not mistake the absent filter for an omission |
| `inherited` | Not applicable to a raw-table copy: an inherited mechanism describes a derived model scoped by its upstream, not a landed table. Treat as `unresolved` here and report it — a raw table cannot inherit a filter it has no upstream for |
| `unresolved`, or no row | **Emit no copy step.** List the object under unresolved items with its registry state |

**An unresolved object is never copied unfiltered.** Copying every tenant's rows into the tenant's own project is a data-residency incident, not a test failure, and it is not undone by deleting rows afterwards — the data has already crossed the boundary. This is why the rule is refuse-and-list rather than warn-and-proceed.

If the registry is absent, stop: `[wire] No tenant_predicate_registry.csv found. Re-run /wire:region-tagging-generate $ARGUMENTS to seed it (or /wire:upgrade for a release created before v3.11.3).`

Print the per-object resolution table (object, mechanism, filter, `resolved_by`) before generating any copy step, and carry the unresolved list into the runbook. `bulk-copy-migration-review` is the gate where a reviewer sees which objects are being left behind and why.

### Step 3: Generate the bulk copy runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/bulk_copy_migration_runbook.md` — or `migration/bulk_copy_migration_runbook_{wave_id}.md` when run with `--wave`, or `migration/bulk_copy_migration_runbook_snapshots.md` when run with `--snapshots`.

**Under `--snapshots` scope, skip this raw-table / connector loop entirely** — generate only the snapshot-history-copy steps below (Step 1s's resolved snapshot set). For every other scope, document the raw-table copy for each source dataset/table in scope (Step 1w's resolved set under `--wave`, otherwise every landed table for connectors with `include_in_migration: true`; smallest / lowest-risk first) via the mechanism chosen in the migration strategy:

- **BigQuery Data Transfer Service** — a transfer config per table whose query applies that table's resolved tenant filter (Step 2a), or reads a tenant-scoped source view, landing in the target dataset.
- **GCS-staged** — Snowflake `COPY INTO @<tenant_stage> FROM (SELECT ... WHERE <resolved filter>)` to the dedicated GCS bucket, then a BigQuery load job from that bucket into the target table. An `object_carve` table unloads whole, with no `WHERE`.

**Snapshot history copy (`copy_and_continue` snapshots).** A dbt snapshot is an SCD-2 history table, not a re-ingestable source — its closed versions exist only in the built snapshot relation and cannot be reconstructed from the current source. For every snapshot assigned `copy_and_continue` in the migration register / strategy (skip any assigned `rebuild_from_T` — those start fresh at `T` on a recorded sign-off, so there is no history to copy), add a copy step that moves the **built snapshot table** source→target, landing at the snapshot's exact `target_schema` relation (from the snapshot catalog) so the target `dbt snapshot` run finds and continues it in place. The copy must:

- **Preserve the payload columns and the four dbt meta columns** — `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to` — in their exact ordinal order (payload first, meta columns at the tail in that order), never dropping or reordering them. A dropped or reordered meta column breaks continuation.
- **Translate column types via the pair's `type_mapping.md`**, reading the SCD meta-column types from the active pair's **"Snapshot SCD mechanisms"** section — never hardcode them. `dbt_scd_id` is a string/varchar hash; the temporal meta columns follow the snapshot's `updated_at` type mapping.
- **Freeze the source snapshot at the strategy's baseline instant `T` first** — read the source from the zero-copy clone at `T` (the `wire_baseline` schema, `… AT (TIMESTAMP => '<T>')`), not the live snapshot, so continued source snapshotting does not move the copied history and the copied `dbt_scd_id` set matches what the target adopt-and-continue run will extend.
- **Tenant scope** — under carve-out (`migration.scope == tenant_carveout`), filter the unload to only the in-scope tenant/region history: apply the snapshot's resolved tenant filter (Step 2a, and any region predicate) to the snapshot extract exactly as for a landed table, so only the extracted tenant's version rows are copied. In a **full migration** (the `--snapshots` path), the snapshot-history copy is **unfiltered** — copy the whole history, with no tenant predicate.

The target-side adopt-and-continue (`dbt snapshot --select <snap>`) is run by `dbt-migration-generate` after this copy lands — this runbook only moves the history. Note the ordering in the runbook: copy the built snapshot history before the target `dbt snapshot` run, never after (a `dbt snapshot` against an empty target relation would open fresh version rows and orphan the copied history).

Structure the runbook with these sections (mirroring the ingestion migration runbook):

1. **Pre-flight checklist** — scoped service account in place, tenant guard confirmed, target schemas exist, staging bucket dedicated (GCS-staged path), copy mechanism selected.
2. **Two-stage copy steps** (smallest / lowest-risk table first):
   - **Stage 1 — pilot partition.** For each table, copy a single bounded partition (e.g. one month, or a bounded slice of the partition key), filtered by the tenant predicate.
   - **Validation gate.** Run equivalency **check 1 (row count)** and **check 6 (row-level checksum)** scoped to that partition and the tenant predicate, on both source and target (see `equivalency/validate.md`). Proceed to Stage 2 only if both pass. On failure, stop and route to `/wire:equivalency-investigate`.
   - **Stage 2 — remainder.** Copy the rest of the table's rows for the tenant, then re-run check 1 over the full tenant row set.
3. **Credential rotation checklist** — scoped service account key, GCS bucket access, BigQuery Data Editor on the target dataset only; nothing granted on other tenants' projects.
4. **Post-copy validation steps** — hand off to `/wire:equivalency-validate` for the full seven-check pass (tenant-scoped) once all tables are copied.
5. **Source decommission procedure** — deferred to the cutover phase; the source stays live and unmodified throughout the copy.

### Step 4: Update status

```yaml
artifacts:
  bulk_copy_migration:
    generate: complete
    method: runbook
    file: migration/bulk_copy_migration_runbook.md
    generated_date: "{{TODAY}}"
    copy_mechanism: bq_data_transfer | gcs_staged
    scope: tenant_carveout | full_migration      # which guard path this run took
    copy_path: raw_and_snapshots | snapshots_only # snapshots_only under --snapshots
    tables_in_runbook: N
    snapshots_in_runbook: N                       # copy_and_continue snapshot histories copied
    tenant_predicate: "{{migration.tenant_predicate}}"   # null for an unfiltered full-migration snapshot copy
    wave: "B01"                  # set only when run with --wave; the wave id just processed
    waves_complete: ["B01"]      # set only when run with --wave; accumulates across runs
    mode: standard | bring_in    # bring_in only under --mode bring-in
    bring_in:                    # set only under --mode bring-in
      copyable: N                # tables classified COPYABLE (chunked copy)
      export: N                  # tables classified EXPORT (client execute-pack)
      connector_only: N          # tables still served by a live connector — no copy step
      vintage_pin: "<instant>"   # the sizing pass's high-water mark every extract is bounded by
```

### Step 5: Output next command

```
/wire:bulk-copy-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/bulk_copy_migration_runbook.md` (`_{wave_id}` suffix when run with `--wave`)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact_id, `Bulk Copy Migration` as artifact_name, and the `file` value from `artifacts.bulk_copy_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bulk_copy_migration` as artifact, `generate` as action.

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
