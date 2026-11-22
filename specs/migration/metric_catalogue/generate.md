---
wire_schema: "1.0"
command: generate
artifact: metric_catalogue
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: document
    path: "audit/metric_catalogue.md"
    description: "Every calculated metric in the source estate grouped by name, with a candidate class, a proposed ruling per group, and the findings that change numbers silently"
  - type: report
    path: "audit/metric_catalogue.csv"
    description: "One row per metric group with candidate_class and empty ruling, canonical_formula and target_name columns for the review to fill"
  - type: report
    path: "audit/metric_catalogue.json"
    description: "Full catalogue from looker_studio_metrics.py: every definition with its location"
preconditions:
  - artifact: looker_studio_audit
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Group every calculated field in the Looker Studio estate by metric name, flag copies, aliases and conflicts, and propose one definition per metric for the client to rule on"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metric_catalogue` and `artifact_file_path: audit/metric_catalogue.md` before proceeding.

---

# Metric Catalogue: Generate

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Looker Studio has no shared semantic model. Each data source and each chart holds its own formulas, so one metric is often defined many ways (CTR as clicks over impressions in one data source, link clicks over reach times 100 in another). Migrating those definitions one for one rebuilds the silos in Omni. The metric catalogue turns many report-level definitions into one agreed set before the Omni model is built.

`wire/scripts/looker_studio_metrics.py` does the deterministic part: it collects every calculated field, normalises each formula (rules in `wire/bi_pairs/looker_studio_to_omni/translation_guide.md`) and groups definitions by metric name with a candidate class. The agent does the judgement part: a proposed ruling per group. The client rules in `/wire:metric-catalogue-review`. Nothing here resolves a conflict on the client's behalf.

## Prerequisites

- `looker_studio_audit review: approved`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/datasource_catalog.csv`
- `.wire/releases/$ARGUMENTS/artifacts/business_rules.yaml` (if present: definitions already agreed)
- `.wire/releases/$ARGUMENTS/decisions.md`
- `wire/bi_pairs/looker_studio_to_omni/translation_guide.md`

## Workflow

### Step 1: Build the catalogue

```bash
python3 <plugin-root>/scripts/looker_studio_metrics.py \
  --reports .wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json \
  --out .wire/releases/$ARGUMENTS/audit
```

Writes `metric_catalogue.json` and `metric_catalogue.csv`. Candidate classes:

| Class | Meaning | What the review decides |
|---|---|---|
| `same_definition` | Every copy has the same normalised formula | Confirm and merge into one measure |
| `same_shape_different_fields` | Same calculation over differently named fields | Alias of one metric (merge), or different things sharing a name (rename both, for example paid CTR and organic CTR) |
| `conflict` | Different calculations under one name | Which definition is right, or whether both stay under new names |

Findings: `sum_of_ratio` marks a chart that sums a per-row ratio (a sum of ratios, not a ratio of sums). Its numbers are wrong at any total level and will change when rebuilt correctly.

### Step 2: Propose a ruling per group

For every group that is not `same_definition` with one copy, write a proposal. Read `business_rules.yaml` first: a metric already defined there is proposed as that definition. Then:

- `same_definition` with several copies: propose merge into one measure, `target_name` in the warehouse naming convention.
- `same_shape_different_fields`: say which inputs are the same business quantity under different source names (for example `_cost_` and `common__cost`) and which are not (`link_clicks` from paid social versus `clicks` from search). Propose merge or rename accordingly.
- `conflict`: list each formula with where it is used (reports, data sources, chart counts) and propose the definition that is a ratio of totals over the widest agreed inputs. Never propose a sum of ratios.
- `sum_of_ratio` findings: propose the ratio-of-totals form and state that the number will change.

A proposal is a recommendation, not a ruling. For every `conflict`, write a `parked_decisions` entry in `status.md` (kind `ruling`, artifact `metric_catalogue`, the question "Which definition of <metric> is correct?") unless `decisions.md` already holds a ruling.

### Step 3: Write the catalogue document

**Output location**: `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md`

Sections:
- Summary: definitions found, groups by class, copies merged, conflicts, findings
- Conflicts: one subsection per group, each formula with its locations, the proposed ruling and the parked decision id
- Aliases and renames: the `same_shape_different_fields` groups with proposals
- Copies: the `same_definition` groups with more than one copy, as one table
- Findings: each `sum_of_ratio` with location, formula and the corrected form
- Reference key: every code used (decision ids, group keys) with its meaning, per `specs/utils/reference_legibility.md`

Leave the `ruling`, `canonical_formula` and `target_name` columns in `metric_catalogue.csv` empty; the review fills them.

### Step 4: Update status

```yaml
artifacts:
  metric_catalogue:
    generate: complete
    file: audit/metric_catalogue.md
    data_file: audit/metric_catalogue.csv
    generated_date: "{{TODAY}}"
    definition_count: N
    group_count: N
    conflict_count: N
    alias_count: N
    finding_count: N
    rulings_parked: N
    generated_files:
      - audit/metric_catalogue.md
      - audit/metric_catalogue.csv
      - audit/metric_catalogue.json
```

### Step 5: Output summary

Print the counts, the conflicts with their questions, and the next command:

```
/wire:metric-catalogue-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md`
- `.wire/releases/$ARGUMENTS/audit/metric_catalogue.csv`
- `.wire/releases/$ARGUMENTS/audit/metric_catalogue.json`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact_id, `Metric Catalogue` as artifact_name, and the `file` value from `artifacts.metric_catalogue` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metric_catalogue` as artifact, `generate` as action.
