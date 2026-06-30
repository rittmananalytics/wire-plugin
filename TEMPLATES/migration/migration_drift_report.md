# Migration Drift Report: {{ENGAGEMENT_NAME}}

**Release**: {{RELEASE_FOLDER}}
**Run date**: {{TODAY}}
**Live source HEAD (drift_head)**: {{DRIFT_HEAD}}
**Compared against**: each model's `last_migrated_commit` in the migration register

## Summary

| Classification | Count |
|----------------|-------|
| Modified (drifted) | |
| Removed | |
| New (unmigrated) | |
| Unchanged | |
| Downstream syncs flagged | |
| Masking changes | |

## Per-model drift

| Model | Classification | Change summary | Prior equivalence | New state |
|-------|----------------|----------------|-------------------|-----------|
| | modified/removed/new/unchanged | | pass@T / fail / none | drifted/removed/pending |

<!-- "validated, now drifted" = last_validated_commit == old last_migrated_commit; its prior pass is stale. -->

## Downstream Hightouch syncs flagged

<!-- From audit/lineage/model_sync_map.json. A re-migrated/removed Gold model flags every sync that reads it. -->

| Triggering model | Sync | Destination | Config diff (what the drift implies) | Action |
|------------------|------|-------------|--------------------------------------|--------|
| | | | | re-validate / re-point / retire |

## Masking changes (policy-tag hook)

<!-- Source meta.masking_policy added/changed/removed → re-run target-setup policy-tag generation for the affected objects. -->

| Model | Column | Masking change | Required action |
|-------|--------|----------------|-----------------|
| | | added / changed / removed | re-run `/wire:target-setup-generate` (policy tags) for `<object>` |

## Next actions

```
# Re-migrate drifted models, then re-validate in baseline mode:
/wire:dbt-migration-generate {{RELEASE_FOLDER}} --select <drifted models>
/wire:equivalency-validate {{RELEASE_FOLDER}} --baseline --batch <N>
# Where masking changed:
/wire:target-setup-generate {{RELEASE_FOLDER}}   # regenerate 04_security.sql policy tags
```
