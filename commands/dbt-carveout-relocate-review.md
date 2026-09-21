---
description: Human adjudication gate for relocated carve-out dbt models
argument-hint: <release-folder> [--wave id \
---

# Human adjudication gate for relocated carve-out dbt models

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
    'command': 'dbt-carveout-relocate-review',
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

## Workflow Specification

---
wire_schema: "1.0"
command: review
artifact: dbt_carveout_relocate
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
  - artifact: dbt_carveout_relocate
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Human adjudication gate for relocated carve-out dbt models — approve the manifest, spot-check injected predicates, resolve any manual-review-required models
argument-hint: <release-folder> [--wave id | --batch N | --select selector]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Carveout Relocate — Review

## Purpose

Human approval gate before a batch/wave of relocated carve-out models is considered done. Presents the relocation manifest, a diff sample of injected predicates, and the manual-review-required list — the reviewer either signs off the manual-review entries by hand (then re-runs generate/validate on just those models) or resolves them here with an explicit note.

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — which manifest to review, mirroring the scope `dbt-carveout-relocate-generate` was run with. Under `--wave`, load `dbt_carveout_relocate_manifest_{wave_id}.md`; otherwise, load the unscoped `dbt_carveout_relocate_manifest.md`. `--batch` and `--select` runs write the unscoped filename today (only `--wave` output is filename-suffixed), so both read the unscoped manifest.

## Prerequisites

- `migration/dbt_carveout_relocate_manifest.md` (or `_{wave_id}.md` under `--wave`) with `validate: pass`

## Workflow

### Step 1: Present the manifest summary

Display: scope resolved (wave/batch/selector), source and target project paths, target project/dataset, and the per-bucket counts (confident-region relocated unchanged, shared-row-level with predicate injected, manual-review-required).

### Step 2: Present a diff sample of injected predicates

For a representative sample of `shared-row-level` models (or all of them, if the set is small), show the before/after diff around the injected `WHERE` clause, so the reviewer can confirm the predicate landed on the outermost `SELECT` and reads correctly — not just that a check passed.

### Step 3: Resolve the manual-review-required list

If non-empty, this blocks approval until every entry is resolved one of two ways:
- **Hand-fix and re-run** — the reviewer (or a consultant) edits the model's injection point directly, then re-runs `dbt-carveout-relocate-generate`/`-validate` scoped to just that model (`--select <model>`) so it clears the flag on its own merits.
- **Explicit sign-off here** — the reviewer records why the model is correct as relocated despite the flag (e.g. it's `confident-region` in disguise and doesn't need a predicate at all, or the ambiguous structure was checked by hand and found safe). This is the sign-off `dbt-carveout-relocate-validate`'s Check 4 looks for.

If any entry has neither a clean re-run nor an explicit sign-off, stop: `[wire] N manual-review-required model(s) unresolved. Address each before approving.`

### Step 3b: Rule on the proposed dispositions (v3.11.3)

The manifest's **proposed dispositions** are the models Rung 4 resolved from live evidence: a row-count-by-column probe, its result, and the precedent it was compared against. Each is a proposal, not a ruling. Present each one as: the model, the two (or more) candidate resolutions, the probe query, its result, and the precedent.

For each, the reviewer either **accepts** — the registry row's `resolved_by` becomes `adjudication` and `confidence` becomes `high`, which also makes it immune to being overwritten by a later re-run — or **rejects and rules otherwise**, recording the mechanism and expression they want and the reason the probe was not decisive. Reject is a real answer: a distribution that is 100% one market today does not prove the column is the tenant boundary, and the reviewer is the one who knows whether it is.

Also present, separately, any probe whose result **contradicts an existing object-level adjudication** — a row distribution that disagrees with a prior `exclude`/`carve_in` ruling. That is a re-adjudication question for `region-tagging-review`, not something to settle here; list it and route it back.

Leaving proposals unruled blocks approval: `[wire] N proposed disposition(s) awaiting a ruling. Accept or reject each before approving.` This is what `dbt-carveout-relocate-validate`'s Check 4b looks for.

### Step 4: Record decision

```markdown
## Review — dbt Carveout Relocate

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Scope**: {{WAVE_OR_BATCH_OR_SELECTOR}}
**Decision**: approved | changes_requested

### Manual-review-required sign-offs
[Per entry: model, reason it was flagged, resolution (hand-fixed and re-validated / signed off), rationale if signed off]
```

### Step 5: Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
    manual_review_signoffs:      # one entry per manual-review-required model resolved by explicit sign-off (not by hand-fix + re-run)
      - model: "<model_name>"
        rationale: "<reason>"
```

### Step 6: Output next command

If approved, and more waves/batches remain in the carve-out plan:
```
/wire:dbt-carveout-relocate-generate $ARGUMENTS --wave <next>
```

If this was the last wave/batch, and this run targeted the playground:
```
Re-run against production once playground equivalency passes:
/wire:dbt-carveout-relocate-generate $ARGUMENTS --wave <id> --target-project <production-project>
```

## Review Gate

This review is the point where a relocated batch/wave is considered done. Re-running `dbt-carveout-relocate-generate` for the same scope after this gate overwrites the relocated files and requires re-validation and re-review.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `review` as action.

Execute the complete workflow as specified above.
