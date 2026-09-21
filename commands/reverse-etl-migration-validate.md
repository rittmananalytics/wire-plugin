---
description: Validate reverse ETL migration runbook completeness, plus the authored twins — primaryKey casing (error) and destination-set safety
argument-hint: <release-folder> [--wave id] [--twins-only]
---

# Validate reverse ETL migration runbook completeness, plus the authored twins — primaryKey casing (error) and destination-set safety

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
    'command': 'reverse-etl-migration-validate',
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
command: validate
artifact: reverse_etl_migration
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
  - artifact: reverse_etl_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate reverse ETL migration runbook completeness and sync coverage
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Reverse ETL Migration — Validate

## Purpose

Checks the reverse ETL migration runbook for completeness — the migration topology is recorded, every in-scope sync has migration steps, SQL translations are present for rewrite_model syncs, rebuild plans cover all Customer Studio audiences and Journeys, validation is preview-based against a frozen baseline with syncs disabled, sync-level transformation logic is reviewed, and Lightning schema provisioning is documented. Produces a PASS/FAIL report.

From v3.11.6 it also validates the **authored twins themselves**, not only the plan: the `primaryKey` casing rule (Check 13) and the destination-set safety check (Check 14). Both read the config files on the branch, so they cover twins authored by hand as well as those `reverse-etl-twin-generate` wrote.


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Flags

