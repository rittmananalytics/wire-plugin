# Equivalency Report: {{ENGAGEMENT_NAME}} — Run {{RUN_NUMBER}}

**Release**: {{RELEASE_FOLDER}}
**Run date**: {{TODAY}}
**Run number**: {{RUN_NUMBER}}
**Source platform**: {{SOURCE_PLATFORM}}
**Target platform**: {{TARGET_PLATFORM}}
**Migration scope**: {{MIGRATION_SCOPE}}  <!-- full_migration | tenant_carveout -->
**Tenant predicate**: {{TENANT_PREDICATE}}  <!-- tenant_carveout only: the WHERE clause applied to every data-bearing check; blank for full_migration -->

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
