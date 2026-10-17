// Wire Studio 4.x front end. Plain JavaScript, no build step.
// Every value from the record is set with textContent (never innerHTML), except
// rendered Markdown, which is sanitised with DOMPurify first. "Run in Claude Code"
// posts to api/launch with the per-run token from the page's meta tag.
//
// Hosted mode (meta studio-mode = hosted): the same views, read only, behind
// another site's sign-in. No directives, no Run in Claude Code, no Copy, no
// lanes (work starts from the tracker and the agents run it). The page's own
// requests go to the base path in meta studio-base.
"use strict";

const meta = (name) => (document.querySelector(`meta[name="${name}"]`) || {}).content || "";
const HOSTED = meta("studio-mode") === "hosted";
const BASE = /^\/([A-Za-z0-9_-]+\/)*$/.test(meta("studio-base")) ? meta("studio-base") : "/";

const main = document.getElementById("main");
let summary = null;
let release = null;
let selected = { node: null, decision: null, lane: null, ticket: null };
let refreshTimer = null;

// ---------- helpers ----------
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
async function api(path) {
  const r = await fetch(BASE + path.replace(/^\//, ""), { headers: { Accept: "application/json" } });
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || r.statusText);
  return body;
}
function toast(msg) {
  const t = h("div", { class: "toast", role: "status" }, msg);
  document.body.append(t);
  setTimeout(() => t.remove(), 2500);
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast("Copied. Paste it into the orchestrating session."); }
  catch { toast("Copy failed: select the text and copy it by hand."); }
}
function header(crumbs, title, right) {
  return h("header", { class: "top" },
    h("div", {}, h("div", { class: "crumbs" }, crumbs), h("h1", {}, title)), right || null);
}
function stateClass(state) {
  if (state === "complete") return "complete";
  if (state === "not applicable") return "na";
  return state.split(":")[0];
}
function stepText(steps) {
  const mark = { complete: "✓", pass: "✓", approved: "✓", fail: "✗", failed: "✗", changes_requested: "✗", not_started: "-", not_applicable: "n/a", in_progress: "…" };
  return Object.entries(steps).map(([k, v]) => `${k[0].toUpperCase()} ${mark[String(v).toLowerCase()] || v}`).join("  ");
}
function setNav(view) {
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === view));
  const rn = document.getElementById("release-nav");
  rn.hidden = !release || view === "home";
  if (release) {
    for (const a of rn.querySelectorAll("a")) a.href = `#/r/${encodeURIComponent(release.name)}/${a.dataset.nav}`;
    document.getElementById("nav-waiting").textContent = release.inbox.length;
    const live = release.lanes.filter((l) => l.state !== "complete").length;
    document.getElementById("nav-lanes").textContent = live ? `${live} live` : "";
    document.getElementById("nav-lanes-link").hidden = HOSTED;
    const tk = release.tickets && !release.tickets.error ? release.tickets : null;
    document.getElementById("nav-tickets-link").hidden = !release.tickets;
    document.getElementById("nav-tickets").textContent = tk ? `${tk.counts.closed} of ${tk.counts.total}` : "";
  }
}

const TOKEN = meta("studio-token");
async function runInClaude(text, out) {
  if (HOSTED) return;
  out.replaceChildren(h("span", { class: "muted" }, "Opening Claude Code…"));
  try {
    const r = await fetch(BASE + "api/launch", { method: "POST", headers: { "Content-Type": "application/json", "X-Studio-Token": TOKEN }, body: JSON.stringify({ directive: text }) });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || r.statusText);
    out.replaceChildren(h("p", { class: body.launched ? "muted" : "error", style: "margin:8px 0 0" }, body.message),
      body.launched ? null : h("div", { class: "directive", style: "margin-top:8px" }, body.command));
  } catch (e) { out.replaceChildren(h("div", { class: "error", style: "margin-top:8px" }, String(e.message || e))); }
}
// An editable directive with Copy and Run in Claude Code. Placeholders such as
// <your decision> must be replaced before the server will launch it.
// Hosted mode shows no directives: work starts from the tracker.
function directiveBox(text) {
  if (HOSTED) return null;
  const ta = h("textarea", { class: "directive", rows: String(Math.min(6, Math.max(2, Math.ceil(text.length / 90)))), "aria-label": "Directive", style: "width:100%;resize:vertical" });
  ta.value = text;
  const out = h("div", { "aria-live": "polite" });
  const claim = release && release.claim && release.claim.held && !release.claim.stale
    ? h("p", { class: "muted", style: "margin:8px 0 0" }, `${release.claim.user || "Another session"} holds the release claim. The new session will offer to join, take over or move, as the claim rule requires.`) : null;
  const launchable = !summary || !summary.launch || summary.launch.claude_on_path;
  return h("div", {}, ta,
    h("div", { class: "row", style: "margin-top:10px" },
      h("button", { type: "button", class: "btn", onclick: () => runInClaude(ta.value, out), disabled: launchable ? null : true,
                    title: launchable ? "Opens a new terminal running claude with this directive" : "claude is not on PATH" }, "Run in Claude Code"),
      h("button", { type: "button", class: "btn ghost", onclick: () => copy(ta.value) }, "Copy")),
    claim, out);
}