- `--wave <id>` — validate the wave-labelled runbook (`reverse_etl_migration_runbook_{wave_id}.md`) against the syncs `migration/migration_batching.csv` assigns to this wave, resolved identically to `reverse-etl-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Every check below reads "in-scope sync" as this resolved set instead of every `include_in_migration: true` sync.
- `--twins-only` — run Checks 13 and 14 only, against the twin configs on the branch. For the tight loop after `reverse-etl-twin-generate`, and for a pre-raise gate on a hand-authored batch, without re-validating the whole runbook.

## Prerequisites

- `migration/reverse_etl_migration_runbook.md` (or `_{wave_id}.md` under `--wave`) exists — not required under `--twins-only`
- For Checks 13 and 14: the Hightouch config repo is reachable, on the working branch, and its default branch can be read

## Validation Checks

**Check 1 — Topology recorded**
The runbook states the chosen topology (additive PR-gated repo — the default — or additive to dedicated never-shared destinations, or parallel workspace, or in-place API re-point) with a rationale. For the default additive path, it documents the repo branch, the additive target-warehouse source connection, the new decoy-bearing test syncs, and PR A. For `additive_dedicated_destination`, it documents the per-destination gate evidence (the destination exists on the target side; its id appears in no existing sync's destination set) and the single-PR cutover plan. For the parallel-workspace path, it documents the repo clone, new workspace, GitHub Sync configuration, destination re-authentication, and target-warehouse source connection.
PASS: Topology and its setup steps present. FAIL: Topology not stated or build steps missing.

**Check 2 — All in-scope syncs covered**
Every sync with `include_in_migration: true` in the audit has a section in the runbook.
PASS: All syncs present. FAIL: List missing syncs.

**Check 3 — rewrite_model syncs have SQL diffs**
Every `rewrite_model` sync includes a before/after SQL diff showing the original and translated query.
PASS: All diffs present. FAIL: List syncs missing SQL diff.

**Check 4 — Translated SQL verified on target**
Each rewrite_model sync documents the result of running the translated SQL against the target warehouse (row count, primary key check).
PASS: All verifications present. FAIL: List unverified translations.

**Check 5 — Rebuild plans documented**
Every `rebuild` sync has a documented schema mapping and step-by-step rebuild plan.
PASS: All rebuild plans present. FAIL: List missing rebuild plans.

**Check 6 — Validation is preview-based against a frozen baseline, decoy destinations only**
The validation procedure compares model outputs and audience sizes against a frozen source baseline (not live production) and uses sync previews / record inspection. Decoy-mode test syncs carry decoy destination IDs only — production destination IDs are absent. A dedicated-mode sync (`destination_mode: dedicated` under `additive_dedicated_destination`) has no decoy: it carries its confirmed dedicated destination id, which appears in no existing sync's destination set, and previews against that. It does not enable a sync against a live shared destination to validate.
PASS: Validation is preview-based against a baseline; decoy-mode syncs carry decoy IDs only; dedicated-mode syncs carry their confirmed dedicated id. FAIL: Validation relies on live runs to shared production destinations, compares against moving production, or a decoy-mode test sync carries a production destination ID.

**Check 7 — Sync-level transformation logic reviewed**
The runbook records a per-sync review of sync-level logic — field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion — separate from model-output comparison.
PASS: Sync-level review present for all in-scope syncs. FAIL: List syncs missing the review.

**Check 8 — Lightning schema provisioning documented**
If any Lightning syncs are in scope, the runbook includes the `CREATE SCHEMA` and `GRANT` statements.
PASS: Present, or no Lightning syncs. FAIL: Missing.

**Check 9 — Rollback procedures present**
The runbook includes a rollback procedure for the chosen topology and each approach type used (additive: revert PR C — disable target syncs / restore decoy IDs — and revert PR B to re-enable source syncs; dedicated: revert the single cutover PR, which re-enables the old source-warehouse syncs and removes the new dedicated-destination syncs; parallel: don't enable / disable new-workspace syncs and re-enable the source workspace; in-place: re-apply original `sourceId`).
PASS: Rollbacks present. FAIL: List missing rollbacks.

**Check 10 — Source left active until cutover, cutover is two client-merged PRs**
The runbook does not disable the source syncs (or source workspace) during the migration phase — only at cutover, via a client-merged PR, once confidence is established. For the default additive topology, cutover is two PRs merged together by the client: PR B disables every source-origin sync and PR C enables every target-origin sync (swapping decoy IDs back to production). For `additive_dedicated_destination`, cutover for dedicated-mode syncs is **one** client-merged PR that adds the new dedicated-destination syncs (authored paused) and disables the old source-warehouse syncs together; decoy-mode fallback syncs keep the two-PR cutover. RA does not enable/disable syncs directly.
PASS: Source disable / decommission appears only in the cutover/sign-off section, gated behind client-merged PRs; the two-PR cutover is documented (additive topology) or the one-PR cutover is documented (dedicated topology). FAIL: Source disable appears in the migration or validation steps, or cutover mutates the workspace outside a client-merged PR.

**Check 11 — Destination mapping present**
For the additive topologies, the runbook includes the destination mapping table (one row per in-scope sync). Decoy-mode rows: production destination ID → decoy ID of the same destination type, a scoped credential with write access to decoy targets only, and confirmation that production destination IDs are absent from the test syncs until cutover. Rows with `destination_mode: dedicated` are exempt from the decoy requirements; for each, the check is instead that both decoy columns are blank and the gate evidence is recorded (the destination exists on the target side; its id appears in no existing sync's destination set).
PASS: Mapping table present; decoy-mode rows carry decoy, credential, and absent-production-IDs statements; dedicated-mode rows carry gate evidence (or topology is parallel/in-place). FAIL: Missing for an additive topology, or a dedicated-mode row lacks gate evidence.

**Check 12 — Scope gate and approach re-verification recorded**
The runbook lists any syncs deferred because their source model is not yet built on target ("Deferred — source model not built on target"), and any syncs reclassified from `repoint` to `rewrite_model` by the approach re-verification, with the construct found.
PASS: Both lists present (empty lists stated explicitly). FAIL: Either omitted.

---

Checks 13 and 14 read the **twin config files on the branch**, not the runbook. Checks 1–12 validate the plan; these two validate what was actually authored, whether by `reverse-etl-twin-generate` or by hand. Hand-authored twins are the population every known defect of this class came from, so the checks deliberately do not care which produced them. Check 13 and every other config check apply unchanged to dedicated-mode twins; only Check 14's expectation branches, as stated there.

**Check 13 — `primaryKey` casing (`REVERSE_ETL_PRIMARY_KEY_CASE`, error severity)**

For every twin config on the branch whose source is the target warehouse, read its `primaryKey` and fail if it contains **any** upper-case character.

A BigQuery-source Hightouch sync whose `primaryKey` is not lower-case runs successfully and sends **nothing**. There is no error, no partial send, and no alert: the run is green and the destination receives zero rows. That is the whole reason this sits at error severity rather than warn — it is the failure mode indistinguishable from success, and the only signal is a destination quietly going stale.

The rule was written down at error severity in an engagement rule set and **no command evaluated it**. `dbt-migration-lint` loads engagement rules but operates on the dbt project and contains no reverse-ETL path, so it never opened the files the rule describes. A by-hand sweep of 621 authored twins later found **22 with upper-case keys**, including every sync in one open PR; all 22 would have sent nothing. Check 13 is where that rule now actually runs.

PASS: every twin's `primaryKey` is entirely lower-case. FAIL (error severity, blocks the gate): list each offending **file path and key**, with the target model's actual column casing where it can be resolved. Report the count separately from other findings — this one is worth seeing on its own line.

**Check 14 — Destination safety, as a set comparison**

Build, **once per run**, the complete set of destination ids referenced by every source-warehouse sync on the client repo's **default branch**. Then test each twin's destination id against that set. A twin whose destination is in the set fails.

The set is built once and tested against, and per-file lookups are banned, because a per-file check cannot see the whole and the wrong rule follows naturally from inspection. The first attempt at this on one engagement was a fixed list of Google Sheets destination ids — correct for 151 of 776 syncs and silently passing the other 625, which went to Google Ads customer match, DV360, Salesforce, Facebook custom audiences, Slack and Iterable. A destination type is not a safety property; membership of the live-destination set is.

No destination type appears anywhere in this check. If a check ever needs to name a destination type to decide safety, that is the bug this check exists to prevent.

A twin the mapping marks `destination_mode: dedicated` has no decoy, so the expectation branches: its destination id must equal the mapping's confirmed dedicated id **and** — the same set logic — appear in no existing sync's destination set. Set membership fails a dedicated twin exactly as it fails a decoy twin: "dedicated" is a claim this check re-verifies on every run, not a label that exempts the twin from it. A dedicated twin whose destination differs from the confirmed id is also a failure (`dedicated_id_mismatch`).

Also report, as **information** rather than a failure: any destination id shared by two or more twins. Fan-in is legitimate in some designs (several models feeding one audience) and a copy-paste mistake in others, and the check cannot tell which — so it names them and leaves the reading to a person.

PASS: no twin's destination appears in the source-warehouse destination set. FAIL (error severity): list each twin, its destination id, and the source-warehouse sync that also writes there. If the default branch cannot be read, the check is `unverified`, never `pass` — an unreadable branch means the set is unknown, and an unknown set cannot clear a twin.

### Write validation report

Append a `## Validation` section to `migration/reverse_etl_migration_runbook.md` following the standard format.

Update status:
```yaml
artifacts:
  reverse_etl_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    twins_checked: N                     # Checks 13/14 scope
    primary_key_case_failures: N         # REVERSE_ETL_PRIMARY_KEY_CASE, error severity
    production_destination_failures: N   # twin pointing into the live destination set
    dedicated_id_mismatches: N           # dedicated-mode twin whose destination differs from the mapping's confirmed id
    shared_destination_twins: N          # information only, not a failure
    destination_set_source: default_branch | unverified
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```

If PASS: `/wire:reverse-etl-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact_id, `Reverse ETL Migration` as artifact_name, and the `file` value from `artifacts.reverse_etl_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_migration` as artifact, `validate` as action.

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
