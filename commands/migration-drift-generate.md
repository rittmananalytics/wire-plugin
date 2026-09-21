---
description: Scheduled drift gate — diff live source vs last-migrated commit, flag downstream syncs and masking changes
argument-hint: <release-folder>
---

# Scheduled drift gate — diff live source vs last-migrated commit, flag downstream syncs and masking changes

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
    'command': 'migration-drift-generate',
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
artifact: migration_drift
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Scheduled drift gate — diff the live source dbt repo against each migrated model's last-migrated commit, classify new/modified/removed, flag downstream Hightouch syncs, and trigger the masking-policy hook

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_drift` and `artifact_file_path: migration/migration_drift_report.md` before proceeding.

---

# Migration Drift — Generate

## bi_migration mode

On a `bi_migration` release the source is the client's LookML repo (`migration_sources.lookml`) and the content is the Looker instance, not a dbt project and a warehouse. The gate keeps its shape (refresh, diff against each row's baseline, classify, blast radius, report) with these rules, tested by `wire/tests/bi_migration/validate_bi_drift.py`:

**Model rows** (`object_type` `view` or `topic`), diffed with `git diff --name-status <last_migrated_commit>..<head> -- <lkml_file>` on the refreshed snapshot:

| Finding | Rule | Register |
|---|---|---|
| `not_applicable` | `last_migrated_commit` is null (never translated) | unchanged |
| `unchanged` | file not in the diff | unchanged |
| `modified` | file `M`. Re-run the four-class rule (`wire/bi_pairs/looker_to_omni/feature_detection.md`) on the changed view; `class_changed` when the class differs from the catalog, `blocking` when the new class is `redesign` (a mechanical view that gained Liquid cannot be re-translated mechanically) | `state: drifted`, `drift_head`, change summary in `notes` |
| `removed` | file `D` | `state: drifted`, `notes: removed_upstream` |
| `renamed` | file `R` | `state: drifted`, new path in `notes` |
| `impacted` | a topic whose model file is unchanged but which references a drifted view | `notes: impacted_by <views>` |
| `unregistered_new` | file `A` with no register row | reported; the plan decides whether it joins a batch |

**Content rows** (`object_type` `dashboard` or `look`), compared through the Looker API: `content_drifted` when Looker's `updated_at` is newer than the row's `source_updated_at`; `unknown` when the baseline is null (never drifted on missing data); otherwise `unchanged`. A `content_drifted` dashboard whose content batch is complete needs `omni-content-generate --batch <id>` re-run for that dashboard before its next parity run.

Blast radius on this release type is topics and dashboards that reference a drifted view, read from `audit/dependencies.jsonl` and each batch's `migration/omni_model/<batch_id>/dependencies.jsonl` (the two halves of one graph, joined on `object_uri`), not Hightouch syncs; Steps 3, 4, 5, 5b and 5c do not apply. Scheduling and CI gating are unchanged.

**Evidence invalidation.** After classification, recompute every affected object's evidence fingerprint: `python3 <plugin-root>/scripts/bi_evidence.py invalidate --old <stored components> --new <recomputed components> [--target-change-kind semantic|presentation_only] [--row-filtering-policy]`, and write the result's `invalidated` kinds to `stale_kinds` in `migration/parity/evidence.csv`. The rules, tested by `wire/tests/bi_migration/validate_bi_evidence.py`: a changed LookML definition, dependency closure, `parity_as_of`, test contract or adapter version stales `numeric_parity` and `interaction_fidelity`; a semantic Omni change (from `omni-model-reverse-port`: sql, aggregate type, filters, joins, timeframes) stales those and `presentation_fidelity`; a presentation-only Omni change (labels, formats, colours, layout) stales `presentation_fidelity` alone and triggers no warehouse query; a policy change stales `access_parity`, and `numeric_parity` too when the object is under an access filter that shapes rows. A tile with `numeric_parity` in `stale_kinds` no longer counts for the cutover gate until `bi-equivalency-validate` re-runs it. Drift never edits a verdict; it marks the evidence stale and says which tiles to re-run.

**Baseline check.** Compare `migration/baseline.yaml` against what is live: the Looker project's deployed revision, the Omni model id and branch, the converter and comparator versions installed, `parity_as_of` in status.md. Any difference is a `baseline_drift` finding, `blocking`: the plan must re-baseline (`bi-migration-plan-generate` writes a new `baseline_id`) before another parity run counts.


## Purpose

A **scheduled drift gate**. During a long migration the source platform keeps changing — models are added, edited, and removed while batches are being translated and validated. This command diffs the **live** source dbt repo against the commit each model was last migrated from (recorded in the migration register), classifies what changed, updates register state, and surfaces the blast radius: which migrated models drifted, which downstream Hightouch syncs they feed, and whether a masking-policy change needs the policy tags regenerated.

It is designed to run on a schedule (see "Scheduling" below) and as a CI gate on the BigQuery project, so drift is caught the day it happens rather than during a cutover scramble.

## Prerequisites

- `migration/migration_register.csv` exists (`migration-register generate: complete`)
- `migration_sources.dbt` registered — the live source dbt repo
- A dbt binary available **only** for `dbt ls` state comparison (no warehouse connection needed for `ls`), or the manifest-diff fallback below

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` — last-migrated commit per model
- `migration_sources.dbt` (live repo + local snapshot) — the current source state
- `audit/lineage/model_sync_map.json` (from `lineage-generate`) — Gold→Hightouch edges (which syncs read each warehouse model)
- `audit/reverse_etl_audit.md` — the Hightouch sync inventory and config references
- Source model `meta.masking_policy` declarations (schema/properties YAML)
- Translated model SQL under `migration/dbt/` — scanned for `-- MARKET GAP:` NULL-pad markers (Step 5b)
- Active platform pair `translation_guide.md` — the **"Deployment-integration / provenance defect patterns"** section (rule 4, `STALE_NULL_PAD_BRONZE_PRESENT`)

