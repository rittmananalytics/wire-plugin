// Wire Studio: the Session view. The Wire CLI's session, driven from the page
// (local mode only). Lines typed here go to the session; its output comes back
// as events and is shown as it arrives. The session is the writer of the
// record, as in a terminal; Studio relays. Conversations are kept in
// .wire/local/sessions/ and can be opened again, renamed, exported or deleted.
// Everything from the session is set with textContent, never innerHTML.
"use strict";

const SESSION = { id: null, after: 0, poll: 0, alive: false, busySince: 0, timer: null };

async function sessionApi(path, body) {
  const opts = { headers: { Accept: "application/json", "X-Studio-Token": TOKEN } };
  if (body !== undefined) {
    opts.method = "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(BASE + path.replace(/^\//, ""), opts);
  const out = await r.json();
  if (!r.ok) throw new Error(out.error || r.statusText);
  return out;
}

// Set by the console view: what a change of the sidebar's release selector does
// here (`use <release>` in the running session). Cleared when the view closes.
let onSessionRelease = null;

function stopSessionView() {
  SESSION.poll += 1;  // any poll loop still running sees a newer generation and stops
  clearInterval(SESSION.timer);
  onSessionRelease = null;
}

// A Lucide icon (lucide.dev, ISC licence, lucide-static 1.70.0), drawn inline:
// message-square-dot is New session, chevron-down opens the model list.
// A string is a path; ["circle", {...}] a circle.
const LUCIDE = {
  "message-square-dot": ["M12.7 3H4a2 2 0 0 0-2 2v16.286a.71.71 0 0 0 1.212.502l2.202-2.202A2 2 0 0 1 6.828 19H20a2 2 0 0 0 2-2v-4.7",
                         ["circle", { cx: 19, cy: 6, r: 3 }]],
  "chevron-down": ["m6 9 6 6 6-6"],
  plus: ["M5 12h14", "M12 5v14"],
};
function lucide(name, size = 16) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [k, v] of Object.entries({ width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", class: `lucide lucide-${name}` })) {
    svg.setAttribute(k, String(v));
  }
  for (const d of LUCIDE[name]) {
    const [tag, attrs] = typeof d === "string" ? ["path", { d }] : d;
    const el = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
    svg.append(el);
  }
  return svg;
}

// The sidebar: New session (an icon button beside the Wire CLI link) and,
// while the Wire CLI view is open, the last ten sessions under it.
const SESSIONS_SHOWN = 10;
document.getElementById("nav-new-session").append(lucide("message-square-dot", 18));

async function openConversation(id) {
  try {
    const st = await sessionApi("/api/session/start", { id });
    location.hash = `#/session/${encodeURIComponent(st.id)}`;
  } catch (err) { toast(String(err.message || err)); }
}
async function removeConversation(id, title) {
  if (!window.confirm(`Delete "${title || id}"? The transcript is removed from .wire/local/sessions/.`)) return;
  try {
    await sessionApi(`/api/session/${encodeURIComponent(id)}/delete`, {});
    if (id === SESSION.id) location.hash = "#/session"; else refreshSessionNav();
  } catch (err) { toast(String(err.message || err)); }
}
function renderSessionNav(conversations) {
  const list = document.getElementById("session-nav-list");
  const shown = (conversations || []).slice(0, SESSIONS_SHOWN);
  list.replaceChildren(...(shown.length ? shown.map((c) => h("div", { class: "sess-row" },
    h("a", { href: `#/session/${encodeURIComponent(c.id)}`, class: c.id === SESSION.id ? "active" : null,
             onclick: (ev) => { ev.preventDefault(); openConversation(c.id); } },
      h("span", { class: "t" }, c.title || "(untitled)"),
      h("span", { class: "m" }, c.release || "no release"),
      h("span", { class: "m" }, `${c.updated || ""}${c.live ? " · running" : ""}`)),
    h("button", { type: "button", class: "x", title: "Delete", "aria-label": `Delete ${c.title || c.id}`,
                  onclick: () => removeConversation(c.id, c.title) }, "×")))
    : [h("p", { class: "sess-empty" }, "No sessions yet.")]));
}
async function refreshSessionNav(release) {
  try {
    const r = await sessionApi("/api/sessions" + (release ? `?release=${encodeURIComponent(release)}` : ""));
    if (r.available) renderSessionNav(r.conversations);
    else document.getElementById("session-nav-list").replaceChildren();
    return r;
  } catch (err) {
    document.getElementById("session-nav-list").replaceChildren(h("p", { class: "sess-empty" }, String(err.message || err)));
    throw err;
  }
}

// The "+" at the left of the box: a menu with one item, Add Files to release.
// The server opens the operating system's file picker and then its save dialog
// (starting in the release's folder) and copies the file inside the repository only.
function plusMenu() {
  const item = h("button", { type: "button", class: "box-menu-item", role: "menuitem" }, "Add Files to release");
  const menu = h("div", { class: "box-menu", role: "menu", hidden: true }, item);
  const btn = h("button", { type: "button", class: "box-plus", title: "Add", "aria-label": "Add", "aria-haspopup": "menu", "aria-expanded": "false" },
    lucide("plus", 18));
  const el = h("div", { class: "box-plus-wrap" }, btn, menu);
  function close() { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  function onOutside(ev) {
    if (!el.isConnected) { document.removeEventListener("click", onOutside); return; }  // the view has gone
    if (!el.contains(ev.target)) close();
  }
  btn.addEventListener("click", () => {
    menu.hidden = !menu.hidden;
    btn.setAttribute("aria-expanded", String(!menu.hidden));
    if (!menu.hidden) item.focus();
  });
  el.addEventListener("keydown", (ev) => { if (ev.key === "Escape") { close(); btn.focus(); } });
  document.addEventListener("click", onOutside);
  item.addEventListener("click", async () => {
    close();
    btn.disabled = true;
    try {
      const r = await sessionApi("/api/files/add", { release: selectedRelease() });
      if (r.added) toast(`Added ${r.added}`);
    } catch (err) { toast(String(err.message || err)); }
    finally { btn.disabled = false; }
  });
  return el;
}

// The model list at the right of the box: light grey, the model's name and a
// down arrow. show(m) sets the model in use, choices(list) the ones offered.
function modelPicker(onPick) {
  const sel = h("select", { class: "model-select", "aria-label": "Model", title: "The model this session runs on" });
  const el = h("label", { class: "model-pick" }, sel, lucide("chevron-down", 14));
  let offered = [];
  let current = null;
  function render() {
    if (!current) { el.hidden = true; return; }
    el.hidden = false;
    const opts = offered.some((c) => c.key === current.key) ? offered : [{ key: current.key, label: current.label }, ...offered];
    sel.replaceChildren(...opts.map((c) => h("option", { value: c.key }, c.label)));
    sel.value = current.key;
    sel.disabled = opts.length < 2;
  }
  sel.addEventListener("change", async () => {
    const key = sel.value;
    const prev = current;
    try {
      const m = await onPick(key, offered.find((c) => c.key === key));
      sel.blur();
      current = m || prev;
    } catch (err) { toast(String(err.message || err)); }
    render();
  });
  el.hidden = true;
  return {
    el,
    value: () => (current ? current.key : ""),
    show(m) { if (m && document.activeElement !== sel) { current = m; render(); } },
    choices(list) { offered = list || []; render(); },
  };
}

// The numbered options of a question ("  1. Dagster (the client runs it)").
function optionsOf(prompt) {
  const out = [];
  for (const line of String(prompt).split("\n")) {
    const m = /^\s*(\d+)\.\s+(.+?)\s*$/.exec(line);
    if (m) out.push({ n: m[1], label: m[2] });
  }
  return out;
}

// The opening screen: one box, centred, until the first line is sent.
function viewSessionStart() {
  SESSION.id = null;
  const box = h("textarea", { class: "session-input", rows: "1", placeholder: "Type to start developing using Wire CLI",
                              "aria-label": "What do you want to build today?" });
  const enter = h("button", { type: "submit", class: "hero-enter ready", title: "Enter", "aria-label": "Enter" }, "Enter ↵");
  const note = h("div", { class: "hero-note", "aria-live": "polite" });
  // five commands under the box: what the release can run now (the runnable
  // set's order), then general opening commands. A click runs it, as Enter would.
  const opening = h("div", { class: "opening", "aria-label": "Commands to start with" });
  function showOpening(list) {
    opening.replaceChildren(...(list || []).map((c) => h("button", { type: "button", class: "opening-cmd mono", title: c.why,
      onclick: () => { box.value = c.line; box.rows = 1; begin(); } }, c.line)));
  }
  // nothing is running yet: a pick is kept here and sent with the first line
  const picker = modelPicker(async (key, c) => c);
  let starting = false;

  async function begin(ev) {
    if (ev) ev.preventDefault();
    const first = box.value.trim();
    if (!first || starting) { box.focus(); return; }
    starting = true;
    enter.disabled = box.disabled = true;
    note.replaceChildren(h("span", { class: "muted" }, "Starting the Wire CLI…"));
    try {
      const st = await sessionApi("/api/session/start", { release: selectedRelease(), first, model: picker.value() || null });
      location.hash = `#/session/${encodeURIComponent(st.id)}`;
    } catch (err) {
      starting = false;
      enter.disabled = box.disabled = false;
      note.replaceChildren(h("div", { class: "error" }, String(err.message || err)));
    }
  }
  box.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.shiftKey) begin(ev); });
  box.addEventListener("input", () => {
    box.rows = Math.min(6, Math.max(1, box.value.split("\n").length));
  });

  refreshSessionNav(selectedRelease()).then((r) => {
    if (!r.available) {
      note.replaceChildren(h("div", { class: "error" }, `The Wire CLI is not available here: ${r.reason}.`));
      enter.disabled = box.disabled = true;
      return;
    }
    picker.choices(r.models);
    picker.show(r.default_model);
    showOpening(r.opening);
  }).catch((err) => note.replaceChildren(h("div", { class: "error" }, String(err.message || err))));
  // a release picked in the menu changes the commands offered
  onSessionRelease = (name) => refreshSessionNav(name).then((r) => { if (r.available) showOpening(r.opening); }).catch(() => {});

  setTimeout(() => box.focus(), 0);
  return h("div", { class: "session-hero" },
    h("div", { class: "hero-inner" },
      h("h1", { class: "hero-title" }, "What do you want to build today?"),
      // the same box as the console's, at the bottom of a running session
      h("form", { class: "composer-box hero-box", onsubmit: begin }, plusMenu(), box, picker.el, enter),
      opening, note));
}