// ---------- routing ----------
async function route() {
  clearInterval(refreshTimer);
  const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  try {
    if (!summary) summary = await api("/api/summary");
    if (parts[0] === "r" && parts[1]) {
      if (!release || release.name !== parts[1]) selected = { node: null, decision: null, lane: null, ticket: null };
      release = await api(`/api/release/${encodeURIComponent(parts[1])}`);
      const view = parts[2] || "overview";
      render(view, parts.slice(3).join("/"));
      if (view !== "file") refreshTimer = setInterval(refresh, 15000);
    } else if (HOSTED && parts[0] === "" && summary.releases.length && !sessionGet("studio-home")) {
      // Hosted: open the most recently updated release first; Releases lists the rest.
      sessionSet("studio-home", "1");
      location.replace(`#/r/${encodeURIComponent(summary.releases[0].name)}/overview`);
    } else {
      release = null;
      summary = await api("/api/summary");
      render("home");
    }
  } catch (e) {
    main.replaceChildren(h("div", { class: "content" }, h("div", { class: "error" }, String(e.message || e))));
  }
}
async function refresh() {
  if (!release) return;
  try {
    release = await api(`/api/release/${encodeURIComponent(release.name)}`);
    const parts = location.hash.replace(/^#\/?/, "").split("/");
    render(parts[2] || "overview");
  } catch { /* keep the last good view */ }
}
function sessionGet(k) { try { return sessionStorage.getItem(k); } catch { return null; } }
function sessionSet(k, v) { try { sessionStorage.setItem(k, v); } catch { /* storage blocked */ } }
function hostedChrome() {
  if (!HOSTED) return;
  const back = meta("studio-back");
  const a = document.getElementById("nav-back");
  if (back && /^\/[A-Za-z0-9_/-]*$/.test(back)) { a.href = back; a.hidden = false; }
  document.getElementById("foot").textContent = "Read only. Reads .wire/ from the project's repository on GitHub and the release-type graph. "
    + "Work on the release starts from its tickets; decisions are made there.";
}
hostedChrome();
function render(view, arg) {
  setNav(view);
  const views = { home: viewHome, overview: viewOverview, tickets: viewTickets, decisions: viewDecisions, lanes: HOSTED ? viewOverview : viewLanes, record: viewRecord, file: viewFile };
  main.replaceChildren((views[view] || viewOverview)(arg));
}

// ---------- views ----------
function viewHome() {
  const e = summary.engagement;
  const rows = summary.releases.map((r) => h("tr", {},
    h("td", {}, h("a", { href: `#/r/${encodeURIComponent(r.name)}/overview` }, r.name), r.legacy ? h("span", { class: "tag warn", style: "margin-left:8px" }, "pre-3.4 layout") : null),
    HOSTED ? h("td", { class: "mono" }, r.branch || "-", r.other_branches && r.other_branches.length ? h("span", { class: "muted" }, ` (also on ${r.other_branches.join(", ")})`) : null) : null,
    HOSTED ? h("td", {}, r.last_updated || "-") : null,
    h("td", { class: "mono" }, r.project_type || "-"),
    h("td", {}, r.error ? h("span", { class: "tag bad" }, r.error)
      : r.tickets ? `${r.tickets.closed} of ${r.tickets.total} tickets closed` : `${r.complete} of ${r.total}`),
    h("td", {}, r.waiting ? h("strong", {}, r.waiting) : "0"),
    HOSTED ? null : h("td", {}, r.lanes_live || "0")));
  return h("div", {},
    header([summary.repo, h("span", { class: "tag" }, `framework: ${summary.framework.layout}`),
            e.orchestration_mode === "manual" ? h("span", { class: "tag warn" }, "manual mode") : null],
           e.present ? e.title : "Releases"),
    h("div", { class: "content" },
      h("section", { class: "card", "aria-labelledby": "rel-h" },
        h("h2", { id: "rel-h" }, "Releases"),
        summary.releases.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Release"), HOSTED ? [h("th", {}, "Branch"), h("th", {}, "Last updated")] : null,
            h("th", {}, "Type"), h("th", {}, "Progress"), h("th", {}, HOSTED ? "Waiting on a decision" : "Waiting on you"), HOSTED ? null : h("th", {}, "Lanes live"))),
          h("tbody", {}, rows))) : h("p", { class: "empty" }, "No releases found under .wire/releases/."))));
}

