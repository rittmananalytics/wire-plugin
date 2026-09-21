---
description: Closed fix-and-re-review loop — auto-apply the deterministic pre-PR-review fixes, re-run the gate, escalate only findings that need a human decision
argument-hint: <release-folder> [--batch N 
---

# Closed fix-and-re-review loop — auto-apply the deterministic pre-PR-review fixes, re-run the gate, escalate only findings that need a human decision

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
    'command': 'dbt-migration-fix',
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
command: utility
artifact: dbt_migration
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: ingestion_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Closed fix-and-re-review loop — auto-apply the deterministic fixes from the pre-PR review, re-run the gate, and escalate only the findings that genuinely need a human decision
argument-hint: <release-folder> [--batch N | --wave id | --model name] [--base ref] [--max-iterations N] [--dry-run] [--severity LEVEL]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Migration — Fix

## Purpose

The mutation counterpart to `dbt-migration-pre-pr-review`. The review command is read-only by design — it finds the deploy-time defects and emits them as a structured list, but it never edits a model. This command closes the loop: it ingests those findings, **auto-applies every fix that is deterministic and semantically safe**, re-runs the gate, and hands the consultant only the minority of findings that genuinely need a human decision. It exists so a wave of mechanical fixes (add `SAFE_CAST`, prefix `SAFE.`, re-anchor a regex, drop a redundant `TIMESTAMP()` wrap, author a `policy_tags` from the tag map) is not hand-worked model by model.

This is to `dbt-migration-pre-pr-review` what `equivalency-fix` is to `equivalency-validate`: detection stays read-only; fixing is a separate, explicit, re-runnable step.

## What it does and does not touch

- It edits **only** the translated model files under `migration/dbt/` (and re-runs them against the **test** project). It never writes to a source platform or any `data_safety.production_projects` project — same guard as `dbt-migration-generate`.
- It never auto-resolves a finding that needs a decision (see the fix-policy table). Those are escalated, not guessed.
- `--dry-run` classifies and prints the plan (what would be auto-fixed, what would be escalated) without editing anything.

## Flags

- `--batch N` / `--wave <id>` / `--model <name>` — scope, resolved exactly as `dbt-migration-pre-pr-review` resolves them (Step 0w / Step 1w); wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). `--wave` and `--batch` cannot be combined.
- `--models <names>` — narrow a `--wave`/`--batch` to a named subset (the register-driven resume subset — see `dbt-migration-generate`).
- `--base <ref>` — the diff base the findings were taken against; passed through to the review re-runs.
- `--max-iterations N` — cap on the auto-fix loop (default 5, matching `dbt-migration-generate`'s per-model loop). The loop stops earlier when no auto-fixable finding remains or a pass makes no progress.
- `--severity error|warn|info` — minimum severity to act on (default `error`; `warn` to also auto-fix warnings).
- `--dry-run` — classify and print the plan; apply nothing.
- `--config <path>` / `--tag-map` / `--target-dataset` / `--dbt-project-path` — per-run config overlays, mirroring `dbt-migration-generate` exactly.

## Inputs

- The latest `dbt-migration-pre-pr-review` findings report for the scope (`migration/pre_pr_review/*_pre_pr_review.json`). If it is missing or older than the current translated diff, run `dbt-migration-pre-pr-review` first to refresh it.
- Active platform pair — the fix hints and the fix-policy for each pattern come from the pair's rule sections (`translation_guide.md`: Deployment type-divergence patterns, Edge-case runtime-failure patterns, Column governance / masking mechanisms), never hardcoded here.
- Engagement fix-policy overrides at `.wire/engagement/platform_pair_overrides/{pair}/fix_policy.md`, if present — lets an engagement move a pattern between `auto`/`propose`/`decision` with a documented reason.
- The PII tag map (`migration.pii_tag_map_path`) — used to decide whether a governance finding is auto-fixable (a tag-map entry exists) or a decision (it does not).

## Fix-policy classification

Every finding is classified into one of three policies. The default mapping below is driven by the finding's pattern/category; the pair or engagement override may adjust it. The rule is deliberately conservative — a fix is only `auto` when it is deterministic **and** semantically correct regardless of the model's intent.

**`auto` — apply automatically, then re-run the gate.** The fix restores the source's behaviour and cannot be wrong:
- `UNGUARDED_JSON_PARSE` → prefix `SAFE.` (null-on-error matches the source)
- `CAST_BLANK_STRING_NUMERIC` → `SAFE_CAST`
- `UNANCHORED_REGEX` → re-anchor `^(?:...)$`
- `DIV0_NULL_COERCION` → rewrite to `IF(b = 0, 0, SAFE_DIVIDE(a, b))` (`DIV0`) / `IF(b = 0 OR b IS NULL, 0, SAFE_DIVIDE(a, b))` (`DIV0NULL`) — the `IF(...)` form restores the source's NULL/zero-divisor semantics exactly, so a bare `SAFE_DIVIDE` or an `IFNULL`/`COALESCE` wrapper is always the wrong translation
- `TS_WRAP_ALREADY_TS` → drop the redundant temporal wrap
- `ARRAY_AGG_NULLS` → add `IGNORE NULLS`
- `IMPLICIT_JOIN_COERCION` → explicit `CAST` to the shared deployment type
- `JSON_FN_ON_STRING` / `JSON_FN_ON_JSON` → align the accessor to the deployment column type
- `governance_regression` **when the tag map has an entry** for the source masking policy → author the `policy_tags`
- `column_order_drift` (W6b) → reorder the output projection to source ordinal order plus the pair's allow-listed tail columns. This finding is a **pure reorder** — the column set already matches (source columns + allow-listed tail); only the order differs — so restoring source order is deterministic and parity-restoring, never a change to what the model emits. It fires only when no `column_order_waived` reason is recorded; a waiver suppresses the finding upstream, so an intentional reorder is never auto-reverted. (A set-level mismatch — an unexpected non-allow-listed column, or a missing source column — is not this finding: it surfaces as the schema check's extra/missing-columns FAIL and is escalated, since dropping or adding a column is intent-dependent.)