function viewSession(cid) {
  stopSessionView();
  if (!cid) return viewSessionStart();
  const gen = SESSION.poll;
  SESSION.id = cid || null;
  SESSION.after = 0;
  SESSION.alive = false;

  const transcript = h("div", { class: "transcript", role: "log", "aria-live": "polite", tabindex: "0" });
  const jump = h("button", { type: "button", class: "btn ghost jump", hidden: true, onclick: () => scrollEnd(true) }, "Jump to latest");
  const choices = h("div", { class: "choices row" });
  const status = h("div", { class: "sbar-status mono" }, "");
  const busy = h("div", { class: "sbar-busy mono" }, "");
  const input = h("textarea", { class: "session-input", rows: "1", placeholder: "A Wire command, or what you want next",
                                "aria-label": "Message to the session" });
  const send = h("button", { type: "button", class: "hero-enter ready", "aria-label": "Enter" }, "Enter ↵");
  // the model the next command runs on, kept with the conversation
  const picker = modelPicker(async (key) => {
    const m = await sessionApi(`/api/session/${encodeURIComponent(SESSION.id)}/model`, { key });
    loadList();
    return m;
  });
  // the conversation's title: not shown above the console (the menu lists it); Rename starts from it
  const titleEl = h("span", {}, "Session");
  const ended = h("div", { class: "ended", hidden: true });
  let lanes = {};
  let lastNote = "";
  let block = null;  // the current output block: replies stream into it

  function nearEnd() { return transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 60; }
  function scrollEnd(force) {
    if (force || nearEnd()) transcript.scrollTop = transcript.scrollHeight;
    jump.hidden = nearEnd();
  }
  transcript.addEventListener("scroll", () => { jump.hidden = nearEnd(); });

  function outBlock() {
    if (!block) { block = h("div", { class: "out" }); transcript.append(block); }
    return block;
  }
  function busyText() {
    if (!SESSION.busySince) return "";
    const s = Math.floor((Date.now() - SESSION.busySince) / 1000);
    const clock = s >= 3600 ? `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    const ln = Object.entries(lanes).map(([k, v]) => `${k} ${v}`).join(", ");
    return `running: ${SESSION.busyLabel} ${clock}${ln ? ` · lanes: ${ln}` : ""}${lastNote ? ` · last: ${lastNote}` : ""}`;
  }
  function showChoices(items) {
    choices.replaceChildren(...items.map((c) => h("button", { type: "button", class: "btn ghost", onclick: c.onclick || (() => sendLine(c.send)) }, c.label)));
  }

  function apply(e, live) {
    const stick = nearEnd();
    switch (e.type) {
      case "input":
        block = null;
        transcript.append(h("div", { class: "you mono" }, `› ${e.text}`));
        showChoices([]);
        break;
      case "out":
        outBlock().append(document.createTextNode(e.text + "\n"));
        if (live && /go \/ adjust \/ cancel\?\s*$/.test(e.text)) {
          showChoices([{ label: "Go", send: "go" }, { label: "Adjust…", onclick: () => { input.value = "adjust "; input.focus(); } }, { label: "Cancel", send: "cancel" }]);
        }
        break;
      case "text":
        outBlock().append(document.createTextNode(e.text));
        break;
      case "ask": {
        block = null;
        transcript.append(h("div", { class: "ask" }, e.prompt));
        const opts = optionsOf(e.prompt);
        if (live) showChoices(opts.map((o) => ({ label: `${o.n}. ${o.label}`, send: o.n })));
        input.placeholder = opts.length ? "Pick an option, or type your own answer" : "Your answer";
        break;
      }
      case "ready":
        input.placeholder = "A Wire command, or what you want next";
        break;
      case "status":
        status.textContent = e.text + (e.next ? `   next: ${e.next}` : "");
        break;
      case "busy":
        if (e.label) { SESSION.busySince = Date.now(); SESSION.busyLabel = e.label; lanes = {}; lastNote = ""; }
        else { SESSION.busySince = 0; }
        busy.textContent = busyText();
        break;
      case "note":
        lastNote = e.text;
        busy.textContent = busyText();
        break;
      case "lane":
        lanes[e.label] = e.state;
        busy.textContent = busyText();
        break;
      case "end":
        block = null;
        transcript.append(h("div", { class: "muted" }, "Session ended."));
        break;
      default:
        break;
    }
    if (stick) scrollEnd(true); else jump.hidden = false;
  }

  function setState(st) {
    SESSION.alive = !!st.alive;
    titleEl.textContent = st.title || "New session";
    // the sidebar's release selector follows the session's release
    if (st.release && document.activeElement !== releaseSel && st.release !== releaseSel.value) selectRelease(st.release);
    picker.show(st.model);
    input.disabled = send.disabled = !SESSION.alive;
    ended.hidden = SESSION.alive || !SESSION.id;
    if (!SESSION.alive && SESSION.id) {
      showChoices([]);
      ended.replaceChildren(h("span", { class: "muted" }, "This conversation is not running. "),
        h("button", { type: "button", class: "btn ghost", onclick: () => openConversation(SESSION.id) }, "Resume it"));
    }
  }

  async function pollLoop() {
    while (gen === SESSION.poll && SESSION.id) {
      try {
        const r = await sessionApi(`/api/session/${encodeURIComponent(SESSION.id)}/events?after=${SESSION.after}&wait=25`);
        if (gen !== SESSION.poll) return;
        for (const e of r.events) { apply(e, true); SESSION.after = Math.max(SESSION.after, e.seq); }
        setState(r.state);
        if (!r.state.alive) { loadList(); return; }
      } catch (err) {
        if (gen !== SESSION.poll) return;
        transcript.append(h("div", { class: "error" }, String(err.message || err)));
        await new Promise((res) => setTimeout(res, 3000));
      }
    }
  }

  async function sendLine(text) {
    const line = (text === undefined ? input.value : text);
    if (!SESSION.id || !SESSION.alive || line === undefined) return;
    if (text === undefined) input.value = "";
    try { await sessionApi(`/api/session/${encodeURIComponent(SESSION.id)}/input`, { line }); }
    catch (err) { toast(String(err.message || err)); }
    input.focus();
  }
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); sendLine(); }
  });
  input.addEventListener("input", () => { input.rows = Math.min(6, Math.max(1, input.value.split("\n").length)); });
  send.addEventListener("click", () => sendLine());

  async function rename() {
    const t = window.prompt("Name this conversation", titleEl.textContent);
    if (!t || !SESSION.id) return;
    try { const m = await sessionApi(`/api/session/${encodeURIComponent(SESSION.id)}/rename`, { title: t }); titleEl.textContent = m.title; loadList(); }
    catch (err) { toast(String(err.message || err)); }
  }
  async function exportMd() {
    if (!SESSION.id) return;
    try {
      const r = await fetch(BASE + `api/session/${encodeURIComponent(SESSION.id)}/export`, { headers: { "X-Studio-Token": TOKEN } });
      if (!r.ok) throw new Error((await r.json()).error || r.statusText);
      const url = URL.createObjectURL(await r.blob());
      const a = h("a", { href: url, download: `wire-session-${SESSION.id}.md` });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { toast(String(err.message || err)); }
  }
  async function stop() {
    if (!SESSION.id) return;
    try { await sessionApi(`/api/session/${encodeURIComponent(SESSION.id)}/stop`, {}); } catch (err) { toast(String(err.message || err)); }
  }
  async function loadList() {
    try {
      const r = await refreshSessionNav();
      if (!r.available) {
        transcript.append(h("div", { class: "error" }, `Sessions are not available: ${r.reason}.`));
        input.disabled = send.disabled = true;
        return;
      }
      picker.choices(r.models);
    } catch (err) { /* shown in the sidebar */ }
  }

  const view = h("div", { class: "session-view" },
    h("div", { class: "session-body" },
      h("section", { class: "session-main" },
        // no header above the console: its buttons sit at the top of the console itself
        h("div", { class: "session-tools row" },
          h("button", { type: "button", class: "btn ghost", onclick: rename }, "Rename"),
          h("button", { type: "button", class: "btn ghost", onclick: exportMd }, "Export (.md)"),
          h("button", { type: "button", class: "btn ghost", onclick: stop }, "Stop")),
        h("div", { class: "transcript-wrap" }, transcript, jump),
        ended, choices,
        h("div", { class: "sbar" }, status, busy),
        h("div", { class: "composer" }, h("div", { class: "composer-box" }, plusMenu(), input, picker.el, send)))));

  clearInterval(SESSION.timer);
  // the sidebar's release selector: `use <release>` in this session
  onSessionRelease = (name) => sendLine(`use ${name}`);
  SESSION.timer = setInterval(() => { if (SESSION.busySince) busy.textContent = busyText(); }, 1000);
  loadList();
  pollLoop();
  return view;
}
