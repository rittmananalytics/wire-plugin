---
description: Experimental: Capture and catalog Looker Studio reports: definitions, layout, data sources, calculated fields, chart data and BigQuery job history, each component and data source classified
argument-hint: <release-folder>
---

# Experimental: Capture and catalog Looker Studio reports: definitions, layout, data sources, calculated fields, chart data and BigQuery job history, each component and data source classified

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
    'command': 'looker-studio-audit-generate',
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
artifact: looker_studio_audit
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
mcp_contextual:
  - bigquery
produces:
  - type: document
    path: "audit/looker_studio_audit.md"
    description: "Looker Studio estate audit: reports, pages, components, data sources, blends and calculated fields, each with a translation class, plus coverage gaps and access requests"
  - type: report
    path: "audit/looker_studio/content_catalog.csv"
    description: "One row per report, page, component and blend with translation_class, grid position and usage"
  - type: report
    path: "audit/looker_studio/datasource_catalog.csv"
    description: "One row per data source with connector, location, access and translation_class"
  - type: report
    path: "audit/looker_studio/reports/<report_id>/report.json"
    description: "Extracted report definition per report (looker_studio_extract.py)"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Capture and catalog the Looker Studio estate (report definitions, layout, data sources, calculated fields, chart data and BigQuery job history) and classify every component and data source for the move to Omni"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: looker_studio_audit` and `artifact_file_path: audit/looker_studio_audit.md` before proceeding.

---

# Looker Studio Audit: Generate

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catalogs the client's Looker Studio (formerly Data Studio) reports so the metric catalogue and the migration plan can decide what moves to Omni and how. Looker Studio has no supported API for report definitions, so the audit reads them from the editor itself through three evidence routes:

| Route | What it gives | Source | Access needed |
|---|---|---|---|
| B | Report definition: pages, layout, components, fields, chart-level formulas, filters, blends, parameters; each data source's connection and calculated fields | Looker Studio editor calls (`getReport`, `getSchema`, `getBlockDatasource`), recorded in a headed Chrome session | View on each report; Edit on each data source |
| C | Each chart's query specification and the values it displayed, for every connector, plus the BigQuery job link for BigQuery charts | Looker Studio chart data calls (`batchedDataV2`), recorded on the same page visits | View on each report |
| A | The SQL each BigQuery chart ran, and usage over the last 180 days | `INFORMATION_SCHEMA.JOBS` in the billing project, jobs labelled `looker_studio_report_id` | BigQuery Resource Viewer on the billing project |

Routes B and C use undocumented endpoints that Google can change without notice. Route A is supported and is the fallback for SQL and usage. Every script is deterministic and makes no AI call; the agent runs them, reads their output and writes the audit report. It never hand-writes what a script emits.

This is a **BI-tool** audit. It does not change the warehouse, and it changes nothing in Looker Studio: the capture script navigates only and never clicks, types or saves.

## Prerequisites

- Release folder with `project_type: bi_migration` and `bi_pair: looker_studio_to_omni` in `status.md`
- `bi_migration.looker_studio_reports`: the report URLs in scope, one per line
- `bi_migration.looker_studio_namespace`: a short client slug used in object identities (`lookerstudio:<namespace>:...`)
- `bi_migration.looker_studio_capture_consent`: who approved automated read-only access to the reports, and when. Required before the first capture. Routes B and C use the consultant's own Google sign-in to read the editor's internal calls; the client must agree to that in writing
- Python 3.10 or later with Playwright (`python3 -m pip install playwright`) and Google Chrome, on the consultant's machine
- Access as listed above. Without Edit on a data source, its connection and formulas are not readable; the audit records the gap and continues

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The reports listed in `bi_migration.looker_studio_reports`
- `wire/bi_pairs/looker_studio_to_omni/translation_guide.md` (classes and normalisation rules)
- `wire/bi_pairs/looker_studio_to_omni/feature_detection.md` (what each response field means)
- `wire/bi_pairs/looker_studio_to_omni/tooling.md` (setup, access requests, data handling)
- `.wire/engagement/bi_pair_overrides/looker_studio_to_omni/` (optional engagement overrides)

## Workflow

### Step 1: Locate the release and check the gates

Confirm `project_type: bi_migration` and `bi_pair: looker_studio_to_omni`. Read the report list and the namespace. If `looker_studio_capture_consent` is empty, stop and output:

```
Looker Studio capture needs recorded client consent for automated, read-only access
to the reports with your own Google account. Record it in status.md as
bi_migration.looker_studio_capture_consent (approved_by, date), then re-run:
/wire:looker-studio-audit-generate $ARGUMENTS
```

Make sure `.wire/releases/*/audit/looker_studio/captures/` is in the repository's `.gitignore`; add the line if it is missing. Captures hold chart values and can hold credentials stored in connector settings, so they are never committed. The capture script refuses to write into a tracked folder.

If `audit/looker_studio_audit.md` already exists, ask whether to re-generate (overwrite) or update (re-capture only the reports named).

### Step 2: Capture (Routes B and C)

Run, from the repository root:

```bash
python3 <plugin-root>/scripts/looker_studio_capture.py \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/captures \
  --screenshots <report_url> [<report_url> ...]
```

The first run opens Chrome on a separate profile under `~/.wire/looker_studio/` and waits up to 5 minutes for the consultant to sign in. Tell the consultant to sign in with the account that has the access listed above, and that the window will move between pages and data sources on its own. Later runs reuse the profile.

The script visits every page (hidden pages included) so every data source's field list is requested, then opens each data source's editor. It writes `meta.json` per report with the capture time, the Looker Studio app version, the revision read (published or draft), the pages that failed to open and the data sources visited. A report that returns no definition is reported as `FAILED` and the script exits non-zero; record the failure and the likely cause (no access, wrong account) and continue with the others.

