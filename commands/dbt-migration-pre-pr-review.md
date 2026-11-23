---
description: "Pre-submission faithfulness review over a translated diff — deploy-time defect class static parse/lint cannot catch, before a PR is opened"
argument-hint: "<release-folder> [--batch N | --wave id | --model name] [--base ref] [--severity LEVEL] [--format FORMAT]"
---

# Pre-submission faithfulness review over a translated diff — deploy-time defect class static parse/lint cannot catch, before a PR is opened

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
    'command': 'dbt-migration-pre-pr-review',
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
artifact: dbt_migration
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
  - artifact: dbt_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Pre-submission faithfulness review over a translated dbt diff — surfaces the deploy-time defect class that static parse/lint cannot catch, before a PR is opened
argument-hint: <release-folder> [--batch N | --wave id | --model name] [--base ref] [--severity LEVEL] [--format FORMAT]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Migration — Pre-PR Faithfulness Review

## Purpose

A structured faithfulness review over a **translated diff**, run **before** a PR is opened against the client repo. It targets the exact defect class that a `dbt parse`/`dbt run` on one default code path, plus static lint, cannot catch — the defects that on a live engagement were repeatedly sent back in the client's PR review because they only fail at deploy time, not in the validation warehouse.

It does not re-derive the checks from scratch. It composes the surfaces the widened gate already defines — Check 5 all-code-path build (W2), the deployment type pre-flight (W3), and the governance/masking equivalence check (W4) — plus the pair's edge-case runtime-failure patterns, into one reviewable findings list resolved **locally** instead of in the client's PR queue. Everything is driven by the active platform pair, so it generalises across every migration.

## Relationship to the other migration gates

| | catches | when it runs |
|---|---|---|
| `dbt-migration-lint` | valid target SQL that diverges silently (arg-order, NULL-handling, timezone, hash) — static, no warehouse | after generate, before Tier 3 |
| `dbt-migration-validate` | compile completeness + Check 5 all-code-path build across every target/incremental/test surface | after generate |
| `equivalency-validate` | live row/schema/value/governance equivalence on both warehouses | during parallel run |
| **`dbt-migration-pre-pr-review` (this)** | a **synthesis** over the diff of the deploy-time defect class: unrendered branches, unported tests, edge-case runtime failures, deployment type mismatch, dropped governance | **before the PR is opened** |

This is the last gate before the diff leaves for the client. It re-reads the other gates' results where they exist and re-checks the diff directly where they don't — it never assumes a green lint or a passing validate means the diff is faithful.

## Flags

- `--batch N` — review topological batch N only (`dbt_audit.batch_number`).
- `--wave <id>` — review execution wave `<id>` (the `migration_batching.csv` scheme). Accepts zero-padded (`B01`) or bare (`1`) forms, normalised identically to `dbt-migration-generate`'s `--wave`. Wave-id form and normalisation are the shared contract in `specs/utils/wave_resolution.md` (normative; accepts `2`, `B02`, `b2`, or the `W02` display form). `--batch` and `--wave` read different numbering schemes — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.`
- `--model <name>` — review a single translated model.
- `--base <ref>` — the git ref the translated diff is taken against (default: the branch point / `main`). The review scopes to files changed in the diff, so a re-review after a fix only re-checks what moved.
- `--severity error|warn|info` — minimum severity to report (default: `info`).
- `--format md|json` — report format (default: `md`; `json` for CI gating).
- `--config <path>` / `--tag-map <path>` / `--target-dataset <name>` / `--dbt-project-path <path>` — per-run config overlays, mirroring `dbt-migration-generate`'s **Config overlay** section exactly. Orthogonal to scope.

`--batch`/`--wave`/`--model` resolve scope exactly as `dbt-migration-validate` and `dbt-migration-lint` resolve theirs (Step 0w / Step 1w); the resolved model set is the review scope.

## Inputs

