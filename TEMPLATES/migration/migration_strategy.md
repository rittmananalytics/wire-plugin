# Migration Strategy: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Generated**: {{TODAY}}
**Platform pair**: {{SOURCE_PLATFORM}} → {{TARGET_PLATFORM}}

## Translation Approach

### Data Type Mapping

See `wire/platform_pairs/{{PLATFORM_PAIR}}/type_mapping.md` for the full mapping. Key decisions for this engagement:

| Source Type | Target Type | Decision |
|------------|------------|---------|
| | | |

### SQL Dialect Translation

| Feature | Source Pattern | Target Pattern | Approach |
|---------|---------------|---------------|---------|
| | | | |

### dbt Configuration Changes

| Setting | Source Value | Target Value | Notes |
|---------|-------------|-------------|-------|
| adapter | | | |
| dispatch overrides | | | |
| partition/cluster config | | | |

### Connector Migration Approach

[Describe whether connectors will be cloned or recreated, and why]

### Security Migration Approach

[Describe how source roles/policies translate to target IAM/roles]

## Migration Phases

### Phase 1: Target Setup

**Entry criterion**: This strategy approved by client.
**Work**: Execute DDL scripts in `migration/target_setup_scripts/`.
**Exit criterion**: All schemas, tables, and roles created on target. Smoke test passes.
**Rollback**: Drop all created schemas and objects on target.
**Estimated duration**: N days

### Phase 2: Parallel Ingestion

**Entry criterion**: Target setup complete.
**Work**: Activate N Fivetran connectors to target destination.
**Exit criterion**: All connectors syncing successfully to target.
**Rollback**: Deactivate target connectors. Source connectors unaffected.
**Estimated duration**: N days

### Phase 3: dbt Migration

**Entry criterion**: Parallel ingestion running.
**Work**: Translate and validate N batches of dbt models.
**Exit criterion**: All batches translated, validated, and reviewed.
**Rollback**: Not applicable — source dbt project unchanged.
**Estimated duration**: N weeks

### Phase 4: Orchestration Migration

**Entry criterion**: dbt migration batches complete.
**Work**: Recreate N jobs on target orchestration configuration.
**Exit criterion**: All jobs created and passing manual test runs.
**Rollback**: Delete target jobs. Source jobs unaffected.
**Estimated duration**: N days

### Phase 5: Equivalency Validation

**Entry criterion**: Orchestration migration complete. At least 2 full target job runs complete.
**Work**: Run equivalency checks until checks_failing == 0.
**Exit criterion**: All equivalency checks pass (or accepted differences are formally agreed).
**Rollback**: Not applicable — read-only phase.
**Estimated duration**: N days to N weeks

### Phase 6: Cutover Rehearsal

**Entry criterion**: Equivalency validation complete.
**Work**: Execute the full cutover sequence on staging at production scale. Time each step.
**Exit criterion**: Sequence runs clean end to end, rollback proven to work, step timings recorded and fed into the runbook.
**Rollback**: Not applicable — staging only.
**Estimated duration**: 1 day

### Phase 7: Cutover

**Entry criterion**: Rehearsal passed.
**Work**: Execute cutover runbook during agreed maintenance window. Keep source live through the rollback window afterwards.
**Fast-rollback deadline**: [time limit after maintenance window starts — and no later than the first production write to target]
**Rollback window**: source kept live and rollback-ready for 7–14 days; decommission as a separate scheduled step after it closes.
**Estimated duration**: 1–4 hours cutover; rollback window 7–14 days; decommission ~1 day

## Equivalency Success Criteria

### Default Tolerances

| Check Type | Tolerance | Override Procedure |
|-----------|-----------|-------------------|
| Row count | ±0.1% | Update per-table tolerance in this section |
| Schema | Exact match (modulo expected type translations) | Document accepted column differences |
| Value sampling | ±1% on numeric stats | Document accepted statistical differences |
| Freshness | Within max(sync_frequency, 24h) of source | |
| dbt tests | 100% pass | Document known pre-existing test failures |
| Row-level checksum | Aggregate hash match over same row set | Document accepted canonicalisation differences |
| Business invariants | Exact for counts; ±0.01% for monetary sums | Define per invariant below |

### Business Invariants

Engagement-specific control totals that must reconcile between source and target. These confirm the data still *means* the same thing, not just that it moved.

| Invariant | Query (both platforms) | Tolerance |
|-----------|-----------------------|-----------|
| Total revenue | `SELECT SUM(amount) FROM orders` | ±0.01% |
| Active customer count | | exact |
| | | |

### Per-Table Overrides

| Table | Check Type | Custom Tolerance | Justification |
|-------|-----------|-----------------|--------------|
| | | | |

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

## Go/No-Go Checklist for Cutover

- [ ] All equivalency checks passing (or accepted differences formally agreed)
- [ ] All orchestration jobs passing manual test runs on target
- [ ] BI tool connections identified and change scripts prepared
- [ ] Full cutover rehearsed on staging at production scale; timings recorded
- [ ] Maintenance window communicated to all users
- [ ] Client executive sponsor confirmed
- [ ] Rollback team nominated and briefed; rollback decision tree agreed
- [ ] Rollback window agreed and source decommission scheduled after it
- [ ] No business-critical reporting deadline within 48h of cutover
- [ ] Monitoring alerts configured for target platform

## Notes

[Add strategy-specific decisions and context here]