function releaseHeader(title, right) {
  const r = release;
  return header([summary.engagement.title || summary.repo, h("span", { "aria-hidden": "true" }, "/"),
                 h("span", { class: "mono" }, r.name),
                 h("span", { class: "tag" }, r.project_type || "unknown type"),
                 r.resolved && r.resolved.profile ? h("span", { class: "tag" }, `profile: ${r.resolved.profile}`) : null,
                 r.tickets ? h("span", { class: "tag" }, "built from tickets") : null,
                 r.branch ? h("span", { class: "tag" }, `branch: ${r.branch}`) : null,
                 HOSTED ? null : r.claim.held ? h("span", { class: r.claim.stale ? "tag warn" : "tag" }, `claim: ${r.claim.user || "?"}${r.claim.stale ? " (stalled)" : ""}`) : h("span", { class: "tag warn" }, "no release claim")],
                title, right);
}

function viewOverview() {
  const r = release;
  if (!r.resolved) return h("div", {}, releaseHeader("Release overview"), h("div", { class: "content" }, h("div", { class: "error" }, r.error || "This release could not be resolved.")));
  const g = r.resolved.graph;
  const tk = r.tickets && !r.tickets.error ? r.tickets : null;
  const applicable = g.filter((n) => n.state !== "not applicable");
  const complete = applicable.filter((n) => n.state === "complete").length;
  const phases = [];
  for (const n of g) {
    let p = phases.find((x) => x.id === n.phase);
    if (!p) phases.push(p = { id: n.phase, name: n.phase_name, nodes: [] });
    p.nodes.push(n);
  }
  if (!selected.node) selected.node = (g.find((n) => n.state.startsWith("parked")) || g.find((n) => n.state.startsWith("runnable")) || g[0] || {}).id;
  const sel = g.find((n) => n.id === selected.node) || g[0];

  const graph = h("div", { class: "graph" }, phases.map((p) => h("div", { class: "phase" },
    h("span", { class: "ph" }, p.name),
    p.nodes.map((n) => h("button", { type: "button", class: `node ${stateClass(n.state)}`, "aria-pressed": n.id === selected.node ? "true" : "false",
      onclick: () => { selected.node = n.id; render("overview"); } },
      h("span", { class: "t" }, n.id.replace(/_/g, " ")), h("span", { class: "s" }, stepText(n.steps)),
      sliceProgress(n.id))))));

  const plan = r.run_plan;
  // A release built from tickets: each node also shows its slices (4.2.6).
  function sliceProgress(id) {
    const x = tk && tk.release[id];
    if (!x) return null;
    const pct = x.slices ? Math.round((100 * x.complete) / x.slices) : 0;
    return [h("span", { class: "s" }, `${x.complete} of ${x.slices} slice${x.slices === 1 ? "" : "s"} done${x.in_progress ? `, ${x.in_progress} in progress` : ""}`),
      h("span", { class: "bar", "aria-hidden": "true" }, h("span", { style: `width:${pct}%` }))];
  }
  return h("div", {},
    releaseHeader("Release overview", r.inbox.length ? h("a", { class: "btn", href: `#/r/${encodeURIComponent(r.name)}/decisions`, style: "text-decoration:none" }, `Review ${r.inbox.length} decision${r.inbox.length === 1 ? "" : "s"}`) : null),
    h("div", { class: "content" },
      r.error ? h("div", { class: "error" }, r.error) : null,
      r.tickets && r.tickets.error ? h("div", { class: "error" }, r.tickets.error) : null,
      h("div", { class: "kpis" },
        tk ? kpi("Tickets closed", tk.counts.closed, `of ${tk.counts.total}`) : kpi("Artifacts complete", complete, `of ${applicable.length}`),
        tk ? kpi("Tickets that can start", tk.counts.can_start, `${tk.counts.waiting} waiting`)
           : kpi("Runnable now", r.resolved.order.length, `parallel ${r.resolved.parallel.length} of ${r.resolved.lanes_max}`),
        kpi(HOSTED ? "Waiting on a decision" : "Waiting on you", r.inbox.length),
        HOSTED ? null : kpi("Lanes live", r.lanes.filter((l) => l.state !== "complete").length, r.lanes.some((l) => l.state === "stalled") ? "1+ stalled" : ""),
        r.spend ? kpi("AI spend recorded", `$${r.spend.cost.toFixed(2)}`, `${r.spend.measured_rows} of ${r.spend.rows} log rows measured`) : null),
      h("section", { class: "card", "aria-labelledby": "g-h" },
        h("div", { class: "row", style: "justify-content:space-between;margin-bottom:12px" },
          h("h2", { id: "g-h", style: "margin:0" }, "Artifact graph", h("span", { class: "note" }, tk ? "release-level states: a step is complete only when complete in every slice" : `release-types/${r.project_type}.yaml`)),
          h("div", { class: "legend" },
            h("span", { style: "--c: var(--ok)" }, "Complete"), h("span", { style: "--c: var(--accent)" }, "Runnable"),
            h("span", { style: "--c: var(--wait)" }, "Waiting on you"), h("span", { style: "--c: var(--block)" }, "Blocked or not applicable"))),
        graph),
      h("div", { class: "two" },
        h("section", { class: "card", "aria-labelledby": "s-h" },
          h("h2", { id: "s-h" }, sel.id.replace(/_/g, " ")),
          h("p", { class: "muted", style: "margin:0 0 10px" }, sel.state),
          h("p", { class: "mono", style: "font-size:13px;margin:0 0 10px" }, stepText(sel.steps)),
          sel.depends_on.length ? h("p", { class: "muted" }, "Depends on: ", sel.depends_on.join(", ")) : null,
          sel.file ? h("p", {}, h("a", { href: `#/r/${encodeURIComponent(r.name)}/file/${encodeURIComponent(sel.file)}` }, `Open ${sel.file}`)) : h("p", { class: "muted" }, "No file recorded yet.")),
        tk ? h("section", { class: "card", "aria-labelledby": "p-h" },
          h("h2", { id: "p-h" }, "Tickets that can start"),
          r.ticket_next ? [
            HOSTED ? h("ul", {}, r.ticket_next.tickets.map((k) => h("li", {}, h("a", { class: "mono", href: `#/r/${encodeURIComponent(r.name)}/tickets/${encodeURIComponent(k)}` }, k))))
              : h("p", { class: "muted", style: "margin:0 0 10px" }, "This release is built from tickets, so work starts from a ticket. Each line opens it with /wire:work."),
            ...r.ticket_next.commands.map((c) => HOSTED ? null : h("div", { style: "margin-bottom:10px" }, directiveBox(c))),
            h("p", {}, h("a", { href: `#/r/${encodeURIComponent(r.name)}/tickets` }, "See every ticket and slice"))
          ] : h("p", { class: "empty" }, "No ticket can start now. See the Tickets page for what each one waits on."))
        : h("section", { class: "card", "aria-labelledby": "p-h" },
          h("h2", { id: "p-h" }, "Runnable set"),
          plan ? [
            h("p", { class: "muted", style: "margin:0 0 10px" }, `In order, within lanes_max ${r.resolved.lanes_max}.${HOSTED ? "" : " Paste this to get the run plan shown and approved in the session."}`),
            h("ol", { style: "margin:0 0 12px;padding-left:20px;display:flex;flex-direction:column;gap:6px" }, plan.commands.map((c) => h("li", { class: "mono", style: "font-size:13px" }, c))),
            directiveBox(plan.directive)
          ] : h("p", { class: "empty" }, "Nothing can start now. See the decision inbox.")))));
}
function kpi(k, v, small) {
  return h("div", { class: "card kpi" }, h("span", { class: "k" }, k), h("span", { class: "v" }, String(v), small ? h("small", {}, ` ${small}`) : null));
}

