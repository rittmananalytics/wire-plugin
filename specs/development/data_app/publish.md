---
wire_schema: "1.0"
command: utility
artifact: data_app
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: app
      description: "--app <slug>. Publish one app (default: ask when status.md lists several)"
    - name: flags
      description: "--dry-run shows the publish command and target and stops; --folder-id <id> overrides the toolkit's publish folder for this run"
preconditions:
  - artifact: data_app
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Publish a validated Looker Data App to the Looker instance through Google's publisher, after a dry run and the user's confirmation; re-publishes in place; never run by a lane or autopilot"
argument-hint: <release-folder> [--app <slug>] [--dry-run] [--folder-id <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# data_app Publish Command

**Experimental.** See `data_app-generate` for the marker and what it means.

## Purpose

Put a validated app on the client's Looker instance, where it becomes a dashboard with one extension tile, in the folder the toolkit is configured for. Publishing creates persistent objects on the client's instance, so it is an interactive action: a person confirms every run, and Google's `publish-data-app.py` is the only path (its skill forbids custom publish scripts, and so does this one).

## Usage

```bash
/wire:data_app-publish 20260115_acme_dashboards --dry-run
/wire:data_app-publish 20260115_acme_dashboards
```

## Workflow

### Step 0: Who is asking

Read `WIRE_INVOKED_BY`. If it is `lane`, `orchestrator` or `autopilot`, stop:

```
Publishing a data app is the release director's action. Run /wire:data_app-publish typed, in your own session.
```

The orchestrating session lists it as a decision; it never dispatches it.

### Step 1: Resolve the app and the toolkit

1. `--app <slug>`, else the one app in `status.md`, else ask which.
2. `python3 <wire>/scripts/data_app_toolkit.py check` (toolkit at or above the pin; config present). Then `push` the repo copy, so what is published is the committed source:

   ```bash
   python3 <wire>/scripts/data_app_toolkit.py push --app <slug> --source <data_apps_path>/<slug>
   ```

   If the repo copy has uncommitted changes, list them and stop: the published copy must be a committed one, so the dashboard id lands on a file git knows.

3. `data_app.validate` is `pass` for this app and `validated_date` is not older than the source file's last commit. Otherwise stop and name `/wire:data_app-validate`.

### Step 2: Plan

```bash
python3 <wire>/scripts/data_app_toolkit.py publish plan --app <slug> [--folder-id <id>]
```

The plan shows, without running anything: the instance host (from the toolkit's config, masked to the host), the publish folder id, the title (the catalog page name), whether this is a first publish or a re-publish (`@looker-dashboard-id` in the source header, or `looker_dashboard_id` in status; the two must agree), and the exact `publish-data-app.py` command. With `--dry-run`, stop here.

Ask: **Publish / Cancel**.

### Step 3: Run

On Publish:

```bash
python3 <wire>/scripts/data_app_toolkit.py publish run --app <slug> --confirm [--folder-id <id>]
```

The wrapper runs Google's publisher from the toolkit root, with `--dashboard-id` when re-publishing (without it every publish creates another dashboard), and never with `--confirm-replace` on the first attempt.

Outcomes:

| Outcome | What to do |
|---|---|
| Success | The output ends with the dashboard address. Report it as the real instance address, never a local one. Report how many widget queries were registered and every `skipped:` and `warning:` line with its reason: those widgets have no "Explore from here" or may open a different query. |
| `user_mismatch` envelope | The dashboard was last updated by someone else. Stop and ask: "Dashboard <id> was last updated by '<name>', but you are '<current user>'. Updating it overwrites their work. Proceed?" Only on an explicit yes, run again with `--confirm-replace`. |
| `def_too_large` | The app is over the extension size cap (900 KB by default). Trim inline assets; do not raise the cap. |
| `looker_http_404` on `/data_app_extension` | The instance has no `inline_extensions` feature or the preview is off. A Looker admin's action; stop. |
| `looker_http_403` / `404` permission | The API user lacks a permission the Prerequisites table in `data_app-generate` lists. Stop and name it. |
| "dashboard header stays visible" warning | The publish succeeded; the instance cannot hide the dashboard header. Tell the user; do not retry. |

### Step 4: Pull the publish tags back

The publisher writes `@looker-dashboard-id`, `@looker-instance`, `@created-at`, `@created-by`, `@updated-at`, `@updated-by` and `@toolkit-version` into the toolkit copy's header. Bring them back to the source:

```bash
python3 <wire>/scripts/data_app_toolkit.py pull --app <slug> --source <data_apps_path>/<slug> --tags-only
```

Commit the source with the tags (`specs/utils/commit.md`), so the next re-publish, from any machine, targets the same dashboard.

### Step 5: Update status

```yaml
artifacts:
  data_app:
    apps:
      - slug: <slug>
        looker_dashboard_id: "<id>"
        looker_dashboard_url: "<instance>/dashboards/<id>"
        published_date: "{{TODAY}}"
        published_by: "<Looker user>"
        toolkit_version: "<VERSION>"
        widget_queries_registered: N
        widget_queries_skipped: N
```

Under `/wire:work` with ticket delivery, write the same to the ticket record's front matter.

### Step 6: Stop the preview server

From the toolkit root: `python3 skills/data-app-previewer/tools/stop-preview.py`.

## Gemini CLI

The same steps; the scripts run as shown.

## Edge Cases

### The source header and `status.md` disagree on the dashboard id

Stop. One of them is stale. The header was written by the publisher at the last publish; status was written by this command. Ask which dashboard is live, fix the other, then run again.

### Publishing from the toolkit's `examples/` or from a working copy

Refused by Step 1: only a pushed, committed repo copy is published.

### A copy of the published dashboard was made in Looker

Say so to the client: copies share one extension, so a re-publish changes every copy. Ask for the copies to be deleted before the next publish.

## Post-Execution Hooks

1. **Execution log**: one row in `execution_log.md` following `specs/utils/execution_log.md`.
2. **Auto-commit**: `specs/utils/commit.md` with artifact `data_app`, action `publish`.
