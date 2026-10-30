---
description: List the client's related repositories and look up code in them, read only, cited by repo and commit
argument-hint: list, refresh [<id>], find <text> [--repo <id>] [--path <glob>], add <github_url> --id <id> --role <role>, remove <id>, or check
---

# List the client's related repositories and look up code in them, read only, cited by repo and commit

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'utils-repos',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: utility
artifact: repos
domain: utils
release_types: []
action_type: utility
logs_execution: false
description: List the client's related repositories and look up code in them, read only, cited by repo and commit
argument-hint: "<list | refresh [<id>] | find <text> [--repo <id>] [--path <glob>] | add <github_url> --id <id> --role <role> | remove <id> | check>"

---

# Related Repos Command

## Purpose

A client's work often spans several repositories: an Airflow repo lands the
sources and schedules the runs, a dbt repo models them, a LookML repo serves
them. Work in one needs context from the others. This command lets a session
in one repository read the client's other repositories, read only, and cite
what it read by repo and commit (wire#381).

The engagement lists the related repos once, in the `related_repos:` block of
`.wire/engagement/context.md`. Where each person's copy is lives in
`.wire/local/repos.yml`, which is git-ignored. A repo with no local copy is
cloned blobless to `~/.wire/repos/<org>/<repo>/` with the person's own git
access. The schema is `wire/schemas/related-repos-schema.md`.

`client_repo:` keeps working: it is read as one entry, id `client_repo`, role
`code`.

## Usage

```bash
/wire:utils-repos list                                  # each repo: role, commit, fetch age, state
/wire:utils-repos refresh                               # clone or fetch every repo
/wire:utils-repos refresh airflow                       # one repo
/wire:utils-repos find orders_raw                       # search every repo at its recorded commit
/wire:utils-repos find orders_raw --repo airflow --path 'dags_*/**'
/wire:utils-repos add https://github.com/<org>/<repo> --id airflow --role orchestration --paths 'dags_*/,plugins/'
/wire:utils-repos remove airflow
/wire:utils-repos check                                 # check the list and the local file
```

Not scoped to a release. Run in the engagement repository.

## Workflow

Every step runs `python3 <wire>/scripts/related_repos.py <sub-command>` in the
engagement repository and shows its output. The script is plain Python and
git; it makes no AI call and no network call except `git clone` and
`git fetch`.

### list

Run `related_repos.py list`. Show its table: repo id, role, lookup setting,
short commit, fetch age, state (`ready`, `stale`, `unreachable`,
`not refreshed`, `not fetched`) and where the local copy is. `list` reads
only what is on disk.

If a repo is `not fetched` or older than a day, offer `refresh`. Do not run it
unasked.

### refresh

Run `related_repos.py refresh [<id>]`. For each repo it fetches the default
branch, or clones it the first time, and records the commit it read in
`.wire/local/repos_state.json`. Report one line per repo.

- **Unreachable:** say so with git's reason and carry on with the others. The
  usual cause is that the person has no access to that repository. Never ask
  for a password or token, never suggest putting one in the URL, and never
  store one. Point to `gh auth login` (or the person's own git setup) if the
  reason is an authentication error.
- **Stale:** the fetch failed but an earlier one worked. Lookups still read
  the earlier commit; say which.

### find

Run `related_repos.py find <text> [--repo <id>] [--path <glob>] [--regex]`.
It searches each local copy with `git grep` at the commit the last refresh
recorded, within the entry's `paths` unless `--path` is given, and prints one
line per hit: `<id>@<short commit>:<path>:<line>  <text>`.

Present the hits grouped by repo, with the citation for each. When you use a
finding in an answer, an artifact, an iteration file or a PR body, cite it as
`<id>@<short commit>:<path>`. To read a whole file a hit names, read it at the
same commit: `git -C <local copy> show <commit>:<path>`. Never read the
working tree of a person's clone: it may hold unfinished work on another
branch.

### add

1. Run `related_repos.py add <github_url> --id <id> --role <role> [--branch B]
   [--paths a,b] [--description T] [--lookup L]` without `--yes`. It shows the
   entry it would add as a diff of `context.md` and writes nothing. It refuses
   an id or URL already listed, and a URL with a user or token in it.
2. Ask: **Add / Change / Cancel**. Suggest a role from the repository's
   contents if the person did not give one (`dbt_project.yml`: `dbt`; a `dags`
   folder: `orchestration`; `*.lkml`: `lookml`).
3. On **Add**, run the same command with `--yes`, then commit
   `.wire/engagement/context.md` on the current branch
   (`specs/utils/commit.md`), message `repos: add <id>`.
4. Offer `refresh <id>`.

If the person already has a clone, offer to write its path to
`.wire/local/repos.yml` (`<id>: <path>`). That file is personal and is not
committed.

### remove

1. Run `related_repos.py remove <id>` without `--yes`: it shows the diff.
2. Ask: **Remove / Cancel**. On **Remove**, run it with `--yes` and commit
   `context.md`, message `repos: remove <id>`.
3. Any local copy is left where it is. Say where it is, so the person can
   delete it if they want to.

`client_repo` cannot be removed this way; it is edited by hand.

### check

Run `related_repos.py check`. It reports ids that are missing, malformed or
listed twice, unknown roles and lookup values, unknown fields, a URL listed
twice or holding a credential, lines in `.wire/local/repos.yml` for repos not
listed, and `.wire/local/` not being git-ignored. Exit 1 on any problem.
Offer to fix each one; fix none unasked.

## Rules

1. **Read only.** Never commit, push, check out, branch, merge, or write a
   file in a related repo, by script or by hand. A change a related repo needs
   is a separate piece of work in that repository: say what it is and where,
   and stop.
2. **On request.** Look in a related repo only when the person asks, or when
   a command offers a lookup and the person accepts. The `lookup` setting on
   an entry is `on_request` by default; `offer` lets commands offer; `auto` is
   reserved and treated as `offer`.
3. **Cite.** Every finding taken from a related repo carries its citation,
   `<id>@<short commit>:<path>`, wherever it is used.
4. **No credentials.** Git uses the person's own access. Nothing asks for,
   writes or stores a credential.
5. **Nothing private leaks.** The entries are client data in the client's
   repository.
6. Plain text, no emojis.

## Gemini CLI

The same spec and script. No change.

Execute the complete workflow as specified above.