- The translated diff: files under `migration/dbt/` changed against `--base` (SQL + companion YAML).
- Active platform pair (resolved from `status.md` `source_platform`/`target_platform`, or the `--config` overlay):
  - `translation_guide.md` — the **"Deployment type-divergence patterns"**, **"Edge-case runtime-failure patterns"**, and **"Column governance / masking mechanisms"** sections.
  - `translation_reference.md` §11 gotcha checklist and the `dbt-migration-lint` rule catalogue.
- Where they exist, the other gates' results: `dbt-migration-validate`'s Check 5 coverage report, the W3 deployment type pre-flight result (`specs/utils/deployment_type_preflight.md`), and `equivalency-validate`'s governance check. A gate that has not run is re-checked directly against the diff, not assumed clean.

## Check catalogue

Run every check over each in-scope model in the diff. Each finding records `severity`, `file:line`, the offending construct, the fix hint, and the source (pair section / gate) it came from.

**Check 1 — Unrendered dev/incremental branches (W2).** Flag `{% if target.name == '...' %}` branches and `{% if is_incremental() %}` predicates in the diff that a single default-target full-refresh build never renders. If `dbt-migration-validate`'s Check 5 coverage report shows the model was compiled under every target and built twice, cite it as covered; otherwise flag it `error` — an unrendered branch is the single most common way a defect reaches the client PR. Fix hint: run `dbt-migration-validate` (Check 5) so every target and the incremental second run are exercised.

**Check 2 — Unported tests.** Flag generic/singular tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments in the diff's companion YAML that still contain source-dialect SQL, reference an unresolved `macro`/`var`, or a test macro not present in the target project. `dbt parse` and `dbt run` pass these; only `dbt build` runs them. Severity `error`. Fix hint: translate the test SQL and confirm `dbt build` executes it (Check 5c).

**Check 3 — Edge-case runtime failures.** Apply the active pair's **"Edge-case runtime-failure patterns"** to the diff — for SF→BQ: `CAST_BLANK_STRING_NUMERIC` (uncast blank-string→numeric), `UNGUARDED_JSON_PARSE` (bare `PARSE_JSON` with no `SAFE.`), `UNANCHORED_REGEX` (`REGEXP_CONTAINS` from an anchored `REGEXP_LIKE`/`RLIKE`), `DIV0_NULL_COERCION` (a `DIV0`/`DIV0NULL` emitted as bare `SAFE_DIVIDE`, `IFNULL(SAFE_DIVIDE(…),0)`, or `COALESCE(SAFE_DIVIDE(…),0)` instead of the faithful `IF(...)` form). These compile and pass a sample that lacks a triggering row, then fail on the first blank/malformed/boundary row at deploy. The specific patterns are sourced from the pair — do not hardcode a dialect. Severity per the pair (default `error` for a hard runtime failure, `warn` for a silent divergence — except where the pair marks a silent divergence `error`, e.g. `DIV0_NULL_COERCION`, because it corrupts NULL-sensitive checksum/DQ guards undetectably). Fix hint: the pair's fix (`SAFE_CAST`, `SAFE.PARSE_JSON`, `^(?:...)$` anchoring, the `IF(...)` divide form).

**Check 4 — Deployment-warehouse type mismatch (W3).** Run (or read, if already run) `specs/utils/deployment_type_preflight.md` over the diff's models. Flag every firing deployment type-divergence pattern (a `TIMESTAMP()` wrap on an already-typed column, a JSON function on a STRING/JSON-mismatched column, an implicit cross-type join coercion) and surface the explicit warning when the validation warehouse differs from deployment. Severity `error` for a firing pattern, `warn` for a validation≠deployment warehouse with no firing pattern. Fix hint: the pair's fix for the pattern.

**Check 5 — Dropped column governance metadata (W4).** Compare each diffed model's column-level protection at target against the source masking policy / policy tag for the same column, per the pair's **"Column governance / masking mechanisms"** section. Flag every column protected at source but unprotected at target (`error`, `governance_regression`), and every `MANUAL REVIEW REQUIRED` masking flag `dbt-migration-generate` left unresolved. Fix hint: author the target `policy_tags` / masking, or resolve the tag map entry.

