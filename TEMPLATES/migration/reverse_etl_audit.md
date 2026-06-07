# Reverse ETL Audit: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Data source**: {{DATA_SOURCE}}
**Tool**: {{REVERSE_ETL_TOOL}}
**Source platform**: {{SOURCE_PLATFORM}}

## Summary

| Metric | Value |
|--------|-------|
| Total syncs | {{TOTAL_SYNCS}} |
| Included in migration | {{INCLUDED_COUNT}} |
| Decommission candidates | {{DECOMMISSION_COUNT}} |
| Low complexity | {{LOW_COUNT}} |
| Medium complexity | {{MEDIUM_COUNT}} |
| High complexity | {{HIGH_COUNT}} |
| Lightning engine syncs | {{LIGHTNING_COUNT}} |
| dbt model syncs | {{DBT_MODEL_COUNT}} |

## Migration Approach Distribution

| Approach | Count | Notes |
|----------|-------|-------|
| repoint | | Model SQL is portable; re-point source after warehouse cutover |
| rewrite_model | | SQL uses source-platform dialect; translate before re-pointing |
| rebuild | | Customer Studio audience or Journey; full rebuild required |
| decommission | | Disabled or unused; exclude from migration |

## Sync Catalog

| Sync ID | Sync Name | Model Name | Model Type | Destination | Destination Type | Mode | Schedule | Status | Last Run | Row Volume | Sync Engine | Warehouse Objects | Complexity | Approach | Include | Notes |
|---------|-----------|-----------|-----------|------------|-----------------|------|----------|--------|----------|-----------|------------|------------------|-----------|---------|---------|-------|
| | | | | | | | | | | | | | | | | |

## Warehouse Dependency Map

Maps each sync to the warehouse tables/views it depends on. These objects must exist on the target platform before the sync can be re-pointed.

| Sync Name | Warehouse Objects | Migration Batch | Ready to Re-point |
|-----------|-----------------|----------------|------------------|
| | | | |

## dbt Model Sync Dependencies

Syncs referencing dbt models cannot be re-pointed until the corresponding dbt migration batch is complete.

| Sync Name | dbt Model | dbt Audit Status | Migration Batch | Earliest Re-point Phase |
|-----------|-----------|-----------------|----------------|------------------------|
| | | | | |

## Lightning Engine Syncs

The following syncs use the Lightning sync engine. The target warehouse must have these schemas provisioned (Hightouch creates them automatically on first run, subject to `CREATE SCHEMA` permissions):

```sql
CREATE SCHEMA IF NOT EXISTS hightouch_planner;
CREATE SCHEMA IF NOT EXISTS hightouch_audit;
```

| Sync Name | Current Source | Action Required |
|-----------|---------------|----------------|
| | | |

## Decommission Candidates

| Sync Name | Destination | Last Successful Run | Reason for Decommission |
|-----------|------------|-------------------|------------------------|
| | | | |

## Recommended Re-point Order

1. Low complexity / repoint syncs with no dbt model dependencies (activate first — lowest risk)
2. Low/Medium complexity / repoint syncs depending on early dbt migration batches
3. Medium complexity / rewrite_model syncs (after model SQL translation is validated)
4. High complexity / rebuild syncs — Customer Studio audiences and Journeys (last — require most testing)

## Notes

[Add any additional context or findings here]
