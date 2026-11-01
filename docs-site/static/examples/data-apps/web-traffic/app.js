/**
 * @title Web Traffic
 * @description Website traffic for rittmananalytics.com as a three-tab app: volume, sources and audience on Overview; landing pages with an executive summary, a search box and a detail drawer on Pages; a bounce-rate gauge, a page-category treemap and a heat-mapped channel scorecard on Engagement. Every figure is a live query on the analytics model's web_sessions_fact explore. Built by Wire (data_app, wire#387).
 */

import { DataApp, html, nothing, createNumericCol, createPercentageCol } from '/runtime/data-app.js';

export const elementName = 'web-traffic-app';

const WEEK = 'web_sessions_fact.session_start_ts_week';
const SPARK_WINDOW = { 'web_sessions_fact.session_start_ts_week': '13 weeks ago for 13 weeks' };

// Definitions shown in the drawer, from the explore's own field descriptions.
const GLOSSARY = {
  'web_sessions_fact.total_sessions': { label: 'Sessions', format: 'int',
    text: 'The number of distinct web sessions. A session ends after 30 minutes without activity.' },
  'web_events_fact.total_unique_users': { label: 'Unique Users', format: 'int',
    text: 'Distinct users (one per browser, by blended user id) who generated at least one event in the window.' },
  'web_events_fact.total_page_views': { label: 'Page Views', format: 'int',
    text: 'Distinct Page View events across the sites.' },
  'web_sessions_fact.bounced_session_rate': { label: 'Bounce Rate', format: 'percent1',
    text: 'Bounced sessions divided by total sessions. A bounced session saw one page and did nothing else. Lower is better.' },
  'web_events_fact.total_conversions': { label: 'Meetings Booked', format: 'int',
    text: 'Distinct Meeting Booked events: a visitor booked a call through the site.' },
};

const TREND_METRICS = [
  { value: 'web_sessions_fact.total_sessions', label: 'Sessions', format: 'int' },
  { value: 'web_events_fact.total_page_views', label: 'Page views', format: 'int' },
  { value: 'web_events_fact.total_conversions', label: 'Meetings', format: 'int' },
];

const BAR_OPTIONS = {
  legend: { enabled: false },
  xAxis: { reversed: true, lineWidth: 0, tickLength: 0, labels: { style: { fontSize: '12px' } } },
  yAxis: { title: { text: null }, gridLineColor: 'rgba(15, 26, 43, .08)' },
  plotOptions: { bar: { borderRadius: 4, pointPadding: 0.12, groupPadding: 0.08 } },
};
const RING_OPTIONS = {
  legend: { enabled: true, align: 'right', verticalAlign: 'middle', layout: 'vertical', itemStyle: { fontSize: '12px', fontWeight: '500' } },
  plotOptions: { pie: { innerSize: '72%', dataLabels: { enabled: false }, borderWidth: 2, showInLegend: true } },
};
const TREND_OPTIONS = {
  legend: { enabled: false },
  xAxis: { lineWidth: 0, tickLength: 0, labels: { style: { fontSize: '11px' } } },
  yAxis: { min: 0, title: { text: null }, gridLineColor: 'rgba(15, 26, 43, .08)' },
  plotOptions: { areaspline: { fillOpacity: 0.28, lineWidth: 2.5, marker: { enabled: false } } },
};
const TREEMAP_OPTIONS = {
  plotOptions: { treemap: { borderWidth: 2, borderColor: '#ffffff', dataLabels: { style: { fontSize: '12px', fontWeight: '600', textOutline: 'none' } } } },
};

// Heat-mapped scorecard cells. The column's maximum is read from the grid's
// own rows each time a cell renders (12 rows, so cheap), never from app state:
// state set from a grid callback is not there for the first render. The scale
// is square root, so a column running from 15,000 down to 4 still grades
// instead of putting every row but the top one at the floor. Text goes white
// once the blended cell is dark.
function heatCell(field, format, tone) {
  const [r, g, b] = tone.split(',').map(Number);
  return (params) => {
    if (!params.data) return '';
    const raw = Number(params.data[field]) || 0;
    let max = 0;
    params.api.forEachNode(n => { const v = Number((n.data || {})[field]) || 0; if (v > max) max = v; });
    const share = max > 0 ? Math.sqrt(Math.max(raw, 0) / max) : 0;
    const alpha = 0.06 + share * 0.9;
    // luminance of the cell over white, to pick the text colour
    const lum = (0.2126 * (alpha * r + (1 - alpha) * 255) + 0.7152 * (alpha * g + (1 - alpha) * 255) + 0.0722 * (alpha * b + (1 - alpha) * 255)) / 255;
    const text = lum < 0.62 ? '#ffffff' : '#0b1a2b';
    const shown = format === 'percent1' ? `${(raw * 100).toFixed(1)}%` : raw.toLocaleString('en-GB');
    return `<div style="background: rgba(${r}, ${g}, ${b}, ${alpha.toFixed(2)}); color: ${text}; border-radius: 6px; padding: 4px 8px; text-align: right; font-weight: 600;">${shown}</div>`;
  };
}

export class WebTrafficApp extends DataApp {
  static properties = {
    activeTab: { type: String },
    channel: { type: String },
    site: { type: String },
    trendMetric: { type: String },
    topN: { type: Number },
    pageSearch: { type: String },
    drawer: { type: Object },
  };

  constructor() {
    super();
    this.lookerModel = 'analytics';
    this.explore = 'web_sessions_fact';
    this.activeTab = 'overview';
    this.channel = 'All';
    this.site = 'All';
    this.trendMetric = 'web_sessions_fact.total_sessions';
    this.topN = 8;
    this.pageSearch = '';
    this.drawer = null;
  }

  // Every widget's filters: Looker's own filter bar, cross-filters from the
  // charts, the two dropdowns, and the spec's default date window. A widget's
  // own filter is passed as `local`, never written under .query.filters.
  getEffectiveFilters(local = {}) {
    const filters = { ...(this.dashboardFilters || {}), ...(this.crossFilters || {}) };
    if (!filters['web_sessions_fact.session_start_ts_date']) {
      filters['web_sessions_fact.session_start_ts_date'] = '90 days';
    }
    if (this.channel !== 'All') filters['web_sessions_fact.channel'] = this.channel;
    if (this.site !== 'All') filters['web_sessions_fact.site'] = this.site;
    return { ...filters, ...local };
  }

  sparkFilters() {
    const f = this.getEffectiveFilters(SPARK_WINDOW);
    delete f['web_sessions_fact.session_start_ts_date'];
    return f;
  }

  scopeLabel() {
    return ['Last 90 days', this.channel === 'All' ? 'all channels' : this.channel,
            this.site === 'All' ? 'both sites' : this.site].join(' · ');
  }