**Check 6 — Unpinned `SELECT *` and column-order drift (W6).** Two parts, both driven by the pair:
- **`SELECT *` (W6a, static diff check).** Flag any changed model whose **final/output** projection is an unpinned star — `SELECT *`, `SELECT <alias>.*`, or `SELECT * EXCEPT(...)` — using the same paren-depth scan as `dbt-migration-lint`'s `UNPINNED_SELECT_STAR` (import/staging CTEs may `SELECT *` internally; only the depth-0 output projection is flagged). If `dbt-migration-lint` has run over the scope, cite its `UNPINNED_SELECT_STAR` findings rather than re-detecting. Severity `error`. Fix hint: expand to the explicit source column list in source ordinal order.
- **Column order (W6b, from the schema-check result).** Read the schema-equivalence check's column-order result (`equivalency-validate` check type 2 / `dbt-migration-generate` Check B). Surface every `column_order_drift` for a diffed model — the target column sequence does not match source ordinal order plus the pair's allow-listed tail columns — unless the model carries a `column_order_waived` waiver. Severity `error`. Where the schema check has not run for the scope, note it as a coverage gap (not "clean"). Fix hint: reorder the output projection to source ordinal order, or record a `column_order_waived` reason.

## Workflow

### Step 0 — Load config overlay, resolve project(s) and scope
Load any `--config`/`--tag-map`/`--target-dataset`/`--dbt-project-path` overlay exactly as `dbt-migration-generate` Step 0c describes (in-memory, never written back, `data_safety.production_projects` never overridable). Resolve the dbt project(s) via `specs/utils/dbt_manifest_parse.md` Steps 1–2. Resolve the review scope from `--batch`/`--wave`/`--model` (mirroring `dbt-migration-lint` Step 1/1w). Resolve the platform pair and load its three consumed sections plus the lint catalogue.

### Step 1 — Compute the diff
Diff `migration/dbt/` against `--base`. The review scope is the intersection of the changed files and the resolved model set — a re-review after a fix re-checks only what moved.