**`propose` — draft the fix, but a human confirms.** Deterministic to write, but intent-dependent, so it is drafted into the escalation queue as a ready-to-apply suggestion rather than committed silently:
- `STRING_FN_ON_NONSTRING` → `CAST(col AS STRING)` **or** remove the string function (a `TRIM()` on an id may be spurious — the consultant decides which)
- `MATERIALIZATION_DRIFT` → restore the source materialisation or declare the override
- `UNPINNED_SELECT_STAR` (W6a) → expand the output-projection star into the explicit source column list, in source ordinal order — deterministic given the resolved upstream schema, but which columns are intended (and whether an `EXCEPT` was deliberate) is a judgment, so it is drafted, not committed silently
- stale companion-YAML descriptions

**`decision` — no safe auto fix; escalate for a human.** The finding needs information or a judgment the loop does not have:
- `dag_registration` — register the model in the target orchestration DAG (a wave/orchestration decision)
- `deployment_type_unconfirmed` — needs the real Bronze column type we do not yet have read access to (the B-side access gap)
- `layer_relocation` — a source/dataset move that must be documented and agreed
- `parity_vs_correctness` — a product decision (accept the more-correct target behaviour, or force strict parity)
- `data_availability` / market gap — "re-verify when the connector lands"
- `governance_regression` **when no tag-map entry exists** — the masking policy is unresolved and must be mapped first

## Workflow

### Step 0 — Load config, resolve scope and pair
As `dbt-migration-pre-pr-review` Step 0. Load any `--config`/discrete overlays (in-memory, never written back, `data_safety.production_projects` never overridable). Resolve the project(s) via `specs/utils/dbt_manifest_parse.md`, the review scope, the platform pair, and the pair + engagement fix-policy tables.

### Step 1 — Ensure current findings
Locate the latest pre-PR review report for the scope. If it is missing, or older than the current translated diff (compare mtimes / the recorded `--base` and reviewed commit), run `dbt-migration-pre-pr-review` for the scope first so the loop acts on current findings.

### Step 2 — Classify
Classify every finding into `auto` / `propose` / `decision` per the table above (pair/engagement overrides applied). In `--dry-run`, print the classified plan and stop here.

