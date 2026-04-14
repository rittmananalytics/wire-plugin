---
name: looker-dashboard-mockup
description: >
  Generates pixel-accurate, interactive Looker dashboard HTML mockups from a plain-language
  description of the dashboard's contents. Use this skill whenever the user asks to mock up,
  prototype, visualise, or design a Looker dashboard — including requests like "create a Looker
  dashboard for X", "what would a Looker dashboard for X look like", "mock up a dashboard showing
  Y metrics", "prototype a Looker view for Z data", or any request to visualise analytics data in
  a Looker-style layout. Also trigger when the user shares a list of KPIs, charts, or data tables
  and asks how they would look in Looker. The output is a single self-contained HTML file that
  faithfully reproduces the Looker UI chrome (header, sidebar, filter pills, title bar, footer)
  and uses Chart.js for interactive charts.
---

# Looker Dashboard Mockup Generator

Generates a single self-contained HTML file that looks and behaves like a real Looker dashboard.
The output uses the official Looker design system (Google Sans, teal sidebar, blue filter pills,
stat cards with coloured top bars, Chart.js charts) and includes all Looker UI chrome.

## Step 1 — Gather the Specification

Before generating anything, extract (or ask for) these details from the user's request:

| Field | What to ask / infer |
|-------|---------------------|
| **Dashboard title** | Required — what is this dashboard called? |
| **Data domain** | e.g. Sales Pipeline, Delivery Health, Finance, Marketing |
| **KPI tiles** | Up to 6 — metric name, example value, unit, trend direction and %, sub-label |
| **Charts** | For each: title, chart type (line/bar/doughnut/horizontal-bar/area), axes labels, data series names |
| **Table** | Column headers, 5–8 sample rows of realistic data |
| **Filter pills** | Which dimensions should appear as filters (e.g. Date Range, Client, Status) |
| **Tabs** | Tab names across the top (e.g. Overview, Pipeline, Finance) |
| **Client / brand name** | Used in breadcrumb and footer |

If any field is missing and cannot be reasonably inferred from context, ask before generating.
For everything else, invent plausible but realistic sample data — never leave tiles or charts empty.

## Step 2 — Read the Design Reference

**Before writing any HTML**, read the design system reference:

```
wire/skills/looker-dashboard-mockup/references/design-system.md
```

This file contains:
- All CSS custom properties (colours, radius, shadows)
- Component class definitions (stat-card, chart-card, filter-pill, etc.)
- Chart.js configuration patterns for every chart type
- Table markup patterns including mini-bar, badge, and sort-icon helpers
- The full sidebar and header HTML structure

Do not guess at colours or class names — use the reference verbatim.

## Step 3 — Generate the HTML

Produce **one complete, self-contained HTML file** following this structure:

```
<head>
  Google Sans font import
  Chart.js CDN (4.4.1 from cdnjs)
  <style> — full CSS from design-system.md, no Tailwind/external CSS needed
</style>

<body>
  <header>        — Looker logo mark SVG, hamburger, icon buttons, avatar initials
  <div.body>
    <aside.sidebar> — Create button, nav sections, active state on current tab
    <main.main>
      <div.titlebar>   — Breadcrumb + h1 + action icons (heart, folder, refresh, more)
      <div.filter-bar> — One .filter-pill-wrap per filter dimension + Run button
      <div.tab-bar>    — One .tab per tab, first tab .active
      <div.content>    — KPI grid, chart rows, table, bottom chart row
  <footer>        — Dashboard name + disclaimer + "Prepared by · date"

  <script>
    Chart.defaults setup
    One new Chart(...) per canvas
    toggleSidebar(), setActive(), switchTab() helpers
  </script>
```

### Content Layout Rules

**KPI grid**: `grid-template-columns: repeat(N, 1fr)` where N = number of KPIs (max 5).
Each stat-card gets a `--card-accent` pointing to a different `--chart-N` variable.

**Chart rows**: use CSS grid.
- Single wide chart: `grid-template-columns: 1fr`
- Two charts side by side: `grid-template-columns: 3fr 2fr` (wide + narrow)
- Three charts: `grid-template-columns: 2fr 1fr 1fr`
- Never put more than 3 charts in one row.

**Table**: always include a bottom strip with Data / Results / SQL tabs and a row-count + timing indicator.

**Charts**: set `canvas` heights explicitly via a wrapper `div` with `height: Npx`. Use:
- Line/area: `height: 200px` in the main row, `height: 180px` in the bottom row
- Doughnut: `height: 200px` — always `cutout: '62%'`, legend `position: 'right'` or `'bottom'`
- Horizontal bar: `height: 180px`, `indexAxis: 'y'`
- Vertical bar: `height: 200px`

### Data Realism Rules

- Use realistic but anonymised values (£/$/€ with K/M suffixes for money)
- Trend arrows: ↑ for positive → success colour, ↓ for negative → destructive colour, → for neutral → muted
- Table badges: Green/Amber/Red for RAG-style status; Blue for state labels
- Mini progress bars in tables: width% matches a percentage column value
- Chart data should tell a coherent story — don't just use sequential numbers

### Stat Card Colour Cycling

Cycle through `--chart-1` through `--chart-6` for `--card-accent`:
1 → chart-1 (blue), 2 → chart-3 (yellow), 3 → chart-5 (orange), 4 → chart-6 (teal), 5 → chart-2 (purple), 6 → chart-4 (red)

## Step 4 — Output the File

Write the complete HTML to the path specified by the caller (e.g. `.wire/<project-folder>/design/mockups/<dashboard-slug>.html`),
where `<dashboard-slug>` is a lowercase-hyphenated version of the dashboard title.

Follow up with a brief summary (3–5 bullet points) of what was generated — tile names, chart types,
table columns — so the user can quickly verify it matches their intent without opening the file.

## Step 5 — Iteration

If the user asks to change specific tiles, charts, or data:
- Re-read the design-system.md reference to confirm you're using correct class names
- Make targeted edits to the relevant `<canvas>` block or stat-card HTML
- Re-write the full file (do not produce partial diffs — always output the complete file)
- Present the updated file

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/design-system.md` | Complete CSS, component patterns, Chart.js config — **read before generating** |
