// Wire Studio: Settings (local mode only). One page, one link in the menu,
// three sections:
// - API keys: the Claude and OpenAI keys, kept in the macOS Keychain, or on
//   Linux and WSL in ~/.wire/secrets.env (owner-only), never in the
//   repository. The page never receives a key back: only whether each is set,
//   where from, and its last four characters.
// - MCP sign-ins: the engagement's MCP servers and your Codex sign-in to each.
//   Adding or removing a server is in the Wire CLI box's + menu, which sends
//   it to the session (the file it changes is committed).
// - This machine: `wire doctor`, and whether a newer Wire CLI is out.
"use strict";

async function keysApi(path, body) {
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

function keyStatus(k, store) {
  if (!k.source) return h("span", { class: "tag warn" }, "Not set");
  const where = k.source === "environment" ? "from the environment Studio started with"
    : k.source === store ? `in the ${store}` : `in ${k.source}`;
  return h("span", {}, h("span", { class: "tag" }, "Set"), " ", h("span", { class: "muted" }, `${where} ${k.hint}`.trim()));
}

function keyNotes(k, store) {
  const notes = [];
  if (k.in_store && k.source && k.source !== store) {
    const from = k.source === "environment" ? "the environment" : k.source;
    notes.push(`The key in use comes from ${from}, which wins over the ${store} entry (${k.store_hint}).`);
  }
  const files = (k.also || []).filter((p) => p !== store && p !== "environment");
  if (files.length && k.source === store) {
    notes.push(`Also set in ${files.join(", ")}. The ${store} key is used. You can delete the line from that file.`);
  }
  return notes.map((n) => h("p", { class: "muted", style: "margin:6px 0 0" }, n));
}

function keyRow(k, state, rerender) {
  const input = h("input", { type: "password", class: "key-input", autocomplete: "off", spellcheck: "false",
    placeholder: `${k.prefix}…`, "aria-label": k.label });
  const msg = h("div", { role: "status" });
  async function act(path, body, done) {
    msg.replaceChildren(h("span", { class: "muted" }, "Saving…"));
    try {
      const out = await keysApi(path, body);
      input.value = "";
      toast(done);
      rerender(out);
    } catch (e) { msg.replaceChildren(h("div", { class: "error", style: "margin-top:8px" }, String(e.message || e))); }
  }
  const save = () => {
    if (!input.value.trim()) { input.focus(); return; }
    act("/api/settings/keys/set", { name: k.name, value: input.value }, "Saved. New sessions use this key; a running session keeps the key it started with.");
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });
  return h("section", { class: "card" },
    h("h3", { class: "key-title" }, k.label),
    h("div", { class: "key-status" }, h("span", { class: "mono muted" }, k.name), " ", keyStatus(k, state.store)),
    ...keyNotes(k, state.store),
    state.available ? h("div", { class: "key-form" },
      input,
      h("button", { type: "button", class: "btn", onclick: save }, k.in_store ? "Replace" : "Save"),
      k.in_store ? h("button", { type: "button", class: "btn ghost", onclick: () => {
        if (window.confirm(`Remove the ${k.label} from the ${state.store}?`)) {
          act("/api/settings/keys/delete", { name: k.name }, "Removed.");
        }
      } }, "Remove") : null) : null,
    msg);
}

function viewKeys(body) {
  const rerender = (state) => {
    const keychain = state.available && !state.store.startsWith("/") && !state.store.startsWith("~");
    const where = keychain ? "your Mac's Keychain" : `${state.store}, a file only you can read`;
    const order = keychain
      ? ["a key set in your terminal before Studio was started", "this project's .wire/local/secrets.env file",
         "your Mac's Keychain (where this page saves keys)", "~/.wire/secrets.env"]
      : ["a key set in your terminal before Studio was started", "this project's .wire/local/secrets.env file",
         "~/.wire/secrets.env (where this page saves keys)"];
    body.replaceChildren(
      h("section", { class: "card" },
        h("p", { style: "margin:0" },
          "You don't need these keys if Claude Code is installed and signed in on this computer. " +
          "Without a key, the Wire CLI uses your Claude Code sign-in, and its use counts against your Claude plan. " +
          "Add a Claude API key to bill usage to an API account instead, or an OpenAI API key to use OpenAI's models."),
        state.available
          ? h("p", { style: "margin:8px 0 0" },
              `Keys you save here are stored in ${where}. They are not saved in the project. ` +
              "After you save a key, Studio shows only its last four characters, so you can tell keys apart.")
          : h("p", { class: "error", style: "margin:8px 0 0" }, `Keys cannot be saved from here: ${state.reason}.`),
        h("p", { class: "muted", style: "margin:8px 0 0" },
          "If the same key is set in more than one place, Wire uses the first one it finds, in this order: " +
          order.map((o, i) => `${i + 1}. ${o}`).join("; ") + ".")),
      ...state.keys.map((k) => keyRow(k, state, rerender)));
  };
  keysApi("/api/settings/keys").then(rerender)
    .catch((e) => body.replaceChildren(h("div", { class: "error" }, String(e.message || e))));
}

