---
wire_schema: "1.0"
command: generate
artifact: discovery_analyses
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: requirements_matrix
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate the three analyses — Hierarchy of Needs, PPT, and Maturity Curve

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Discovery Analyses — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Produces the three analyses applied to the consolidated requirements:

1. **Analytics Hierarchy of Needs** — bar chart + tier-by-tier prose diagnosis
2. **People / Process / Technology (PPT)** — bar chart + axis-by-axis prose diagnosis
3. **Data Analytics Maturity Curve** — single pin placement + prose justification

Plus the per-axis word-cloud labels, the verbatim quote selections, and the MoSCoW + Phase layering done after the diagnosis.

These analyses are the load-bearing diagnostic work of the discovery. They drive the Findings Playback deck (Phase 4) and they are what the sponsor signs off on at the playback. Per the playbook: this is **internal RA work** — the client does not see the matrix or this analyses file in raw form.

Models Phase 3 Steps 3–8 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (reviewed and approved)
- All interview write-ups (for verbatim quote selection)

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery` and that the requirements matrix is `review: complete`.
2. If not, stop: "Requirements matrix has not been reviewed. Run `/wire:requirements-matrix-review $ARGUMENTS` first."

### Step 2: Hierarchy of Needs analysis

Walk every row of the matrix. Confirm or correct the Hierarchy tier. The rule:

> The lowest tier whose absence is blocking it.

Count rows per tier. Produce a bar chart specification (the rendered chart is generated at deck-build time; here we record the counts and the diagnostic prose).

Write a 4–6 bullet prose diagnosis explaining the shape of the chart **in the client's terms**. Reference specific verbatim quotes. Worked example from a prior engagement, for tone:

> "Modeling challenges, data ingestion issues from external vendors, frequent schema changes affecting pipeline stability... Critical issues include poor SAP reconciliation, poor testing/QA processes..."

If the distribution is unusual (all clean/no analyse, or top-heavy with no clean/collect), call that out explicitly — it is itself a finding.

### Step 3: PPT analysis

Walk the matrix again. Confirm or correct the PPT axis. The rule:

> The axis whose absence is causing it.

Count rows per axis. Write a 4–6 bullet axis-by-axis diagnosis:

- **People** — what skills, roles, structure, or accountability is the binding constraint?
- **Process** — what gates, QA, decision trees, or governance are missing?
- **Technology** — what tooling, infrastructure, or semantic layer gaps?

Worked example (14 Capabilities, 7 Technology, 5 People) — diagnosed as **fundamentally a Process problem** with adequate underlying tooling.

If the consultant tagged "Capabilities" as a fourth axis for any rows (inline-roadmap pattern), include a fourth section.

Refusing to choose one axis per row is refusing to diagnose. If any row reads as "a bit of all three", revisit during this step.

### Step 4: Maturity Curve placement

Pin the client at one of the five stages, based on the combined picture from the Hierarchy and PPT analyses:

- **Data Chaos** — fragmented, low-trust, firefighting (Prior engagements have landed here)
- **Order** — strategic and operational alignment, standard practices adhered to
- **Democratisation** — efficient self-service across departments
- **Innovation** — beyond the basics; new data products and solutions
- **Return** — innovation drives competitive advantage

Write a 3–5 bullet justification grounded in evidence from the interviews. **Do not place the pin generously to be polite.** Prior engagements have landed at Data Chaos — saying so was honest, not insulting. If the consultant has placed the pin and the diagnosis prose doesn't justify it, this is the moment to challenge.

### Step 5: Word cloud labels (per axis)

For each PPT axis (and the cross-cutting "Capabilities" axis if used), extract 6–12 short hashtag-style theme labels from the rows tagged to that axis. Labels should use the **client's own language** where possible.

Worked example — a prior engagement's Process word cloud:
`MissingQualityGates` `RushToProduction` `SkipArchitectureReview` `SkipBusinessValidation` `BrokenCommunication` `UnclearAccountability` `MissingDecisionTrees`

If the labels read like a glossary instead of the client's voice, redo them from the verbatim quotes.

### Step 6: Quote selection (per playback section)

For each of these sections of the playback deck, pick 3–4 verbatim quotes:

- Current State opener (dark navy divider)
- Hierarchy diagnosis (per-tier supporting quotes)
- PPT diagnosis (per-axis supporting quotes)
- Desired Future State opener
- Each per-axis section divider (3 quotes each)

Strong quotes are **short, specific, and emotionally accurate**. The "driving a car without a speedometer" quote from a prior engagement is the canonical example — it does more diagnostic work than a paragraph of prose.

### Step 7: MoSCoW and Phase layering

Now (and only now) layer in MoSCoW (Must / Should / Could / Won't) and Phase (1 / 2 / Future) tags on every row of the requirements matrix. Apply these directly to `requirements_matrix.md` — update the `MoSCoW` and `Phase` columns from `TBD` to actual values.

Rule of thumb:
- **Must / Phase 1** — sponsor-backed, foundation-tier, in-scope domain, count ≥ 2 stakeholders
- **Should / Phase 1** — strong support, in-scope, but de-risk-able
- **Could / Phase 2** — material but not on the critical path for the go/no-go decision
- **Won't / Future** — out-of-scope or premature

### Step 8: Resolve conflicts

Walk the Conflicts log. For each:
- Name the contradiction explicitly
- Name RA's recommendation (with reasoning)
- Mark whether the sponsor needs to decide it at the playback

Add a `## Sponsor decisions required` section listing every unresolved conflict.

