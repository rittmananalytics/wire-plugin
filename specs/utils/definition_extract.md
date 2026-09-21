---
description: Shared convention — enumerating metric and field definitions across a semantic layer, BI tool and ad-hoc SQL, classifying the conflicts between them, and taking in definitions from systems Wire cannot read
---

# Definition Extract — Shared Convention

Cited by `specs/discovery/business_rules/generate.md` and
`specs/agentic_data_stack/metric_audit/generate.md`.

Both commands need the same two things: find every place a metric is defined, and
say how the definitions differ. They diverge after that. `metric_audit` goes on to
score coverage against `query_audit`'s real questions and to recommend which
metrics are safe to promote into a semantic layer. `business_rules` goes on to
record a decision, an approver and a test per rule. Neither is a superset of the
other, so the shared half lives here and the algorithm cannot drift between them.

Extracted from `metric_audit/generate.md` Steps 2 and 3 without behaviour change,
then extended with the unreachable-source intake below.

---

### Step 2: Enumerate Metric Definitions

Collect metric definitions from every available source:

**dbt Semantic Layer / MetricFlow:**
```bash
# List all metrics
dbt sl list metrics
# Or read YAML directly
find <dbt_project_path> -name "*.yml" | xargs grep -l "^metrics:" | head -20
```

**LookML (Looker):**
```bash
# Find all measure definitions
grep -r "type: \(sum\|count\|average\|count_distinct\|max\|min\)" <lookml_path> --include="*.lkml" -l
```

**dbt schema.yml measures (if using dbt Semantic Layer but not MetricFlow):**
```bash
find <dbt_project_path> -name "*.yml" | xargs grep -l "measures:"
```

For each metric/measure found, record:
- Name
- Source (dbt SL / LookML / schema.yml / BI tool)
- Definition (SQL expression or aggregation type + field)
- Grain / time dimensions available
- Description (if any)
- Domain

### Step 3: Identify Definition Conflicts

Flag conflicts when the same business concept is defined differently across sources. Common conflict patterns:

| Conflict type | Example |
|---|---|
| Filter difference | `active_users`: Looker filters last 30 days; dbt SL filters last 90 days |
| Aggregation difference | `revenue`: Looker uses SUM(gross); dbt SL uses SUM(net) |
| Grain difference | `orders`: Looker counts order lines; dbt SL counts order headers |
| Name collision | Two metrics named `conversion_rate` measuring different funnels |

For each conflict, document both definitions and flag for governance_design resolution.
---

## Step 3b: Take in definitions from systems Wire cannot read

The steps above read dbt, LookML and `schema.yml`, because those are text in a
repository. Plenty of business logic is not: SAP BW transformations, Hana SQL
views, SAC models, a Looker Studio data source, a spreadsheet that acts as
production.

There is no reader for those, and pretending otherwise is how a definition
register ends up covering only the systems that were easy. The intake path is
explicit instead:

```
--import <path>
```

`<path>` is a file or directory of exported SQL, model text, or a screenshot
transcription. For each definition it yields, record:

| Field | Rule |
|---|---|
| `source` | The system name, e.g. `sap_bw`, `hana`, `sac`, `looker_studio` |
| `object` | The object inside it, plus how it was obtained: `ZSD_GROSS_SALES.sql (manual export 2026-08-14)` |
| `expression` | The definition as written, verbatim. Not paraphrased |
| `export_date` | When the export was taken |
| `exported_by` | Who took it |

An imported definition is a first-class variant and participates in conflict
classification exactly like a dbt or LookML one. What it does not carry is
freshness: the source may have changed since the export, so `export_date` and
`exported_by` are required, and a consuming command warns when an import is older
than the register entry that cites it.

**Never infer an expression.** If the export is a screenshot and the SQL is not
legible, record the definition as `unknown` with the evidence attached and the
person to ask. An invented expression is worse than a blank, because everything
downstream treats it as fact.

## What this convention does not do

- It does not decide which definition is right. `business_rules` records a
  decision with an approver; `metric_audit` recommends and defers to
  `governance_design`.
- It does not score coverage against real queries. That needs `query_audit`,
  which exists only in an `agentic_data_stack` release.
- It does not read Modality `.mml` models. That is
  `specs/utils/mml_import.md`, and a model there carries entities and
  relationships rather than metric expressions.
