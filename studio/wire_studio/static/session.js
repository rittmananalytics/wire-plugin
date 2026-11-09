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

// The "+" at the left of the box. Add Files to release is done by the server:
// it opens the operating system's file picker and then its save dialog
// (starting in the release's folder) and copies the file inside the
// repository only. Every other item sends a line to the session, as if typed
// (`send`), so the session runs it and writes what it changes:
//   mcp add <server> [url] | mcp remove <server> | mcp check <release>
//   persona set <persona> [--local] | repos list | repos refresh
// Lists for the dialogs come from Studio's read-only settings endpoints.
function plusMenu(send) {
  const items = [];
  const item = (label, run) => {
    const b = h("button", { type: "button", class: "box-menu-item", role: "menuitem" }, label);
    b.addEventListener("click", async () => { close(); await run(); });
    items.push(b);
    return b;
  };
  const sep = () => h("div", { class: "box-menu-sep", role: "separator" });
  const menu = h("div", { class: "box-menu", role: "menu", hidden: true },
    item("Add Files to release", addFiles),
    sep(),
    item("Add MCP server…", addMcp),
    item("Remove MCP server…", removeMcp),
    item("Check MCP servers for this release", () => {
      const rel = selectedRelease();
      if (!rel) { toast("No release in this repository."); return; }
      send(`mcp check ${rel}`);
    }),
    sep(),
    item("Set my persona…", setPersona),
    item("Related repositories", () => send("repos list")),
    item("Refresh related repositories", () => send("repos refresh")));
  const btn = h("button", { type: "button", class: "box-plus", title: "Add", "aria-label": "Add", "aria-haspopup": "menu", "aria-expanded": "false" },
    lucide("plus", 18));
  const el = h("div", { class: "box-plus-wrap" }, btn, menu);
  function close() { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  function onOutside(ev) {
    if (!el.isConnected) { document.removeEventListener("click", onOutside); return; }  // the view has gone
    if (!el.contains(ev.target)) close();
  }
  // Open below the box when it fits, else above it: with a long conversation
  // the box sits at the bottom of the window and a menu below it is cut off.
  function place() {
    menu.classList.remove("up");
    menu.style.bottom = "";
    const box = (el.closest(".composer-box") || el).getBoundingClientRect();
    const below = window.innerHeight - box.bottom;
    if (below >= menu.offsetHeight + 24 || box.top <= below) return;
    // above the whole box, 8px clear of its top edge, however tall the text makes it
    menu.classList.add("up");
    menu.style.bottom = `calc(100% + ${Math.round(el.getBoundingClientRect().top - box.top) + 8}px)`;
  }
  btn.addEventListener("click", () => {
    menu.hidden = !menu.hidden;
    btn.setAttribute("aria-expanded", String(!menu.hidden));
    if (!menu.hidden) place();
    if (!menu.hidden) items[0].focus();
  });
  el.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") { close(); btn.focus(); return; }
    if (menu.hidden || (ev.key !== "ArrowDown" && ev.key !== "ArrowUp")) return;
    ev.preventDefault();
    const i = items.indexOf(document.activeElement);
    items[(i + (ev.key === "ArrowDown" ? 1 : items.length - 1)) % items.length].focus();
  });
  document.addEventListener("click", onOutside);

  async function addFiles() {
    btn.disabled = true;
    try {
      const r = await sessionApi("/api/files/add", { release: selectedRelease() });
      if (r.added) toast(`Added ${r.added}`);
    } catch (err) { toast(String(err.message || err)); }
    finally { btn.disabled = false; }
  }
  async function mcpServers() {
    try { return (await sessionApi("/api/settings/mcp")).servers; }
    catch (err) { toast(String(err.message || err)); return null; }
  }
  async function addMcp() {
    const servers = await mcpServers();
    if (!servers) return;
    const offered = servers.filter((s) => !s.selected);
    if (!offered.length) { toast("Every server in Wire's catalogue is already in this engagement."); return; }
    const sel = h("select", { class: "dlg-input", "aria-label": "Server" },
      ...offered.map((s) => h("option", { value: s.key }, s.purpose ? `${s.key}: ${s.purpose}` : s.key)));
    const url = h("input", { class: "dlg-input mono", type: "url", "aria-label": "Server URL", spellcheck: "false" });
    const hint = h("p", { class: "muted", style: "margin:4px 0 0" });
    const fill = () => {
      const s = offered.find((x) => x.key === sel.value);
      url.value = s.placeholder ? "" : s.url;
      url.placeholder = s.placeholder ? "https://… (your organisation's server)" : s.url;
      hint.textContent = s.placeholder ? "This server is hosted by each organisation: enter its URL." : "Wire's URL for this server. Change it only if yours differs.";
    };
    sel.addEventListener("change", fill);
    fill();
    const ok = await dialog("Add MCP server",
      "Adds the server to .wire/engagement/mcp_servers.yml for the whole team. Commit the file afterwards. Each person then signs in under Settings, MCP sign-ins.",
      [h("label", { class: "dlg-label" }, "Server", sel), h("label", { class: "dlg-label" }, "URL", url), hint], "Add",
      () => {
        const s = offered.find((x) => x.key === sel.value);
        const u = url.value.trim();
        if (s.placeholder && !/^https:\/\/\S+$/.test(u)) return "Enter the server's https:// URL.";
        if (u && !/^https:\/\/\S+$/.test(u)) return "The URL must start with https:// and have no spaces.";
        return null;
      });
    if (!ok) return;
    const s = offered.find((x) => x.key === sel.value);
    const u = url.value.trim();
    send(`mcp add ${s.key}${u && u !== s.url ? " " + u : (s.placeholder ? " " + u : "")}`);
  }
  async function removeMcp() {
    const servers = await mcpServers();
    if (!servers) return;
    const mine = servers.filter((s) => s.selected);
    if (!mine.length) { toast("This engagement uses no MCP servers."); return; }
    const sel = h("select", { class: "dlg-input", "aria-label": "Server" }, ...mine.map((s) => h("option", { value: s.key }, s.key)));
    const ok = await dialog("Remove MCP server",
      "Removes the server from .wire/engagement/mcp_servers.yml for the whole team. Commit the file afterwards. Sign-ins stay in each person's Codex store.",
      [h("label", { class: "dlg-label" }, "Server", sel)], "Remove");
    if (ok) send(`mcp remove ${sel.value}`);
  }
  async function setPersona() {
    let st;
    try { st = await sessionApi("/api/settings/persona"); }
    catch (err) { toast(String(err.message || err)); return; }
    const current = st.current && st.current.persona;
    const radios = st.personas.map((p) => h("label", { class: "dlg-choice" },
      h("input", { type: "radio", name: "persona", value: p.id, checked: p.id === current ? true : null }),
      h("span", {}, h("strong", {}, p.name), h("span", { class: "muted" }, ` ${p.focus}`))));
    const local = h("input", { type: "checkbox" });
    const ok = await dialog("Set my persona",
      current ? `Yours now: ${current} (from ${st.current.source}). It changes what some commands show you, never what they write.`
        : "None set. Your persona changes what some commands show you, never what they write.",
      [...radios, h("label", { class: "dlg-check" }, local,
        st.email ? ` This clone only (not the team roster, where you are ${st.email})` : " This clone only (git user.email is not set, so the team roster cannot find you)")],
      "Set", () => (radios.some((r) => r.querySelector("input").checked) ? null : "Choose a persona."));
    if (!ok) return;
    const pick = radios.map((r) => r.querySelector("input")).find((i) => i.checked).value;
    send(`persona set ${pick}${local.checked || !st.email ? " --local" : ""}`);
  }
  return el;
}

