---
wire_schema: "1.0"
command: generate
artifact: current_state_appraisal
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder, e.g. .wire/releases/01-acme-discovery"
  optional:
    - name: section
      description: "--section \"<title>\" adds a free-form section to the appraisal for engagement-specific material (migration sizing, an acquisition engine, a regulatory constraint). Repeatable."
produces:
  - type: document
    path: "planning/current_state_appraisal.md"
    description: "Appraisal of the existing platform, sources, tooling, documentation, governance and data quality"
preconditions: dynamic
delegates_to:
  - utils/discovery_analyst_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
  - utils/meeting_context
  - utils/reference_legibility
description: Appraise the client's current state — platform, sources, replication, tooling, documentation, governance, data quality — from documentation and interviews rather than system access
argument-hint: <release-folder> [--section "<title>"]
---

# Current State Appraisal — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: current_state_appraisal` and `artifact_file_path: planning/current_state_appraisal.md` before proceeding.

---

## Purpose

Discovery has three pillars: map the current state, map the target state, agree
the roadmap. This is the first of them.

The `diagnostic` profile covers current state through the Hierarchy of Needs and
People–Process–Technology analyses, which diagnose *what is wrong* in the
client's own words. That is a different document from a factual account of *what
exists*, and a modelling-led discovery needs the second one: the platform
components, the sources and their owners, how data is replicated, what tooling
is in place, what documentation exists, and where governance sits today.

It is written from documentation, interviews and whatever the client can show on
a screen share. It does **not** assume system access. Where a fact could not be
established, it says so and names who could establish it. An appraisal with
honest gaps is useful; an appraisal that guesses is not.

## Scope boundary

| This document | Not this document |
|---|---|
| What exists today, factually | What we propose (that is the target state design) |
| Who owns each source, and who to ask | A diagnosis of organisational maturity (`discovery_analyses`) |
| Where governance sits today, and where it does not | A governance design (`ads_governance-design`, a different release type) |
| The gaps in our own knowledge, named | Requirements (`requirements_matrix`) |

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/status.md` — `discovery_profile`, client name, engagement context
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` (reviewed)
- All interview write-ups under `.wire/releases/$ARGUMENTS/interviews/`

**Optional**:
- Anything in `.wire/releases/$ARGUMENTS/artifacts/` — architecture diagrams, existing documentation, a chart of accounts, exported schema listings
- Fathom transcripts via `specs/utils/meeting_context.md`
- `modality_project.yaml` if the client already models in Modality — the source list in its logical model files is evidence for Section 2

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Read `status.md`.
2. Confirm `release_type: sop_discovery`. If not, stop and name the release type found.
3. Follow `specs/utils/precondition_gate.md`. Its Step 0 resolves this artifact's
   gate from `wire/release-types/sop_discovery.yaml` and applies the active
   profile. If `discovery_profile` is `diagnostic`, this phase is not enabled and
   the gate stops here — that is correct, not a failure. Report:

   ```
   current_state_appraisal is not part of the diagnostic profile.

   The diagnostic profile covers current state through discovery_analyses
   (Hierarchy of Needs and People–Process–Technology).

   To run it anyway, set discovery_profile: modelling_led in status.md, or
   enable it as an optional artifact.
   ```

### Step 2: Establish what is known, and from where

Every claim in this document carries its source. Build the evidence set first:

1. List each input document read, with its date. A document older than 6 months
   is recorded with its age; a reader needs to know whether "current" means
   this quarter or last year.
2. From the interview write-ups, extract every factual statement about the
   platform, distinct from the tagged PAIN / GOAL / CONSTRAINT / OPPORTUNITY
   findings. "We replicate SAP nightly with Fivetran" is a Section 3 fact.
   "The nightly SAP load breaks silently" is a requirements-matrix row.
3. Record who said each fact. Two stakeholders contradicting each other on a
   factual matter is itself a finding, and it belongs in Section 10.

### Step 3: Write the appraisal

Write `planning/current_state_appraisal.md`. Sections 1 to 9 are the standing
shape. Every row of every table carries an `Evidence` column naming the document
or interview it came from, and a `Confidence` value of `confirmed`, `reported`
or `unknown`.

**Section 1 — Platform components.** One row per component: name, layer
(ingestion, storage, transformation, orchestration, BI, activation), vendor,
who administers it, whether it is in scope for change.

**Section 2 — Sources.** One row per source system: name, business owner,
technical owner, what it holds, grain of the records that matter, how it is
accessed today. This is the section a later `logical_model` reads: when a
modelling-led discovery produces a logical model, its per-entity source mapping
must reconcile against this list, and `logical_model-validate` checks that it
does.

**Section 3 — Replication and integration.** How each source reaches the
warehouse: tool, schedule, full or incremental, known failure modes. Where a
source is not replicated at all, say so; that is a roadmap input.

**Section 4 — Transformation and modelling.** What exists: dbt project or not,
layering conventions or the absence of them, hand-written SQL in the BI tool,
stored procedures, spreadsheets that act as production.

**Section 5 — Reporting and consumption.** BI tools in use, roughly how many
reports, who builds them, which reports the business actually runs on. Name the
handful of reports whose numbers are treated as authoritative — a later
equivalency or definition dispute starts from that list.

**Section 6 — Documentation.** What documentation exists, where it lives, when
it was last touched, and whether the team uses it. A wiki nobody opens is a
finding, not documentation.

**Section 7 — Governance and ownership today.** Who decides what a metric
means. How a definition change is agreed, if it is. Whether anyone holds a
metric or entity register. What the lifecycle of a new metric looks like from
request to production. This is a factual account of the present, not a proposed
governance model.

**Section 8 — Personal and regulated data.** Where personal data sits, which
jurisdictions apply, what the client already asserts about retention and access.
Reported, not audited: this section names what the client says and who said it.

**Section 9 — Data quality, as experienced.** The reconciliation problems the
team lives with, each traced to an interview. Where a number is known not to
tie, record both figures and the reports they come from.

**Section 10 — Gaps and contradictions.** Two lists. First, every fact we could
not establish, with the person who could establish it and what we asked for.
Second, every factual contradiction between sources, with both versions and both
attributions. Neither list is a failure state. An empty Gaps list on a
documentation-only appraisal is implausible and `validate` treats it as suspect.

**Free sections.** Engagement-specific material goes in its own section, added
with `--section "<title>"` and placed after Section 10. Sizing a migration, an
acquisition integration engine, a regulatory programme: these matter enormously
to one engagement and are noise in the standing shape, so the framework does not
name them. A free section carries the same Evidence and Confidence discipline as
the standing sections.

### Step 4: Reference legibility

Follow `specs/utils/reference_legibility.md`. This document is cited by
`logical_model`, `delivery_roadmap` and the playback deck, so any code it mints
(`CS-n` for an appraisal finding) is expanded at first mention and carries a
Reference key table.

### Step 5: Status and log

Update `status.md`: `artifacts.current_state_appraisal.generate: complete`.
Follow `specs/utils/execution_log.md`.

Then run `/wire:current-state-appraisal-validate $ARGUMENTS` (automatic under
`specs/utils/auto_validate.md`).

## Output

`.wire/releases/$ARGUMENTS/planning/current_state_appraisal.md`
