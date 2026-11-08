# The fork decision (item 6 of wire#408): draft

Written during the concept run on 4 November 2026. The numbers come from
`CONCEPT_RUN.md`; this document says what they mean for the three routes and
what the Codex fork costs in practice, measured by doing it once.

## What was built overnight

| Piece | State |
|---|---|
| Wire CLI (`wire`, the session, `run`, typed commands, Studio's resolver, the record) | On `feature/wire-cli-5.0`, 143 CLI checks, full suite green |
| Harnesses | `codex` (OpenAI key or ChatGPT login, or LM Studio for a local model), `claude` (Claude Code with an API key), `codex` plus the bridge (Claude without Claude Code) |
| Installer | `install-wire.sh` (curl), `Formula/wire.rb` (brew tap on the public `wire-plugin` repo), `package-cli.sh`, `publish-cli-release.sh`; tested by installing into a scratch home |
| Fork | `rittmananalytics/codex`, branch `wire/brand`: the welcome screen draws the Wire mark, the session title reads "Wire (Codex v...)"; built from source with Rust 1.95; packaged as `wire-agent` and run as the Wire harness in a smoke test (the welcome screen itself is not yet verified by eye: the renderer compiles and its snapshot tests are expected to differ) |

## The three routes, after the run

**Unforked Codex plus the Python CLI** is what the concept run used. It
runs real Wire specs on three model families with the record kept correctly
and the lane rules enforced by the hooks and the CLI's own consolidation.
Every defect found during the run was in Wire's own code (the hook's
redirect scan, lane logs overwritten, rulings missing from the brief), not in
the harness. The one thing it cannot do is run without a harness installed.

**The fork** adds a binary of our own. What it bought in one night: the
startup screen and the title. What it did not need to buy: provider support,
because the bridge gives Claude through the Responses API with prompt
caching, and the keys, hooks, skills and agents all work from the repository
without a fork. What it costs: a Rust workspace of 133 crates, a toolchain
pin (1.95.0), a clean release build of 11m 26s on an M5 Max (the first attempt
lost 26 minutes to a dependency fetch that needed cargo pointed at the system
git), a 374 MB binary (264 MB stripped, 106 MB compressed) against the 2 MB
CLI package, and a rebase against an upstream that pushed commits the same
day. The tests and
snapshots that name "OpenAI Codex" break on the first branding change.

**Wire's own loop on the vendor SDKs** was not built. The run gives no reason
to: the harnesses did the agent work well enough that every failure traced
back to Wire's own code, and the sandboxing and hooks they provide would have
to be rebuilt.

## What task B added

Task B (regenerate the dbt models) found two things task A could not. First,
the harnesses are not where the risk is: all three ran a 72 KB spec to
completion or to a correct stop, and every refusal that was wrong traced to
Wire's hook or brief parser, now fixed. Second, the models differ in judgement
where the specification and the conventions disagree: Claude kept the
approved names and accepted the lint findings, the OpenAI lane stopped and
asked, the local model renamed everything to the convention. That is a
question for Wire's specs (which should say which wins) and for the eval
in item 5's successor, not for the harness choice.

## Recommendation

Ship the unforked route as the product: the installer with the Python CLI,
`codex` from npm or the standalone `wire-agent` binary built from the
branded fork when a release ships it, the `claude` harness for Claude Code
users, and the bridge for Claude without Claude Code. Keep the fork to
branding only, rebuilt from upstream tags rather than rebased continuously,
so its cost is one build per Wire release, not a standing engineering line.
Revisit a deeper fork only if a Wire tool needs to live inside the agent
process (compact dbt output as dbt's Wizard does), which nothing in the
concept run required.

## Open

- Task B numbers (dbt generation: code output, lint findings, coverage).
- The standalone binary's build time and size, and notarisation for macOS
  installs outside the terminal.
- Claude through the bridge measured on a lane (a fourth leg of task A).
