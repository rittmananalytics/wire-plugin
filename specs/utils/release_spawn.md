---
wire_schema: "1.0"
command: utility
artifact: release
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Create downstream delivery release folders from an approved discovery release brief

---

# Release Spawn Command

## Purpose

Reads the approved release brief and sprint plan from a completed discovery release and creates the folder structure, status files, and initial artifact scope for each planned downstream delivery release. This is the bridge from discovery to delivery.

## Inputs

**Required**:
- `$ARGUMENTS` — the discovery release folder (e.g. `01-discovery`)
- A completed discovery release with a signed-off `planning/release_brief.md`

## Workflow

### Step 1: Locate the Discovery Release

**Process**:
1. Try `.wire/releases/$ARGUMENTS/` (two-tier layout)
2. Fall back to `.wire/$ARGUMENTS/` (legacy layout)
3. Read `planning/release_brief.md` and `planning/sprint_plan.md`
4. If the release brief hasn't been reviewed and signed off, output an error:
   ```
   The release brief for [folder] must be signed off before spawning delivery releases.
   Run /wire:release-brief-review [folder] first.
   ```

### Step 2: Extract Downstream Releases

From Section 4 (Downstream Releases) of the release brief, extract the planned delivery releases. Each should have:
- Release name
- Release type (`full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement`)
- Scope summary
- Priority order

Also check the sprint plan's "Downstream Releases" section for start dates.

If the downstream releases section is empty or unclear, ask directly in chat:
```
List the delivery releases to create (name: type, one per line):
e.g.
02-data-foundation: pipeline_only
03-reporting: dashboard_extension
```

### Step 3: Confirm with User

Output the list of releases to be created:
```
I'll create the following delivery releases:

[N]  .wire/releases/02-data-foundation/  (pipeline_only)
[N]  .wire/releases/03-reporting/        (dashboard_extension)

This will create status.md and the standard folder structure for each.
Proceed? (yes/no)
```

Use `AskUserQuestion` to confirm.

### Step 4: Create Each Delivery Release

For each planned delivery release, in priority order:

1. **Determine release number**: Next available sequential number (pad to 2 digits: 01, 02, 03...)
2. **Create folder**: `.wire/releases/[NN]-[release_name]/`
3. **Create subdirectories** appropriate for the release type:
   - All types: `artifacts/`, `planning/`
   - full_platform / pipeline_only / dbt_development: `requirements/`, `design/`, `dev/`, `test/`, `deploy/`, `enablement/`
   - dashboard_extension: `requirements/`, `design/`, `dev/`, `enablement/`
   - enablement: `enablement/`
4. **Create status.md** from the discovery status template:
   - Use `TEMPLATES/discovery-status-template.md` as a base — but populate with the delivery release type's artifact scope
   - Set release type, client name, engagement name from the parent engagement context
   - Set `spawned_from: [discovery_release_folder]` in the YAML frontmatter
   - Set `created_date` to today

**Bash command for folder creation:**
```bash
mkdir -p .wire/releases/[folder]/{artifacts,planning,requirements,design,dev,test,deploy,enablement}
```

### Step 4.5: Data Model Registry — Automatic Setup Attempt (Conditional, Silent)

Same gap this closes as `specs/new.md`'s and `specs/autopilot.md`'s equivalent steps — and the one place this had been missed until a dry run caught it: `data_model-generate`'s canonical-vertical matching only ever *checks* for a local registry copy, it never *fetches* one. `/wire:new` only attempts the clone for the very first release created with an engagement, and Autopilot only attempts it inside its own end-to-end run — neither covers the everyday discovery-to-delivery path, where a `discovery`/`sop_discovery` release (which never uses `data_model` itself) spawns downstream delivery releases via this command that might. Without this step, a consultant who went discovery → `/wire:release-spawn` → manual delivery commands (a very common path, not just an Autopilot corner case) would get the registry silently skipped forever despite having real GitHub access, exactly like the original bug.

1. **Check relevance.** For each release type just spawned in Step 4, read `wire/release-types/<type>.yaml`. If **none** of them has a `phases[].artifacts[]` entry with `id: data_model`, skip this step silently — nothing spawned here will ever call `data_model-generate`. (Only relevant if at least one spawned release is `full_platform`, `dbt_development`, or `dashboard_first`.)
2. **Check whether setup was already attempted.** `ls ~/.wire/data_model_registry_setup_attempted 2>/dev/null`. If it exists, skip silently — already handled, on this machine, by a prior engagement or an earlier release in this same engagement.
3. **Attempt it.** If relevant and no attempted-marker exists, follow `specs/utils/data_model_registry_setup.md` as an automated (non-interactive) caller — see that spec's Step 1.5 for what changes in that mode. It writes the attempted marker itself; nothing further to do here. This runs once regardless of how many spawned releases actually need `data_model` — the first one to need it is enough to trigger it for all of them.
4. **Report minimally.** On success, the setup spec's own automated-mode output (one unobtrusive line) is enough. On failure, say nothing at all; continue to Step 5 exactly as if this step didn't exist.

### Step 5: Add .gitkeep Files

```bash
touch .wire/releases/[folder]/requirements/.gitkeep
touch .wire/releases/[folder]/design/.gitkeep
touch .wire/releases/[folder]/dev/.gitkeep
touch .wire/releases/[folder]/test/.gitkeep
touch .wire/releases/[folder]/deploy/.gitkeep
touch .wire/releases/[folder]/enablement/.gitkeep
```

### Step 6: Update Discovery Release Status

In the discovery release's `status.md`, add to the `notes` section:
```yaml
notes:
  - "Delivery releases spawned [date]: [list of release folders]"
```

### Step 7: Output Completion Summary

```
## Delivery Releases Created ✅

The following delivery releases have been spawned from [discovery_release_folder]:

| Release | Type | Folder | Status |
|---------|------|--------|--------|
| [name] | [type] | .wire/releases/[folder]/ | Ready |
| [name] | [type] | .wire/releases/[folder]/ | Ready |

### To start work on a delivery release:

1. Start a session:
   /wire:session-start releases/[folder]

2. Generate requirements:
   /wire:requirements-generate releases/[folder]

3. Check status:
   /wire:status releases/[folder]

Note: status tracking is updated automatically only when work runs through Wire
commands. Work done conversationally (agent-assisted or by hand) must reconcile
the record before raising a PR:
   /wire:status-sync releases/[folder]

The discovery release brief and sprint plan are stored at:
.wire/releases/[discovery_folder]/planning/

Reference them when generating requirements and design artifacts for the delivery releases.
```

## Edge Cases

### Release name conflicts
If a folder with the derived name already exists, append a letter suffix (e.g. `02-data-foundation-b`).

### Unknown release type
If a downstream release has an unrecognised type, create the basic folder structure (artifacts, planning) and note "type: custom — set up artifact scope manually" in the status.md.

### Legacy layout
If the discovery release is in legacy layout (`.wire/$ARGUMENTS/` not `.wire/releases/$ARGUMENTS/`), create new releases in the same layout for consistency. Note this in the status.md.

## Output Files

For each spawned release:
- `.wire/releases/[folder]/` directory structure
- `.wire/releases/[folder]/status.md`

Updated:
- `.wire/releases/[discovery_folder]/status.md`
