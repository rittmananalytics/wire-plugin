---
wire_schema: "1.0"
command: generate
artifact: requirements_matrix
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
  - artifact: stakeholder_interview
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Generate the Discovery Requirements Matrix from tagged interview write-ups

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Requirements Matrix — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Harvests every tagged theme from every stakeholder interview write-up, de-duplicates near-identical themes, and produces the **Discovery Requirements Matrix** — the structured single source of truth for the three analyses in `discovery_analyses`.

This is internal RA work. The matrix is **not** the sponsor deliverable — the Findings Playback deck is. The matrix's job is to make Phase 3 mechanical: tag harvest → de-duplicate → classify → diagnose.

Models Phase 3 Steps 1–2 (and prepares for Steps 3–8) of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/interviews/*.md` — every interview file (must all pass `/wire:stakeholder-interview-validate --all`)
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` — to read the in-scope domain list
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md` — to read priority and resolve `source_stakeholders` counts

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Confirm `release_type: sop_discovery`.
2. Confirm every interview file passes validation. If any are failing or missing tags, stop: "Tag failures present in [N] interview files. Run `/wire:stakeholder-interview-validate --all` and fix before consolidating. Retrofitting tags here will lose diagnostic signal."
3. Confirm every P0 stakeholder from the map has an interview write-up. If any are missing, ask the consultant whether to proceed (some P0s legitimately couldn't be booked) or pause.

### Step 2: Tag harvest

Walk every interview file. For every theme bullet, extract:
- Bullet text (verbatim)
- Domain tag (the `#<domain>` tag)
- Type tag (one of `#pain` `#requirement` `#kpi` `#risk` `#existing-asset`)
- Hierarchy tier (one of `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`)
- PPT axis (one of `#people` `#process` `#technology`)
- Source stakeholder (from the file's `slug`)
- Verbatim quote (the closest verbatim sentence from the same write-up, or the stakeholder quote at the top of the file)

Do not paraphrase. Copy bullet text verbatim into the matrix.

### Step 3: De-duplicate

Cluster identical or near-identical themes (same Hierarchy tier + same PPT axis + same domain + semantically equivalent bullet text). For each cluster:
- Choose the strongest bullet text as the canonical Title/Description
- Sum the count of source stakeholders
- Note the priority mix (e.g. "3 P0, 1 P1")
- If the sponsor is a source stakeholder, set `sponsor_backing: Y`
- Carry forward the strongest verbatim quote across all clustered sources

### Step 4: Generate Req IDs

For each de-duplicated row, assign `R-<DOMAIN>-<NN>` where `<DOMAIN>` is the upper-case domain tag and `<NN>` is a zero-padded sequence within that domain.

### Step 5: Draft the matrix

**Output**: `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`

```markdown
# Discovery Requirements Matrix: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}
**Status**: Internal RA — pre-analyses

## Source

- Interview files: {{N}} write-ups across {{N_domains}} in-scope domains
- Tag set: enforced by `/wire:stakeholder-interview-validate`

## Matrix

| Req ID | Domain | Type | Hierarchy | PPT axis | Title | Description | Verbatim quote | Source stakeholders | Count | Sponsor backing | MoSCoW | Phase | Confidence | Source systems | Existing asset | Conflicts / open questions |
|--------|--------|------|-----------|----------|-------|-------------|----------------|---------------------|-------|-----------------|--------|-------|------------|----------------|----------------|----------------------------|
| R-RETAIL-01 | retail | pain | clean | process | Store-level conversion not trusted | Store managers cannot trust footfall numbers because SAP/EPOS reconciliation runs weekly and breaks silently. | "We can't trust the conversion numbers, so we just call head office." | Maud, Laura, Sav | 3 | Y | TBD | TBD | High | SAP, CowHills EPOS, Footfall | LD-520 | None |

Notes on the columns:
- **MoSCoW** and **Phase** are deliberately left `TBD` here. They are layered in by `/wire:discovery-analyses-generate` Step 8 (after Hierarchy / PPT / Maturity Curve placement).
- **Confidence** is the consultant's confidence that this is the right ask. High / Medium / Low.
- **Conflicts / open questions** is where you call out contradictions between stakeholders without silently picking a side.

## Conflicts log

[Cluster every contradiction across stakeholders here. Name both sides, name who said what. The Findings Playback will surface these to the sponsor as forced-decision items.]

## Coverage

- In-scope domains (from engagement brief): {{list}}
- Domains represented in matrix: {{list}}
- Domains under-represented (fewer than 3 requirements): {{list — flag in playback}}

## Tag distribution (preview — drives the analyses)

### By Hierarchy tier
| Tier | Count |
|---|---|
| Collect | N |
| Clean | N |
| Define & Track | N |
| Analyse | N |
| Optimise & Predict | N |

### By PPT axis
| Axis | Count |
|---|---|
| People | N |
| Process | N |
| Technology | N |

These counts are previewed here for sanity-check; the diagnostic prose comes in `/wire:discovery-analyses-generate`.
```

### Step 6: Update status

```yaml
artifacts:
  requirements_matrix:
    generate: complete
    file: planning/requirements_matrix.md
    generated_date: {{TODAY}}
    generated_files:
      - planning/requirements_matrix.md
```

### Step 7: Sync to document store

The Confluence / Notion mirror is the working surface for the rest of the consolidation. Follow `specs/utils/docstore_sync.md`.

### Step 8: Output summary

Show: total requirements after de-dup, breakdown by Hierarchy tier and PPT axis, count of conflicts logged, list of under-represented domains.

```
/wire:requirements-matrix-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


---

## Optional columns: business value and ROI measure

Off by default. Enabled by `requirements_matrix.optional_columns` in `status.md`,
or asked for at generate time. A modelling-led discovery normally wants them,
because its roadmap is presented to a sponsor who is choosing between initiatives.

| Column | Content | Rule |
|---|---|---|
| `business_value` | What the business gets, in its own words, with a figure where the stakeholder gave one | Never invented. A row whose stakeholder gave no value statement reads `not stated`, not a guess |
| `roi_measure` | The measure that would show the value landed, and where it is read from today | Must name a measure that exists or state that it does not exist yet |

`not stated` is a legitimate value and appears in the review as a question for the
sponsor. A fabricated value figure is worse than a blank, because the roadmap is
prioritised against it.

## Optional type tag: `#question`

The four mandatory tags (`#pain`, `#goal`, `#constraint`, `#opportunity`) classify
what a stakeholder said. A modelling-led discovery also gathers the business
questions the platform must answer, which are not any of the four: "what is our
gross margin by channel by week" is neither a pain nor a goal.

`#question` marks a row as a business question. A `#question` row:

- states the question as the business asks it, not as a metric name
- names the entities it needs, which become a coverage check against the
  conceptual model
- carries its `business_value` and `roi_measure` when those columns are on

`logical_model-validate` and `conceptual_model-validate` do not fail on a
`#question` row whose entities are missing; `delivery_roadmap-generate` reads them
as candidate Release 1 scope. The tag is additive: it does not replace the four,
and a row may carry `#question` alongside `#pain`.
