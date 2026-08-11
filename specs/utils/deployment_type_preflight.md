---
description: Internal utility — pre-flight check that a translated model's column types are validated against the REAL deployment warehouse, not a scratch/sample validation project whose types differ
---

# Deployment Warehouse Type Pre-Flight Utility

A shared utility for `dbt-migration-generate` and `equivalency-validate`. Models are frequently generated and validated against a scratch, sample, or playground warehouse whose column **types** differ from the real deployment target — native JSON vs JSON-as-STRING, `TIMESTAMP` vs `DATETIME`, a numeric landed as STRING. A model that builds clean in that validation warehouse then errors on deploy, because a type-sensitive construct (a `TIMESTAMP()` wrap, a `PARSE_JSON`, an implicit join coercion) only fails against the deployment warehouse's actual types. Row-level equivalency never sees this — it compares data, not the type surface the DDL will hit.

This pre-flight closes that gap: it reads the **deployment** warehouse's actual column types and flags the type-divergence patterns declared for the active platform pair, before anyone opens a PR. It is dialect-agnostic — the pattern list comes from the pair, so new pairs inherit the check automatically.

## Inputs (provided by the calling spec)

- `release_folder` — the release folder under `.wire/releases/`
- `models` — the in-scope translated models (with their translated SQL and companion YAML)
- `platform_pair` — resolved from `status.md` `source_platform`/`target_platform` (or a `--config` overlay)
- `validation_target` — the profile/project the model was generated/validated against (the scratch/sample/playground warehouse, if any)
- `deployment_target` — the profile/project the model will actually deploy to. Resolve from the deployment profile / `{{ target.database }}` as declared for the engagement (`migration.deployment_project` in `status.md` if set, else the prod-like target in `profiles.yml`)

## Procedure

### Step 1: Read the deployment warehouse's actual column types

Query the **deployment** warehouse — never the validation warehouse — for the actual column types of every relation each in-scope model reads or writes. Use the platform's catalog: `INFORMATION_SCHEMA.COLUMNS` (BigQuery: dataset-scoped; Snowflake: `db.INFORMATION_SCHEMA.COLUMNS`), or the target MCP's `get_table_info`/schema-lookup tool. For a BigQuery deployment target, route the lookup through `bigquery_mcp_fallback.md` (`operation: schema_lookup`) on a connection failure — a metadata-read outage is not a type divergence and must not be reported as one.

If the deployment warehouse is unreachable and no cached deployment schema exists, stop and report — this check cannot be satisfied against the validation warehouse's types, and silently substituting them is the exact failure mode it exists to prevent.

### Step 2: Load the pair's type-divergence patterns

Read the **"Deployment type-divergence patterns"** section of the active pair's `translation_guide.md`. This is the sourced, per-pair rule list — do **not** hardcode a dialect's patterns here. Each pattern names a construct in the translated SQL, the deployment column type it is sensitive to, and the failure it produces. If an engagement override file exists at `.wire/engagement/platform_pair_overrides/{pair}/type_divergence.md`, layer it on top (an override wins on the same pattern id).

For Snowflake → BigQuery the pair declares at least:
- a `TIMESTAMP()` (or `DATETIME()`) wrap applied to a column that is **already** that type at deployment — a redundant/erroring cast;
- `PARSE_JSON` / `JSON_VALUE` / `JSON_QUERY` / `JSON_TYPE` applied to a `STRING` deployment column (or a native-`JSON` function applied where the column landed as STRING, or vice-versa);
- an implicit `STRING = INT64` (or other cross-type) join coercion the source relied on and the target rejects.

### Step 3: Flag divergence against the deployment types

For every in-scope model, match each pattern against the translated SQL using the deployment column types read in Step 1. A pattern fires only when the deployment type actually triggers it — e.g. `PARSE_JSON(col)` fires only when `col` is `STRING` at deployment, not when it is native `JSON`. Record each hit with: model, `file:line`, the construct, the deployment column and its actual type, the pattern id, and the fix hint from the pair.

### Step 4: Warn explicitly when the validation warehouse differs from deployment

Compare `validation_target` and `deployment_target`. When they differ **at all** — different project, dataset, or any column whose type differs between the two — emit an explicit warning rather than passing silently: name the warehouses and every column whose type differs, so the reviewer knows the model was validated somewhere its types don't match deployment. A model can clear every data check in the validation warehouse and still carry a latent deploy-time type error; the warning is what makes that visible. When the two targets are the same warehouse, record "validation and deployment warehouse are the same — no type-drift risk" so the absence of a warning is a decision on the record, not an omission.

## Output (returned to the calling spec)

A structured result the caller folds into its own report:
- `deployment_target` and `validation_target` (and whether they differ)
- per-model divergence findings (model, `file:line`, construct, deployment column + type, pattern id, fix hint)
- the explicit same/differ warning from Step 4
- `status`: `pass` (no divergence, or validation == deployment) | `warn` (validation ≠ deployment, no firing pattern) | `fail` (at least one pattern fired against the deployment types)

The caller decides how a `fail` gates its own flow (`dbt-migration-generate` records it in the batch summary and the model's `.diff.md`; `equivalency-validate` records it in the equivalency report). This utility never writes to a warehouse and never edits a model.