  openMetric(field) { this.drawer = { kind: 'metric', field }; }
  openPage(row) { this.drawer = { kind: 'page', title: row['web_sessions_fact.first_page_title'] }; }
  closeDrawer() { this.drawer = null; }

  kpiCard(cls, field, foot, body) {
    return html`
      <div class="wt-kpi ${cls}" role="button" tabindex="0" title="Open the definition and the channel breakdown"
        @click=${() => this.openMetric(field)}
        @keydown=${e => { if (e.key === 'Enter' || e.key === ' ') this.openMetric(field); }}>
        ${body}
        <div class="wt-kpi-foot"><span>${foot}</span><span class="wt-kpi-more">Details ›</span></div>
      </div>`;
  }

  renderDrawer() {
    if (!this.drawer) return nothing;
    const d = this.drawer;
    const filters = this.getEffectiveFilters();
    let heading, sub, body;
    if (d.kind === 'metric') {
      const g = GLOSSARY[d.field];
      heading = g.label; sub = d.field;
      body = html`
        <p class="wt-drawer-text">${g.text}</p>
        <p class="wt-panel-label">${g.label} by channel</p>
        <app-chart bare id="drawer-metric-by-channel" type="bar" title="${g.label} by channel" height="300px"
          value-format=${g.format} color="var(--app-primary)" .options=${BAR_OPTIONS}
          .query=${{ fields: ['web_sessions_fact.channel', d.field], sorts: [d.field + ' desc'], limit: '10' }}
          .filters=${filters}></app-chart>`;
    } else {
      heading = d.title; sub = 'landing page';
      body = html`
        <p class="wt-drawer-text">Sessions that started on this page, by week, under the page's current filters.</p>
        <p class="wt-panel-label">Sessions by week</p>
        <app-chart bare id="drawer-page-trend" type="areaspline" title="Sessions by week" height="260px"
          value-format="int" color="var(--wt-primary)" .options=${TREND_OPTIONS}
          .query=${{ fields: [WEEK, 'web_sessions_fact.total_sessions'], sorts: [WEEK] }}
          .filters=${this.getEffectiveFilters({ 'web_sessions_fact.first_page_title': d.title })}></app-chart>
        <p class="wt-panel-label" style="margin-top: 14px;">Channel mix for this page</p>
        <app-chart bare id="drawer-page-channels" type="donut" title="Channel mix" height="170px"
          value-format="int" .options=${RING_OPTIONS}
          .query=${{ fields: ['web_sessions_fact.channel', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'], limit: '6' }}
          .filters=${this.getEffectiveFilters({ 'web_sessions_fact.first_page_title': d.title })}></app-chart>`;
    }
    return html`
      <div class="wt-backdrop" @click=${() => this.closeDrawer()}></div>
      <aside class="wt-drawer" role="dialog" aria-label=${heading}>
        <div class="wt-drawer-head">
          <div><p class="wt-eyebrow wt-eyebrow-dark">${sub}</p><h3>${heading}</h3></div>
          <button class="wt-close" @click=${() => this.closeDrawer()} aria-label="Close">×</button>
        </div>
        ${body}
      </aside>`;
  }

  renderOverview() {
    const filters = this.getEffectiveFilters();
    const metric = TREND_METRICS.find(m => m.value === this.trendMetric) || TREND_METRICS[0];
    return html`
      <section class="wt-section">
        <div class="wt-section-title"><h2>Volume and audience</h2><span>weekly trend of a chosen measure, with who is visiting and on what</span></div>
        <div class="wt-story">
          <div class="wt-panel">
            <div class="wt-panel-head">
              <p class="wt-panel-label">Weekly Trend <em>week starting</em></p>
              <div class="wt-segment" role="group" aria-label="Trend measure">
                ${TREND_METRICS.map(m => html`
                  <button class="wt-seg-btn ${this.trendMetric === m.value ? 'active' : ''}" @click=${() => { this.trendMetric = m.value; }}>${m.label}</button>`)}
              </div>
            </div>
            <!-- catalog row 7: Weekly Trend -->
            <app-chart bare id="da-chart-weekly-trend" type="areaspline" title="Weekly Trend" height="320px"
              value-format=${metric.format} color="var(--wt-primary)" .options=${TREND_OPTIONS}
              .query=${{ fields: [WEEK, this.trendMetric], sorts: [WEEK] }}
              .filters=${filters}></app-chart>
          </div>
          <div class="wt-stack">
            <div class="wt-panel">
              <p class="wt-panel-label">Device Split</p>
              <app-chart bare id="da-chart-device-split" type="donut" title="Device Split" height="140px" cross-filter
                value-format="int" .options=${RING_OPTIONS}
                .query=${{ fields: ['web_sessions_fact.device_category', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'] }}
                .filters=${filters}></app-chart>
            </div>
            <div class="wt-panel">
              <p class="wt-panel-label">New vs Returning</p>
              <app-chart bare id="da-chart-new-vs-returning" type="donut" title="New vs Returning" height="140px" cross-filter
                value-format="int" .options=${RING_OPTIONS}
                .query=${{ fields: ['web_sessions_fact.new_or_returning_user', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'] }}
                .filters=${filters}></app-chart>
            </div>
          </div>
        </div>
      </section>

      <section class="wt-section">
        <div class="wt-section-title">
          <h2>Where visits come from</h2><span>attributed channel, and the referring site where there is one</span>
          <label class="wt-slider">Top <strong>${this.topN}</strong>
            <input type="range" min="5" max="15" step="1" .value=${String(this.topN)}
              @input=${e => { this.topN = Number(e.target.value); }} aria-label="How many bars to show">
          </label>
        </div>
        <div class="wt-pair">
          <div class="wt-panel">
            <p class="wt-panel-label">Sessions by Channel</p>
            <app-chart bare id="da-chart-sessions-by-channel" type="bar" title="Sessions by Channel" height="300px" cross-filter
              value-format="int" color="var(--app-primary)" .options=${BAR_OPTIONS}
              .query=${{ fields: ['web_sessions_fact.channel', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'], limit: String(this.topN) }}
              .filters=${filters}></app-chart>
          </div>
          <div class="wt-panel">
            <p class="wt-panel-label">Top Referrers <em>sessions with a referrer</em></p>
            <app-chart bare id="da-chart-top-referrers" type="bar" title="Top Referrers" height="300px" cross-filter
              value-format="int" color="var(--wt-secondary)" .options=${BAR_OPTIONS}
              .query=${{ fields: ['web_sessions_fact.referrer_host', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'], limit: String(this.topN) }}
              .filters=${this.getEffectiveFilters({ 'web_sessions_fact.referrer_host': '-NULL' })}></app-chart>
          </div>
        </div>
      </section>`;
  }

