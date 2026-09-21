---
description: Design dbt model structure
argument-hint: <project-folder>
---

# Design dbt model structure

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
    'command': 'data_model-generate',
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
artifact: data_model
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate dbt data model specification and physical ERD
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Model Generate Command

Follow `specs/utils/data_designer_delegate.md` before executing the workflow below.

## Purpose

Generate the full dbt-layer data model specification — covering staging, integration, and warehouse layers — together with a **Physical Entity-Relationship Diagram (ERD)** as a Mermaid erDiagram showing every model with its columns, primary keys, foreign keys, and relationships. This is the primary input for dbt code generation.

The data model specification narrows the LLM's generation space for the dbt phase: every model name, column name, join path, surrogate key composition, and test definition is determined here, not during code generation.

## Usage

```bash
/wire:data_model-generate YYYYMMDD_project_name
```

## Prerequisites

**Default** (all project types except `dashboard_first`):
- `requirements`: `review: approved`
- `conceptual_model`: `review: approved` — provides the entity framework
- `pipeline_design`: `review: approved` — provides source table names and replication details

**Dashboard-first** (`dashboard_first` project type):
- `requirements`: `review: approved`
- `viz_catalog`: `generate: complete` — provides the measures, dimensions, and dashboard structure

## Workflow

### Step 1: Verify Prerequisites and Read Inputs

1. Read `.wire/<project_id>/status.md`
2. Read `project_type` from frontmatter
3. **If `dashboard_first`**:
   - Verify `requirements.review` is `approved` and `viz_catalog.generate` is `complete`
   - Read the following in order:
     - `requirements/requirements_specification.md`
     - `design/visualization_catalog.md` (measures, dimensions, dashboard structure)
     - `design/dashboard_spec.md` (dashboard purpose and layout)
   - Also read `artifacts/` for SOW and domain context
4. **Otherwise (default)**:
   - Verify all three default prerequisites are met. For each that is not:
     ```
     Error: [artifact] must be approved before data model generation.
     Run: /wire:[artifact]:review <project_id>
     ```
   - Read the following in order:
     - `requirements/requirements_specification.md`
     - `design/conceptual_model.md` (entities, relationships)
     - `design/pipeline_architecture.md` (source tables, staging model names)
     - `design/logical_model.md` **if it exists** (keys, cardinality, identity
       resolution, normalisation and attribution decisions). `logical_model` is
       optional, so its absence is normal and not an error. When it is present it
       is authoritative for the decisions it records, and this command uses them
       rather than re-deriving them: the primary key of an entity and why, the
       cardinality and the foreign keys that carry it, and where normalisation
       was deliberately traded away. Re-deriving them here is the duplication
       `logical_model` exists to remove, and the two answers will not always
       agree.
4. Use Glob to find all files in `.wire/<project_id>/artifacts/**/*`
5. Read any source schema examples, existing dbt models, or SQL files in `artifacts/`

### Step 1.5: Check for a Canonical Vertical Match (Automatic, Advisory)

This step runs automatically on every engagement — there's no opt-in flag to set. It has three possible outcomes: a proposal to the practitioner, a silent skip, or (if declined) no effect on anything downstream. It can never fail the command and never blocks Step 2.

1. **Resolve the registry location, dev mode first:**
   - Check for `wire/data-model-registry/` in the repo root (present only when developing Wire itself, from `wire/scripts/sync-data-model-registry.sh`).
   - If not found, check `~/.wire/data-model-registry/` (present only if this consultant has personally run `/wire:utils-data-model-registry-setup` and has access to the private `wire-data-model-registry` repo).
   - If neither exists, **skip silently to Step 2** — no message, no note in the output spec. Most engagements and most consultants will land here; this is expected, not a degraded path.