const CLAUDE_TAG = {
  signed_in: ["tag", "Signed in"],
  not_signed_in: ["tag warn", "Not signed in"],
  unreachable: ["tag warn", "Cannot connect"],
};

function claudeTag(s) {
  const [cls, text] = CLAUDE_TAG[s.claude_status] || ["tag muted-tag", "Not checked"];
  return h("span", { class: cls }, text);
}

function codexTag(s) {
  if (s.login && s.login.state === "running") return h("span", { class: "tag warn" }, "Codex: finish signing in in the browser");
  if (s.codex_signed_in === true) return h("span", { class: "tag" }, "Codex: signed in");
  if (s.codex_signed_in === false) return h("span", { class: "tag warn" }, "Codex: not signed in");
  return h("span", { class: "tag muted-tag" }, "Codex: not checked");
}

function viewMcp(body) {
  let timer = null;
  let wasRunning = false;
  async function load(signin) {
    clearTimeout(timer);
    try { render(await keysApi(`/api/settings/mcp${signin ? "?signin=1" : ""}`)); }
    catch (e) { body.replaceChildren(h("div", { class: "error" }, String(e.message || e))); }
  }
  async function signIn(key) {
    try {
      render(await keysApi("/api/settings/mcp/login", { key }));
      toast("A browser window opens for the sign-in.");
    } catch (e) { toast(String(e.message || e)); }
  }
  function howToSignIn(s, st) {
    if (!st.claude) return null;
    return h("p", { class: "muted", style: "margin:6px 0 0" }, s.plugin
      ? `To sign in: run /mcp in Claude Code and choose ${s.claude_name}. That one sign-in works in Claude Code and in Wire CLI runs.`
      : "This server is not part of the Wire plugin. A sign-in made with /mcp in Claude Code does not reach Wire CLI runs for it yet.");
  }
  function render(st) {
    const mine = st.servers.filter((s) => s.selected);
    const running = mine.some((s) => s.login && s.login.state === "running");
    // while a Codex sign-in runs, look again every 3 seconds; when it ends, check the sign-ins
    if (running) timer = setTimeout(() => { if (body.isConnected) load(false); }, 3000);
    else if (wasRunning) timer = setTimeout(() => { if (body.isConnected) load(true); }, 0);
    wasRunning = running;
    const rows = mine.map((s) => h("section", { class: "card" },
      h("h3", { class: "key-title" }, s.key),
      h("div", { class: "key-status" }, st.claude ? claudeTag(s) : null, st.codex ? codexTag(s) : null,
        h("span", { class: "muted mono" }, s.url)),
      s.purpose ? h("p", { class: "muted", style: "margin:6px 0 0" }, s.purpose) : null,
      howToSignIn(s, st),
      s.login && s.login.state === "failed" ? h("div", { class: "error", style: "margin-top:8px" }, `Codex sign-in failed: ${s.login.message || "see Codex"}`) : null,
      st.codex ? h("div", { class: "key-form" },
        h("button", { type: "button", class: "btn ghost", disabled: s.login && s.login.state === "running" ? true : null,
          onclick: () => signIn(s.key) }, s.codex_signed_in ? "Sign in to Codex again" : "Sign in with Codex")) : null));
    const where = st.claude
      ? "Wire CLI sessions here run on Claude Code. Sign-ins are yours: Claude Code keeps them, never the repository or Studio."
      : st.codex
        ? "Wire CLI sessions here run on Codex. Sign-ins are yours: Codex keeps them, never the repository or Studio."
        : "Neither Claude Code nor Codex is installed here, so Studio cannot check or start a sign-in.";
    body.replaceChildren(
      h("section", { class: "card" },
        h("p", { style: "margin:0" }, mine.length
          ? `This engagement uses ${mine.length} MCP server${mine.length === 1 ? "" : "s"} (${st.file}).`
          : `This engagement uses no MCP servers yet (${st.file}).`),
        h("p", { class: "muted", style: "margin:8px 0 0" }, where),
        h("p", { class: "muted", style: "margin:8px 0 0" },
          "To add or remove a server for the whole team, use the + menu in the Wire CLI box. The change is written to the file above; commit it so the team shares the list."),
        mine.length && (st.claude || st.codex) ? h("div", { class: "key-form" },
          h("button", { type: "button", class: "btn ghost", onclick: (ev) => { ev.target.disabled = true; ev.target.textContent = "Checking…"; load(true); } },
            st.checked ? "Check again" : "Check sign-ins"),
          st.claude ? h("span", { class: "muted" }, "Starts Claude Code for a few seconds to see what a Wire CLI run would see. No model is used.") : null) : null),
      ...rows,
      st.claude ? h("section", { class: "card" },
        h("h3", { class: "key-title" }, "Sign in with Claude Code"),
        h("p", { class: "muted", style: "margin:0 0 8px" },
          "Open Claude Code in this repository, run /mcp and choose the server (plugin:wire:<name> for the Wire plugin's servers). Then use Check sign-ins above."),
        claudeMcp()) : null);
  }
  load(false);
}

