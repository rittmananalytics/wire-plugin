# Provenance Footer Template

Every response from the agentic data stack must end with this footer.

---
Source tier: [Semantic | Curated | Raw]
Dataset: [metric_name or project.schema.table_name]
Freshness: [YYYY-MM-DD HH:MM UTC | unknown]
Domain owner: [email]
---

## Tier Descriptions

**Semantic** — Answer derived from a defined semantic layer metric (dbt SL, MetricFlow, or LookML measure). Highest confidence. The metric definition is the canonical source of truth.

**Curated** — Answer derived from a governed canonical dbt model. High confidence. No semantic metric was available but the canonical table was used per governance design.

**Raw** — Answer required ad-hoc SQL not covered by a semantic metric or documented curated pattern. Use with care. Verify against a canonical dashboard before using in external reports.

## Freshness

Use the last successful dbt run timestamp from `target/run_results.json`:
```bash
jq '.metadata.generated_at' target/run_results.json
```

If dbt metadata is unavailable, use the last_modified timestamp of the canonical table from the warehouse information_schema, or "unknown" if neither is accessible.
