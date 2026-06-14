---
sidebar_position: 17
title: "Tutorial: Upgrading Your Release"
---

# Tutorial: Upgrading Your Release

## What this tutorial covers

This tutorial shows how to upgrade an existing Wire release folder to match a newer version of the plugin. It covers why upgrades are necessary, what `/wire:upgrade` does and does not touch, and how to verify that the upgrade completed correctly — using a real-world scenario of a dormant engagement resuming after a six-week pause.

## Scenario

| | |
|-|-|
| **Client** | Pennant Capital Management |
| **Release** | `01-pennant-platform` |
| **Release type** | `full_platform` |
| **Created with** | Wire v3.8.2 |
| **Current plugin version** | v3.9.4 |
| **Gap** | 6 weeks dormant |
| **State** | Design phase complete, development not yet started |

The data engineering team at Pennant is ready to resume. The plugin has been updated to v3.9.4 during the pause. Before any development commands run, the release folder needs to be brought up to the current schema.

## Why release upgrades are needed

Wire stores engagement state in `status.md` inside the release folder. That file has a schema — it contains sections for artifact status, wire agent assignments, open questions, and plugin version stamps. The schema evolves between Wire releases as new features ship.

Version 3.9 added three things that v3.8 does not know about: a `wire_agents` block listing which specialist agents are assigned to each artifact, an `orchestration` artifact type in the development phase, and a `data_quality` sub-section inside testing. It also introduced a `wire_plugin_version` stamp that records which version of the plugin created or last modified the file.

A release created on v3.8 has none of these. When you run `/wire:status` against it using the v3.9.4 plugin, you get a complete picture of the artifacts Wire v3.8 knew about — but the new sections are absent, and some commands will warn that expected schema fields are missing. The `orchestration` artifact never appears in the status summary, so if you run `/wire:orchestration-generate`, Wire does not know where to record the result.

The fix is one command. But run the dry-run first.

## Running /wire:upgrade

**Dry run — see what will change without touching any files:**

```
/wire:upgrade 01-pennant-platform --dry-run
-> Wire upgrade — dry run (no files modified)
-> Release: 01-pennant-platform
-> Current schema version:  v3.8.2
-> Target schema version:   v3.9.4

   Changes that would be applied:
   ──────────────────────────────
   1. Add wire_agents block — assigns specialist agents to each artifact
      based on release type (full_platform). 14 agents will be listed.

   2. Add orchestration artifact — inserts under Development phase,
      status: not_started. Positioned after dbt, before semantic_layer.

   3. Add data_quality sub-sections — adds dbt_tests, freshness_checks,
      and row_count_reconciliation fields inside the testing phase block.

   4. Add wire_plugin_version stamp — records v3.9.4 as the managing
      plugin version. Adds last_upgraded_at: 2026-06-14.

   4 changes identified. Run without --dry-run to apply.
   0 existing fields will be modified. 0 files outside status.md will be touched.
```

Nothing changes in the dry run. The output shows exactly what will be added. Four additions, no modifications to existing content. Marcus reviews the list — all four are schema additions, not decisions being changed or artifacts being regenerated. He runs the upgrade:

```
/wire:upgrade 01-pennant-platform
-> Wire upgrade — 01-pennant-platform
-> Applying 4 schema changes to status.md...

   [1/4] wire_agents block added — 14 agents assigned.
   [2/4] orchestration artifact added — status: not_started.
   [3/4] data_quality sub-sections added.
   [4/4] wire_plugin_version: 3.9.4 stamped. last_upgraded_at: 2026-06-14.

-> status.md updated. Schema version: v3.9.4.
-> Upgrade complete. Run /wire:status to verify.
```

Four seconds. The release folder is now on the current schema.

## What /wire:upgrade does NOT do

This is worth being explicit about. `/wire:upgrade` modifies only `status.md`, and only the schema sections — the structural blocks that Wire uses to track state. It does not touch anything else.

It does not regenerate artifacts. The approved pipeline design, data model, and conceptual model remain exactly as they were approved. No content is rewritten.

It does not change design decisions. `decisions.md` is untouched. The grain choices, surrogate key approach, and scope decisions made during the design phase are preserved exactly.

It does not modify generated code. Any SQL models, LookML views, Fivetran connector configs, or other code files that exist in the release folder are not touched by `/wire:upgrade`.

The command is a schema migration, not a content refresh. Think of it as running `dbt migrate` on a database — it changes the table structure, not the data inside it.

## After upgrading

```
/wire:start
-> Wire Framework v3.9.4
-> Active release: 01-pennant-platform
-> Type:           full_platform
-> Client:         Pennant Capital Management
-> Phase:          2 — Design (complete), 3 — Development (not started)

   Wire agents — available for this release:
     discovery-analyst         requirements-generate (complete)
     data-designer             conceptual_model-generate, pipeline_design-generate,
                               data_model-generate (all complete)
     pipeline-engineer         pipeline-generate
     dbt-developer             dbt-generate
     orchestration-engineer    orchestration-generate
     semantic-layer-developer  semantic_layer-generate
     ... (8 further agents)

   Artifact status:
     Requirements         approved
     Conceptual model     approved
     Pipeline design      approved
     Data model           approved
     Pipeline             not_started    <- next
     dbt                  not_started
     Orchestration        not_started
     Semantic layer       not_started
     ...
```

The `wire_agents` block is now present and correctly populated for the `full_platform` release type. The `orchestration` artifact appears in the development sequence alongside `pipeline` and `dbt`, all at `not_started`. The engagement can now resume with the full v3.9.4 feature set — including `/wire:delegate` for batch delegation, which was not available in v3.8.

## Checking for required upgrades

Before resuming any dormant engagement, run `/wire:utils-version` to see both the installed plugin version and the schema version of any active releases:

```
/wire:utils-version
-> Wire Framework
-> Installed version:  v3.9.4
-> Active in session:  v3.9.4

   Release folders detected:
     01-pennant-platform          schema v3.9.4    up to date
     02-aldgate-financial-platform  schema v3.9.4    up to date
     03-norwood-migration         schema v3.8.1    UPGRADE REQUIRED
       -> Run /wire:upgrade 03-norwood-migration to bring to v3.9.4
```

Any release whose schema version is behind the installed plugin version will show "UPGRADE REQUIRED" and the exact command to run. Releases that are already current show "up to date". Run `/wire:utils-version` at the start of any session on a release that has been dormant — it is the fastest way to catch a schema mismatch before it causes unexpected warnings mid-session.