// /mcp is a Claude Code command: Run in Claude Code and Copy only (no Wire CLI).
function claudeMcp() {
  const out = h("div", {});
  return h("div", {},
    h("div", { class: "directive" }, "/mcp"),
    h("div", { class: "key-form" },
      h("button", { type: "button", class: "btn", onclick: () => runInClaude("/mcp", out) }, "Run in Claude Code"),
      h("button", { type: "button", class: "btn ghost", onclick: () => copy("/mcp") }, "Copy")),
    out);
}

function viewMachine(body) {
  const update = h("div", { role: "status" });
  async function checkUpdate(ev) {
    ev.target.disabled = true;
    update.replaceChildren(h("span", { class: "muted" }, "Checking GitHub for a newer release…"));
    try {
      const r = await keysApi("/api/settings/update");
      update.replaceChildren(...r.lines.map((ln) => h("p", { class: r.ok ? "muted" : "error", style: "margin:8px 0 0" }, ln)));
    } catch (e) { update.replaceChildren(h("div", { class: "error", style: "margin-top:8px" }, String(e.message || e))); }
    finally { ev.target.disabled = false; }
  }
  body.replaceChildren(h("p", { class: "muted" }, "Checking this machine…"));
  keysApi("/api/settings/machine").then((r) => {
    body.replaceChildren(
      h("section", { class: "card" },
        h("h3", { class: "key-title" }, `Wire CLI ${r.version}`),
        h("p", { class: "muted", style: "margin:0" }, "What this machine can run, as `doctor` in the Wire CLI reports it. Key values are never shown."),
        h("div", { class: "table-wrap", style: "margin-top:12px" }, h("table", {},
          h("tbody", {}, ...Object.entries(r.rows).map(([k, v]) => h("tr", {}, h("td", { class: "mono" }, k), h("td", {}, v))))))),
      h("section", { class: "card" },
        h("h3", { class: "key-title" }, "Updates"),
        h("p", { class: "muted", style: "margin:0" }, "Studio and the Wire CLI ship in the Wire plugin. Update the plugin with /plugin update wire@rittman-analytics in Claude Code; a standalone Wire CLI with wire update."),
        h("div", { class: "key-form" }, h("button", { type: "button", class: "btn ghost", onclick: checkUpdate }, "Check for a newer Wire CLI")),
        update));
  }).catch((e) => body.replaceChildren(h("div", { class: "error" }, String(e.message || e))));
}

const SETTINGS_SECTIONS = [
  ["keys", "API keys", viewKeys],
  ["mcp", "MCP sign-ins", viewMcp],
  ["machine", "This machine", viewMachine],
];

function viewSettings() {
  // each section loads on its own: This machine runs `wire doctor`, which takes a few seconds
  const sections = SETTINGS_SECTIONS.map(([id, title, fill]) => {
    const body = h("div", { class: "settings-body" }, h("p", { class: "muted" }, "Loading…"));
    fill(body);
    return h("section", { class: "settings-section", id: `settings-${id}`, "aria-labelledby": `settings-${id}-h` },
      h("h2", { class: "settings-title", id: `settings-${id}-h` }, title), body);
  });
  const jump = h("nav", { class: "settings-jump", "aria-label": "Settings sections" },
    ...SETTINGS_SECTIONS.map(([id, title]) => h("button", { type: "button", class: "btn ghost",
      onclick: () => document.getElementById(`settings-${id}`).scrollIntoView({ behavior: "smooth", block: "start" }) }, title)));
  return h("div", {}, header([summary ? summary.repo : "", h("span", { class: "tag" }, "this workstation")], "Settings"),
    h("div", { class: "content" }, jump, ...sections));
}