2. **Resolve the vertical, in two tiers — don't stop at "no exact match":**
   - Read `.wire/engagement/context.md`. If `data_model_registry.vertical` is already set to a non-null value (a consultant can set this by hand at any time), use it directly as a **confident match** and skip to Step 3.
   - Otherwise, list `<registry_root>/verticals/` to see what's actually there right now — **do not assume a fixed set of names**. The registry evolves independently of this spec and of Wire's own release cycle; it started with six verticals, has since had more added, and will likely keep growing. Treat whatever's in that directory at the moment this command runs as the real, current list, and read each one's own schema descriptions (each vertical's schemas sit at `<registry_root>/verticals/<vertical>/schemas/<schema>/<schema>.yml`, one directory per schema, holding the YAML alongside a `<schema>.dbml` ERD, so the YAML is not directly in `schemas/`) to judge fit rather than string-matching the industry name:
     - **Confident match**: the client's actual business is recognizably an instance of one of the verticals actually present — e.g. a retail e-commerce client against `retail`, or a B2B SaaS client against a `saas` vertical, if one exists in the registry at the time.
     - **Adjacent match**: no vertical currently in the registry is a confident fit, but one vertical's entity *shape* is still structurally close to what this client needs, even though that vertical was built from a different kind of business. A gap like "no vertical for this specific industry yet" is not a reason to propose nothing — e.g. if no vertical matches a B2B SaaS client confidently, `subscription-commerce`'s subscriber/subscription/subscription_event/monthly_retention/subscription_revenue entities may still be a structurally close analogue for an MRR/NRR model, even though that vertical's content was built from a different kind of subscription business. Propose an adjacent match explicitly labeled as approximate — don't silently withhold it just because it isn't a clean industry match.
   - If neither a confident nor an adjacent vertical exists, proceed to Step 3 with no vertical candidate at all — this remains a normal, common outcome, not a failure.

3. **Independently check cross-vertical patterns — this runs regardless of what Step 2 found, and gets the same confident/adjacent tiering Step 2 uses.** Cross-vertical relevance is not conditional on having a vertical match; a client can need `crm_identity_resolution` (reconciling contacts/accounts across two or more CRM/marketing tools — a routine problem for any B2B business, `saas` vertical or not) whether or not any vertical matched at all.
   - Read `<registry_root>/cross-vertical/schemas/*/*.yml` and check each one against this client's actual sources, entities, and requirements — e.g. `crm_identity_resolution` for multi-system contact/account reconciliation, `ga4_ecommerce` if the client uses GA4, `multi_touch_attribution` for paid media across channels, `finance_revenue_recognition` if ASC 606-style deferred revenue is in scope. Respect each schema's `depends_on_schemas` field for sequencing (e.g. `ga4_ecommerce` depends on `event_tracking_and_sessionization`).
   - **A schema's own description names a specific originating context (e.g. "for a consultancy's or agency's own CRM operations"). Treat that as who it happened to be built for, not as a boundary on who can use it.** Look past the described origin and ask the same question Step 2 asks for verticals: is the underlying entity shape and technique still structurally the same problem this client actually has? `crm_identity_resolution`'s stated framing is an agency reconciling contacts across its own CRM tools — but the technique (union multiple CRM sources, resolve identity by email/domain matching, produce one canonical `contact_pk`/`company_pk`) is the same technique a client needs for its own multi-CRM contact-mismatch problem, regardless of what kind of business that client runs. Reject a cross-vertical schema for being a poor structural fit — different entities, different join shape, a problem this client doesn't actually have — never merely for being described for a different kind of organization than this client.
   - Distinguish, the same way Step 2 does:
     - **Confident**: the schema's own description already matches this client's situation in substance, regardless of the specific words used to frame it.
     - **Adjacent**: the description frames it around a different kind of organization, but the entities and technique are still the same underlying problem — propose it, explicitly noting the reframe (e.g. "built for an agency's own CRM reconciliation, but the same technique applies to your client's own CRM systems").
   - If Step 2 found nothing and this step finds nothing either (confident or adjacent), **skip silently to Step 2 of the main workflow** (Define Source Definitions) — no message, no note. This remains the majority-case, expected outcome for most engagements.

3b. **If the client has an authoritative model of their own, the proposal is a
   comparison, not a starting structure.** When `status.md` has
   `model_source: modality`, the entity set, keys and cardinality already came
   from the client's own model, by way of `conceptual_model` and, if it ran,
   `logical_model`. The registry proposal does not replace that. Present it as a
   comparison against what the client already authored, and name every
   disagreement rather than resolving one silently. Three kinds recur:

   - **An entity the registry has and the client's model does not.** Do not add
     it because the registry lists it as core. Say the registry expects it, say
     the client's model does not carry it, and ask. Where the requirements also
     put it out of scope, that is three sources agreeing and it is simply
     excluded, with the reason recorded.
   - **An entity the client's model has and the registry does not.** Keep it.
     `conceptual_model` already accounted for it; carry that reason forward
     rather than re-deriving or dropping it.
   - **A grain the registry splits and the client's model does not, or the
     reverse.** This is the one that quietly restructures a client's model. A
     registry schema proposing an order-header and an order-line fact where the
     client's model carries a single entity is a real design question about
     grain, not a naming difference. State both grains, state which was taken,
     and record why. `data_model-validate`'s Canonical Vertical Comparison
     already reports a grain that "notably diverges"; this makes the decision
     deliberate rather than something that check discovers afterwards.

   Where the registry and the client's model disagree and the requirements settle
   it, the requirements settle it, and the divergence from the registry is
   recorded. The 4-4-5 versus 4-5-4 retail calendar is the worked example: the
   registry's structure is worth keeping, its seed contents are not, and a
   confident vertical match adopted unread would ship the wrong calendar.

4. **Propose whatever was found, tiered by confidence — never auto-adopt:**
   - **Confident vertical match**: present as a strong proposal:
     ```
     Wire found a canonical data model that may fit this engagement: [vertical] — [schema_name].
     Standard marts: [list from standard_marts]
     Entities: [list]

     Use this as the starting structure for the data model? (yes / adapt / no)
     ```
   - **Adjacent vertical match only**: present with the mismatch stated plainly, not hidden:
     ```
     No vertical in the registry is an exact industry match for [client's actual industry] — there's no
     [inferred missing vertical, e.g. "saas"] vertical yet. The closest available entity shape is
     [vertical] — built from [what that vertical's content actually covers], not [client's industry].
     Entities: [list]

     This may still be a reasonable starting point for [specific reason, e.g. "the MRR/NRR model"].
     Worth using loosely, or skip entirely? (yes / adapt / no)
     ```
   - **Cross-vertical pattern(s)** found in Step 3 — present alongside whichever vertical proposal exists above, or on their own if no vertical proposal exists at all. If confident:
     ```
     Also relevant regardless of industry fit: [cross-vertical schema name] — [one-line reason
     specific to this client's actual requirements/sources].
     Include this pattern too? (yes / adapt / no)
     ```
     If adjacent — say so plainly rather than silently reframing it:
     ```
     Also potentially relevant: [cross-vertical schema name] — built for [the schema's stated
     originating context, e.g. "an agency's own CRM operations"], but the same technique
     ([one line on the actual mechanism]) applies to [this client's actual situation].
     Worth using loosely, or skip entirely? (yes / adapt / no)
     ```
   - **yes** (any of the above) — use the proposed entity list, grain, and naming as a baseline for Steps 2–7, adjusted for this client's actual source systems and column names. For a vertical match (confident or adjacent), record `data_model_registry.vertical: <vertical>` in `.wire/engagement/context.md` if not already set. For accepted cross-vertical patterns, record them in `data_model_registry.cross_vertical_schemas: [<schema_name>, ...]` (append, don't overwrite).
   - **adapt** — ask which specific entities/marts to keep, drop, or rename; use the rest as-is. Record as above.
   - **no** — proceed with Step 2 onward exactly as if that specific match were never proposed. Do not write it to context.md — an explicit decline should not get treated as a manual override on the next run. Worth a one-line note in the spec that a match existed but wasn't used (useful signal for the registry's own maintainers), but no other effect. Each proposal (vertical, cross-vertical) is decided independently — declining one doesn't decline the other.