### Step 3: Extract each report

```bash
python3 <plugin-root>/scripts/looker_studio_extract.py \
  --capture .wire/releases/$ARGUMENTS/audit/looker_studio/captures/<report_id> \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>
```

Writes `report.json` and `report.md`. The extractor redacts connector settings whose names look like secrets (password, token, API key) and keeps every unconfirmed enum code as a raw number. If it stops with `ERROR`, the capture's structure is not one it knows (an endpoint changed): record the app version from `meta.json`, stop, and raise it as a blocking issue. Do not hand-edit `report.json`.

### Step 4: Record chart data (Route C)

```bash
python3 <plugin-root>/scripts/looker_studio_parity.py \
  --capture .wire/releases/$ARGUMENTS/audit/looker_studio/captures/<report_id> \
  --report .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json \
  --out .wire/releases/$ARGUMENTS/migration/parity/looker_studio/<report_id> \
  --namespace <looker_studio_namespace>
```

Writes one folder per chart result (`source.csv`, optional `compare.csv` and `totals.csv`, `contract.yaml`) and `recordings.json`. These are the expected results `bi-equivalency-validate` compares Omni against. They hold aggregated values as users saw them on the dashboards; if the engagement's data handling rules do not allow those in the repository, add the folder to `.gitignore` and record that in `status.md` as `bi_migration.chart_recordings_tracked: false`.

### Step 5: Read BigQuery job history (Route A, when access allows)

`recordings.json` names the billing project and location of every BigQuery chart's job. For each distinct pair:

```bash
python3 <plugin-root>/scripts/looker_studio_jobs.py fetch --billing-project <project> --location <location> \
  --report-id <report_id> --out .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>
python3 <plugin-root>/scripts/looker_studio_jobs.py link \
  --jobs .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>/jobs_raw.json \
  --report .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>
```

If `fetch` fails for lack of `bigquery.jobs.listAll`, record the billing project under "Access requests" and continue: usage is then `unknown` for that report. Never infer usage from anything else.

### Step 6: Build the catalogs

```bash
python3 <plugin-root>/scripts/looker_studio_catalog.py \
  --reports .wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json \
  --chart-sql .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/*/chart_sql.json \
  --namespace <looker_studio_namespace> \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio
```

Writes `content_catalog.csv` and `datasource_catalog.csv`. The classes are the rule in `translation_guide.md`, applied by the script:

| Data source class | Meaning |
|---|---|
| `map` | BigQuery table or view; the Omni model can read the same table |
| `assisted` | BigQuery custom SQL; becomes a dbt model or an Omni SQL view |
| `pipeline` | Community connector, Google product connector or Sheets; no known warehouse copy, so the plan raises a pipeline task |
| `blocked` | Definition not read (Edit refused, or not captured) |

| Component class | Meaning |
|---|---|
| `mechanical` | Supported chart type, no chart-level formula, no comparison period, not on a blend |
| `assisted` | Needs a decision: chart-level formula, comparison period, blend, combo or bullet chart, or a control |
| `redesign` | No Omni equivalent (community visualisations and other types) |
| `drop` | Decorative shapes and images; text boxes (recreated by hand) |

### Step 7: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`

Include:
- Capture record: per report, the capture time, app version, revision read (published or draft, and whether unpublished changes exist), pages that failed to open
- Summary table: reports, pages (visible and hidden), components by kind, report-level components, blends, parameters, filters, data sources by connector, data-source and chart-level calculated fields
- Classification breakdown: components and data sources by class
- Report families: reports whose visible page names match are copies of one template (for example one per client); list each family. The plan merges a family into one Omni template with filters
- Data source register: every data source with connector, location (project, dataset, table, or the connector and its non-secret settings), class, and which reports and blends use it
- Pipeline needs: every `pipeline` data source, with what would have to land in the warehouse
- Blends: inputs, join type (named only where confirmed) and keys
- Usage: from Route A, components and data sources by last run; `unknown` where Route A did not run
- Coverage gaps: refused and uncaptured data sources, data sources without a field list, pages that failed, charts with no recording
- Access requests: a ready-to-send list naming each missing permission and the object it is for (Edit on data source X; BigQuery Resource Viewer on billing project Y)

### Step 8: Update status

```yaml
artifacts:
  looker_studio_audit:
    generate: complete
    file: audit/looker_studio_audit.md
    generated_date: "{{TODAY}}"
    report_count: N
    page_count: N
    hidden_page_count: N
    component_count: N
    datasource_count: N
    datasources_blocked: N
    datasources_pipeline: N
    chart_recordings: N
    usage_source: bigquery_jobs | partial | unavailable
    app_versions: [<from meta.json>]
    generated_files:
      - audit/looker_studio_audit.md
      - audit/looker_studio/content_catalog.csv
      - audit/looker_studio/datasource_catalog.csv
```

### Step 9: Output summary

Print the totals, the class breakdown, the access requests, and the next command:

```
/wire:looker-studio-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/content_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/datasource_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json` and `report.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>/chart_sql.json` (when Route A ran)
- `.wire/releases/$ARGUMENTS/migration/parity/looker_studio/<report_id>/` (Route C recordings)
- `.wire/releases/$ARGUMENTS/audit/looker_studio/captures/` (git-ignored, never committed)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact_id, `Looker Studio Audit` as artifact_name, and the `file` value from `artifacts.looker_studio_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_studio_audit` as artifact, `generate` as action.

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

`/wire-usage` prints the session's runs with their duration, tokens and cost.
The plugin's `metrics` option, or `WIRE_METRICS=false`, turns the backfill
off. On runtimes without the mod (Gemini CLI), the metric cells keep the
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
