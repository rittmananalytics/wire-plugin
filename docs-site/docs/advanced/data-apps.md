---
sidebar_position: 15
title: Looker Data Apps
---

# Looker Data Apps

:::caution[Experimental]

Looker Data Apps is a Looker preview feature (Looker-hosted instances, Looker 26.18 or later), and Google's toolkit changes between releases. Wire's `data_app` artifact is marked experimental until it has run end to end on a client estate. Looker is the only target: `bi_tool: omni` stops with a message. Omni apps are planned under the same commands.

:::

A Data App is an interactive page on the Looker semantic layer: a KPI strip, charts that cross-filter each other, a detail table, tabs where the design has them, laid out freely rather than on a dashboard grid. It is one file, `apps/<slug>/app.js`, written in Google's Lit runtime, and Looker serves it as a dashboard holding one extension tile. Every widget queries a LookML explore as the person viewing it, so model access, permissions and row-level filters apply as on any dashboard.

Google's [Data Apps toolkit](https://docs.cloud.google.com/looker/docs/data-apps) does the authoring, preview, verification and publish. Wire adds what a delivery needs around it: the widget plan from the mockup the stakeholder approved, field resolution against the approved semantic layer, its own rules, validation with a verdict, and a publish step a person confirms.

## What is included

| Part | What it does |
|---|---|
| `data_app` artifact | `/wire:data_app-generate`, `-validate`, `-review`, and the `-publish` utility. Optional in `full_platform`, `dbt_development`, `dashboard_first` and `dashboard_extension`, gated as `dashboards` is |
| Widget plan | `data_app_plan.py plan` turns the visualization catalog into one widget per row through a fixed table, gives each a stable id, and resolves every field against the explore. What it cannot map or resolve is listed, never guessed |
| Rules | `conventions/data_apps.yml`, DA-001 to DA-016: Google's tile sandbox rules plus Wire's own (no literal rows, no credential, a header, the runtime import, unique ids). Checked by `lint_conventions.py --domain data_apps` |
| Toolkit wrapper | `data_app_toolkit.py`: `check` (toolkit present and at the pinned version, config present with values masked), `push` and `pull` (the app between the repo and the toolkit), `diff`, `verify` (Google's `verify-app.py`, stages 1 to 3), `publish plan` and `publish run --confirm` |
| Skill | `data-apps`: activates on app work, defers to Google's `data-app-creator` skill for the code, carries the rules and the limits |

## Setting it up

1. A Looker admin switches on Data Apps (Admin, General, Previews) and enables API keys for the builder's account. The builder needs `access_data`, `explore`, `see_user_dashboards`, `save_content`, `save_dashboards`, and Manage Access, Edit on the publish folder.
2. The consultant installs the toolkit: `bash <(curl -fsSL https://dl.google.com/looker-data-apps/install.sh)`. It asks for the instance address, an API key and the publish folder, and writes them to its own `data-apps-config.json`. Wire never reads that file.
3. In the engagement repo, add a `data_apps:` block to `.wire/engagement/context.md` (the path where app sources live, the publish folder, the model and explores). On each machine, put the toolkit path in `.wire/local/data_apps.yml` as `toolkit_path:`; the file is git-ignored.
4. Check: `python3 <wire>/scripts/data_app_toolkit.py check`. It compares the toolkit's version with `wire/data_apps/pinned_toolkit_version.txt` and refuses an older one.

## How a release uses it

The app is built from the same design chain as a dashboard. `mockups-generate` writes the visualization catalog, the dashboard spec (its interaction notes now say whether the page is a dashboard, a data app or both) and the mockup HTML. `data_app-generate` then:

1. Reads the live explore's field list once, through Google's `explore-model.py`, into the release record.
2. Runs the plan: one widget per catalog row, chart types from the table (KPI, line, area, column, bar, donut, pie, table, scatter, funnel, treemap, gauge, text), fields resolved exactly or by a unique suffix, filters from the spec, tabs and cross-filtering from the interaction notes. A `map` row is unmapped and written as a table; `region` with two candidate fields is unresolved. Both are counted in `status.md`.
3. Writes `app.js` in the client repo following Google's skill, with the plan's ids and titles, nothing invented.
4. Lints it, pushes a copy into the toolkit, runs Google's verification (syntax, sandbox rules, a dry run of every query against Looker), fixes what it can, and starts the local preview.

`data_app-validate` runs twelve checks, among them the plan's coverage check of `app.js`, the rules, and Google's verify. A toolkit that is not installed makes the verify `unverified`, which is a fail. `data_app-review` records the stakeholder's decision on the preview or the published app. `data_app-publish` shows a plan (instance host, folder, first publish or re-publish, the exact command), asks, runs Google's publisher, and brings the dashboard id the publisher writes into the file's header back into the repo. A lane, the orchestrator or autopilot cannot publish.

```
/wire:data_app-generate 03-sales-app
/wire:data_app-validate 03-sales-app
/wire:data_app-review   03-sales-app
/wire:data_app-publish  03-sales-app --dry-run
/wire:data_app-publish  03-sales-app
```

## Where the code lives

The source of truth is the client repo, at the path `data_apps.path` names. The toolkit's own `apps/` folder is a working copy: `push` writes it, and refuses to overwrite a copy someone edited there (`pull` brings such an edit back, `--force` overwrites). The toolkit's preview server refuses symlinks outside its root, which is why the two are copies. After a publish, `pull --tags-only` copies the publisher's header tags (`@looker-dashboard-id` and the rest) into the repo file, so a re-publish from any machine targets the same dashboard.

## The rules

| Id | Rule | Checked |
|---|---|---|
| DA-001 | JSDoc header with `@title` and `@description` | script |
| DA-002 | Runtime imported from `/runtime/data-app.js` | script |
| DA-003 | No relative import | script |
| DA-004 | No inline `on*=` handler | script |
| DA-005 | No `alert`, `confirm`, `prompt` | script |
| DA-006 | No `localStorage` or `sessionStorage` | script |
| DA-007 | No `window.open`, no `target="_blank"` | script |
| DA-008 | No relative asset URL | script |
| DA-009 | No `connectExtensionHost()` | script |
| DA-010 | No `document.body` or `documentElement` mutation | script |
| DA-011 | No literal rows on a widget | script |
| DA-012 | No credential in the app | script |
| DA-013 | `getEffectiveFilters()` spreads the dashboard and cross filters | presence only |
| DA-014 | `customElements.define(...)` | script |
| DA-015 | No `fetch()` or `XMLHttpRequest` | script, warning |
| DA-016 | No widget id used twice | script |

A client adds rules or switches one off with a reason in `.wire/conventions/data_apps.yml` with `extends: wire`. See [Convention rules](./convention-rules.md).

## What a Data App cannot do

In the Looker preview as of October 2026: no embedding, no internal dashboard themes, no PDF download or scheduled PDF delivery, no LookML export or import. A published app's dashboard must not be copied in Looker, because copies share one extension and a re-publish changes all of them. Viewers' browsers must reach `www.gstatic.com`. Where the client needs any of these, `dashboards` is the right artifact; the two can run side by side on the same catalog.

## Worked example

[Tutorial: A Looker Data App](../tutorials/looker-data-app) reproduces a real run on Rittman Analytics' own Looker instance: a three-tab Web Traffic app over the Web Analytics explore with KPI cards floating over a hero band, a metric switcher, a top-N slider, a search box, a detail drawer, a gauge, a treemap and a heat-mapped scorecard, verified by Google's tool and published as a dashboard. The full source is published with it.

## Three rules the live run added

- **A widget's own filter goes through `getEffectiveFilters(local)`**, never under `.query.filters`. The runtime takes a query's own filters in place of the shared `.filters`, so the widget loses the date window, the dropdowns and the cross-filters without any error.
- **Widget ids and fields are static text.** A widget built by a helper from arguments gives Google's publisher nothing to register ("fields comes from a loop variable or helper argument") and the plan check nothing to find. Each widget is written out in full, however alike they look.
- **Sankey is not available.** The toolkit's bundled Highcharts has no sankey module and a tile cannot load one from the network. Gauges, treemaps, funnels and heat-mapped grids are.

## Tests

`wire/tests/development/validate_data_app_plan.py` plans the fixture catalog and checks a fixture app against it; `validate_data_app_conventions.py` runs the rules over four fixture apps and a client override; `validate_data_app_toolkit.py` runs the wrapper against a stand-in toolkit with stub verify and publish tools. No test reaches a Looker instance.
