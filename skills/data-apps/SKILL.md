---
name: data-apps
description: >
  Experimental. Proactive skill for Looker Data Apps (Google's Data Apps toolkit, a Lit module per app published as a dashboard-mounted extension). Auto-activates when writing or changing an apps/<slug>/app.js, when /wire:data_app-generate, -validate, -review or -publish runs, when the user asks for an app, an interactive page or a freeform dashboard on the Looker semantic layer, and when a mockup's Presentation line says data_app. Covers the rule set (lint_conventions.py --domain data_apps), the widget plan (data_app_plan.py), the toolkit wrapper (data_app_toolkit.py: check, push, pull, diff, verify, publish), Google's own skills and tools, the tile sandbox, and what a Data App cannot do. Looker only; bi_tool: omni stops.
---

# Data Apps Skill (experimental)

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | data-apps | activated | Looker Data App work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

## Purpose

Build, check and publish Looker Data Apps on a client's semantic layer. A Data App is one Lit ES module, `apps/<slug>/app.js`, written against Google's runtime (`<app-kpi>`, `<app-chart>`, `<app-grid>`, `<app-select>`) and published by Google's toolkit as a Looker dashboard holding one extension tile. Every widget queries a LookML explore as the viewing user, so model access, permissions and row-level access filters apply as they do on a dashboard. Google's toolkit does the authoring, preview, verification and publish. Wire adds the record, the gates, the widget plan from the approved mockup, field resolution against the approved semantic layer, its own rules, and the publish control.

**Experimental.** Looker Data Apps is a preview feature (Looker-hosted instances, Looker 26.18 or later, switched on under Admin, General, Previews). Google's toolkit changes between releases; Wire pins the version it was built against in `wire/data_apps/pinned_toolkit_version.txt` and refuses an older one. Omni apps are not supported yet; the commands are named so they can be, and `bi_tool: omni` stops with a message.

## Files this skill reads

| File | Holds |
|---|---|
| `<toolkit>/skills/data-app-creator/SKILL.md`, `reference/LIT_DATA_APPS.md`, `recipes/*.md` | Google's authoring rules, the component contract, the recipes. Read as files; the toolkit symlinks them into its own `.claude/skills/`, not into the client repo |
| `<toolkit>/data-apps-config.json` | The Looker instance, API key and publish folder. **Never read it, never print it, never copy it.** Google's tools read it; `data_app_toolkit.py check` reports which keys are present |
| `.wire/local/data_apps.yml` | `toolkit_path:` for this person's machine (git-ignored). `WIRE_DATA_APPS_TOOLKIT` overrides it; `~/looker-data-apps` is the default |
| `.wire/engagement/context.md` `data_apps:` | `path` (where app sources live in the client repo), `publish_folder_id`, `model`, `explores` |
| `conventions/data_apps.yml` (Wire's) or `.wire/conventions/data_apps.yml` (the client's, with `extends: wire`) | The rules, DA-001 to DA-016 |
| `wire/data_apps/pinned_toolkit_version.txt` | The toolkit version Wire was built against |

**The source of truth is the client repo**: `<data_apps_path>/<slug>/app.js`. The toolkit's `apps/<slug>/` is a working copy for preview and publish, written by `data_app_toolkit.py push`. The preview server refuses symlinks outside its root, hence copies.

## When This Skill Activates

- A file named `app.js` under an `apps/` or `data_apps/` folder imports `/runtime/data-app.js`.
- `/wire:data_app-generate`, `-validate`, `-review` or `-publish` runs.
- The user asks for a Looker "app", an interactive or freeform page, tabs, cross-filtering or drill on the semantic layer, or a Data App by name.
- `design/dashboard_spec.md` has `Presentation: data_app` in its interaction notes.

**Keywords**: "data app", "Looker app", "Lit", "app-kpi", "app-chart", "app-grid", "extension tile", "publish-data-app", "verify-app", "freeform dashboard".

---

## Step 0: Toolkit, credentials, rules

1. `python3 <wire>/scripts/data_app_toolkit.py check`. Stop on any problem it lists (no toolkit, no config, version older than the pin). A newer version is a warning to record.
2. Google's credential gate, from the toolkit root: `python3 skills/data-app-creator/tools/check-credentials.py --json`. Exit 1 is a hard stop: report the tool's hint and end the turn. Do not look for credentials elsewhere, do not write code.
3. Rule file: `.wire/conventions/data_apps.yml` if present (with `extends: wire` it keeps Wire's rules and adds its own), else Wire's `conventions/data_apps.yml`.

| Id | Rule | Checked by script |
|---|---|---|
| DA-001 | JSDoc header with `@title` and `@description`; the publisher's tags stay in it | yes |
| DA-002 | Import the runtime from `/runtime/data-app.js` | yes |
| DA-003 | No relative import: one file, nothing else is served | yes |
| DA-004 | No inline `on*=` handler (CSP) | yes |
| DA-005 | No `alert`, `confirm`, `prompt` | yes |
| DA-006 | No `localStorage` or `sessionStorage` | yes |
| DA-007 | No `window.open`, no `target="_blank"` | yes |
| DA-008 | No relative asset URL | yes |
| DA-009 | No `connectExtensionHost()` | yes |
| DA-010 | No `document.body` or `documentElement` mutation | yes |
| DA-011 | No literal rows on a widget (`.data=${[...]}`) | yes |
| DA-012 | No credential in the app | yes |
| DA-013 | `getEffectiveFilters()` spreads `this.dashboardFilters` and `this.crossFilters` | presence only |
| DA-014 | `customElements.define(...)` and a default export | yes |
| DA-015 | No `fetch()` or `XMLHttpRequest` | yes, warning |
| DA-016 | No widget id used twice | yes |

```bash
python3 <wire>/scripts/lint_conventions.py --domain data_apps \
  --convention <resolved data_apps.yml> --path <data_apps_path>/<slug> --new-project
```

Every app Wire writes is new, so `--new-project` applies each rule at its own severity. Fix every error. Each remaining warning gets a disposition in the app's record: `fixed`, `justified` with a reason, or `acknowledged`. Findings never block a pull request on their own; validate does.

## Writing an app

Follow `/wire:data_app-generate` when there is a release. The rules that hold whether or not there is one:

1. **Plan first, deterministically.** `data_app_plan.py plan` turns the catalog into one widget per row with a stable id (`da-<tag>-<slug of title>`), the chart type from a fixed table, and the fields resolved against the explore's field list. Read the plan; write the widgets it lists, nothing else. An unmapped chart type is written as a table and reported; an unresolved field is left out and reported. Never invent a field.
2. **Google's skill governs the code.** Read `<toolkit>/skills/data-app-creator/SKILL.md` before writing: the MVP template, the composition floor (a KPI strip, a trend, a breakdown, a detail table), `getEffectiveFilters()` spreading both filter maps, `cross-filter` on segmented charts only, formats (`percent1` for ratios, `usd`, `int`), the layout rules, the tile sandbox table. Fetch the recipes the plan's chart types need with `get-recipe.py`; do not page through `runtime/data-app.js`.
3. **Discovery is scoped.** `explore-model.py <model> <explore> --json` once for the field list. `--probe` only with `--fields`; never an unscoped `--sample` on a wide explore.
4. **One file, written in one pass**, then targeted edits. Keep the JSDoc header and every publisher tag.
5. **A widget's own filters go through `getEffectiveFilters(local)`.** The runtime takes `filters` inside a widget's `.query` in place of the shared `.filters`, so a widget written with `.query=${{ ..., filters: {...} }}` loses the date window, the dropdowns and the cross-filters. Found on the first live run: a referrers chart with `filters: { 'x.referrer_host': '-NULL' }` in its query showed all-time counts. Write `.filters=${this.getEffectiveFilters({ 'x.referrer_host': '-NULL' })}` instead, and nothing under `.query.filters`.
6. **Ids and fields are static text.** Every widget carries the plan's `id` and its `fields` as literals in the tag, written out in full, even when five KPI cards look alike. A helper that builds the id or the fields from an argument gives the publisher nothing to register ("fields comes from a loop variable or helper argument": no "Explore from here" for that widget) and gives the plan check nothing to find. A `.map()` over a `const` array of literals is the one loop the publisher unrolls. A switcher whose field reads app state is registered with its starting value and reported as a warning, which is acceptable for a chart whose measure the user picks.
7. **The source lives in the repo.** Write to `<data_apps_path>/<slug>/app.js`, then `data_app_toolkit.py push`. Never edit the toolkit copy; `push` refuses to overwrite one that was edited there, and `pull` brings a deliberate edit back.

## Verify and preview

```bash
python3 <wire>/scripts/data_app_toolkit.py push --app <slug> --source <data_apps_path>/<slug>
python3 <wire>/scripts/data_app_toolkit.py verify --app <slug>       # Google's verify-app.py, stages 1-3, --no-browser
cd <toolkit> && python3 skills/data-app-previewer/tools/start-preview.py apps/<slug>/app.js
```

Stage 1 is syntax, stage 2 the tile sandbox rules and the widget extraction, stage 3 a dry run of every widget query against Looker (a model that does not exist, a field Looker rejects, an empty result). On a failure read the hint, fix the repo copy, push and verify again; do not ask the user. Five rounds, then report what remains. Delegate the loop to a subagent when one is available, so the output stays out of the main session.

The preview has two modes. `?app=...&inspect=1` mounts the app on the page for DOM checks. `?app=...` (or `&sandbox=true`) runs it in an opaque-origin iframe the way a published tile does; look at that one before calling it done. Stop the server when finished: `stop-preview.py`.

## Publishing

Only through `/wire:data_app-publish`, which wraps Google's `publish-data-app.py` in a plan, a confirmation and a record. Never run the publisher yourself, never write a publish script, never publish from a lane, the orchestrator or autopilot. A re-publish needs the dashboard id (the `@looker-dashboard-id` tag the publisher writes; `pull --tags-only` brings it into the repo). `--confirm-replace` only after a `user_mismatch` envelope and the user's explicit yes.

## What a Data App cannot do (Looker preview, October 2026)

| Limit | What to say |
|---|---|
| No embedding, no internal dashboard themes | A Data App is for Looker users on the instance. An embedded audience needs a LookML dashboard |
| No PDF download, no scheduled PDF delivery | Use `dashboards` for anything that goes out by email |
| No LookML export or import | The app is code in the repo, not LookML |
| Copying the dashboard in Looker | Copies share one extension: a re-publish changes every copy. Ask for copies to be deleted |
| Viewers need `www.gstatic.com` | The runtime and component libraries load from there |
| The tile has no outbound network | Every query goes through the runtime; no third-party calls |
| Instance requirement | Looker-hosted, 26.18 or later, preview toggle on, `inline_extensions` feature |

## Gemini CLI

The same steps; Gemini reads this file and Google's `SKILL.md` as files and runs the scripts as shown.

## Related

- `specs/development/data_app/{generate,validate,review,publish}.md`
- `conventions/data_apps.yml`, `wire/schemas/convention-schema.md`
- `wire/scripts/data_app_plan.py`, `wire/scripts/data_app_toolkit.py`, `wire/scripts/lint_conventions.py`
- `skills/lookml-content-authoring/SKILL.md` for the semantic layer the app queries
- Looker Data Apps: https://docs.cloud.google.com/looker/docs/data-apps