function viewDecisions() {
  const r = release;
  const items = r.inbox;
  if (!items.length) return h("div", {}, releaseHeader("Decision inbox"), h("div", { class: "content" }, h("p", { class: "empty" }, "Nothing is waiting on you.")));
  if (!items.find((d) => d.id === selected.decision)) selected.decision = items[0].id;
  const cur = items.find((d) => d.id === selected.decision);
  return h("div", {},
    releaseHeader("Decision inbox", h("span", { class: "muted" }, `${items.length} open`)),
    h("div", { class: "content" }, h("div", { class: "split" },
      h("ul", { class: "list", "aria-label": "Decisions" }, items.map((d) => h("li", {},
        h("button", { type: "button", class: "item", "aria-pressed": d.id === cur.id ? "true" : "false", onclick: () => { selected.decision = d.id; render("decisions"); } },
          h("span", { class: "meta" }, h("span", {}, d.kind), h("span", {}, d.since || "")),
          h("span", { class: "title" }, d.question || d.ref))))),
      h("section", { class: "card", "aria-labelledby": "d-h" },
        h("span", { class: "muted" }, `${String(cur.kind).toUpperCase()} · ${cur.ref}`),
        h("h2", { id: "d-h", style: "margin:6px 0 12px;font-size:20px" }, cur.question || cur.ref),
        cur.artifact ? h("p", { class: "muted" }, "Artifact: ", cur.artifact) : null,
        cur.awaiting ? h("p", { class: "muted" }, "Awaiting: ", cur.awaiting) : null,
        HOSTED ? null : h("p", { class: "muted", style: "margin:16px 0 6px" }, "Directive for the orchestrating session"),
        directiveBox(cur.directive),
        cur.artifact && graphFile(cur.artifact) ? h("p", { style: "margin-top:12px" }, h("a", { href: `#/r/${encodeURIComponent(r.name)}/file/${encodeURIComponent(graphFile(cur.artifact))}` }, "Open the artifact")) : null,
        h("p", { class: "muted", style: "margin-top:16px" }, HOSTED ? "Read only. The decision is made on the ticket; the session working the release records it in the execution log and decisions.md."
          : "Studio does not record the decision. The Claude Code session records it in the execution log and decisions.md, as the single writer.")))));
}
function graphFile(id) {
  const n = release.resolved && release.resolved.graph.find((x) => x.id === id);
  return n && n.file;
}

