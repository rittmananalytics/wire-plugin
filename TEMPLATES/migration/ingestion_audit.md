# Ingestion Audit: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Data source**: {{DATA_SOURCE}}
**Source platform**: {{SOURCE_PLATFORM}}

## Summary

| Metric | Value |
|--------|-------|
| Total connectors | {{TOTAL_CONNECTORS}} |
| Included in migration | {{INCLUDED_COUNT}} |
| Excluded | {{EXCLUDED_COUNT}} |
| Low complexity | {{LOW_COUNT}} |
| Medium complexity | {{MEDIUM_COUNT}} |
| High complexity | {{HIGH_COUNT}} |
| With column exclusions | {{COLUMN_EXCLUSION_COUNT}} |

## Connector Catalog

| Connector ID | Connector Name | Service Type | Destination Schema | Sync Frequency | Status | Row Count | Complexity | Include | Notes |
|-------------|---------------|-------------|-------------------|---------------|--------|----------|-----------|---------|-------|
| | | | | | | | | | |

## By Service Type

| Service Type | Count | Complexity Distribution |
|-------------|-------|------------------------|
| | | |

## Excluded Connectors

| Connector | Reason for Exclusion |
|-----------|---------------------|
| | |

## Column Exclusions

| Connector | Schema | Table | Column | Exclusion Reason |
|-----------|--------|-------|--------|-----------------|
| | | | | |

## Recommended Migration Order

1. Low complexity connectors (activate first — lowest risk)
2. Medium complexity connectors
3. High complexity connectors (activate last — require most monitoring)

## Notes

[Add any additional context or findings here]
