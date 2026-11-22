---
wire_schema: "1.0"
command: validate
artifact: stakeholder_interview
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate four-tag completeness on every theme bullet of a stakeholder interview write-up
argument-hint: "[release-folder] [--stakeholder <slug> | --all]"

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Interview — Validate

## Purpose

Mechanically enforces the **mandatory four-tag rule** on every theme bullet of every interview write-up. This is the most consequential validation in the SOP discovery release type — the three analyses in `discovery_analyses` are only as good as the tags applied here, and the playbook's failure modes explicitly warn against retrofitting tags from the consolidated matrix.

Validate runs in two modes:
- `--stakeholder <slug>` — validate one interview write-up
- `--all` — validate every interview in the release and produce a coverage report

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md` (per-stakeholder mode)
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`

## Workflow

### Step 1: Locate and parse

1. Resolve `$ARGUMENTS`. Read the stakeholder map.
2. Decide mode:
   - If `--stakeholder <slug>` provided → validate that single file
   - If `--all` provided (or no arg) → list every file under `planning/interviews/` and validate each

### Step 2: Per-file checks

For each interview file, run these checks. **Definitions are closed sets** — anything outside these sets fails.

#### Front-matter
- [ ] `slug` present and matches the file name
- [ ] `stakeholder_name`, `title`, `department`, `priority` populated
- [ ] `interview_date` is an ISO date
- [ ] `fathom_url` present, OR a note in the body explaining "no recording"

#### Stakeholder quote
- [ ] `## Stakeholder quote` section present and not the template placeholder text
- [ ] Quote is in blockquote (`>`) format

#### Meeting summary
- [ ] At least 5 of the 7 standard bullets present (role, painful thing, decision/workflow, KPIs, existing assets, risks, scope notes)

#### Theme bullets — the four-tag rule
For every line under `### Theme list` (or any `## Themes` subsection that contains bullet themes):

- [ ] Bullet text is non-empty
- [ ] Bullet ends with a tag cluster matching the regex pattern (case-sensitive):
  - **Domain tag**: `#[a-z][a-z0-9-]+` (any kebab-case lowercase tag — domain set is configurable per engagement; do not hard-code)
  - **Type tag**: exactly one of `#pain` `#requirement` `#kpi` `#risk` `#existing-asset`
  - **Hierarchy tag**: exactly one of `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`
  - **PPT tag**: exactly one of `#people` `#process` `#technology`
- [ ] **Exactly one tag from each of the four sets** appears on the line. Zero or two tags from a set is a FAIL on that line.
- [ ] Uncertain tags (`?` suffix, e.g. `#process?`) are surfaced as WARNINGs — the consultant must confirm before review.

A line with `#retail #pain #clean #process` passes. A line with `#retail #pain #process` fails (missing Hierarchy). A line with `#retail #pain #clean #analyse #process` fails (two Hierarchy tags).

### Step 3: Cross-file coverage check (`--all` mode only)

- [ ] Every P0 stakeholder in the stakeholder map has an interview file
- [ ] Every P1 stakeholder in the stakeholder map has an interview file OR is explicitly marked deferred in `status.md → interviews[].generate: deferred`
- [ ] Every interview file's `slug` matches a row in the stakeholder map

### Step 4: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/interviews/_validation_report.md` (covers all files in `--all` mode) or `.wire/releases/$ARGUMENTS/planning/interviews/<slug>_validation.md` (single-file mode).

```markdown
# Stakeholder Interview Validation Report

**Release**: $ARGUMENTS
**Mode**: [single / all]
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Per-file summary

| File | Theme bullets | Fully tagged | Missing tag | Uncertain (`?`) | Result |
|---|---|---|---|---|---|
| maud-bakker.md | 12 | 12 | 0 | 0 | ✅ |
| sav-jansen.md | 9 | 7 | 2 | 0 | ❌ |
| ola-jin.md | 11 | 9 | 0 | 2 | ⚠️ |

## Failures (must fix before consolidation)

### sav-jansen.md — line 47
> Store-level conversion is not visible in real time `#retail #pain #process`

Missing Hierarchy tag. Add one of: `#collect` `#clean` `#define-track` `#analyse` `#optimise-predict`.

### sav-jansen.md — line 52
> Footfall counts are unreliable `#retail #pain #clean #process #people`

Two PPT tags (`#process` and `#people`). Pick the binding constraint and remove the other.

## Warnings (resolve before review)

### ola-jin.md — line 31
> `#process?` suffix — consultant confirmation needed

## Coverage (--all mode)

| Stakeholder map row | Priority | Interview file | Status |
|---|---|---|---|
| Maud Bakker | P0 | maud-bakker.md | ✅ |
| Sav Jansen | P0 | sav-jansen.md | ❌ failing |
| Ola Jin | P1 | ola-jin.md | ⚠️ |
| Pieter Hoekstra | P1 | — | ❌ missing file |

## Next Steps

1. Fix every FAIL line by adding/removing tags as flagged
2. Resolve `?` suffixes by confirming the tag choice
3. Re-run validation
4. When PASS: /wire:stakeholder-interview-review $ARGUMENTS --stakeholder <slug>
```

### Step 5: Update status

For each validated file:
```yaml
interviews:
  - slug: <slug>
    validate: complete   # or "failed"
    themes_tagged: <count>
```

Aggregate `stakeholder_interview` state in `artifacts`:
- `validate: complete` — only when every interview file passes
- `validate: failed` — if any file fails

### Step 6: Output summary

Show the worst N failures with file:line references. Don't show every check — just what needs fixing.

## Output Files

- Validation report file(s) as above
- Updated `.wire/releases/$ARGUMENTS/status.md`