function viewLanes() {
  const r = release;
  if (!r.lanes.length) return h("div", {}, releaseHeader("Lanes"), h("div", { class: "content" }, h("p", { class: "empty" }, "No lane state files in lanes/.")));
  if (!r.lanes.find((l) => l.label === selected.lane)) selected.lane = (r.lanes.find((l) => l.state === "stalled") || r.lanes[0]).label;
  const cur = r.lanes.find((l) => l.label === selected.lane);
  return h("div", {},
    releaseHeader("Lanes", h("span", { class: "muted" }, `${r.lanes.length} state file${r.lanes.length === 1 ? "" : "s"}`)),
    h("div", { class: "content" }, h("div", { class: "split" },
      h("ul", { class: "list", "aria-label": "Lanes" }, r.lanes.map((l) => h("li", {},
        h("button", { type: "button", class: "item", "aria-pressed": l.label === cur.label ? "true" : "false", onclick: () => { selected.lane = l.label; render("lanes"); } },
          h("span", { class: "meta" }, h("span", { class: "mono" }, l.label), h("span", { class: `badge ${l.state}` }, l.state)),
          h("span", { class: "muted" }, `Last write ${l.last_write} (${l.minutes_since_write} min ago)`),
          h("span", { style: "font-size:13px" }, l.summary))))),
      h("section", { class: "card lane", "aria-labelledby": "l-h" },
        h("h2", { id: "l-h" }, cur.label),
        cur.state === "stalled" ? h("div", { class: "error" }, `No write for ${cur.minutes_since_write} minutes. The lane brief allows 30. To re-dispatch it, run or copy this directive:`,
          h("div", { style: "margin-top:8px" }, directiveBox(`Re-dispatch lane ${cur.label} in ${r.name} from its state file.`))) : null,
        h("p", { class: "muted mono" }, cur.path),
        h("pre", { class: "state" }, cur.text)))));
}

function viewRecord() {
  const r = release;
  const log = [...r.execution_log].reverse();
  const cols = log.length ? Object.keys(log[0]) : [];
  return h("div", {},
    releaseHeader("Record and rulings"),
    h("div", { class: "content" },
      h("section", { class: "card", "aria-labelledby": "ru-h" },
        h("h2", { id: "ru-h" }, `Rulings`, h("span", { class: "note" }, "decisions.md")),
        r.rulings.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, ["Id", "When", "By", "Title", "Applies to", "Ruling"].map((c) => h("th", {}, c)))),
          h("tbody", {}, r.rulings.map((x) => h("tr", {}, h("td", { class: "mono" }, x.id), h("td", {}, x.when), h("td", {}, x.by), h("td", {}, x.title), h("td", { class: "mono" }, x.applies_to), h("td", {}, x.ruling)))))) : h("p", { class: "empty" }, "No rulings recorded.")),
      h("section", { class: "card", "aria-labelledby": "it-h" },
        h("h2", { id: "it-h" }, "Iterations", h("span", { class: "note" }, "tickets worked inside this release")),
        r.iterations.rows.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, Object.keys(r.iterations.rows[0]).map((c) => h("th", {}, c)))),
          h("tbody", {}, r.iterations.rows.map((row) => h("tr", {}, Object.values(row).map((v) => h("td", {}, v))))))) : h("p", { class: "empty" }, "No iterations.")),
      r.tickets && !r.tickets.error && r.tickets.activity.length ? ticketActivity(r.tickets.activity) : null,
      h("section", { class: "card", "aria-labelledby": "lg-h" },
        h("h2", { id: "lg-h" }, "Execution log", h("span", { class: "note" }, `${log.length} rows, newest first`)),
        log.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, cols.map((c) => h("th", {}, c)))),
          h("tbody", {}, log.map((row) => h("tr", {}, cols.map((c) => h("td", { class: c === "Command" ? "mono" : null }, row[c]))))))) : h("p", { class: "empty" }, "No execution log."))));
}

