---
sidebar_position: 20
title: "Tutorial: A Looker Data App"
---

# Tutorial: A Looker Data App on the Web Analytics explore

:::caution[Experimental]

The `data_app` artifact is experimental and Looker only. This tutorial reproduces a real run on Rittman Analytics' own Looker instance on 1 November 2026, with Google's Data Apps toolkit 1.2.0. The commands, scripts, outputs and defects are the real ones.

:::

This tutorial builds a three-tab Looker Data App over the `web_sessions_fact` explore (labelled Web Analytics) in the `analytics` model: sessions, users and page views with weekly sparklines, a weekly trend with a metric switcher, channel and referrer bars with a top-N slider, device and new-versus-returning rings, a landing-page table with a search box and an executive summary beside it, a detail drawer that opens from a KPI card or a table row, a bounce-rate gauge, a page-category treemap and a heat-mapped channel scorecard. It was previewed in the tile sandbox, verified by Google's own tool and published to the instance as dashboard 419.

What a Data App is, how Wire supports it and the rules it checks are on the [Looker Data Apps](../advanced/data-apps) page. This page is the walkthrough.

## What you need

| Requirement | Who |
|---|---|
| A Looker-hosted instance, 26.18 or later, with Data Apps switched on under Admin, General, Previews | Looker admin |
| API keys enabled for your user, and the dashboard author permissions (`access_data`, `explore`, `see_user_dashboards`, `save_content`, `save_dashboards`), plus Manage Access, Edit on the publish folder | Looker admin |
| Google's toolkit: `bash <(curl -fsSL https://dl.google.com/looker-data-apps/install.sh)`, which asks for the instance address, the client ID and secret, and a folder ID | You |
| Python 3.9 or later, and Node for the toolkit's syntax check | You |
| Wire 4.4.6 or later | You |

The toolkit writes the credentials to its own `data-apps-config.json`. Wire never reads that file and never copies it. Put the toolkit's path in `.wire/local/data_apps.yml` as `toolkit_path:`; the folder is git-ignored.

## The design inputs

A Data App is built from the same mockup chain as a dashboard: the visualization catalog and the dashboard spec that `mockups-generate` writes. For this run they were written by hand. The catalog has one row per widget:

```csv
dashboard_page,visualization_name,chart_type,measures,dimensions
Web Traffic,Sessions,KPI tile,web_sessions_fact.total_sessions,
Web Traffic,Unique Users,KPI tile,web_events_fact.total_unique_users,
Web Traffic,Page Views,KPI tile,web_events_fact.total_page_views,
Web Traffic,Bounce Rate,KPI tile,web_sessions_fact.bounced_session_rate,
Web Traffic,Meetings Booked,KPI tile,web_events_fact.total_conversions,
Web Traffic,Weekly Trend,area,web_sessions_fact.total_sessions; web_events_fact.total_page_views; web_events_fact.total_conversions,web_sessions_fact.session_start_ts_week
Web Traffic,Sessions by Channel,horizontal bar,web_sessions_fact.total_sessions,web_sessions_fact.channel
Web Traffic,Device Split,donut,web_sessions_fact.total_sessions,web_sessions_fact.device_category
Web Traffic,New vs Returning,donut,web_sessions_fact.total_sessions,web_sessions_fact.new_or_returning_user
Web Traffic,Top Landing Pages,table,web_sessions_fact.total_sessions; web_sessions_fact.bounced_session_rate; web_events_fact.total_conversions,web_sessions_fact.first_page_title
Web Traffic,Top Referrers,horizontal bar,web_sessions_fact.total_sessions,web_sessions_fact.referrer_host
Web Traffic,Case Study Views,KPI tile,web_events_fact.total_case_study_page_views,
Web Traffic,Blog Views,KPI tile,web_events_fact.total_blog_page_views,
Web Traffic,Services Views,KPI tile,web_events_fact.total_services_page_views,
Web Traffic,Bounce Rate Target,gauge,web_sessions_fact.bounced_session_rate,
Web Traffic,Sessions by Page Category,treemap,web_sessions_fact.total_sessions,web_sessions_fact.first_page_category
Web Traffic,Channel Scorecard,table,web_sessions_fact.total_sessions; web_events_fact.total_page_views; web_events_fact.total_conversions; web_sessions_fact.bounced_session_rate,web_sessions_fact.channel
```