## Workflow

### Step 1: Refresh the live source

Run (or confirm a fresh) `/wire:migration-source-refresh $ARGUMENTS dbt` so the comparison is against the current source HEAD, not a stale snapshot. Record the live HEAD commit as `drift_head`.

### Step 2: Per-model state diff

For each `state = migrated` row in the register, compare its `last_migrated_commit` against `drift_head`. Use dbt's state comparison — **`dbt ls --select state:modified`** against a manifest built at `last_migrated_commit` as the `--state` baseline:

```
dbt ls --select state:modified --state <manifest@last_migrated_commit> --output name
```

`dbt ls` needs no warehouse connection. **Fallback (no dbt binary):** diff the model's `.sql` and its companion YAML between `last_migrated_commit` and `drift_head` with `git diff --name-status`, and parse `ref()`/`source()` + `{{ config() }}` to approximate modified/added/removed.

Classify each model:
- **modified** — the model (or its compiled definition / config / upstream refs) changed since `last_migrated_commit`. Set register `state = drifted`, record `drift_head` and a one-line change summary in `notes`.
- **removed** — the model no longer exists at `drift_head`. Set `state = removed`.
- **new** — a model present at `drift_head` with no register row. Add a row with `state = pending` (it needs migrating).
- **unchanged** — leave `state` as-is.

A model that drifted but whose `last_validated_commit` equals its old `last_migrated_commit` is flagged **"validated, now drifted"** — its prior equivalency pass is stale.

### Step 3: Flag downstream Hightouch syncs (Gold→Hightouch lineage)

For every model classified **modified** or **removed**, resolve its downstream Hightouch syncs from `model_sync_map.json` (emitted by `lineage-generate`). A re-migrated or removed Gold model flags every sync that reads it: those syncs must be re-validated (modified) or re-pointed/retired (removed). List each flagged sync with the model that triggered it.

### Step 4: Hightouch config diff

For each flagged sync, produce a **Hightouch config diff**: compare the sync's current config in the GitHub-Sync repo (model SQL, field mappings, filters) against what `reverse-etl-migration` translated, and show what the upstream drift implies — e.g. a renamed/removed column the sync's model SQL still references. This tells the reverse-ETL owner exactly what to re-translate, rather than just "something upstream changed."

### Step 5: Masking-change hook