// ---------- tickets (releases built from tickets, 4.2.0) ----------
const CELL = { complete: ["✅", "Complete"], in_progress: ["🔄", "In progress"], blocked: ["⚠️", "Blocked"], not_started: ["⏸️", "Not started"] };
const NEXT = { done: "Done", in_progress: "In progress", blocked: "Blocked", waiting: "Waiting", parked: "Needs a ruling", can_start: "Can start", plain: "Plain work", cancelled: "Cancelled", unknown: "Unknown" };
function nextClass(s) {
  return { done: "complete", can_start: "runnable", in_progress: "running", waiting: "blocked", blocked: "stalled", parked: "parked" }[s] || "na";
}
// A merged ticket whose rows are not yet in the release record is rolled up;
// any other ticket is opened (or resumed) with /wire:work.
function ticketDirective(r, t) {
  return t.rows_awaiting_rollup ? `/wire:status-sync ${r.name}` : `/wire:work ${r.name} ${t.key}`;
}
function viewTickets(arg) {
  const r = release;
  const tk = r.tickets;
  if (arg) selected.ticket = arg;  // #/r/<release>/tickets/<ticket> opens that ticket
  if (!tk) return h("div", {}, releaseHeader("Tickets"), h("div", { class: "content" }, h("p", { class: "empty" }, "This release is built artifact by artifact, not from tickets.")));
  if (tk.error) return h("div", {}, releaseHeader("Tickets"), h("div", { class: "content" }, h("div", { class: "error" }, tk.error)));
  if (!tk.tickets.find((t) => t.key === selected.ticket)) selected.ticket = (tk.tickets.find((t) => t.next === "can_start") || tk.tickets[0] || {}).key;
  const cur = tk.tickets.find((t) => t.key === selected.ticket);
  const table = h("div", { class: "table-wrap" }, h("table", { class: "slices" },
    h("thead", {}, h("tr", {}, h("th", {}, "Slice"), tk.steps.map((s) => h("th", {}, s)))),
    h("tbody", {}, tk.slices.map((sl) => h("tr", {}, h("td", { class: "mono" }, sl.id),
      tk.steps.map((s) => { const c = sl.cells[s]; return h("td", { class: c ? `cell ${c.state}` : "cell" },
        c ? [h("span", { title: CELL[c.state][1], "aria-label": CELL[c.state][1] }, CELL[c.state][0]), " ", c.tickets.join(", ")] : ""); }))))));
  const roll = Object.entries(tk.release).map(([s, x]) => h("span", { class: x.state === "complete" ? "tag" : "tag warn", style: "margin-right:6px" }, `${s}: ${x.complete} of ${x.slices} slices`));
  return h("div", {},
    releaseHeader("Tickets", h("span", { class: "muted" }, `${tk.counts.closed} of ${tk.counts.total} closed · ${tk.tracker || "tracker"} ${tk.tracker_project || ""}`)),
    h("div", { class: "content" },
      h("section", { class: "card", "aria-labelledby": "sl-h" },
        h("h2", { id: "sl-h" }, "Slices", h("span", { class: "note" }, `design source: ${tk.design_source || "wire"} · imported ${tk.imported}`)),
        table,
        h("p", { style: "margin:12px 0 0" }, roll)),
      h("div", { class: "split" },
        h("ul", { class: "list", "aria-label": "Tickets" }, tk.tickets.map((t) => h("li", {},
          h("button", { type: "button", class: "item", "aria-pressed": cur && t.key === cur.key ? "true" : "false", onclick: () => { selected.ticket = t.key; render("tickets"); } },
            h("span", { class: "meta" }, h("span", { class: "mono" }, t.key), h("span", { class: `badge ${nextClass(t.next)}` }, NEXT[t.next] || t.next)),
            h("span", { class: "title" }, t.title),
            t.waits_on.length ? h("span", { class: "muted" }, `Waits for ${t.waits_on.join(", ")}`) : null,
            t.rows_awaiting_rollup ? h("span", { class: "muted" }, "Merged, not yet rolled up") : null,
            progressSummary(t))))),
        cur ? h("section", { class: "card", "aria-labelledby": "tk-h" },
          h("span", { class: "muted" }, `${String(cur.kind || "").toUpperCase()} · ${cur.record_state}${cur.merged ? " · merged" : ""}`),
          h("h2", { id: "tk-h", style: "margin:6px 0 12px;font-size:20px" }, `${cur.key}: ${cur.title}`),
          h("p", { class: "muted" }, "Slices: ", h("span", { class: "mono" }, cur.slices.join(", ") || "-")),
          h("p", { class: "muted" }, "Wire steps: ", h("span", { class: "mono" }, cur.steps.join(", ") || "none (plain work)")),
          cur.blocked ? h("div", { class: "error" }, `Blocked: ${cur.blocked}`) : null,
          cur.unmet.length ? h("p", { class: "muted" }, "Waiting on: ", h("span", { class: "mono" }, cur.unmet.join(", "))) : null,
          cur.needs_ruling.length ? h("p", { class: "muted" }, "Needs a ruling: ", cur.needs_ruling.join("; ")) : null,
          h("p", { class: "muted" }, `Ticket log: ${cur.log_rows} row${cur.log_rows === 1 ? "" : "s"}${cur.rows_awaiting_rollup ? `, ${cur.rows_awaiting_rollup} not yet in the release log` : ""}`),
          ticketProgress(r, cur),
          ticketFiles(r, cur),
          ticketRows(cur),
          h("p", { style: "margin-top:16px" }, h("a", { href: `#/r/${encodeURIComponent(r.name)}/file/${encodeURIComponent(cur.record)}` }, "Open the ticket record"),
            cur.url ? [" · ", h("a", { href: cur.url, target: "_blank", rel: "noopener noreferrer" }, "Open in the tracker")] : null),
          !HOSTED && cur.next !== "plain" && cur.next !== "cancelled" ? [h("p", { class: "muted", style: "margin:16px 0 6px" }, "Directive"), directiveBox(ticketDirective(r, cur))] : null)
          : h("p", { class: "empty" }, "No tickets in the map.")),
      tk.link_check.length ? h("section", { class: "card", "aria-labelledby": "lc-h" },
        h("h2", { id: "lc-h" }, "Tracker link check", h("span", { class: "note" }, "Wire's order against the tracker's 'blocked by' links")),
        h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Ticket"), h("th", {}, "Missing in the tracker"), h("th", {}, "In the tracker, not in Wire's order"))),
          h("tbody", {}, tk.link_check.map((x) => h("tr", {}, h("td", { class: "mono" }, x.ticket), h("td", { class: "mono" }, x.missing_in_tracker.join(", ") || "-"), h("td", { class: "mono" }, x.not_in_wire_order.join(", ") || "-"))))))) : null,
      HOSTED ? null : h("section", { class: "card", "aria-labelledby": "rf-h" },
        h("h2", { id: "rf-h" }, "Tracker changed?"),
        h("p", { class: "muted", style: "margin:0 0 10px" }, "Wire lists new, changed and removed tickets and asks before changing the map."),
        directiveBox(`/wire:tickets-import ${r.name} --refresh`))));
}
// ---------- progress inside a ticket (4.2.6) ----------
const ACT = { recorded: "Recorded", found: "Found, not recorded", not_done: "Not done" };
function progressSummary(t) {
  const p = t.progress;
  if (!p || p.error || !p.counts) return null;
  const c = p.counts, total = c.recorded + c.found + c.not_done;
  if (!total) return null;
  return h("span", { class: "muted" }, `${c.recorded} of ${total} recorded${c.found ? `, ${c.found} found` : ""}`);
}
function ticketProgress(r, t) {
  const p = t.progress;
  if (!p) return null;
  if (p.error) return h("p", { class: "muted" }, `Progress: ${p.error}`);
  if (!p.progress.length) return null;
  const acts = ["generate", "validate", "review"];
  const cell = (x) => !x ? h("div", { class: "act na" }, h("span", { class: "v" }, "n/a"))
    : h("div", { class: `act ${x.state}` }, h("span", { class: "v" }, x.state === "not_done" ? "Not done" : `${x.state === "found" ? "Found: " : ""}${x.value}`),
        x.evidence ? h("span", { class: "e" }, x.evidence) : null);
  const missing = p.missing || [];
  return h("div", { class: "tsec" },
    h("div", { class: "row", style: "justify-content:space-between" },
      h("h3", {}, "Progress"),
      h("div", { class: "legend" }, h("span", { style: "--c: var(--ok)" }, ACT.recorded), h("span", { class: "dash", style: "--c: var(--accent)" }, ACT.found), h("span", { style: "--c: var(--line)" }, ACT.not_done))),
    h("div", { style: "overflow-x:auto" }, h("div", { class: "pgrid", role: "table", "aria-label": `Progress of ${t.key}` },
      h("div", { class: "ph", role: "row" }, ["Wire step", "Generate", "Validate", "Review"].map((c) => h("span", { role: "columnheader" }, c))),
      p.progress.map((s) => h("div", { class: "pr", role: "row" }, h("span", { class: "mono", role: "rowheader" }, s.step), acts.map((a) => h("div", { role: "cell" }, cell(s.actions[a]))))))),
    missing.length ? h("div", { class: "found-note" },
      h("p", { style: "margin:0 0 8px" }, `${missing.length} result${missing.length === 1 ? "" : "s"} found in the ticket's logs or changed files, not recorded in the ticket record.` +
        (HOSTED ? "" : t.merged ? " Status sync proposes them for your confirmation:" : " The ticket's session records them:")),
      directiveBox(t.merged ? `/wire:status-sync ${r.name}` : `/wire:work ${r.name} ${t.key}`)) : null);
}
function ticketFiles(r, t) {
  const f = t.progress && t.progress.files;
  if (!f || (f.error && t.record_state === "planned")) return null;
  if (f.error) return h("div", { class: "tsec" }, h("h3", {}, "Files changed"), h("p", { class: "muted" }, f.error));
  const status = { A: "added", M: "changed", D: "deleted", T: "type changed" };
  return h("div", { class: "tsec" },
    h("h3", {}, "Files changed", h("span", { class: "note" }, `${f.files.length} file${f.files.length === 1 ? "" : "s"}, +${f.added} −${f.deleted}, ${f.branch}${f.merged ? " (merged)" : ` against ${f.base}`}`)),
    f.files.length ? h("div", { class: "fgroups" }, f.groups.map((g) => h("div", { class: "fgroup" },
      h("span", { class: "muted" }, `${g.name} · ${g.files.length}`),
      h("ul", {}, g.files.map((x) => h("li", {},
        x.status === "D" ? h("span", { class: "mono del" }, x.path) : h("a", { class: "mono", href: `#/r/${encodeURIComponent(r.name)}/file/${encodeURIComponent(x.path)}`, title: x.path }, x.path.split("/").pop()),
        h("span", { class: "muted" }, ` ${status[x.status] || x.status}`))))))) : h("p", { class: "empty" }, "No files changed yet."));
}
function ticketRows(t) {
  const a = t.progress && t.progress.activity;
  if (!a || !a.rows.length) return null;
  const cols = ["Timestamp", "Command", "Result", "Detail", "By"];
  return h("div", { class: "tsec" },
    h("h3", {}, "Activity", h("span", { class: "note" }, a.source === "ticket log" ? "from the ticket's own log" : "from the release log: this ticket has no log of its own")),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, cols.map((c) => h("th", {}, c)))),
      h("tbody", {}, a.rows.map((row) => h("tr", {}, cols.map((c) => h("td", { class: c === "Command" ? "mono" : null }, row[c] || ""))))))));
}