  renderPages() {
    const filters = this.getEffectiveFilters();
    const search = this.pageSearch.trim();
    const gridFilters = search ? this.getEffectiveFilters({ 'web_sessions_fact.first_page_title': `%${search}%` }) : filters;
    return html`
      <section class="wt-section">
        <div class="wt-section-title"><h2>What visits land on</h2><span>the first page of each session; click a row for its trend and channel mix</span></div>
        <div class="wt-split">
          <aside class="wt-summary">
            <p class="wt-eyebrow wt-eyebrow-dark">Executive summary</p>
            <h3>Where the first page view lands</h3>
            <p>The home page and the podcast carry most first visits. Case studies and services pages are the pages a buyer reads; the blog is where search traffic arrives. The three figures below are page views in the window for those content groups.</p>
            <!-- catalog rows 13 to 15: content group KPIs -->
            <div class="wt-mini">
              <div class="wt-mini-card">
                <app-kpi bare id="da-kpi-case-study-views" label="Case Study Views" format="int"
                  query-field="web_events_fact.total_case_study_page_views" .filters=${filters}></app-kpi>
              </div>
              <div class="wt-mini-card">
                <app-kpi bare id="da-kpi-blog-views" label="Blog Views" format="int"
                  query-field="web_events_fact.total_blog_page_views" .filters=${filters}></app-kpi>
              </div>
              <div class="wt-mini-card">
                <app-kpi bare id="da-kpi-services-views" label="Services Views" format="int"
                  query-field="web_events_fact.total_services_page_views" .filters=${filters}></app-kpi>
              </div>
            </div>
            <p class="wt-summary-note">Bounce rate on a landing page counts sessions that saw only that page. A high rate on a podcast or blog page is normal; on a services page it is a prompt to look at the page.</p>
          </aside>
          <div class="wt-panel">
            <div class="wt-panel-head">
              <p class="wt-panel-label">Top Landing Pages <em>top 50 by sessions</em></p>
              <label class="wt-search">
                <input type="search" placeholder="Search page titles, then Enter" .value=${this.pageSearch}
                  @change=${e => { this.pageSearch = e.target.value; }} aria-label="Search landing pages">
              </label>
            </div>
            <!-- catalog row 11: Top Landing Pages -->
            <app-grid bare id="da-grid-top-landing-pages" title="Top Landing Pages" height="520px"
              .gridOptions=${{ defaultColDef: { resizable: true, sortable: true }, rowHeight: 34 }}
              .columnDefs=${[
                { field: 'web_sessions_fact.first_page_title', headerName: 'Landing page', flex: 3, minWidth: 280, filter: true },
                createNumericCol({ field: 'web_sessions_fact.total_sessions', headerName: 'Sessions', format: 'int' }),
                createPercentageCol({ field: 'web_sessions_fact.bounced_session_rate', headerName: 'Bounce rate', format: 'percent1' }),
                createNumericCol({ field: 'web_events_fact.total_conversions', headerName: 'Meetings booked', format: 'int' }),
              ]}
              .query=${{ fields: ['web_sessions_fact.first_page_title', 'web_sessions_fact.total_sessions',
                                  'web_sessions_fact.bounced_session_rate', 'web_events_fact.total_conversions'],
                         sorts: ['web_sessions_fact.total_sessions desc'], limit: '50' }}
              .filters=${gridFilters}
              @app-grid-row-click=${e => this.openPage(e.detail.row)}></app-grid>
          </div>
        </div>
      </section>`;
  }

  renderEngagement() {
    const filters = this.getEffectiveFilters();
    const scoreFields = [
      ['web_sessions_fact.total_sessions', 'Sessions', 'int', '79, 96, 255'],
      ['web_events_fact.total_page_views', 'Page views', 'int', '37, 51, 166'],
      ['web_events_fact.total_conversions', 'Meetings', 'int', '255, 141, 115'],
      ['web_sessions_fact.bounced_session_rate', 'Bounce rate', 'percent1', '232, 103, 74'],
    ];
    return html`
      <section class="wt-section">
        <div class="wt-section-title"><h2>How visits engage</h2><span>against the bounce-rate target, by the kind of page they land on, and by channel</span></div>
        <div class="wt-story">
          <div class="wt-panel">
            <p class="wt-panel-label">Sessions by Page Category <em>first page of the session; click to filter</em></p>
            <!-- catalog row 17: Sessions by Page Category -->
            <app-chart bare id="da-chart-sessions-by-page-category" type="treemap" title="Sessions by Page Category" height="340px" cross-filter
              value-format="int" .options=${TREEMAP_OPTIONS}
              .query=${{ fields: ['web_sessions_fact.first_page_category', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.total_sessions desc'], limit: '20' }}
              .filters=${filters}></app-chart>
          </div>
          <div class="wt-panel wt-gauge-panel">
            <p class="wt-panel-label">Bounce Rate Target <em>target under 45%</em></p>
            <!-- catalog row 16: Bounce Rate Target -->
            <app-chart bare id="da-chart-bounce-rate-target" type="solidgauge" title="Bounce Rate Target" height="260px"
              value-format="percent1" polarity="lower-better"
              .query=${{ fields: ['web_sessions_fact.bounced_session_rate'], limit: '1' }}
              .filters=${filters}></app-chart>
            <p class="wt-gauge-note">Red means most sessions see one page and leave. The dial reads the same bounce rate as the headline card.</p>
          </div>
        </div>
      </section>

      <section class="wt-section">
        <div class="wt-section-title"><h2>Channel scorecard</h2><span>each column shaded against its own best channel</span></div>
        <div class="wt-panel">
          <!-- catalog row 18: Channel Scorecard -->
          <app-grid bare id="da-grid-channel-scorecard" title="Channel Scorecard" height="380px"
            .gridOptions=${{ defaultColDef: { resizable: true, sortable: true }, rowHeight: 38 }}
            .columnDefs=${[
              { field: 'web_sessions_fact.channel', headerName: 'Channel', flex: 1.4, minWidth: 160, pinned: 'left', cellStyle: { fontWeight: '600' } },
              ...scoreFields.map(([f, name, fmt, tone]) => ({ field: f, headerName: name, flex: 1, minWidth: 120, type: 'rightAligned', cellRenderer: heatCell(f, fmt, tone) })),
            ]}
            .query=${{ fields: ['web_sessions_fact.channel', 'web_sessions_fact.total_sessions', 'web_events_fact.total_page_views', 'web_events_fact.total_conversions', 'web_sessions_fact.bounced_session_rate'], sorts: ['web_sessions_fact.total_sessions desc'], limit: '12' }}
            .filters=${filters}></app-grid>
        </div>
      </section>`;
  }

