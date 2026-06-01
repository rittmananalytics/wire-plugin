# Migration Report: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Migration completed**: {{CUTOVER_DATE}}
**Platform pair**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}

## Executive Summary

Migration from {{SOURCE_PLATFORM}} to {{TARGET_PLATFORM}} completed on {{CUTOVER_DATE}}.

| Metric | Value |
|--------|-------|
| Total objects migrated | |
| Fivetran connectors | |
| Database tables | |
| dbt models | |
| Orchestration jobs | |
| Security roles/policies | |
| Final equivalency — passing | |
| Final equivalency — accepted differences | |
| Estimated effort | N hours |
| Actual effort | N hours |
| Cutover duration | N hours |
| Equivalency loops required | N |

## What Was Migrated

### Fivetran Connectors

N connectors migrated from [source destinations] to [target destinations]. All connectors syncing on schedule as of {{CUTOVER_DATE}}.

### Database Objects

N tables, N views recreated or translated on {{TARGET_PLATFORM}}.

Key structural decisions made during migration:
- [List key decisions from audit reviews and strategy sign-offs]

### dbt Models

N models translated across N batches. Translation patterns applied:
- [Summary of most common feature translations]

### Orchestration Jobs

N jobs recreated on [target orchestration configuration].

## Equivalency Outcomes

**Final state**: N/N checks passing, N accepted differences.

### Final Equivalency Check Summary

| Check Type | Passing | Failing |
|-----------|---------|---------|
| Row count | | |
| Schema | | |
| Value sampling | | |
| Freshness | | |
| dbt tests | | |

### Accepted Differences

| Object | Difference | Business Justification | Agreed By |
|--------|-----------|----------------------|----------|
| | | | |

### Equivalency Loop History

| Run | Date | Passing | Failing | Actions Taken |
|-----|------|---------|---------|--------------|
| | | | | |

## Issues Encountered and Resolutions

| Issue | Phase | Resolution | Time to Resolve |
|-------|-------|-----------|----------------|
| | | | |

## Lessons Learned

### What worked well

1. [Specific practice that helped]
2. [Specific practice that helped]
3. [Specific practice that helped]

### What would be done differently

1. [Improvement for future migrations]
2. [Improvement for future migrations]

### Recommendations for future migrations

1. [General recommendation]
2. [General recommendation]

## Source Platform Decommission Plan

### Recommended Timeline

| Action | Recommended Date | Owner |
|--------|-----------------|-------|
| Confirm target platform stable (no rollback needed) | +30 days | RA |
| Archive source Fivetran connectors (already paused) | +30 days | Client IT |
| Export source data warehouse DDL as archive | +45 days | Client engineering |
| Disable source platform credentials | +60 days | Client IT |
| Terminate source platform subscription | +90 days | Client finance |

### Objects to Retain on Source (if any)

| Object | Retention Reason | Retention Period |
|--------|-----------------|-----------------|
| | | |

### Estimated Cost Savings After Decommission

| Item | Monthly Cost | Annual Saving |
|------|------------|--------------|
| Source platform compute | | |
| Source platform storage | | |
| Fivetran source connectors (archived) | | |
| **Total** | | |

## Effort Comparison

| Phase | Estimated Hours | Actual Hours | Variance |
|-------|----------------|-------------|---------|
| Audit (all 5) | | | |
| Migration inventory | | | |
| Migration strategy | | | |
| Target setup | | | |
| Ingestion migration | | | |
| dbt migration | | | |
| Orchestration migration | | | |
| Equivalency validation | | | |
| Cutover | | | |
| **Total** | | | |

## Notes

[Add any post-migration observations here]
