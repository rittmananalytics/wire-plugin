# Cutover Runbook: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Platform pair**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}
**Maintenance window**: {{MAINTENANCE_WINDOW_DATE}} at {{MAINTENANCE_WINDOW_TIME}} ({{TIMEZONE}})
**Rollback deadline**: T+120min from maintenance window start

## Pre-Cutover Checklist

Complete all items before the maintenance window begins:

- [ ] All equivalency checks passing (or accepted differences formally signed off)
- [ ] Final equivalency run completed within 24h of cutover
- [ ] All Fivetran target connectors active and syncing on schedule
- [ ] Target dbt project validated — all tests pass
- [ ] Target orchestration jobs created and passing manual test runs
- [ ] BI tool connection strings identified (list below)
- [ ] Application config changes identified (list below)
- [ ] Maintenance window communicated to all users (template below)
- [ ] Rollback decision owner nominated: {{ROLLBACK_OWNER}}
- [ ] Rollback procedure rehearsed with on-call team
- [ ] No month-end / quarter-end reporting deadline within 48h

## Connection Strings to Update

| System | Current Connection | New Connection | Owner |
|--------|------------------|----------------|-------|
| | | | |

## Timed Cutover Sequence

| Time | Action | Owner | Verification |
|------|--------|-------|-------------|
| T-48h | Final equivalency run and sign-off | RA lead | All checks passing |
| T-24h | Send maintenance window notification to all users | RA lead | Notification sent |
| T-0 | Pause all writes to source platform | RA engineer | Confirm no new writes |
| T+15min | Final row count comparison (source vs target) | RA engineer | Counts within tolerance |
| T+30min | Update connection strings in BI tools | Client IT | BI tools connecting to target |
| T+30min | Update application config files | Client engineering | Apps connecting to target |
| T+45min | Activate target orchestration job schedules | RA engineer | Jobs running on schedule |
| T+60min | Pause / archive source Fivetran connectors | RA engineer | Source connectors paused |
| T+75min | Smoke test — run key reports on target | Client analyst | Reports match expected output |
| T+90min | Monitor for errors and alerts | RA engineer | No critical alerts |
| T+120min | **GO/NO-GO DECISION POINT** | {{ROLLBACK_OWNER}} | Full cutover confirmed OR rollback initiated |

## Rollback Procedure

Valid until T+120min. After this point, rollback requires a separate remediation plan.

1. Reactivate source Fivetran connectors (RA engineer — 5 min)
2. Revert BI tool connection strings to source (Client IT — 10 min)
3. Revert application config to source (Client engineering — 10 min)
4. Pause target orchestration job schedules (RA engineer — 5 min)
5. Send rollback notification to users (RA lead — 10 min)
6. Document rollback reason and schedule retrospective

**Total rollback time estimate**: ~40 minutes

## Post-Cutover Monitoring Checklist

For the 48 hours following cutover:

- [ ] All Fivetran target connectors syncing on schedule
- [ ] All orchestration jobs completing successfully
- [ ] All dbt tests passing on target
- [ ] Key business reports validated by client analysts
- [ ] No unexpected data quality alerts
- [ ] Source platform stable (for rollback window)

## Communication Templates

### Maintenance Window Notification

```
Subject: Data Platform Maintenance — [DATE] [TIME]

We will be performing a planned maintenance window on [DATE] from [START_TIME] to [END_TIME] ([TIMEZONE]).

During this window, the following systems will be temporarily unavailable:
- [List of affected BI tools, dashboards, reports]

After the maintenance window, all systems will reconnect to our new data platform. You may need to refresh your browser or reconnect your BI tool.

If you have any questions, contact [CONTACT].
```

### Go-Live Announcement

```
Subject: Data Platform Migration Complete — Action Required

Our data platform migration is complete. All data is now running on [TARGET_PLATFORM].

Action required: [If any manual reconnection steps are needed for users]

If you experience any issues, contact [CONTACT] immediately.
```

## Known Accepted Differences

| Object | Difference | Business Justification |
|--------|-----------|----------------------|
| | | |

## Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| RA Engagement Lead | | |
| Rollback Decision Owner | | |
| Client IT | | |
| Client Engineering | | |