  render() {
    const tabs = [['overview', 'Overview'], ['pages', 'Pages'], ['engagement', 'Engagement']];
    const filters = this.getEffectiveFilters();
    const spark = this.sparkFilters();
    return html`
      <style>
        web-traffic-app {
          /* Rittman Analytics brand: primary #4F60FF, secondary #FF8D73, grey #F7F7FA, chart
             series #AD86FF and #87D5FC, with tints (towards white) and shades (towards ink). */
          --wt-ink: #0b1a2b; --wt-ink-soft: #4b5868;
          --wt-primary: #4f60ff; --wt-primary-t1: #8c97ff; --wt-primary-t2: #b9c0ff; --wt-primary-t3: #e4e7ff;
          --wt-primary-s1: #3545d6; --wt-primary-deep: #2533a6; --wt-primary-s3: #17206b;
          --wt-secondary: #ff8d73; --wt-secondary-t1: #ffbbab; --wt-secondary-t2: #ffd9d0; --wt-secondary-t3: #ffefeb;
          --wt-secondary-s1: #e8674a; --wt-secondary-deep: #b84b32;
          --wt-canvas: #f7f7fa; --wt-line: #e4e6ee;
          --app-bg: var(--wt-canvas); --app-card-bg: #ffffff; --app-border: var(--wt-line); --app-text: var(--wt-ink);
          --app-title: var(--wt-ink); --app-muted: var(--wt-ink-soft); --app-primary: var(--wt-primary); --app-primary-hover: var(--wt-primary-s1);
          --wt-series-3: #ad86ff; --wt-series-4: #87d5fc;
          --app-chart-1: #4f60ff; --app-chart-2: #ff8d73; --app-chart-3: #ad86ff; --app-chart-4: #87d5fc; --app-chart-5: #2533a6;
          --app-chart-6: #ffbbab; --app-chart-7: #8c97ff; --app-chart-unselected: #dde1ea;
          --app-tabs-bg: #e9ebf2; --app-radius: 18px;
          font-family: 'Google Sans', 'Inter', system-ui, -apple-system, sans-serif;
        }
        .wt-root { max-width: 1480px; margin: 0 auto; padding: 18px 22px 44px; color: var(--wt-ink); background: var(--wt-canvas); }

        /* Hero band, with the KPI cards floating over its lower edge */
        .wt-hero { position: relative; overflow: hidden; border-radius: 22px; padding: 26px 30px 70px;
          background: linear-gradient(118deg, #0b1a2b 0%, #141f4d 45%, #3545d6 100%, #4f60ff 130%); color: #fff; box-shadow: 0 18px 40px -24px rgba(11, 26, 43, .7); }
        .wt-hero::after { content: ''; position: absolute; right: -80px; top: -120px; width: 360px; height: 360px; border-radius: 50%;
          background: radial-gradient(circle, rgba(255, 141, 115, .45) 0%, rgba(255, 141, 115, 0) 65%); }
        .wt-hero-row { display: flex; justify-content: space-between; align-items: stretch; gap: 20px; flex-wrap: wrap; position: relative; z-index: 1; }
        .wt-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: rgba(255,255,255,.72); margin: 0 0 6px; }
        .wt-eyebrow-dark { color: var(--wt-ink-soft); }
        .wt-hero h1 { margin: 0; font-size: 30px; line-height: 1.1; letter-spacing: -0.02em; font-weight: 700; }
        .wt-hero p { margin: 10px 0 0; max-width: 680px; font-size: 14px; line-height: 1.5; color: rgba(255,255,255,.82); }
        .wt-scope { display: inline-flex; align-items: center; gap: 8px; margin-top: 14px; padding: 6px 12px; border-radius: 999px;
          background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); font-size: 12px; font-weight: 500; }
        .wt-scope::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--wt-secondary); }
        .wt-hero-side { display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between; gap: 16px; }
        .wt-logo { height: 64px; width: auto; display: block; }
        .wt-hero-controls { display: flex; gap: 12px; flex-wrap: wrap; padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); }
        .wt-hero-controls .da-select-label, .wt-hero-controls label { color: rgba(255,255,255,.85); }

        .wt-kpis { position: relative; z-index: 2; margin: -48px 18px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(190px, 100%), 1fr)); gap: 14px; }
        .wt-kpi { position: relative; background: #fff; border: 1px solid var(--wt-line); border-radius: 18px; padding: 14px 18px 10px; overflow: hidden; cursor: pointer;
          box-shadow: 0 16px 36px -20px rgba(11, 26, 43, .55); transition: transform .15s ease, box-shadow .15s ease; }
        .wt-kpi:hover { transform: translateY(-2px); box-shadow: 0 22px 40px -22px rgba(11, 26, 43, .6); }
        .wt-kpi::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--wt-primary); }
        .wt-kpi.is-secondary::before { background: var(--wt-secondary); }
        .wt-kpi.is-primary-deep::before { background: var(--wt-primary-deep); }
        .wt-kpi app-kpi { display: block; }
        .wt-kpi-foot { display: flex; justify-content: space-between; font-size: 11px; color: var(--wt-ink-soft); margin-top: 6px; }
        .wt-kpi-more { color: var(--wt-primary); font-weight: 600; }

        .wt-tabs-row { display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap; margin: 22px 0 4px; }
        .wt-tabs-row .da-tabs { width: max-content; }
        .wt-tabs-hint { font-size: 12px; color: var(--wt-ink-soft); }

        .wt-section { margin-top: 20px; }
        .wt-section-title { display: flex; align-items: baseline; gap: 12px; margin: 0 0 10px 4px; flex-wrap: wrap; }
        .wt-section-title h2 { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -0.01em; }
        .wt-section-title span { font-size: 12px; color: var(--wt-ink-soft); }
        .wt-panel { background: #fff; border: 1px solid var(--wt-line); border-radius: 18px; padding: 18px 18px 12px; box-shadow: 0 10px 30px -26px rgba(11, 26, 43, .5); }
        .wt-panel-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
        .wt-panel-head .wt-panel-label { margin: 0; }
        .wt-panel-label { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--wt-ink-soft); margin: 0 0 10px; display: flex; justify-content: space-between; gap: 10px; }
        .wt-panel-label em { font-style: normal; font-weight: 500; letter-spacing: 0; text-transform: none; }

        /* Controls: segmented buttons, range slider, search */
        .wt-segment { display: inline-flex; background: var(--app-tabs-bg); border-radius: 10px; padding: 3px; gap: 2px; }
        .wt-seg-btn { border: 0; background: transparent; padding: 6px 12px; font-size: 12px; font-weight: 600; color: var(--wt-ink-soft); border-radius: 8px; cursor: pointer; }
        .wt-seg-btn.active { background: #fff; color: var(--wt-primary); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
        .wt-slider { margin-left: auto; display: inline-flex; align-items: center; gap: 10px; font-size: 12px; color: var(--wt-ink-soft); }
        .wt-slider input { accent-color: var(--wt-primary); width: 140px; }
        .wt-search input { width: 260px; max-width: 100%; padding: 7px 12px; border: 1px solid var(--wt-line); border-radius: 10px; font: inherit; font-size: 13px; background: #fff; color: var(--wt-ink); }
        .wt-search input:focus { outline: 2px solid rgba(79, 96, 255, .35); border-color: var(--wt-primary); }

        /* Layouts */
        .wt-story { display: grid; grid-template-columns: minmax(0, 2.1fr) minmax(0, 1fr); gap: 14px; }
        .wt-stack { display: grid; grid-template-rows: 1fr 1fr; gap: 14px; }
        .wt-pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: 14px; }
        .wt-split { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(0, 2.6fr); gap: 14px; align-items: start; }
        .wt-summary { background: linear-gradient(160deg, #ffffff 0%, var(--wt-primary-t3) 100%); border: 1px solid var(--wt-line); border-radius: 18px; padding: 20px; }
        .wt-summary h3 { margin: 0 0 8px; font-size: 17px; line-height: 1.25; letter-spacing: -0.01em; }
        .wt-summary p { margin: 0 0 12px; font-size: 13px; line-height: 1.55; color: var(--wt-ink-soft); }
        .wt-summary-note { border-top: 1px solid var(--wt-line); padding-top: 12px; }
        .wt-mini { display: grid; gap: 10px; margin: 6px 0 14px; }
        .wt-mini-card { background: #fff; border: 1px solid var(--wt-line); border-radius: 14px; padding: 8px 12px; }
        .wt-gauge-panel { display: flex; flex-direction: column; }
        .wt-gauge-note { margin: 4px 0 6px; font-size: 12px; line-height: 1.5; color: var(--wt-ink-soft); }
        @media (max-width: 980px) { .wt-story, .wt-split { grid-template-columns: 1fr; } .wt-stack { grid-template-rows: auto; grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr)); } .wt-kpis { margin: -40px 8px 0; } }

        /* Drawer */
        .wt-backdrop { position: fixed; inset: 0; background: rgba(11, 26, 43, .45); z-index: 40; }
        .wt-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(520px, 92vw); background: #fff; z-index: 41; padding: 22px 24px; overflow-y: auto;
          box-shadow: -24px 0 60px -30px rgba(11, 26, 43, .6); animation: wtSlide .22s cubic-bezier(.16, 1, .3, 1); }
        @keyframes wtSlide { from { transform: translateX(40px); opacity: 0; } to { transform: none; opacity: 1; } }
        .wt-drawer-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
        .wt-drawer-head h3 { margin: 0; font-size: 20px; line-height: 1.2; letter-spacing: -0.01em; }
        .wt-close { border: 1px solid var(--wt-line); background: #fff; width: 34px; height: 34px; border-radius: 10px; font-size: 20px; line-height: 1; cursor: pointer; color: var(--wt-ink-soft); }
        .wt-drawer-text { font-size: 13px; line-height: 1.55; color: var(--wt-ink-soft); margin: 0 0 14px; }

        /* Scoped overrides of runtime chrome inside my panels only. */
        .wt-panel .chart-header, .wt-kpi .chart-header, .wt-drawer .chart-header, .wt-mini-card .chart-header { display: none; }
        .wt-panel .grid-container { border: 0; }
      </style>

      <div class="wt-root">
        <header class="wt-hero">
          <div class="wt-hero-row">
            <div>
              <p class="wt-eyebrow">Rittman Analytics · Web analytics</p>
              <h1>Web Traffic</h1>
              <p>How many people reach the sites, where they come from, what they land on, and how often a visit turns into a booked meeting. Every figure is a live query on the <strong>web_sessions_fact</strong> explore, as the person viewing it. Click a card for its definition.</p>
              <div class="wt-scope">${this.scopeLabel()}</div>
            </div>
            <div class="wt-hero-side">
              <!-- Wire wordmark, inline SVG: the tile cannot load images from other hosts -->
              <svg class="wt-logo" viewBox="0 0 831 235" role="img" aria-label="Rittman Analytics Wire" xmlns="http://www.w3.org/2000/svg"><path d="M45.8553 87.3287C45.8553 85.6156 46.5398 83.9024 47.5664 82.8745C48.593 81.8466 50.304 81.1614 52.3572 81.1614C54.4105 81.1614 55.7793 81.8466 56.8059 82.8745C57.8325 83.9024 58.5169 85.6156 58.5169 87.3287C58.5169 89.0419 57.8325 90.4124 56.8059 91.7829C55.7793 92.8108 54.0682 93.4961 52.3572 93.4961C50.6462 93.4961 48.9352 92.8108 47.9086 91.7829C46.5398 90.755 45.8553 89.0419 45.8553 87.3287ZM56.4637 101.377V153.114H47.5664V101.377H56.4637Z" fill="white"/><path d="M103.688 145.233V152.428C102.661 153.114 101.293 153.456 99.9237 153.799C98.5549 154.142 96.8439 154.142 95.1329 154.142C89.9998 154.142 86.2355 152.771 83.8401 150.03C81.4447 147.289 80.4181 143.177 80.4181 137.353V108.914H68.4409V101.377H80.4181V87.6714L88.9732 82.532V101.377H104.03V108.914H88.9732V136.325C88.9732 140.094 89.6576 142.835 91.0264 144.205C92.3952 145.576 94.4485 146.261 97.1861 146.261C98.5549 146.261 99.5815 146.261 100.608 145.919C101.635 145.919 102.661 145.576 103.688 145.233Z" fill="white"/><path d="M146.121 145.233V152.428C145.095 153.114 143.726 153.456 142.357 153.799C140.988 154.142 139.277 154.142 137.566 154.142C132.433 154.142 128.669 152.771 126.273 150.03C123.878 147.289 122.851 143.177 122.851 137.353V108.914H110.874V101.377H122.851V87.6714L131.407 82.532V101.377H146.464V108.914H131.407V136.325C131.407 140.094 132.091 142.835 133.46 144.205C134.829 145.576 136.882 146.261 139.619 146.261C140.988 146.261 142.015 146.261 143.041 145.919C144.068 145.919 145.095 145.576 146.121 145.233Z" fill="white"/><path d="M166.311 128.444V153.114H157.414V101.377H166.311V114.739C168.022 109.942 170.418 106.516 173.498 104.118C176.577 101.719 180.342 100.349 184.448 100.349C189.239 100.349 193.003 101.719 195.741 104.118C198.478 106.516 200.532 109.942 201.216 114.396C202.927 109.942 205.323 106.173 208.745 103.775C212.167 101.377 215.931 100.349 220.037 100.349C225.855 100.349 230.303 102.404 233.383 106.516C236.463 110.628 237.832 115.767 237.832 121.934V153.114H228.935V123.99C228.935 119.193 227.908 115.424 226.197 112.341C224.486 109.257 221.064 107.886 216.615 107.886C212.167 107.886 208.745 109.6 206.007 113.026C203.269 116.452 201.9 121.592 201.9 128.102V153.114H193.345V123.647C193.345 118.851 192.319 115.082 190.608 112.341C188.897 109.6 185.475 107.886 181.026 107.886C176.577 107.886 173.155 109.6 170.418 113.026C167.68 116.795 166.311 121.934 166.311 128.444Z" fill="white"/><path d="M264.524 154.142C259.049 154.142 254.942 152.771 252.205 150.373C249.467 147.974 248.098 144.891 248.098 141.122C248.098 138.038 248.783 135.64 249.809 133.927C251.178 132.213 252.547 130.5 254.942 129.13C256.653 128.102 259.049 127.074 261.444 126.389C263.84 125.703 267.262 124.676 271.026 123.99C275.817 122.962 279.581 121.934 281.976 120.907C284.372 119.879 285.398 118.166 285.398 115.767C285.398 113.711 284.372 111.656 282.661 109.942C280.95 108.229 277.87 107.544 273.421 107.544C269.315 107.544 265.893 108.572 263.497 110.628C261.102 112.683 259.049 115.424 257.338 119.193L249.467 116.452C251.52 111.313 254.942 107.544 259.049 104.803C263.155 102.062 268.288 100.691 274.106 100.691C280.608 100.691 285.398 102.062 288.82 105.146C292.243 108.229 293.954 112.341 293.954 118.166V139.409C293.954 142.15 294.296 144.205 295.322 145.233C296.349 146.261 297.718 146.946 299.429 146.946C300.113 146.946 300.798 146.946 301.482 146.604C302.166 146.604 302.509 146.261 303.193 146.261V152.429C302.509 152.771 301.482 153.114 300.455 153.456C299.429 153.799 298.06 153.799 296.691 153.799C292.927 153.799 289.847 152.771 288.136 150.715C286.425 148.66 285.398 145.576 285.398 141.122V138.381C283.687 143.178 280.95 146.604 277.186 149.345C273.763 152.771 269.315 154.142 264.524 154.142ZM267.946 147.289C269.999 147.289 272.395 146.946 274.448 145.919C276.501 144.891 278.554 143.52 280.265 142.15C281.976 140.436 283.345 138.381 284.372 135.982C285.398 133.584 286.083 130.843 286.083 128.102V123.99C285.056 125.361 283.687 126.389 281.634 127.417C279.581 128.444 276.159 129.13 272.395 130.158C267.604 131.185 263.84 132.556 261.444 133.927C259.049 135.297 257.68 137.695 257.68 140.779C257.68 142.835 258.706 144.548 260.417 145.919C261.786 146.604 264.182 147.289 267.946 147.289Z" fill="white"/><path d="M313.117 153.114V101.377H322.014V114.739C323.725 109.942 326.121 106.516 329.543 104.118C332.965 101.719 336.729 100.349 341.178 100.349C347.68 100.349 352.128 102.404 355.55 106.516C358.972 110.628 360.341 115.767 360.341 122.277V153.114H351.444V124.333C351.444 119.536 350.417 115.424 348.364 112.683C346.311 109.6 342.889 108.229 337.756 108.229C333.307 108.229 329.543 109.942 326.463 113.369C323.725 116.795 322.014 121.934 322.014 128.444V153.114H313.117Z" fill="white"/><path d="M35.247 101.376H0V153.114H8.55511V110.285H35.247V101.376Z" fill="white"/><path d="M199.99 204.774C197.937 204.774 196.568 204.432 195.542 203.404C194.515 202.376 194.173 201.348 194.173 199.977C194.173 198.949 194.515 197.922 194.857 197.236C195.199 196.551 195.884 195.866 196.568 195.523C197.253 195.181 197.937 194.838 198.964 194.495C199.99 194.153 201.017 193.81 202.386 193.467C204.097 193.125 205.466 192.782 206.492 192.439C207.519 192.097 207.861 191.412 207.861 190.726C207.861 190.041 207.519 189.356 206.834 188.671C206.15 187.985 205.123 187.643 203.412 187.643C202.044 187.643 200.675 187.985 199.648 188.671C198.622 189.356 197.937 190.384 197.595 191.754L194.515 190.726C195.199 189.013 196.568 187.3 197.937 186.272C199.306 185.244 201.359 184.902 203.412 184.902C205.808 184.902 207.519 185.587 208.888 186.615C210.256 187.643 210.941 189.356 210.941 191.412V199.292C210.941 200.32 211.283 201.005 211.625 201.348C211.967 201.69 212.652 202.033 212.994 202.033C213.336 202.033 213.336 202.033 213.678 202.033C214.021 202.033 214.021 202.033 214.363 202.033V204.432C214.021 204.432 213.679 204.774 213.336 204.774C212.994 204.774 212.31 204.774 211.967 204.774C210.599 204.774 209.572 204.432 208.888 203.746C208.203 203.061 207.861 202.033 207.861 200.32V199.292C207.177 201.005 206.15 202.376 204.781 203.404C203.07 204.432 201.701 204.774 199.99 204.774ZM201.017 202.376C201.701 202.376 202.728 202.376 203.412 202.033C204.097 201.69 204.781 201.348 205.466 200.663C206.15 199.977 206.492 199.292 206.834 198.264C207.177 197.236 207.519 196.551 207.519 195.181V193.467C207.177 193.81 206.492 194.495 205.808 194.838C205.123 195.181 203.755 195.523 202.386 195.866C200.675 196.208 199.306 196.551 198.279 197.236C197.253 197.922 196.91 198.607 196.91 199.635C196.91 200.32 197.253 201.005 197.937 201.69C198.964 202.033 199.648 202.376 201.017 202.376Z" fill="white"/><path d="M223.26 204.431V185.587H226.34V190.384C227.024 188.67 228.051 187.3 229.078 186.615C230.446 185.587 231.815 185.244 233.526 185.244C235.922 185.244 237.633 185.929 238.659 187.643C239.686 189.013 240.37 191.069 240.37 193.467V204.774H237.291V194.153C237.291 192.439 236.948 191.069 236.264 189.698C235.579 188.67 234.211 187.985 232.5 187.985C230.789 187.985 229.42 188.67 228.393 190.041C227.024 191.069 226.34 192.782 226.34 195.523V204.774L223.26 204.431Z" fill="white"/><path d="M256.454 204.774C254.401 204.774 253.032 204.432 252.005 203.404C250.979 202.376 250.637 201.348 250.637 199.977C250.637 198.949 250.979 197.922 251.321 197.236C251.663 196.551 252.348 195.866 253.032 195.523C253.716 195.181 254.401 194.838 255.427 194.495C256.454 194.153 257.481 193.81 258.85 193.467C260.561 193.125 261.929 192.782 262.956 192.439C263.983 192.097 264.325 191.412 264.325 190.726C264.325 190.041 263.983 189.356 263.298 188.671C262.614 187.985 261.587 187.643 259.876 187.643C258.507 187.643 257.138 187.985 256.112 188.671C255.085 189.356 254.401 190.384 254.059 191.754L250.979 190.726C251.663 189.013 253.032 187.3 254.401 186.272C255.77 185.244 257.823 184.902 259.876 184.902C262.272 184.902 263.983 185.587 265.351 186.615C266.72 187.643 267.405 189.356 267.405 191.412V199.292C267.405 200.32 267.747 201.005 268.089 201.348C268.431 201.69 269.116 202.033 269.458 202.033C269.8 202.033 269.8 202.033 270.142 202.033C270.484 202.033 270.484 202.033 270.827 202.033V204.432C270.484 204.432 270.142 204.774 269.8 204.774C269.458 204.774 268.773 204.774 268.431 204.774C267.062 204.774 266.036 204.432 265.351 203.746C264.667 203.061 264.325 202.033 264.325 200.32V199.292C263.64 201.005 262.614 202.376 261.245 203.404C259.876 204.432 258.165 204.774 256.454 204.774ZM257.823 202.376C258.507 202.376 259.534 202.376 260.218 202.033C260.903 201.69 261.587 201.348 262.272 200.663C262.956 199.977 263.298 199.292 263.64 198.264C263.983 197.236 264.325 196.551 264.325 195.181V193.467C263.983 193.81 263.298 194.495 262.614 194.838C261.929 195.181 260.561 195.523 259.192 195.866C257.481 196.208 256.112 196.551 255.085 197.236C254.059 197.922 253.716 198.607 253.716 199.635C253.716 200.32 254.059 201.005 254.743 201.69C255.427 202.033 256.454 202.376 257.823 202.376Z" fill="white"/><path d="M283.146 177.364V204.432H279.724V177.364H283.146Z" fill="white"/><path d="M311.891 185.587L300.598 211.969H297.176L300.598 204.432L292.728 185.93H296.15L301.283 198.607L302.309 201.691L303.336 198.607L308.469 185.93H311.891V185.587Z" fill="white"/><path d="M333.108 201.348V204.089C332.766 204.431 332.081 204.431 331.739 204.431C331.055 204.431 330.712 204.431 330.028 204.431C327.975 204.431 326.606 204.089 325.921 203.061C325.237 202.033 324.553 200.663 324.553 198.607V187.985H320.104V185.244H324.553V180.105L327.632 178.392V185.244H333.108V187.985H327.632V197.922C327.632 199.292 327.975 200.32 328.317 200.663C328.659 201.348 329.686 201.348 330.712 201.348C331.055 201.348 331.739 201.348 332.081 201.348C332.081 201.69 332.766 201.69 333.108 201.348Z" fill="white"/><path d="M342.689 180.447C342.689 179.762 343.032 179.42 343.374 178.734C343.716 178.392 344.4 178.049 345.085 178.049C345.769 178.049 346.454 178.392 346.796 178.734C347.138 179.077 347.48 179.762 347.48 180.447C347.48 181.133 347.138 181.475 346.796 182.161C346.111 182.503 345.427 182.503 344.743 182.503C344.058 182.503 343.374 182.161 343.032 181.818C342.689 181.475 342.689 181.133 342.689 180.447ZM346.454 185.587V204.432H343.032V185.587H346.454Z" fill="white"/><path d="M375.199 192.097L371.777 192.782C371.435 191.411 371.092 190.041 370.066 189.013C369.039 187.985 368.013 187.643 366.302 187.643C365.275 187.643 364.248 187.985 363.564 188.328C362.88 188.67 362.195 189.356 361.511 189.698C360.826 190.041 360.484 191.069 360.484 192.097C360.142 193.125 360.142 193.81 360.142 194.838C360.142 196.894 360.484 198.607 361.511 199.977C362.537 201.348 363.906 202.033 366.302 202.033C368.013 202.033 369.381 201.69 370.066 200.662C371.092 199.635 371.435 198.607 371.777 196.894L375.199 197.579C374.857 198.607 374.514 199.635 374.172 200.32C373.83 201.005 373.146 202.033 372.461 202.376C371.777 203.061 370.75 203.404 369.724 203.746C368.697 204.089 367.67 204.431 366.302 204.431C364.591 204.431 363.222 204.089 362.195 203.746C361.168 203.404 360.142 202.718 359.115 201.69C358.431 200.662 357.746 199.635 357.404 198.607C357.062 197.579 356.72 196.208 356.72 194.838C356.72 193.467 357.062 192.097 357.404 191.069C357.746 190.041 358.431 188.67 359.115 187.985C359.8 186.957 360.826 186.272 362.195 185.929C363.222 185.244 364.591 185.244 366.302 185.244C367.67 185.244 368.697 185.587 369.724 185.929C370.75 186.272 371.435 186.957 372.461 187.3C373.146 187.985 373.83 188.67 374.172 189.698C374.857 190.384 375.199 191.411 375.199 192.097Z" fill="white"/><path d="M384.096 201.005L386.492 198.949C387.176 199.977 388.203 201.005 389.229 201.348C390.256 201.69 391.625 202.376 392.993 202.376C394.362 202.376 395.731 202.033 396.416 201.348C397.1 200.662 397.442 199.977 397.442 199.292C397.442 198.264 396.758 197.579 395.731 197.236C394.362 196.894 392.994 196.551 390.94 196.208C388.887 195.866 387.518 195.523 386.149 194.495C385.123 193.81 384.438 192.439 384.438 191.069C384.438 189.356 385.123 187.985 386.492 186.957C387.86 185.929 389.571 185.244 391.967 185.244C394.02 185.244 395.731 185.587 397.1 186.272C398.469 186.957 399.838 187.985 400.864 189.356L398.469 191.411C397.784 190.384 396.758 189.356 395.731 188.67C394.705 187.985 393.678 187.985 391.967 187.985C390.598 187.985 389.229 188.328 388.887 189.013C388.203 189.698 387.86 190.384 387.86 191.069C387.86 192.097 388.203 192.782 389.229 193.125C390.256 193.467 391.625 193.81 393.336 194.153C394.362 194.153 395.389 194.495 396.073 194.838C397.1 195.18 397.784 195.523 398.469 195.866C399.153 196.208 399.495 196.894 399.838 197.236C400.18 197.921 400.522 198.607 400.522 199.635C400.522 200.32 400.522 201.348 400.18 202.033C399.838 202.718 399.495 203.404 398.811 203.746C398.127 204.431 397.442 204.774 396.416 205.117C395.389 205.459 394.362 205.459 393.336 205.459C391.282 205.459 389.229 205.117 387.86 204.431C386.149 203.061 385.123 202.033 384.096 201.005Z" fill="white"/><rect x="765" y="35" width="64" height="64" fill="white"/><rect x="765" y="78.804" width="21.902" height="21.902" fill="#4F60FF"/><rect x="786.902" y="56.9019" width="21.902" height="43.8039" fill="#4F60FF"/><rect x="808.804" y="35" width="21.902" height="65.7059" fill="#4F60FF"/><rect x="765" y="78.804" width="21.902" height="21.902" fill="#4F60FF"/><rect x="786.902" y="56.9019" width="21.902" height="43.8039" fill="#4F60FF"/><rect x="808.804" y="35" width="21.902" height="65.7059" fill="#4F60FF"/><g clip-path="url(#clip0_571_35)"><path d="M672.187 102.141H638.281V151.675H646.627V110.499H672.187V102.141Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M575.065 116.097L562.895 151.661H555.384L538.565 102.16H547.469L559.439 138.318L571.817 102.16H578.345L590.714 138.318L602.675 102.16H611.676L594.858 151.671H587.341L575.065 116.097Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M628.416 102.141H619.907V151.675H628.416V102.141Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M699.201 152.679C684.781 152.679 674.31 141.7 674.31 126.968C674.31 112.525 683.988 101.254 699.396 101.254C714.902 101.254 724.288 113.909 723.1 129.24H682.902C683.199 138.239 690.409 144.967 699.299 144.967C705.423 144.967 710.656 142.592 713.621 136.66H722.311C719.843 145.366 711.742 152.679 699.201 152.679ZM683.297 122.518H714.113C712.531 113.319 706.411 108.771 699.099 108.771C691.982 108.771 684.976 112.724 683.297 122.518Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M624.162 93.9876C627.081 93.9876 629.447 91.6184 629.447 88.6959C629.447 85.7734 627.081 83.4043 624.162 83.4043C621.244 83.4043 618.878 85.7734 618.878 88.6959C618.878 91.6184 621.244 93.9876 624.162 93.9876Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/></g><g clip-path="url(#clip1_571_35)"><path d="M672.187 102.141H638.281V151.675H646.627V110.499H672.187V102.141Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M575.065 116.097L562.895 151.661H555.384L538.565 102.16H547.469L559.439 138.318L571.817 102.16H578.345L590.714 138.318L602.675 102.16H611.676L594.858 151.671H587.341L575.065 116.097Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M628.416 102.141H619.907V151.675H628.416V102.141Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M699.201 152.679C684.781 152.679 674.31 141.7 674.31 126.968C674.31 112.525 683.988 101.254 699.396 101.254C714.902 101.254 724.288 113.909 723.1 129.24H682.902C683.199 138.239 690.409 144.967 699.299 144.967C705.423 144.967 710.656 142.592 713.621 136.66H722.311C719.843 145.366 711.742 152.679 699.201 152.679ZM683.297 122.518H714.113C712.531 113.319 706.411 108.771 699.099 108.771C691.982 108.771 684.976 112.724 683.297 122.518Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/><path d="M624.162 93.9876C627.081 93.9876 629.447 91.6184 629.447 88.6959C629.447 85.7734 627.081 83.4043 624.162 83.4043C621.244 83.4043 618.878 85.7734 618.878 88.6959C618.878 91.6184 621.244 93.9876 624.162 93.9876Z" fill="white" stroke-width="1.75" stroke-miterlimit="10" stroke="white"/></g><path d="M475.5 -2.18557e-08L475.5 235" stroke="white"/><defs><clipPath id="clip0_571_35"><rect width="185.607" height="70.0874" fill="white" transform="translate(538 83)"/></clipPath><clipPath id="clip1_571_35"><rect width="185.607" height="70.0874" fill="white" transform="translate(538 83)"/></clipPath></defs></svg>
            <div class="wt-hero-controls">
              <!-- spec filter: Channel -->
              <app-select label="Channel" .value=${this.channel}
                .options=${['All', 'Direct', 'Organic Search', 'Referral', 'Organic Social', 'Paid Search', 'Organic Video', 'Email', 'Paid Social']}
                @change=${e => { this.channel = e.detail.value; }}></app-select>
              <!-- spec filter: Site -->
              <app-select label="Site" .value=${this.site}
                .options=${['All', 'rittmananalytics.com', 'careers.rittmananalytics.com']}
                @change=${e => { this.site = e.detail.value; }}></app-select>
            </div>
            </div>
          </div>
        </header>

        <!-- KPI strip floating over the hero: catalog rows 2 to 6. Each widget is
             written out in full so its id and fields are static text for the
             publisher's query registration. -->
        <section class="wt-kpis">
          ${this.kpiCard('', 'web_sessions_fact.total_sessions', '13 weeks, week on week', html`
            <app-kpi bare id="da-kpi-sessions" label="Sessions" format="int" sparkline sparkline-agg="sum"
              .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
              .filters=${spark}></app-kpi>`)}
          ${this.kpiCard('is-primary-deep', 'web_events_fact.total_unique_users', 'Distinct visitors in the window', html`
            <app-kpi bare id="da-kpi-unique-users" label="Unique Users" format="int"
              query-field="web_events_fact.total_unique_users" .filters=${filters}></app-kpi>`)}
          ${this.kpiCard('', 'web_events_fact.total_page_views', '13 weeks, week on week', html`
            <app-kpi bare id="da-kpi-page-views" label="Page Views" format="int" sparkline sparkline-agg="sum"
              .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_events_fact.total_page_views'], sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
              .filters=${spark}></app-kpi>`)}
          ${this.kpiCard('is-secondary', 'web_sessions_fact.bounced_session_rate', 'Single-page sessions, lower is better', html`
            <app-kpi bare id="da-kpi-bounce-rate" label="Bounce Rate" format="percent1" polarity="lower-better"
              query-field="web_sessions_fact.bounced_session_rate" .filters=${filters}></app-kpi>`)}
          ${this.kpiCard('is-secondary', 'web_events_fact.total_conversions', 'Meeting Booked events, 13 weeks', html`
            <app-kpi bare id="da-kpi-meetings-booked" label="Meetings Booked" format="int" sparkline sparkline-agg="sum"
              .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_events_fact.total_conversions'], sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
              .filters=${spark}></app-kpi>`)}
        </section>

        <div class="wt-tabs-row">
          <div class="da-tabs" role="tablist">
            ${tabs.map(([id, label]) => html`
              <button class="da-tab-btn ${this.activeTab === id ? 'active' : ''}" role="tab" aria-selected=${this.activeTab === id}
                @click=${() => { this.activeTab = id; }}>${label}</button>`)}
          </div>
          <span class="wt-tabs-hint">Clicking a bar, a ring segment or a treemap tile filters everything else; click again to clear.</span>
        </div>

        <div class="da-tab-content">
          ${this.activeTab === 'overview' ? this.renderOverview() : nothing}
          ${this.activeTab === 'pages' ? this.renderPages() : nothing}
          ${this.activeTab === 'engagement' ? this.renderEngagement() : nothing}
        </div>

        ${this.renderDrawer()}
      </div>
    `;
  }
}

if (!customElements.get(elementName)) {
  customElements.define(elementName, WebTrafficApp);
}

export default WebTrafficApp;
