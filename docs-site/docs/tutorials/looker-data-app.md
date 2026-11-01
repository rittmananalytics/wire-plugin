---
sidebar_position: 20
title: "Tutorial: A Looker Data App"
---

# Tutorial: A Looker Data App on the Web Analytics explore

:::caution[Experimental]

The `data_app` artifact is experimental and Looker only. The figures on this page are from a real run on Rittman Analytics' own Looker instance on 1 November 2026, with Google's Data Apps toolkit 1.2.0; the app it produced is dashboard 419 on that instance.

:::

This tutorial shows a Looker Data App built, checked, reviewed and published in one release director session. The app is a three-tab Web Traffic page over the `web_sessions_fact` explore (labelled Web Analytics) in the `analytics` model: KPI cards with weekly sparklines, a weekly trend with a metric switcher, channel and referrer bars with a top-N slider, device and new-versus-returning rings, a landing-page table with a search box and an executive summary beside it, a detail drawer that opens from a card or a row, a bounce-rate gauge, a page-category treemap and a heat-mapped channel scorecard.

What a Data App is, how Wire supports it and the rules it checks are on the [Looker Data Apps](../advanced/data-apps) page. This page is the session.

## What you need

| Requirement | Who |
|---|---|
| A Looker-hosted instance, 26.18 or later, with Data Apps switched on under Admin, General, Previews | Looker admin |
| API keys enabled for your user, the dashboard author permissions, and Manage Access, Edit on the publish folder | Looker admin |
| Google's toolkit installed: `bash <(curl -fsSL https://dl.google.com/looker-data-apps/install.sh)`, which asks for the instance address, an API key and a folder | You |
| Wire 4.4.7 or later, and a `data_apps:` block in `.wire/engagement/context.md` naming where app sources live and the publish folder | You |

The toolkit keeps your credentials in its own config file. Wire never reads it.

## The design the app is built from

A Data App is built from the same design chain as a dashboard: the visualization catalog and the dashboard spec that `/wire:mockups-generate` writes next to the HTML mockup, and that `/wire:mockups-review` records the stakeholder's approval of. The catalog has one row per widget, with the explore's field names:

```csv
dashboard_page,visualization_name,chart_type,measures,dimensions
Web Traffic,Sessions,KPI tile,web_sessions_fact.total_sessions,
Web Traffic,Weekly Trend,area,web_sessions_fact.total_sessions; web_events_fact.total_page_views; web_events_fact.total_conversions,web_sessions_fact.session_start_ts_week
Web Traffic,Sessions by Channel,horizontal bar,web_sessions_fact.total_sessions,web_sessions_fact.channel
Web Traffic,Top Landing Pages,table,web_sessions_fact.total_sessions; web_sessions_fact.bounced_session_rate; web_events_fact.total_conversions,web_sessions_fact.first_page_title
Web Traffic,Bounce Rate Target,gauge,web_sessions_fact.bounced_session_rate,
Web Traffic,Sessions by Page Category,treemap,web_sessions_fact.total_sessions,web_sessions_fact.first_page_category
Web Traffic,Channel Scorecard,table,web_sessions_fact.total_sessions; web_events_fact.total_page_views; web_events_fact.total_conversions; web_sessions_fact.bounced_session_rate,web_sessions_fact.channel
```

Seventeen rows in all. The spec carries the three filters and four interaction lines:

```markdown
## Interaction Notes
- Tabs: Overview, Pages, Engagement
- Cross-filter: Sessions by Channel, Top Referrers, Device Split, New vs Returning, Sessions by Page Category
- Drill: a KPI card opens a drawer with the measure's definition and its split by channel; a landing page row opens a drawer with that page's weekly trend and channel mix
- Presentation: data_app
```

## The commands

| Command | What it does |
|---|---|
| `/wire:data_app-generate <release>` | Builds the app from the approved mockup chain and the explore, checks it, and starts the local preview |
| `/wire:data_app-validate <release>` | Checks the app against the design and the semantic layer, and runs Google's own verification; writes a PASS or FAIL report |
| `/wire:data_app-review <release>` | Records the stakeholder's decision |
| `/wire:data_app-publish <release>` | Shows where the app will go, asks, publishes it, and records the dashboard it became |

You do not have to type them. Say what you want, and the orchestrating session works out which command that is from the release type's definition, runs it, tells you what it did, and stops where a decision is yours. See [The Release Director Model](../advanced/release-director).

## The session

The session starts from work Wire had already recorded. The engagement repo holds a release created with `/wire:new` as a [Dashboard Extension](../release-types/dashboard-extension) release. Its requirements were captured with `/wire:requirements-generate` and signed off with `/wire:requirements-review`. Then `/wire:mockups-generate` produced the HTML mockup of the page, in a standard Looker dashboard layout, and with it the visualization catalog and the dashboard spec shown above; the marketing team reviewed the mockup and approved it through `/wire:mockups-review`. That is what "the approved mockup" and "the filters in the spec" refer to in the first prompt: files already in the release, carrying the stakeholder's approval.

The mockup fixes the content, not the look. A Data App does not resemble the dashboard mockup: the hero band, the floating cards, the sidebar and the drawer are designed when the app is generated, following Google's authoring skill and the brand palette. What the stakeholder approved in the mockup is which KPIs, charts and tables appear, on which fields, with which filters, tabs, cross-filtering and drill-through. The app's layout is approved at `data_app-review`, on the preview. The [Dashboard Extension tutorial](./dashboard-extension) walks through those earlier steps on a worked example.

The prompts are the director's; the rest is the orchestrating session.