5. For every model in the final data model that maps to a canonical entity (whether from a confident match, an adjacent match, or an accepted cross-vertical pattern, adopted as-is or adapted), carry that entity's `generation_constraints` and `reference_implementation` pointer(s) forward into that model's spec entry in Step 5 (or Step 3 for staging). This is the only place the registry's worked-example SQL becomes reachable — `dbt-generate` reads `data_model_specification.md` as its primary input either way, so it inherits these pointers automatically; no changes to `dbt-generate` itself are needed. Treat `reference_implementation` strictly as a worked example to read and adapt, never to copy verbatim — the registry's own README is explicit that a specific `.sql` file is not reusable across clients, only the pattern it demonstrates is.

### Step 2: Define Source Definitions

For each source system in the pipeline design, produce a complete dbt `_sources.yml` specification:

```yaml
version: 2

sources:
  - name: <source_system>
    database: <bigquery_project>
    schema: <dataset_name>
    freshness:
      warn_after: {count: <N>, period: hour}
      error_after: {count: <N>, period: hour}
    tables:
      - name: <table_name>
        description: "<Table description>"
        loaded_at_field: <timestamp_column>
        columns:
          - name: <column_name>
            description: "<Column description>"
            tests:
              - not_null
              - unique   # only on PK columns
```