### Step 9: Draft the analyses document

**Output**: `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`

```markdown
# Discovery Analyses: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Status**: Internal RA — feeds Findings Playback deck

## 1. Analytics Hierarchy of Needs

### Distribution

| Tier | Count | % of total |
|---|---|---|
| Collect | N | NN% |
| Clean | N | NN% |
| Define & Track | N | NN% |
| Analyse | N | NN% |
| Optimise & Predict | N | NN% |

### Diagnosis

[4–6 bullets, in client's terms, supported by specific verbatim quotes]

### Supporting quotes (per tier)

- Collect: "..."
- Clean: "..."
- ...

## 2. People, Process, Technology

### Distribution

| Axis | Count | % of total |
|---|---|---|
| People | N | NN% |
| Process | N | NN% |
| Technology | N | NN% |

### Diagnosis

[4–6 bullets — name the binding constraint and the strength axis]

### Per-axis word clouds

**People**: `<label1>` `<label2>` ...
**Process**: `<label1>` `<label2>` ...
**Technology**: `<label1>` `<label2>` ...

### Supporting quotes (per axis)

- People: "..."
- Process: "..."
- Technology: "..."

## 3. Data Analytics Maturity Curve

### Pin: <Data Chaos | Order | Democratisation | Innovation | Return>

### Justification

[3–5 bullets grounded in interview evidence — explain why this pin, not the next one up]

## 4. MoSCoW and Phase summary

| Phase | Must | Should | Could | Won't |
|---|---|---|---|---|
| Phase 1 | N | N | — | — |
| Phase 2 | — | — | N | — |
| Future | — | — | — | N |

(Detailed MoSCoW / Phase tags are recorded directly on each row of `requirements_matrix.md`.)

## 5. Sponsor decisions required

[Every unresolved conflict from the Conflicts log + RA's recommendation. Each item will be forced to a sponsor decision at the playback.]

- [ ] Conflict X — Operations wants daily; Finance wants monthly. RA recommends daily for store-level, monthly for board-level. Sponsor to confirm.
- [ ] ...

## 6. Playback quote bank

(Curated for use in the Findings Playback deck — slide divider quotes and inline diagnostic quotes.)

### Current State opener
- "..."
- "..."
- "..."

### Desired Future State opener
- "..."
- "..."

### Per-axis dividers
[As above — 3 quotes each]
```

### Step 10: Update status

```yaml
artifacts:
  discovery_analyses:
    generate: complete
    file: planning/discovery_analyses.md
    generated_date: {{TODAY}}
    generated_files:
      - planning/discovery_analyses.md
      - planning/requirements_matrix.md   # MoSCoW + Phase columns now filled

sponsor_validation:
  maturity_pin: "<Data Chaos | Order | Democratisation | Innovation | Return>"
```

### Step 11: Sync to document store

Follow `specs/utils/docstore_sync.md`. The Confluence "Discovery Findings Working Document" (per-domain page set) referenced in the playbook is the natural destination.

### Step 12: Output summary

Show: Maturity pin, top-3 by Hierarchy tier, top-3 by PPT axis, conflict count, MoSCoW/Phase counts.

```
/wire:discovery-analyses-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (MoSCoW + Phase columns)
- Updated `.wire/releases/$ARGUMENTS/status.md`