// A small modal form. Resolves true on the action button, false on Cancel or
// Escape. `check` returns an error message to keep the form open, or null.
function dialog(title, intro, fields, action, check) {
  return new Promise((resolve) => {
    const err = h("div", { class: "error", hidden: true, style: "margin-top:10px" });
    const dlg = h("dialog", { class: "dlg", "aria-label": title });
    const done = (value) => { dlg.close(); dlg.remove(); resolve(value); };
    const form = h("form", { method: "dialog", onsubmit: (ev) => {
      ev.preventDefault();
      const why = check ? check() : null;
      if (why) { err.textContent = why; err.hidden = false; return; }
      done(true);
    } },
      h("h2", { class: "key-title" }, title),
      h("p", { class: "muted", style: "margin:0 0 12px" }, intro),
      ...fields, err,
      h("div", { class: "key-form" },
        h("button", { type: "submit", class: "btn" }, action),
        h("button", { type: "button", class: "btn ghost", onclick: () => done(false) }, "Cancel")));
    dlg.append(form);
    dlg.addEventListener("cancel", (ev) => { ev.preventDefault(); done(false); });
    document.body.append(dlg);
    dlg.showModal();
  });
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
// The numbered options at the very end of a reply ("1. New engagement" ...),
// for a command whose question came in its reply and whose prompt is only `you>`.
function trailingOptions(text) {
  const lines = String(text).replace(/\s+$/, "").split("\n");
  const out = [];
  for (let i = lines.length - 1; i >= 0; i--) {
    const m = /^\s*(\d+)\.\s+(.+?)\s*$/.exec(lines[i]);
    if (!m) break;
    out.unshift({ n: m[1], label: m[2] });
  }
  return out;
}
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
      h("form", { class: "composer-box hero-box", onsubmit: begin },
        plusMenu((line) => { box.value = line; box.rows = 1; begin(); }), box, picker.el, enter),
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
        const shown = block ? block.textContent : "";
        block = null;
        transcript.append(h("div", { class: "ask" }, e.prompt));
        let opts = optionsOf(e.prompt);
        if (!opts.length) opts = trailingOptions(shown);
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
        h("div", { class: "composer" }, h("div", { class: "composer-box" },
          plusMenu((line) => (SESSION.alive ? sendLine(line) : toast("This session has ended. Start a new one to run this."))),
          input, picker.el, send)))));

  clearInterval(SESSION.timer);
  // the sidebar's release selector: `use <release>` in this session
  onSessionRelease = (name) => sendLine(`use ${name}`);
  SESSION.timer = setInterval(() => { if (SESSION.busySince) busy.textContent = busyText(); }, 1000);
  loadList();
  pollLoop();
  return view;
}