### Step 2 — Run the check catalogue
Run Checks 1–6 over every in-scope model. Where a downstream gate already produced a result (Check 5 coverage report, W3 pre-flight, W4 governance, the `dbt-migration-lint` `UNPINNED_SELECT_STAR` findings and the schema check's `column_order_drift` result for Check 6), read it rather than re-running; where it hasn't run, check the diff directly. Record each finding in the shape above.

### Step 3 — Write the findings report
Write `migration/pre_pr_review/batch_N_pre_pr_review.md` (or `wave_{id}_...`, or `model_{name}_...`), and `.json` if `--format json`. Structure:
- **Header**: pair, direction, scope, `--base` ref, model count, and the line "resolve these locally — do not open the PR until every `error` is cleared. The PR itself is raised by `/wire:dbt-migration-batch-raise`."
- **Summary**: counts by severity; models clean vs flagged.
- **Findings**: grouped by model, ordered by severity. Each finding shows `file:line`, the construct, the severity, the fix hint, and its source (pair section / gate).
- **Coverage gaps**: any check that could not run (no target profile for W2, no deployment warehouse for W3, no tag map for W4, no schema-check result for the W6b column-order surface) — a gap is "not checked", never "clean".

### Step 4 — Update status
```yaml
artifacts:
  dbt_migration:
    pre_pr_review: pass | fail
    pre_pr_reviewed_date: "{{TODAY}}"
    batch_N_pre_pr_review: pass | fail
    batch_N_pre_pr_findings:
      error: <n>
      warn: <n>
      info: <n>
    wave_pre_pr_review:            # set only when run with --wave, keyed by wave id
      B01: pass | fail
```
`fail` when any `error`-severity finding remains unresolved (warn/info do not fail the gate by default; `--severity` can tighten this for CI).

## CI gating

With `--format json --severity error`, the command exits non-zero when any `error` finding exists, so it drops into a pre-PR check on the migration repo — the intent is to stop a translated diff reaching the client's PR queue while it still carries a deploy-time defect the client would otherwise catch. Document any finding deliberately suppressed for a batch in the batch summary, the same way `-- MANUAL REVIEW` flags are tracked — silent suppression reads as "clean" when it isn't.

## Notes for the implementer

- This command is **read-only** over the translated diff. It never edits models. To act on the findings automatically, run `dbt-migration-fix` — it auto-applies the deterministic fixes, re-runs the gate, and escalates only the findings that need a human decision. (Fixes can also flow back through `dbt-migration-generate` or a hand edit; then re-run this review.)
- The check catalogue is a synthesis, not a re-implementation — Checks 1/4/5 defer to the W2/W3/W4 gates' own logic and results. Keep the pattern lists in the pair, never here, so a new pair inherits the review automatically.
- Position: run after `dbt-migration-validate` and `dbt-migration-lint` pass and before `dbt-migration-review` opens the batch for sign-off — it is the automated faithfulness gate the human review then reads. The raise itself is `dbt-migration-batch-raise`'s job: it consumes this review's result as an eligibility gate and supersedes the old prose ending here ("open the PR").

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `pre_pr_review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration Pre-PR Review` as artifact_name, and the report `file` path as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `pre_pr_review` as action.

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
| YYYY-MM-DD HH:MMZ | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time **in UTC**, written `YYYY-MM-DD HH:MMZ`
  (24-hour, a literal `Z` after the minutes, no `T`, no seconds, no offset):
  `2026-10-17 14:05Z`. Get it with `date -u +"%Y-%m-%d %H:%MZ"` (or
  `python3 <wire>/scripts/log_time.py now`), never from the local clock. The
  same form is used for every time written into a log row, including an
  original time quoted in Detail (`ran 2026-10-17 14:28Z`), in the release log
  and in ticket run logs. From Wire 4.4.3; see "Time zones" below.
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
  - `blocked` — `specs/utils/precondition_gate.md` Step 2 stopped the command on an unmet blocking precondition and the consultant chose not to override; Detail is `gate: <dep_artifact>.<dep_action> required <outcome>, was <actual>` and the Command cell carries the command in full. The Wire mod's commands band shows these rows as `Not run: <command>, gate: <...>`
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

  When a persona is set for the run (`specs/utils/personas.md`), add
  ` as <persona>` to the value: `typed as delivery-manager`,
  `orchestrator [a1b2c3] as delivery-manager`. No persona: the value alone.

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
| YYYY-MM-DD HH:MMZ | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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
   Rows are compared as "Time zones" below says.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Update `status.md` keys in place, then check the file.** When a command
   records a result in `status.md`, it changes the existing key; it never adds
   a second copy of a key in the same block. A value worth keeping (an earlier
   approval date) moves to a `prior_<key>` field or stays in this log, never
   in a duplicate key, because YAML keeps only the last copy and ignores the
   first without an error (wire-plugin#2). The same applies to anyone editing
   the file by hand or by script. After writing `status.md` and before
   appending the row, run `python3 <wire>/scripts/status_file.py check
   .wire/releases/<release_folder>`. If it reports a problem in a line this
   command just wrote, fix it now. If the problem was there before, leave it,
   say so in the output and point to `/wire:status-sync <release_folder>`
   (`specs/utils/status_sync.md` Step 1b). In orchestrated mode the
   orchestrating session runs the check when it writes `status.md` from a
   lane's state file.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.
9. **One time zone.** Every Timestamp, and every time quoted in Detail, is UTC
   with the `Z` suffix. A row is never written in local time, and a time
   with no zone is never converted by guessing the zone it was written in.
10. **Review rows say what they are.** A review result recorded from a merged
    pull request, not from a review command run, follows
    `specs/utils/status_sync.md` Step 4g: By is the approver, Detail says
    `recorded from PR #<n> approved by <name>`, and Session is what ran the
    roll-up.

## Time zones

From Wire 4.4.3 every Timestamp is UTC, `YYYY-MM-DD HH:MMZ`. Before that the
rule said local time, and logs mixed UTC rows with rows in the writer's local
time, so a ticket could appear to close before it opened.

- **Writing.** `date -u +"%Y-%m-%d %H:%MZ"`. A row's time is the UTC time the
  command finished. A roll-up row's Timestamp is the UTC time of the roll-up.
- **Rows with no zone.** `YYYY-MM-DD HH:MM` without `Z` is a row written
  before 4.4.3. It stays valid, is never rewritten, and is read as "zone
  unknown": it may be in any zone from UTC-12 to UTC+14.
- **Anything else** (`2026-10-17T14:05Z`, `14:05+01:00`, `14:05 BST`) is
  unparseable and reported as such.
- **Ordering** (rule 6, `/wire:status-sync` Step 4f). Two rows in the same
  form compare on the values written. A UTC row next to a zone-unknown row is
  out of order only when no zone in that range puts the pair in order; when
  some zones do and some do not, the pair is `zone_unknown`, listed for
  information and not a defect. A log that changes from local time to UTC in
  British summer time (`15:05` then `14:10Z`) is therefore not flagged.
- **Never earlier than the last row.** A roll-up stamps its rows with the
  later of now and the last row's time when the last row is UTC. A last row
  with no zone is not copied into a new row.

The rule is implemented in `<wire>/scripts/log_time.py` (`now`,
`check <execution_log.md>`), used by `ticket_delivery.py merge-log` and tested
by `wire/tests/core/validate_execution_log_order.py`. The Wire mod's metrics
backfill (below) reads both forms: it matches a row on its command and date,
with a day's slack, not on its time.

## Metrics Backfill (Claude Code)

From 4.1.0 the Wire mod (`hooks/register.ts`, a function hook in the Claude
Code plugin) fills the metric cells. It replaces the `Stop` settings hook
(`hooks/wire-metrics.sh` and `wire_metrics.py`), which re-read the session
transcript after each turn.

1. Each Wire command opens a run when it starts: a typed `/wire:` command, or
   a Wire command called through the Skill tool by the orchestrating session,
   a lane or Autopilot.
2. Every model request adds its measured usage to the run open in its own
   loop (the main session, or one subagent). Counts come only from the usage
   the API reports, never estimates.
3. When that loop's turn ends, the run closes and the mod fills the
   Duration (only if still `n/a`), Tokens and Cost cells of the newest row
   whose Command cell names the command, whose Tokens cell is still `n/a`, and
   which is dated no earlier than the day before the run started (a date, not
   a time, because commands write the row's time themselves and it is often
   rough). It
   never touches another cell or row, and never widens a row without the
   metric columns.
4. A row written after the run closed (an orchestrating session writing a
   lane's row once the lane reports) is filled when that write happens.
5. Cost comes from the mod's price table; an unrecognised model leaves Cost
   at `n/a` with Tokens filled.

`/wire-usage` prints the session's runs with their duration, tokens and cost;
`/wire-ran` prints each run in full with its result (4.5.0), as the band above
the prompt draws it. The plugin's `metrics` option, or `WIRE_METRICS=false`,
turns the backfill off. On runtimes without the mod (Gemini CLI), the metric cells keep the
values the workflow wrote.

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
| 2026-02-22 14:30Z | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35Z | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40Z | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12Z | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00Z | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15Z | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30Z | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00Z | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15Z | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00Z | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30Z | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45Z | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00Z | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05Z | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20Z | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
| 2026-02-25 11:02Z | /wire:data_model-generate | complete | ticket CUS-199, ran 2026-02-25 09:40Z: 4 tables | Jane Smith | orchestrator [d4e5f6] | 9m 12s | 201544 | $1.51 |
| 2026-02-25 11:02Z | /wire:data_model-review | approved | recorded from PR #64 approved by John Doe (ticket CUS-199, approved 2026-02-25 10:55Z) | John Doe | orchestrator [d4e5f6] | n/a | n/a | n/a |
```

The last two rows are a ticket roll-up (`specs/utils/status_sync.md` Step 4g)
run by an orchestrating session: the first was rolled up from the ticket's run
log; the second records a review result from the ticket's merged pull request,
so By is the approver, Session is the session that ran the roll-up, and the
metric cells stay `n/a` because no review command ran.
