# /deploy-lookml Command

Deploy LookML files to Looker with automatic validation.

## Usage

### Single File

```
/deploy-lookml <local-file-path> <project-id>
```

**Example:**
```
/deploy-lookml /lookml/dashboards/financial.dashboard.lookml analytics
```

### All Files from Specification

```
/deploy-lookml --all --spec <spec-file-path> <project-id>
```

**Example:**
```
/deploy-lookml --all --spec /docs/design/dashboard-specification.md analytics
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `<local-file-path>` | Yes (single) | Path to local LookML file |
| `<project-id>` | Yes | Looker project ID (e.g., `analytics`) |
| `--all` | No | Deploy all files from specification |
| `--spec <path>` | With `--all` | Path to specification file |

## Behavior

1. **Read** local LookML file(s)
2. **Enable** Looker development mode via `dev_mode(devMode: true)`
3. **Upload** to Looker project (auto-convert `.lookml` → `.lkml`)
4. **Test** all queries:
   - For views/explores: Sample query with 1 row
   - For dashboards: Each element's query individually
5. **Report** results with pass/fail status
6. **Iterate** on failures if requested

## File Extension Handling

Local files can use `.lookml` extension (standard convention). The command automatically converts to `.lkml` when uploading to Looker via MCP, as the Looker API requires this extension.

## Output Example

### Single Dashboard Deployment

```
Deploying: financial.dashboard.lookml → analytics/dashboards/pdd_financial.dashboard.lkml

Enabling dev mode... ✓
Uploading file... ✓

Testing 12 elements...
  ✅ monthly_spending_kpi: 2450.00
  ✅ spending_trend: 24 rows
  ✅ spending_by_category: 8 categories
  ✅ top_merchants: 10 rows
  ⚠️ avg_transaction_kpi: null (no data in filter period)
  ...

Result: 11/12 queries passed, 1 data warning
Dashboard deployed successfully!
```

### Batch Deployment

```
Reading specification: /docs/design/dashboard-specification.md
Found 6 dashboards to deploy

[1/6] financial.dashboard.lookml
  Uploading... ✓
  Testing 12 elements... 12/12 passed ✅

[2/6] health_wellbeing.dashboard.lookml
  Uploading... ✓
  Testing 15 elements... 15/15 passed ✅

[3/6] productivity.dashboard.lookml
  Uploading... ✓
  Testing 16 elements... 14/16 passed ⚠️ (2 data warnings)

...

## Deployment Summary

| File | Status | Queries | Issues |
|------|--------|---------|--------|
| financial.dashboard.lkml | ✅ Deployed | 12/12 | None |
| health_wellbeing.dashboard.lkml | ✅ Deployed | 15/15 | None |
| productivity.dashboard.lkml | ⚠️ Deployed | 14/16 | 2 sparse data |
| communications.dashboard.lkml | ✅ Deployed | 18/18 | None |
| entertainment.dashboard.lkml | ✅ Deployed | 11/11 | None |
| cross_domain.dashboard.lkml | ✅ Deployed | 8/8 | None |

Total: 6 dashboards, 78/80 queries passed
```

## Error Handling

If a query fails:

1. The command reports the specific error
2. Shows which field(s) caused the issue
3. Suggests fixes based on common error patterns
4. Offers to retry after manual fix

**Common Fixes:**
- Field not found → Check `get_dimensions`/`get_measures` for correct names
- Unknown explore → Verify explore name in model file
- Filter error → Use Looker filter syntax ("7 days", "NOT NULL")

## Related Commands

- `/deploy-lookml --help` - Show this help
- `/deploy-lookml --dry-run <file> <project>` - Validate without uploading
- `/deploy-lookml --force <file> <project>` - Skip confirmation prompts
