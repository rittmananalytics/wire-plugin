# Cutover Runbook: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Platform pair**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}
**Maintenance window**: {{MAINTENANCE_WINDOW_DATE}} at {{MAINTENANCE_WINDOW_TIME}} ({{TIMEZONE}})
**Fast-rollback deadline**: T+120min from maintenance window start (or the first production write to target, whichever comes first)
**Rollback window**: source kept live and rollback-ready until {{DECOMMISSION_DATE}} (default 7–14 days post-cutover)

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
- [ ] Full cutover rehearsed end-to-end on staging at production scale; step timings recorded and fed into the sequence below
- [ ] Rollback decision owner nominated: {{ROLLBACK_OWNER}}
- [ ] Rollback procedure rehearsed with on-call team
- [ ] Source-platform decommission scheduled for {{DECOMMISSION_DATE}} (after rollback window closes)
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

The **true point of no return is the first successful production write to the target**, not the clock. Sequence smoke tests and validation to complete before any production write lands on target. Fast rollback is valid until that write, and no later than T+120min.

### Fast rollback steps

1. Reactivate source Fivetran connectors (RA engineer — 5 min)
2. Revert BI tool connection strings to source (Client IT — 10 min)
3. Revert application config to source (Client engineering — 10 min)
4. Pause target orchestration job schedules (RA engineer — 5 min)
5. Send rollback notification to users (RA lead — 10 min)
6. Document rollback reason and schedule retrospective

**Total fast-rollback time estimate**: ~40 minutes

### Decision tree — what warrants a rollback

| Issue | Action |
|-------|--------|
| Data loss or corruption | **Roll back immediately** — no evaluation |
| Performance regression < ~2× slower | Optimise in place (clustering, partitioning, slots); do not roll back |
| Performance regression > ~2× slower, no quick fix | Roll back, investigate |
| Minor data discrepancy (near accepted tolerance) | **Fix forward** — run reconciliation; do not roll back |
| Cosmetic / non-blocking | Log, fix forward, proceed |

### Rollback window

Keep the source platform live and rollback-ready until {{DECOMMISSION_DATE}} (7–14 days post-cutover). T+120min ends the *fast* rollback; the window covers issues that only surface across a full business cycle (month-end close, weekly batch). Decommission the source as a distinct scheduled step only after the window closes with no rollback triggered.

## Post-Cutover Monitoring Checklist

For the first 48 hours following cutover:

- [ ] All Fivetran target connectors syncing on schedule
- [ ] All orchestration jobs completing successfully
- [ ] All dbt tests passing on target
- [ ] Key business reports validated by client analysts
- [ ] No unexpected data quality alerts
- [ ] Source platform stable (kept live for rollback window)

Across the full rollback window (until {{DECOMMISSION_DATE}}):

- [ ] First month-end / weekly batch cycle completed on target without discrepancy
- [ ] Business invariants re-checked after the first full cycle (revenue, key counts)
- [ ] No rollback trigger raised

## Source Decommission (after rollback window closes)

- [ ] Rollback window elapsed with no trigger raised
- [ ] Final snapshot / export of source taken and archived
- [ ] Source connectors and jobs disabled
- [ ] Source platform access revoked and resources decommissioned
- [ ] Decommission confirmed with client sponsor

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
