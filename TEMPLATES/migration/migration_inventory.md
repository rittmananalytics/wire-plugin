# Migration Inventory: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Source → Target**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}

## Executive Summary

| Metric | Value |
|--------|-------|
| Total objects in scope | |
| Fivetran connectors | |
| Database tables | |
| Views (to translate) | |
| dbt models | |
| Orchestration jobs | |
| Security roles / policies | |
| Total effort estimate | N hours |
| Estimated migration duration | N weeks |

## Phase Plan

| Phase | Work Items | Est. Hours | Duration | Dependencies |
|-------|-----------|-----------|----------|-------------|
| 1. Target setup | Create schemas, tables, roles | | | Strategy approved |
| 2. Parallel ingestion | Activate N Fivetran connectors | | | Target setup done |
| 3. dbt migration | Translate N batches | | | Ingestion running |
| 4. Orchestration migration | Recreate N jobs | | | dbt batches done |
| 5. Equivalency validation | Run checks until 0 failing | | | All above done |
| 6. Cutover | Redirect production workloads | 1 day | | Equivalency complete |

## Unified Object Catalog

### Fivetran Connectors

| Connector | Service Type | Destination Schema | Complexity | Migration Approach | Linked dbt Sources |
|-----------|-------------|-------------------|-----------|-------------------|-------------------|
| | | | | | |

### Database Objects

| Database | Schema | Object | Type | Volume Tier | Migration Approach | Feature Tags | Linked dbt Models |
|----------|--------|--------|------|-------------|-------------------|-------------|------------------|
| | | | | | | | |

### dbt Models

| Model | Layer | Batch | Complexity | Feature Tags | Upstream Sources | Orchestration Jobs |
|-------|-------|-------|-----------|-------------|-----------------|-------------------|
| | | | | | | |

### Orchestration Jobs

| Job | Type | Schedule | Criticality | Migration Approach | dbt Models Executed |
|-----|------|---------|------------|-------------------|-------------------|
| | | | | | |

## Dependency Graph

```
[Adjacency list or Mermaid diagram]
```

## Risk Summary

| Risk | Count | Impact |
|------|-------|--------|
| High-complexity connectors | | |
| Complex dbt models | | |
| Objects requiring evaluation | | |
| Models without tests | | |

## Objects Requiring Evaluation

| Object | Type | Open Question | Owner |
|--------|------|--------------|-------|
| | | | |

## Notes

[Add scope decisions and cross-references here]