Freshness thresholds must be calibrated to the replication cadence from the pipeline design:
- Real-time / CDC sources: `warn_after: 30 minutes`, `error_after: 60 minutes`
- Daily batch sources: `warn_after: 25 hours`, `error_after: 49 hours`
- Manual/on-demand: no freshness check

Note any columns that are excluded for data governance reasons (e.g. free-text fields excluded for safeguarding). Document exclusions explicitly.

### Step 3: Define Staging Models

For each source table, define the staging model:

**Naming**: `stg_<source_system>__<entity_name>` (double underscore between source and entity)

**Materialisation**: `view`

**Tags**: `['staging', '<source_system>']`

For each staging model, specify:
- **Grain**: One row per what? (e.g. "one row per daily attendance mark per student per session")
- **Surrogate key**: `dbt_utils.generate_surrogate_key(['<id_columns>'])` → `<entity>_pk`
- **Column renames**: Source column name → standard column name (snake_case, business-meaningful)
- **Derived columns**: Any simple transformations applied at staging (e.g. `is_present = mark_code IN ('/', 'L')`)
- **Exclusions**: Any source columns excluded and why
- **Filters**: Any `WHERE` clause applied (e.g. `WHERE _fivetran_deleted = false`)
- **Tests**: `not_null` and `unique` on `<entity>_pk`; `not_null` on any non-nullable business keys

Use this template format:

```
### stg_<source>__<entity>
**Source**: `<source_system>.<table_name>`
**Grain**: One row per [description]
**Surrogate key**: `generate_surrogate_key(['<col1>', '<col2>'])` → `<entity>_pk`

| Source column | Staged column | Type | Notes |
|--------------|---------------|------|-------|
| <SourceCol> | <staged_name> | string/date/int/bool | |
| <SourceCol> | <staged_name> | timestamp | Renamed from Fivetran audit column |

**Derived columns**:
- `<derived_col>`: `<expression>`

**Filters**: `WHERE <condition>`

**Tests**: `not_null(entity_pk)`, `unique(entity_pk)`, `not_null(<business_key>)`

**Canonical entity** (only if sourced from the data model registry per Step 1.5): `<vertical>/<entity>` — constraints: [`generation_constraints` from the entity YAML] — reference: [`reference_implementation` path(s)]
```

### Step 4: Define Integration Models (if applicable)

For complex transformations that span multiple staging models but are not yet warehouse-level:

**Naming**: `int_<group>__<subject>__<description>` (e.g. `int_core__student__risk_signals`)

**Materialisation**: `view` (or `ephemeral` for simple pass-throughs)

Use integration models for:
- Cross-system joins (e.g. joining ProSolution student IDs to Focus student IDs)
- Business logic that derives flags or categorisations
- Pre-aggregations that feed multiple warehouse models

### Step 5: Define Warehouse Models

For each fact table, dimension table, and aggregate:

**Fact table naming**: `wh_<group>__<entity>_fact` (e.g. `wh_core__attendance_fact`, `wh_core__pastoral_notes_fact`)
**Dimension table naming**: `wh_<group>__<entity>_dim` (e.g. `wh_core__student_dim`, `wh_core__course_dim`)
**Aggregate naming**: `<subject>_<grain>` (e.g. `student_risk_summary`, `daily_attendance_summary`)

**Materialisation**: `table`

**Tags**: `['warehouse', 'fact']` or `['warehouse', 'dimension']`

For each warehouse model specify:
- **Grain**: One row per what?
- **Surrogate key**: composition and name (e.g. `attendance_pk`)
- **Foreign keys**: which dimension PKs are referenced (e.g. `student_fk → student_dim.student_pk`)
- **Measures**: numeric columns with business descriptions
- **Flags/indicators**: boolean derived columns with their logic
- **Audit columns**: `dbt_updated_at: current_timestamp()`
- **Canonical entity** (only if sourced from the data model registry per Step 1.5): `<vertical>/<entity>` — constraints: [`generation_constraints` from the entity YAML] — reference: [`reference_implementation` path(s)]

### Step 6: Define Seed Files

For any configurable business logic (thresholds, mappings, categorisations), specify seed files:

```
### seeds/<seed_name>.csv
**Purpose**: [What business rule this encodes]
**Columns**: [column names and types]
**Sample rows**: [3-5 representative rows]
**Used by**: [which models reference this seed]
```

Common seed patterns:
- Mark type mappings (e.g. attendance mark codes → present/absent/late)
- Risk score thresholds
- Category hierarchies
- Grade orderings

### Step 7: Generate Physical ERD

Produce a Mermaid `erDiagram` showing every warehouse model (and key staging models) with their columns, data types, primary keys, and foreign key relationships. Write this as a `## Physical Data Model` section within the data model specification document.

Use this template:

```
## Physical Data Model

```mermaid
erDiagram
    ENTITY_FCT {
        string entity_pk PK
        string dimension_fk FK
        date event_date
        int measure_column
        bool flag_column
        timestamp dbt_updated_at
    }
    DIMENSION_DIM {
        string dimension_pk PK
        string natural_key
        string display_name
        string category
        timestamp dbt_updated_at
    }
    AGGREGATE_SUMMARY {
        string summary_pk PK
        string dimension_fk FK
        int count_metric
        float rate_metric
        date summary_date
        timestamp dbt_updated_at
    }
    ENTITY_FCT }|--|| DIMENSION_DIM : "dimension_fk"
    AGGREGATE_SUMMARY }|--|| DIMENSION_DIM : "dimension_fk"
```
```

**ERD conventions**:
- Include all warehouse models (facts, dims, aggregates)
- Include staging models only if they are directly referenced by semantic layer (unusual)
- Mark surrogate keys as `PK`, foreign keys as `FK`
- Use types: `string`, `int`, `float`, `bool`, `date`, `timestamp`
- All relationship lines must correspond to a FK → PK join defined in the model specs above
- Relationship label = the FK column name

### Step 8: Write Data Model Specification Document

Write to `.wire/<project_id>/design/data_model_specification.md`:

```markdown
# Data Model Specification: [Project Name]

**Client**: [Client Name]
**Project ID**: [Project ID]
**Generated**: [Date]
**Version**: 1.0

## 1. Source Definitions
[_sources.yml content for each source system]

## 2. Staging Models
[Per-model spec as defined in Step 3]

## 3. Integration Models
[Per-model spec as defined in Step 4, or "Not applicable"]

## 4. Warehouse Models
[Per-model spec as defined in Step 5]

## 5. Seed Files
[Per-seed spec as defined in Step 6, or "Not applicable"]

## 6. Cross-System Join Keys
[Table mapping natural keys across source systems, e.g.:]
| Left model | Column | Right model | Column | Notes |
|-----------|--------|------------|--------|-------|
| stg_focus__notes | enrolment_id | stg_prosolution__attendance | EnrolmentID | Case-sensitive match |

## 7. Physical Data Model

[Mermaid ERD as generated in Step 7]

## 8. dbt Test Coverage Plan
[Summary table: model → PK test → FK tests → custom tests]
```

### Step 9: Update Status

```yaml
data_model:
  generate: complete
  validate: not_started
  review: not_started
  file: design/data_model_specification.md
  generated_date: [today]
```

### Step 10: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_model`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 11: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `data_model`
- `artifact_name`: `Data Model`
- `file_path`: `.wire/releases/[release_folder]/design/data_model.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 12: Confirm and Suggest Next Steps

```
## Data Model Specification Generated

**File**: .wire/<project_id>/design/data_model_specification.md

**Staging models**: [count]
**Integration models**: [count]
**Warehouse models**: [count] ([fact count] facts, [dim count] dims, [agg count] aggregates)
**Seed files**: [count]
**Physical ERD**: included ([entity count] entities, [relationship count] relationships)
**Cross-system joins**: [count — flag if > 0, these are high-risk]
**Canonical vertical**: [vertical name and schema(s) used, or "None — no canonical match found or proposal declined" if Step 1.5 skipped or was declined]

### Next Steps

1. Validate the data model:
   /wire:data_model-validate <project_id>

2. After validation, review with analytics engineering lead:
   /wire:data_model-review <project_id>

NOTE: This is the most consequential review gate. Approving a model with
incorrect grain, wrong join keys, or missing entities is expensive to fix
after dbt code has been generated. Take time with this review.
```

## Edge Cases

### Source Column Names Unknown

If source schema examples are not in `artifacts/`, specify staging model columns at entity-attribute level from the conceptual model, and add:
```
NOTE: Column names are provisional — based on conceptual model attributes.
Actual source column names must be confirmed before dbt:generate.
Add source schema examples to artifacts/ and regenerate.
```

### Extending an Existing dbt Project

If the client has an existing dbt project:
1. Read existing staging models from `artifacts/` to understand current naming conventions
2. Follow those conventions for new models
3. Explicitly note which existing models are being extended vs which are net-new
4. Do not rename or restructure existing models — only add

### Complex Many-to-Many Relationships

If the conceptual model contains a many-to-many relationship, resolve it in the data model:
- Create a bridge/junction table (e.g. `student_course_bridge`)
- Name it clearly and document the resolution in Section 6

## Additional Output for `dashboard_first` Projects

When `project_type` is `dashboard_first`, additionally generate:

1. **`design/source_tables_ddl.sql`** — SQL DDL (CREATE TABLE statements) defining the expected source data schema, derived from the requirements, visualization catalog, and domain knowledge. Use the target warehouse dialect (e.g., BigQuery).

2. **`design/target_warehouse_ddl.sql`** — SQL DDL defining the target dimensional model (facts and dimensions) that will provide the measures and dimensions identified in the visualization catalog.

These DDL files serve as inputs for seed data generation (`/wire:seed_data-generate`) and the dbt project structure.

## Output

This command creates:
- `.wire/<project_id>/design/data_model_specification.md` (includes physical ERD)
- `.wire/<project_id>/design/source_tables_ddl.sql` (dashboard_first projects only)
- `.wire/<project_id>/design/target_warehouse_ddl.sql` (dashboard_first projects only)
- Updates `.wire/<project_id>/status.md`

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
