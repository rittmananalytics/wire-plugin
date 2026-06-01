# Equivalency Report: {{ENGAGEMENT_NAME}} — Run {{RUN_NUMBER}}

**Release**: {{RELEASE_FOLDER}}
**Run date**: {{TODAY}}
**Run number**: {{RUN_NUMBER}}
**Source platform**: {{SOURCE_PLATFORM}}
**Target platform**: {{TARGET_PLATFORM}}

## Summary

| Metric | Value |
|--------|-------|
| Total objects checked | |
| Passing (all 5 checks) | |
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