function ticketActivity(rows) {
  const cols = ["Ticket", ...Object.keys(rows[0]).filter((c) => c !== "Ticket")];
  const recent = [...rows].reverse();
  return h("section", { class: "card", "aria-labelledby": "ta-h" },
    h("h2", { id: "ta-h" }, "Ticket activity", h("span", { class: "note" }, `${rows.length} rows from the tickets' own logs, newest first; added to the release log when each ticket merges`)),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, cols.map((c) => h("th", {}, c)))),
      h("tbody", {}, recent.map((row) => h("tr", {}, cols.map((c) => h("td", { class: c === "Command" || c === "Ticket" ? "mono" : null }, row[c]))))))));
}

function viewFile(path) {
  const r = release;
  const box = h("div", { class: "doc" }, h("p", { class: "loading" }, "Loading…"));
  api(`/api/file?release=${encodeURIComponent(r.name)}&path=${encodeURIComponent(path)}`).then((f) => {
    if (/\.(md|markdown)$/i.test(f.path) && window.marked && window.DOMPurify) {
      const html = DOMPurify.sanitize(marked.parse(f.text));
      box.innerHTML = html;  // sanitised above
      if (window.mermaid) {
        const blocks = box.querySelectorAll("code.language-mermaid");
        blocks.forEach((c) => { const d = h("div", { class: "mermaid" }); d.textContent = c.textContent; c.parentElement.replaceWith(d); });
        try { mermaid.initialize({ startOnLoad: false, securityLevel: "strict" }); mermaid.run({ nodes: box.querySelectorAll(".mermaid") }); } catch { /* leave as text */ }
      }
    } else {
      box.replaceChildren(h("pre", { class: "state" }, f.text));
    }
  }).catch((e) => box.replaceChildren(h("div", { class: "error" }, e.message)));
  return h("div", {},
    releaseHeader(path, h("a", { class: "btn ghost", style: "text-decoration:none", href: `#/r/${encodeURIComponent(r.name)}/overview` }, "Back to overview")),
    h("div", { class: "content" }, h("section", { class: "card" }, box)));
}

window.addEventListener("hashchange", route);
route();