```text
> Build the Web Traffic data app for the marketing team on the Web Analytics
  explore: the approved mockup, three tabs, the filters in the spec.

Release 03-web-traffic-app (dashboard_extension), director: Mark.
Requirements approved 24 Oct, mockups approved 28 Oct: catalog 17 rows, spec
3 filters, tabs Overview / Pages / Engagement, presentation data_app.
Runnable now: data_app-generate.

Running /wire:data_app-generate 03-web-traffic-app
  Toolkit 1.2.0 at ~/looker-data-apps (pinned 1.2.0), config present,
  credentials OK: 18 models visible.
  Explore analytics / web_sessions_fact: 177 dimensions, 22 measures.
  Plan: 17 widgets from 17 catalog rows, 0 unmapped, 0 unresolved,
  3 filters resolved.
  Written: data_apps/web-traffic/app.js (17 widgets, tabs, drawer, two
  dropdowns, metric switcher, top-N slider, search box).
  Rules: 0 errors, 0 warnings.
  Google's verification: syntax ok, sandbox ok, 19 queries dry-run on
  Looker, 0 failed, 0 empty.
  Preview: http://localhost:8765/preview-server/?app=apps/web-traffic/app.js&sandbox=true
  status.md: data_app.generate = complete.

Open the preview and tell me what to change, or say validate.
```

The director opens the preview and finds something.

```text
> Top Referrers shows google.com at 128,000 sessions. The page total is 16,593.

That chart carried its own filter (referrer not null) inside its query, which
replaces the page's filters, so the 90-day window never reached it. Moved it
through the shared filter function. Re-verified: 19 queries, 0 failed.
google.com is now 727 for the window. Nothing else changed.

> Validate it.

Running /wire:data_app-validate 03-web-traffic-app
   1  Target and toolkit                      PASS
   2  Every catalog row produced a widget     PASS  17 of 17
   3  No unmapped chart types                 PASS
   4  Every field resolves                    PASS
   5  Model and explore as recorded           PASS
   6  Every spec filter present               PASS  3 of 3
   7  Wire's rules                            PASS  0 errors
   8  Google's verify, stages 1 to 3          PASS  19 queries
   9  Toolkit copy is the source              PASS
  10  No literal data                         PASS
  11  Titles match the catalog                PASS
  12  Published copy is this source           n/a   not published yet
  Status: PASS. Report: dev/data_app/web-traffic/validation.md
  status.md: data_app.validate = pass.

Next is the stakeholder review. Who is reviewing, and where: the preview, or
shall I publish to a review folder first?

> The marketing lead reviewed it on the preview this morning and approved it.
  Publish it to the Shared folder.

Running /wire:data_app-review 03-web-traffic-app
  review = approved, reviewed_by: marketing lead, 1 Nov 2026.

Running /wire:data_app-publish 03-web-traffic-app
  Target: rittman.eu.looker.com, folder 1 (Shared), title "Web Traffic".
  First publish of this app.
  Publish / Cancel?

> Publish.

  Dashboard 419 created. App stored as its extension. 19 widget queries
  registered, so "Explore from here" works on every widget but one: the
  drawer's breakdown chart, whose measure depends on the card clicked.
  https://rittman.eu.looker.com/dashboards/419
  Dashboard id written into data_apps/web-traffic/app.js, committed on
  feature/03-web-traffic-app, pull request opened for technical review.
  status.md: data_app published, dashboard 419.

Done. Three things to know: a Data App cannot be embedded, printed or
scheduled; do not copy the dashboard in Looker, because copies share one
app; re-publishing from any machine updates 419, not a new dashboard.
```

Four prompts, one correction, one decision. Every step ran a real Wire command, so the release record is the same as a typed run: the plan, the validation report, the review and the dashboard id are all in the release folder and in `status.md`.

## Changing it later

The source is `data_apps/web-traffic/app.js` in the engagement repo, with the dashboard id in its header. A change is a ticket: `/wire:work 03-web-traffic-app` with what to change, and the same four commands run against dashboard 419. Nobody needs the machine the app was first built on.

The full source is published with this page: [web-traffic/app.js](/examples/data-apps/web-traffic/app.js).

## Limits

No embedding, no PDF, no scheduled delivery, no LookML export. The dashboard must not be copied in Looker: copies share one extension, and a re-publish changes every copy. Sankey diagrams are not available: the toolkit's bundled Highcharts has no sankey module, and the tile cannot load one from the network.

## The result

The Overview tab: the hero band with the filters, the five KPI cards floating over its lower edge, the weekly trend with its switcher, the two rings, and the channel and referrer bars with the top-N slider.

![The Overview tab of the Web Traffic data app: a navy-to-blue hero band with the Wire logo and Channel and Site dropdowns, five KPI cards overlapping its lower edge with weekly sparklines, a weekly trend chart with a Sessions, Page views, Meetings switcher, Device Split and New vs Returning rings, and Sessions by Channel and Top Referrers bar charts with a Top 8 slider](/img/data-apps/web-traffic-overview.png)

The Pages tab: the executive summary with three live content-group KPIs beside the landing-page table and its search box.

![The Pages tab: an executive summary panel with Case Study Views, Blog Views and Services Views beside a sortable Top Landing Pages table with a search box, showing sessions, bounce rate and meetings booked per landing page](/img/data-apps/web-traffic-pages.png)

The Engagement tab: the page-category treemap, the bounce-rate gauge and the channel scorecard, each cell shaded against its column's best channel.

![The Engagement tab: a Sessions by Page Category treemap, a Bounce Rate Target solid gauge reading 52.1%, and a Channel Scorecard grid whose Sessions, Page views, Meetings and Bounce rate cells are shaded against each column's best channel](/img/data-apps/web-traffic-engagement.png)

The drawer, opened from the Sessions card: the measure's definition and its split by channel.

![The detail drawer open over the Overview tab, showing the Sessions definition and a Sessions by channel bar chart](/img/data-apps/web-traffic-drawer.png)