The spec carries the filters and the four interaction lines that `data_app-generate` reads:

```markdown
## Filter Dimensions
- Date: web_sessions_fact.session_start_ts_date (default: last 90 days)
- Channel: web_sessions_fact.channel
- Site: web_sessions_fact.site

## Interaction Notes
- Tabs: Overview, Pages, Engagement
- Cross-filter: Sessions by Channel, Top Referrers, Device Split, New vs Returning, Sessions by Page Category
- Drill: a KPI card opens a drawer with the measure's definition and its split by channel; a landing page row opens a drawer with that page's weekly trend and channel mix
- Presentation: data_app
```

## Step 1: Toolkit and credentials

`data_app-generate` Step 0 runs Wire's check and then Google's credential gate. Wire's check reports the toolkit's version against the pin and which config keys are present, with the secrets masked:

```bash
python3 <wire>/scripts/data_app_toolkit.py check
```

```
toolkit: /Users/you/looker-data-apps
version: 1.2.0
pin: 1.2.0
version_vs_pin: equal
config_present: True
config_keys: ["base_url", "client_id (masked)", "client_secret (masked)", "default_explores", "default_model", "publish_folder_id"]
instance_host: rittman.eu.looker.com
problems: []
```

Then, from the toolkit root, Google's own check, which is a hard stop on failure:

```bash
python3 skills/data-app-creator/tools/check-credentials.py --json
```

It returned `ok: true` and the 18 models the API user can see.

## Step 2: The field list

The explore's fields are read once, into the release record, so the plan, validate and review all read the same list:

```bash
python3 skills/data-app-creator/tools/explore-model.py analytics web_sessions_fact --json > dev/data_app/web-traffic/fields.json
```

The explore has 177 dimensions and 22 measures. Do not pass `--probe` without `--fields`: it runs one query per field.

## Step 3: The plan

The plan is the deterministic part. Two people working from the same catalog get the same plan:

```bash
python3 <wire>/scripts/data_app_plan.py plan \
  --catalog design/dashboard_visualization_catalog.csv \
  --spec design/dashboard_spec.md \
  --fields dev/data_app/web-traffic/fields.json \
  --model analytics --explore web_sessions_fact --app web-traffic \
  --out dev/data_app/web-traffic/plan.json
```

```
plan written: dev/data_app/web-traffic/plan.json  rows=17 widgets=17 unmapped=0 unresolved_fields=0 filters=3 (0 unresolved)
```

Each row became a widget with a stable id in the form Google's publisher uses (`da-kpi-sessions`, `da-chart-weekly-trend`, `da-grid-top-landing-pages`), a chart type from the fixed table (`horizontal bar` to `bar`, `donut` to `donut`, `gauge` to `gauge`, `treemap` to `treemap`), its fields resolved against the explore, and `cross_filter: true` on the segmented charts the spec named. A chart type the runtime cannot draw would have been written as a table and listed under `unmapped`; a field not in the explore would have been listed under `unresolved_fields`. Both counts are zero here, and both would fail validate if they were not.

## Step 4: Writing the app

The agent writes `app.js` from the plan, following Google's `data-app-creator` skill, read as a file from the toolkit. The whole file is published with this page: [web-traffic/app.js](/examples/data-apps/web-traffic/app.js). The parts that matter:

**Every widget's filters go through one function.** Looker's own filter bar, the cross-filters, the two dropdowns and the spec's default window are merged once, and a widget's own filter is passed as `local`:

```javascript
getEffectiveFilters(local = {}) {
  const filters = { ...(this.dashboardFilters || {}), ...(this.crossFilters || {}) };
  if (!filters['web_sessions_fact.session_start_ts_date']) {
    filters['web_sessions_fact.session_start_ts_date'] = '90 days';
  }
  if (this.channel !== 'All') filters['web_sessions_fact.channel'] = this.channel;
  if (this.site !== 'All') filters['web_sessions_fact.site'] = this.site;
  return { ...filters, ...local };
}
```

**A KPI card with a sparkline.** The widget is `bare` inside Wire's own card, its id and fields are literals, and the card opens the drawer:

```javascript
${this.kpiCard('', 'web_sessions_fact.total_sessions', '13 weeks, week on week', html`
  <app-kpi bare id="da-kpi-sessions" label="Sessions" format="int" sparkline sparkline-agg="sum"
    .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_sessions_fact.total_sessions'],
               sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
    .filters=${spark}></app-kpi>`)}
```

**The metric switcher.** A segmented control sets `this.trendMetric`; the chart's query reads it:

```javascript
<app-chart bare id="da-chart-weekly-trend" type="areaspline" title="Weekly Trend" height="320px"
  value-format=${metric.format} color="var(--app-primary)" .options=${TREND_OPTIONS}
  .query=${{ fields: [WEEK, this.trendMetric], sorts: [WEEK] }}
  .filters=${filters}></app-chart>
```

**The referrers chart's own filter.** Passed as `local`, never under `.query.filters`:

```javascript
.filters=${this.getEffectiveFilters({ 'web_sessions_fact.referrer_host': '-NULL' })}
```

**The drawer.** Reactive state, a backdrop and an aside; the chart inside it is a live widget, so the number is never interpolated as text:

```javascript
openMetric(field) { this.drawer = { kind: 'metric', field }; }
openPage(row) { this.drawer = { kind: 'page', title: row['web_sessions_fact.first_page_title'] }; }
closeDrawer() { this.drawer = null; }
```

**The heat-mapped scorecard.** AG Grid cell renderers shade each cell against its column's maximum, which `onRowDataUpdated` computes when the rows arrive:

```javascript
function heatCell(field, format, maxByField, tone) {
  return (params) => {
    if (!params.data) return '';
    const raw = Number(params.data[field]) || 0;
    const alpha = Math.max(0.08, (raw / (maxByField[field] || 1)) * 0.55);
    const shown = format === 'percent1' ? `${(raw * 100).toFixed(1)}%` : raw.toLocaleString('en-GB');
    return `<div style="background: rgba(${tone}, ${alpha.toFixed(2)}); border-radius: 6px; padding: 4px 8px; text-align: right; font-weight: 600;">${shown}</div>`;
  };
}
```

The palette goes through the runtime's theme tokens on the host element (`--app-primary`, `--app-chart-1` to `--app-chart-7`, `--app-bg`), so every chart, grid and dropdown picks it up.

## Step 5: Lint, push, verify, preview

Wire's rules first, from the repo:

```bash
python3 <wire>/scripts/lint_conventions.py --domain data_apps \
  --convention <wire>/conventions/data_apps.yml --path data_apps/web-traffic --new-project
```

```
1 file(s) checked — 0 error(s), 0 warning(s)
```

Then the coverage check of the code against the plan:

```bash
python3 <wire>/scripts/data_app_plan.py check --plan dev/data_app/web-traffic/plan.json \
  --app-js data_apps/web-traffic/app.js --fields dev/data_app/web-traffic/fields.json
```

```
pass: true, widgets_expected: 17, widgets_found: 17, missing: [], extra: [], title_mismatches: [],
fields_unresolved: [], model_mismatch: [], explore_mismatch: [], filters_missing: []
```

Then a copy into the toolkit and Google's verification, stages 1 to 4:

```bash
python3 <wire>/scripts/data_app_toolkit.py push --app web-traffic --source data_apps/web-traffic
python3 <wire>/scripts/data_app_toolkit.py verify --app web-traffic --browser
```

```
verify: pass | queries: 19, failed: [], empty: [] | safety: [] | visual ok: True
```

Stage 3 dry-ran all 19 widget queries against Looker; stage 4 rendered the app headless in the tile sandbox and wrote `preview-sandbox.png`. The preview server then serves it on `http://localhost:8765/preview-server/?app=apps/web-traffic/app.js&sandbox=true`.

## Step 6: Validate and review

`/wire:data_app-validate` runs the twelve checks: the plan coverage above, no unmapped chart types, every field resolved, model and explore as recorded, every spec filter present, Wire's rules, Google's verify, the toolkit copy equal to the source, no literal data, titles equal to the catalog. `/wire:data_app-review` records the stakeholder's decision against the sandbox preview or the published dashboard.

## Step 7: Publish

