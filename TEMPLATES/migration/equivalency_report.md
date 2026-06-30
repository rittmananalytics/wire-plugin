# Equivalency Report: {{ENGAGEMENT_NAME}} — Run {{RUN_NUMBER}}

**Release**: {{RELEASE_FOLDER}}
**Run date**: {{TODAY}}
**Run number**: {{RUN_NUMBER}}
**Source platform**: {{SOURCE_PLATFORM}}
**Target platform**: {{TARGET_PLATFORM}}
**Migration scope**: {{MIGRATION_SCOPE}}  <!-- full_migration | tenant_carveout -->
**Tenant predicate**: {{TENANT_PREDICATE}}  <!-- tenant_carveout only: the WHERE clause applied to every data-bearing check; blank for full_migration -->

## Run Metadata

<!-- Captured on every run so the result is reproducible. Live runs set mode=live and leave the baseline fields blank. -->

| Field | Value |
|-------|-------|
| Mode | {{MODE}}  <!-- live | baseline --> |
| Batch | {{BATCH}}  <!-- N or all --> |
| Baseline instant T (UTC) | {{BASELINE_T}}  <!-- baseline mode only --> |
| Snowflake clone location | {{CLONE_LOCATION}}  <!-- e.g. <db>.wire_baseline AT(TIMESTAMP => T) --> |
| Target Bronze watermark | {{TARGET_WATERMARK}}  <!-- e.g. _fivetran_synced <= T (per connector) --> |
| Source repo commit / snapshot SHA | {{SOURCE_COMMIT}} |

## Expected Type Translations Applied

<!-- Cross-platform type changes normalised by the baseline allow-list (VARIANT→JSON/STRING, TIMESTAMP_NTZ→DATETIME, NUMBER-scale rounding, etc.). Recorded as expected — NOT failures. -->

| Object | Column | Source type | Target type | Normalisation applied |
|--------|--------|-------------|-------------|----------------------|
| | | | | |

## Summary

<!-- For tenant_carveout runs, every check below was scoped to the tenant predicate above on both source and target. No new check types are added — min/max is part of value sampling, and checksum and aggregate control totals already exist. -->


| Metric | Value |
|--------|-------|
| Total objects checked | |
| Passing (all applicable checks) | |
| Failing (any check) | |
| Pass rate | |

## Results by Check Type

| Check Type | Passing | Failing |
|-----------|---------|---------|
| Row count | | |
| Schema | | |
| Value sampling | | |
| Freshness | | |
| dbt tests | | |
| Row-level checksum | | |
| Business invariants | | |

## Failing Objects

| Object | Schema | Failing Checks | Severity | Notes |
|--------|--------|---------------|---------|-------|
| | | | | |

## Top 10 Failures by Severity

| Rank | Object | Check Type | Failure Detail | Recommended Action |
|------|--------|-----------|---------------|-------------------|
| 1 | | | | |

## Accepted Differences

| Object | Check Type | Difference | Business Justification |
|--------|-----------|-----------|----------------------|
| | | | |

## Loop History

| Run | Date | Passing | Failing | Delta |
|-----|------|---------|---------|-------|
| | | | | |

## Investigation Notes

[Populated by /wire:equivalency-investigate commands]

## Next Steps

If `checks_failing > 0`:
```
Investigate specific failures:
/wire:equivalency-investigate {{RELEASE_FOLDER}} --object <table_or_model>

Apply fixes:
/wire:equivalency-fix {{RELEASE_FOLDER}} --object <name> --approach "<description>"

Re-run all checks:
/wire:equivalency-validate {{RELEASE_FOLDER}}
```

If `checks_failing == 0`:
```
All checks passing. Cutover is unblocked.
/wire:cutover-generate {{RELEASE_FOLDER}}
```
