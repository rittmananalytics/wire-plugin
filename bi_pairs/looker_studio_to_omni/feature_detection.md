# Looker Studio to Omni: feature detection

Where each construct lives in the captured responses (app version 20261004_0802). `looker_studio_extract.py` reads these paths; if one is missing where it is required, the extractor stops with `CaptureError` rather than writing a partial report.

## Report (`getReport`)

| Construct | Path |
|---|---|
| Name, owner flags, modified date | `reportConfig.shareable` |
| Draft definition | `reportConfig.page[]`, `reportConfig.report` |
| Published definition | `publishedReportRevision.reportConfig` (used when `reportConfig.page` is empty) |
| Unpublished changes exist | `hasChangesToPublish: true` |
| Navigation: sections, page names, order, hidden pages | `reportConfig.navigationInfo.navItems[]` (`section`, `page.pageId`, `page.displayName`, `page.hiddenFromViewer`) |
| Canvas size, navigation style, scaling | `report.attributeConfig.reportAttribute` (`width`, `height`, `viewModeNav`, `viewModeScale`) |
| Theme | `report.resource.theme`, `report.propertyConfig.reportProperty.themeConfig` |
| Components shown on every page | `report.componentConfig[]` |
| Report-level filters | `report.propertyConfig.reportProperty.filters[]` (ids) |
| Filter definitions | `report.resource.filter.entry[]` (`key`, `value.filterDefinition.filterExpression`) |
| Blends | `report.resource.dataViewResource.entry[]` (`value.blockDatasource`) |
| Blend join tree | `blocks[].treeQueryBlockConfig.join` (`left`, `right`, `type`, `joinKeyPair[]`); a leaf is `query` with `datasourceId` and `concepts[]` |
| Parameters | `report.resource.parameterResource[]`, `unifiedParameterResource[]` (kept raw; none seen in a real report yet) |
| Data source aliases | `report.resource.datasourceAlias[]` |

## Page and component

| Construct | Path |
|---|---|
| Page dataset, date range field, filters | `page.propertyConfig.pageProperty` |
| Component groups | `page.groupConfig[]` |
| Components (nested) | `page.componentConfig[]`, each with its own `componentConfig[]` |
| Type | `componentConfig[].type` |
| Position and size (pixels) | `attributeConfig.componentAttribute` (`top`, `left`, `width`, `height`) |
| Stacking order | order within `componentConfig[]` |
| Data source or blend | `propertyConfig.componentProperty.dataset` (`datasetType`, `datasetId`) |
| Dimensions and metrics | `componentProperty.dimensions.labeledConcepts[]`, `metrics.labeledConcepts[]` (concept names) |
| Field definitions | `conceptDefs[]` (`name`, `queryTimeTransformation.dataTransformation`: `sourceFieldName`, `aggregation`, `textFormula`) |
| Sort, filters, row limit, comparison | `componentProperty.sort[]`, `filters[]`, `row`, `compareDateDuration` |
| Text box content | `componentProperty.descriptionProperty.text` (HTML) |

## Data source (`getSchema`, `getBlockDatasource`)

| Construct | Path |
|---|---|
| Field list (view access) | `getSchema`: `schema.dimensions[]`, `schema.metrics[]` with `underlyingConnectorDataType` |
| Definition (Edit access) | `getBlockDatasource`: `published` (or `draft`) |
| Connection | `blocks[]` with `type: 2`: `connectorBlockConfig.connectorConfig` |
| Fields with formulas | `datasourceBlock.fields[]` (`textFormula`, `createdBy`, `defaultAggregationType`) |
| Refused | HTTP 403, `errorStatus.reasonStr: PERMISSION_DENIED` |

`getSchema` is only requested for data sources used on a page that was opened, so the capture opens every page. When it is still missing, the extractor takes the field list from `getBlockDatasource`.

## Chart data (`batchedDataV2`)

| Construct | Path |
|---|---|
| Which chart | `dataRequest[].requestContext.reportContext` (`pageId`, `componentId`, `displayType`) |
| Query specification | `dataRequest[].datasetSpec` (`dataset`, `queryFields`, `filters`, `dateRanges`, `timezone`) |
| Rows | `dataResponse[].dataSubset[].dataset.tableDataset` (`columnInfo`, `column[]`, `size`) |
| Nulls | each column lists only non-null values; `nullIndex` gives the null row positions |
| Main, comparison, totals | `viewTags.compareIndex` 0 or 1; `viewTags.isTotals`; `isMin` and `isMax` subsets are axis helpers |
| BigQuery job | `biJobUrl` (`project=<billing project>&j=bq:<location>:<job id>`) |