Publishing is a utility the release director runs typed, never a lane. It shows the plan first:

```bash
python3 <wire>/scripts/data_app_toolkit.py publish plan --app web-traffic
```

```
title: Web Traffic
instance_host: rittman.eu.looker.com
publish_folder_id: 1
mode: first publish
command: python3 skills/data-app-publisher/tools/publish-data-app.py --def apps/web-traffic/app.js --title Web Traffic
```

Then, after the user's confirmation, the run:

```bash
python3 <wire>/scripts/data_app_toolkit.py publish run --app web-traffic --confirm
```

```
[1/5] dashboard created: id=419
[2/5] data app extension created: db::5dc779b8-... (34,113 bytes)
      registered 19 widget queries
      skipped: drawer-metric-by-channel: fields can't be worked out at publish time
      warning: da-chart-weekly-trend (Weekly Trend): fields read app state; Explore opens the published value
[3/5] dashboard_element created: id=3946
[4/5] layout 420 type=extension, full screen
[5/5] done

https://rittman.eu.looker.com/dashboards/419
```

The publisher wrote its tags into the toolkit copy's header. `pull --tags-only` brought them into the source, so a re-publish from any machine targets dashboard 419:

```javascript
/**
 * @title Web Traffic
 * @description ...
 * @looker-dashboard-id 419
 * @looker-instance https://rittman.eu.looker.com
 * @created-at 2026-11-01T00:45:44Z
 * @toolkit-version 1.2.0
 */
```

The drawer's breakdown chart has no "Explore from here", because which measure it shows depends on which card was clicked. The trend chart's "Explore from here" opens the measure the app was published with. Both are reported, not hidden.

## What the run taught

Three defects were found on the live run, none by the unit tests, and all are now in the skill, the spec or the code:

- **A widget's own filters replace the shared ones.** The referrers chart carried `filters: { referrer_host: '-NULL' }` inside its `.query` and showed all-time counts (google.com at 128,000 sessions instead of 727). The runtime takes a query's own filters in place of `.filters`. Per-widget filters go through `getEffectiveFilters(local)`.
- **Widget ids and fields have to be static text.** A helper that built the five KPI cards from arguments left the publisher nothing to register and the plan check nothing to find. Each widget is written out in full.
- **Google's result shapes.** The per-query result sits under `result`, and the publisher prints "registered N widget queries". The wrapper read both wrongly at first and could not have reported a failed query.

## Limits

No embedding, no PDF, no scheduled delivery, no LookML export. The dashboard must not be copied in Looker: copies share one extension, and a re-publish changes every copy. Sankey diagrams are not available: the toolkit's bundled Highcharts has no sankey module, and the tile cannot load one from the network.

## The result

The Overview tab: the hero band with the filters, the five KPI cards floating over its lower edge, the weekly trend with its switcher, the two rings, and the channel and referrer bars with the top-N slider.

![The Overview tab of the Web Traffic data app: a navy-to-teal hero band with Channel and Site dropdowns, five KPI cards overlapping its lower edge with weekly sparklines, a weekly trend chart with a Sessions, Page views, Meetings switcher, Device Split and New vs Returning rings, and Sessions by Channel and Top Referrers bar charts with a Top 8 slider](/img/data-apps/web-traffic-overview.png)

The Pages tab: the executive summary with three live content-group KPIs beside the landing-page table and its search box.

![The Pages tab: an executive summary panel with Case Study Views, Blog Views and Services Views beside a sortable Top Landing Pages table with a search box, showing sessions, bounce rate and meetings booked per landing page](/img/data-apps/web-traffic-pages.png)

The Engagement tab: the page-category treemap, the bounce-rate gauge and the heat-mapped channel scorecard.

![The Engagement tab: a Sessions by Page Category treemap, a Bounce Rate Target solid gauge reading 52.1%, and a Channel Scorecard grid whose Sessions, Page views, Meetings and Bounce rate cells are shaded against each column's best channel](/img/data-apps/web-traffic-engagement.png)

The drawer, opened from the Sessions card: the measure's definition and its split by channel.

![The detail drawer open over the Overview tab, showing the Sessions definition and a Sessions by channel bar chart](/img/data-apps/web-traffic-drawer.png)