### Step 3 — Auto-fix loop (capped)
Repeat up to `--max-iterations`:
1. For each model with `auto` findings, apply the pattern's deterministic fix. Prefer re-invoking `dbt-migration-generate`'s translate/auto-fix step on that model with the findings passed as guidance (so the fix flows through the same translation path and its own compile/run/equivalency loop), rather than a blind text substitution. Record each applied fix (model, pattern, `file:line`, before/after) in the model's `.diff.md`.
2. Re-run the **deterministic** gate on the affected models only — `dbt-migration-lint`, `dbt-migration-validate` (Check 5), and `dbt-migration-pre-pr-review`'s Wire-side checks. Do **not** re-run the client-review (LLM) lens here — it is non-deterministic and token-heavy; it runs once at the end (Step 4).
3. If the re-run surfaces new `auto` findings (a fix exposed another), continue. If only `propose`/`decision` findings remain, or the model is clean, stop for that model.

Stop the loop when no model has an `auto` finding left, or a full pass makes no progress (guards against an oscillating fix), or the iteration cap is hit. A model still carrying `auto` findings at the cap is escalated with reason `auto_fix_not_converged` — never silently left.

### Step 4 — Confirm with the client-review lens (once)
If an engagement client-review profile is configured (`.wire/engagement/client_review_profile.yaml`), run it once over the now-fixed diff (per `dbt-migration-pre-pr-review`'s client-review lens). Any new `auto` findings it surfaces get one more bounded apply pass (Step 3, one iteration); anything else joins the escalation queue. This keeps the expensive lens as a final confirmation, not a loop body.

### Step 5 — Escalation queue
Emit the residue for the consultant — every `propose` and `decision` finding, grouped by policy then model, each with `severity`, `file:line`, the reason it was not auto-fixed, and (for `propose`) the drafted fix ready to apply. This is the **only** manual surface the consultant sees: the mechanical volume is already gone.

### Step 6 — Report and status
Write `migration/pre_pr_review/{scope}_fix_report.md`:
- **Auto-fixed**: per model, each pattern fixed, iterations used.
- **Escalated**: the `propose`/`decision` queue.
- **Residual gate state**: the final deterministic gate result on the scope (clean / remaining findings).
Update `status.md`:
```yaml
artifacts:
  dbt_migration:
    fix:
      last_run_date: "{{TODAY}}"
      auto_fixed: <n>
      escalated_propose: <n>
      escalated_decision: <n>
      iterations_used: <n>
      residual_errors: <n>          # deterministic error-severity findings still open
```
Update the migration register for every re-fixed model (`state`, `last_migrated_commit`) as `dbt-migration-generate` Step 3.7 does.

### Step 7 — Output next step
If `residual_errors == 0` and the escalation queue is empty:
```
All pre-PR findings resolved. Re-run the review to confirm, then ship the batch:
/wire:dbt-migration-pre-pr-review $ARGUMENTS --wave <id> --format json --severity error
/wire:dbt-migration-batch-raise $ARGUMENTS --wave <id>
```
If the escalation queue is non-empty:
```
Auto-fixed N findings. M need a decision — see migration/pre_pr_review/{scope}_fix_report.md.
Resolve the escalated items, then re-run:
/wire:dbt-migration-fix $ARGUMENTS --wave <id>
```

## CI use

`--dry-run --severity error` reports what would be auto-fixed vs escalated without mutating — safe to run in CI to size the fix work. The applying run is a local/consultant step, not a CI mutation, because it edits translated models.

## Notes for the implementer

- The three-way policy is the contract; keep the pattern→policy mapping in the pair/engagement, not here, so a new pair or a client that trusts a pattern less can move it between `auto`/`propose`/`decision` without a framework change.
- Prefer routing an `auto` fix through `dbt-migration-generate`'s translate loop over a raw text edit — the fix then inherits compile/run/equivalency validation instead of being trusted blind.
- Never auto-apply a `decision` finding, and never widen `auto` to cover a pattern whose correct fix depends on the model's intent — a wrong auto-fix that passes the deterministic gate is worse than an escalation.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `fix` as action.
3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration Fix` as artifact_name, and the fix report path as file_path.
4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `fix` as action.

Execute the complete workflow as specified above.