For each **modified** model, diff its source `meta.masking_policy` (in the model's schema/properties YAML) between `last_migrated_commit` and `drift_head`. If `meta.masking_policy` was **added, changed, or removed** on any column, flag a **masking change** and trigger the policy-tag generator: re-run the `target-setup` security step (`04_security.sql` policy-tag taxonomy / data policies) for the affected objects so the BigQuery policy tags match the new source masking. Record which columns changed and that the policy-tag regeneration is required (do not silently let masking drift — a dropped masking policy that isn't re-applied is a data-exposure risk; a new one that isn't applied breaks the consuming role).

### Step 5b: Stale NULL-pad restore hook (`STALE_NULL_PAD_BRONZE_PRESENT`)

Read the pair's **"Deployment-integration / provenance defect patterns"** section (rule 4) — this is the one rule of that set that belongs in drift, because the column it watches for lands *after* generation, and only a gate that runs against the moving source can see it.

At translation time, `dbt-migration-generate` Step 3.1 item b substitutes `CAST(NULL AS <type>) /* -- MARKET GAP: <col> not present in <markets> ... */` for a source column absent in one or more markets. The connector can later catch up and the column can start carrying real data. For every `state = migrated`/`drifted` model whose translated SQL carries a `-- MARKET GAP:` NULL-pad, re-check the named source column against the **live** source warehouse (the same schema introspection Step 2's diff uses) for the previously-missing market(s):

- If the column is now **present and populated** in the live source for any of the affected markets, flag a **stale NULL-pad** finding: name the model, the column, the market(s) that now carry it, and the synthesized type from the marker. This is **flag-for-restore only** — never auto-rewritten here. Restoring the real column mapping and type is a re-translation decision (`/wire:dbt-migration-generate $ARGUMENTS --select <model>`), not a mechanical edit; note that in the finding.
- If the column is still absent in every affected market, leave the NULL-pad as-is (no finding).

Record each stale NULL-pad in the drift report (Step 6) and set the model's register `state = drifted` (its translation no longer matches the source) with a `notes` entry naming the restored column. Do not silently leave a column synthesizing NULL once the source carries real data — that is a widening, invisible data gap.

### Step 5c: Cross-release triggers (tenant carve-out, #180)

Applies only when `migration.cross_release_triggers` in status.md is non-empty (a carve-out tracking a live parent release). A carve-out inherits the parent's translations, backfills, and defects, and the dependencies between the two releases go stale exactly like blocker notes do — "closes when the parent completes its Bronze backfill" is a caveat nobody re-tests unless a gate does.

For each trigger with `status: open`:

1. **Evaluate the condition** against the parent release's current state — read the parent register at `.wire/releases/<trigger.parent_release>/migration/migration_register.csv` (and, where the condition names them, the parent's verdict log or drift report). A condition is met only by evidence read this run, never by the trigger's age.
2. **When met**, set `status: fired` in status.md and surface the trigger's `action` in the drift report: the dependent carve-out models to re-verify (resolved via the register's `parent_release` / `parent_model` linkage columns), the command to run, and the event that fired.
3. **Parent defect-class propagation.** When the parent release records a defect-class sweep (`equivalency-sweep`) whose pattern hits models this carve-out relocated, mark each relocated copy **re-verify-owed**: append a `notes` entry naming the parent sweep and pattern id, and list the models in the drift report. Their standing verdicts are stale evidence — the parent's fix does not re-prove the copy.
4. A trigger stays `fired` until the surfaced re-verifications complete (the drift report lists it every run); the consultant closes it (`status: closed`) once the dependent register rows carry fresh verdicts.

### Step 6: Write the drift report

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`

Use `TEMPLATES/migration/migration_drift_report.md`. Include: `drift_head` and the run timestamp; counts (modified / removed / new / unchanged); the per-model drift table (model, classification, change summary, prior equivalence state); the flagged downstream syncs with their config diffs; the masking changes with the policy-tag regeneration actions; the **stale NULL-pad restores** (Step 5b) — each flagged model, column, now-present market(s), and synthesized type, marked flag-for-restore; and the **cross-release triggers** (Step 5c) — each fired trigger with its event, the dependent re-verifications, and the re-verify-owed relocated models. Re-write the affected register rows (Step 2, Step 5b, and Step 5c item 3).

### Step 7: Update status

```yaml
artifacts:
  migration_drift:
    generate: complete
    file: migration/migration_drift_report.md
    last_run_date: "{{TODAY}}"
    drift_head: "<commit>"
    modified: N
    removed: N
    new: N
    syncs_flagged: N
    masking_changes: N
    stale_null_pads: N        # STALE_NULL_PAD_BRONZE_PRESENT — MARKET GAP columns now present in the live source, flagged for restore
    cross_release_triggers_fired: N   # carve-out only — triggers whose condition was met this run (Step 5c)
```

### Step 8: Output next command

```
/wire:migration-drift-validate $ARGUMENTS
```

If any models drifted: re-migrate them (`/wire:dbt-migration-generate $ARGUMENTS --select <drifted models>`), then re-run equivalency in baseline mode and, where masking changed, re-run `target-setup`.

## Scheduling

This gate is meant to run unattended. Deploy it two ways (templates in `TEMPLATES/migration/ci/`):

- **Scheduled** — `migration-drift-schedule.yml`: a cron GitHub Actions workflow on the delivery repo that refreshes the source and runs this drift check (e.g. nightly), opening/annotating an issue when drift is found.
- **On-change CI** — `migrated-model-ci.yml`: on any change to a migrated model (path filter derived from the register's `source_path` column), re-run compile + the tiered sweep (Tier 1 `dbt-migration-lint` + Tier 3 `equivalency-validate --baseline`).

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact_id, `Migration Drift` as artifact_name, and the `file` value from `artifacts.migration_drift` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_drift` as artifact, `generate` as action.

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
