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
  plotOptions: { areaspline: { fillOpacity: 0.18, lineWidth: 2.5, marker: { enabled: false } } },
};
const TREEMAP_OPTIONS = {
  plotOptions: { treemap: { borderWidth: 2, borderColor: '#ffffff', dataLabels: { style: { fontSize: '12px', fontWeight: '600', textOutline: 'none' } } } },
};

// Heat-mapped scorecard cells: background opacity scaled to the column's max.
function heatCell(field, format, maxByField, tone) {
  return (params) => {
    if (!params.data) return '';
    const raw = Number(params.data[field]) || 0;
    const max = maxByField[field] || 1;
    const alpha = Math.max(0.08, (raw / max) * 0.55);
    const shown = format === 'percent1' ? `${(raw * 100).toFixed(1)}%` : raw.toLocaleString('en-GB');
    return `<div style="background: rgba(${tone}, ${alpha.toFixed(2)}); border-radius: 6px; padding: 4px 8px; text-align: right; font-weight: 600;">${shown}</div>`;
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
    scorecardMax: { type: Object },
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
    this.scorecardMax = {};
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
          value-format="int" color="var(--app-primary)" .options=${TREND_OPTIONS}
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
              value-format=${metric.format} color="var(--app-primary)" .options=${TREND_OPTIONS}
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
              value-format="int" color="var(--wt-amber)" .options=${BAR_OPTIONS}
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
    const maxBy = this.scorecardMax;
    const scoreFields = [
      ['web_sessions_fact.total_sessions', 'Sessions', 'int', '15, 157, 143'],
      ['web_events_fact.total_page_views', 'Page views', 'int', '59, 110, 165'],
      ['web_events_fact.total_conversions', 'Meetings', 'int', '240, 163, 58'],
      ['web_sessions_fact.bounced_session_rate', 'Bounce rate', 'percent1', '224, 93, 111'],
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
            .gridOptions=${{
              defaultColDef: { resizable: true, sortable: true }, rowHeight: 38,
              onRowDataUpdated: (ev) => {
                const rows = []; ev.api.forEachNode(n => rows.push(n.data || {}));
                const max = {};
                for (const [f] of scoreFields) max[f] = Math.max(1, ...rows.map(r => Number(r[f]) || 0));
                this.scorecardMax = max;
              },
            }}
            .columnDefs=${[
              { field: 'web_sessions_fact.channel', headerName: 'Channel', flex: 1.4, minWidth: 160, pinned: 'left', cellStyle: { fontWeight: '600' } },
              ...scoreFields.map(([f, name, fmt, tone]) => ({ field: f, headerName: name, flex: 1, minWidth: 120, type: 'rightAligned', cellRenderer: heatCell(f, fmt, maxBy, tone) })),
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
          --wt-ink: #0b1a2b; --wt-ink-soft: #40546a; --wt-teal: #0f9d8f; --wt-teal-deep: #0b6b62; --wt-amber: #f0a33a;
          --wt-line: #e3e9ef; --wt-canvas: #f4f7fa;
          --app-bg: var(--wt-canvas); --app-card-bg: #ffffff; --app-border: var(--wt-line); --app-text: var(--wt-ink);
          --app-title: var(--wt-ink); --app-muted: var(--wt-ink-soft); --app-primary: var(--wt-teal); --app-primary-hover: var(--wt-teal-deep);
          --app-chart-1: #0f9d8f; --app-chart-2: #f0a33a; --app-chart-3: #3b6ea5; --app-chart-4: #9b5de5; --app-chart-5: #e05d6f;
          --app-chart-6: #5aa9e6; --app-chart-7: #7cb342; --app-chart-unselected: #d7dee6;
          --app-tabs-bg: #e6edf3; --app-radius: 18px;
          font-family: 'Google Sans', 'Inter', system-ui, -apple-system, sans-serif;
        }
        .wt-root { max-width: 1480px; margin: 0 auto; padding: 18px 22px 44px; color: var(--wt-ink); background: var(--wt-canvas); }

        /* Hero band, with the KPI cards floating over its lower edge */
        .wt-hero { position: relative; overflow: hidden; border-radius: 22px; padding: 26px 30px 70px;
          background: linear-gradient(118deg, #0b1a2b 0%, #0e3147 48%, #0f9d8f 120%); color: #fff; box-shadow: 0 18px 40px -24px rgba(11, 26, 43, .7); }
        .wt-hero::after { content: ''; position: absolute; right: -80px; top: -120px; width: 360px; height: 360px; border-radius: 50%;
          background: radial-gradient(circle, rgba(240, 163, 58, .35) 0%, rgba(240, 163, 58, 0) 65%); }
        .wt-hero-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap; position: relative; z-index: 1; }
        .wt-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: rgba(255,255,255,.72); margin: 0 0 6px; }
        .wt-eyebrow-dark { color: var(--wt-ink-soft); }
        .wt-hero h1 { margin: 0; font-size: 30px; line-height: 1.1; letter-spacing: -0.02em; font-weight: 700; }
        .wt-hero p { margin: 10px 0 0; max-width: 680px; font-size: 14px; line-height: 1.5; color: rgba(255,255,255,.82); }
        .wt-scope { display: inline-flex; align-items: center; gap: 8px; margin-top: 14px; padding: 6px 12px; border-radius: 999px;
          background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); font-size: 12px; font-weight: 500; }
        .wt-scope::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--wt-amber); }
        .wt-hero-controls { display: flex; gap: 12px; flex-wrap: wrap; padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); }
        .wt-hero-controls .da-select-label, .wt-hero-controls label { color: rgba(255,255,255,.85); }

        .wt-kpis { position: relative; z-index: 2; margin: -48px 18px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(190px, 100%), 1fr)); gap: 14px; }
        .wt-kpi { position: relative; background: #fff; border: 1px solid var(--wt-line); border-radius: 18px; padding: 14px 18px 10px; overflow: hidden; cursor: pointer;
          box-shadow: 0 16px 36px -20px rgba(11, 26, 43, .55); transition: transform .15s ease, box-shadow .15s ease; }
        .wt-kpi:hover { transform: translateY(-2px); box-shadow: 0 22px 40px -22px rgba(11, 26, 43, .6); }
        .wt-kpi::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--wt-teal); }
        .wt-kpi.is-amber::before { background: var(--wt-amber); }
        .wt-kpi.is-navy::before { background: #3b6ea5; }
        .wt-kpi app-kpi { display: block; }
        .wt-kpi-foot { display: flex; justify-content: space-between; font-size: 11px; color: var(--wt-ink-soft); margin-top: 6px; }
        .wt-kpi-more { color: var(--wt-teal-deep); font-weight: 600; }

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
        .wt-seg-btn.active { background: #fff; color: var(--wt-teal-deep); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
        .wt-slider { margin-left: auto; display: inline-flex; align-items: center; gap: 10px; font-size: 12px; color: var(--wt-ink-soft); }
        .wt-slider input { accent-color: var(--wt-teal); width: 140px; }
        .wt-search input { width: 260px; max-width: 100%; padding: 7px 12px; border: 1px solid var(--wt-line); border-radius: 10px; font: inherit; font-size: 13px; background: #fff; color: var(--wt-ink); }
        .wt-search input:focus { outline: 2px solid rgba(15, 157, 143, .35); border-color: var(--wt-teal); }

        /* Layouts */
        .wt-story { display: grid; grid-template-columns: minmax(0, 2.1fr) minmax(0, 1fr); gap: 14px; }
        .wt-stack { display: grid; grid-template-rows: 1fr 1fr; gap: 14px; }
        .wt-pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: 14px; }
        .wt-split { display: grid; grid-template-columns: minmax(260px, 1fr) minmax(0, 2.6fr); gap: 14px; align-items: start; }
        .wt-summary { background: linear-gradient(160deg, #ffffff 0%, #eef6f5 100%); border: 1px solid var(--wt-line); border-radius: 18px; padding: 20px; }
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
        </header>

        <!-- KPI strip floating over the hero: catalog rows 2 to 6. Each widget is
             written out in full so its id and fields are static text for the
             publisher's query registration. -->
        <section class="wt-kpis">
          ${this.kpiCard('', 'web_sessions_fact.total_sessions', '13 weeks, week on week', html`
            <app-kpi bare id="da-kpi-sessions" label="Sessions" format="int" sparkline sparkline-agg="sum"
              .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_sessions_fact.total_sessions'], sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
              .filters=${spark}></app-kpi>`)}
          ${this.kpiCard('is-navy', 'web_events_fact.total_unique_users', 'Distinct visitors in the window', html`
            <app-kpi bare id="da-kpi-unique-users" label="Unique Users" format="int"
              query-field="web_events_fact.total_unique_users" .filters=${filters}></app-kpi>`)}
          ${this.kpiCard('', 'web_events_fact.total_page_views', '13 weeks, week on week', html`
            <app-kpi bare id="da-kpi-page-views" label="Page Views" format="int" sparkline sparkline-agg="sum"
              .query=${{ fields: ['web_sessions_fact.session_start_ts_week', 'web_events_fact.total_page_views'], sorts: ['web_sessions_fact.session_start_ts_week desc'], limit: '13' }}
              .filters=${spark}></app-kpi>`)}
          ${this.kpiCard('is-amber', 'web_sessions_fact.bounced_session_rate', 'Single-page sessions, lower is better', html`
            <app-kpi bare id="da-kpi-bounce-rate" label="Bounce Rate" format="percent1" polarity="lower-better"
              query-field="web_sessions_fact.bounced_session_rate" .filters=${filters}></app-kpi>`)}
          ${this.kpiCard('is-amber', 'web_events_fact.total_conversions', 'Meeting Booked events, 13 weeks', html`
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
