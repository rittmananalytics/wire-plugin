# Wire Framework v3.4.0 — Engagement Planning Feature Brief

**Branch:** `feature/engagement-planning`
**Prepared:** 2026-03-23
**Status:** For review — revised after call with Olivier Dupuis, 23 March 2026

---

## 1. Context: republicofdata-io/lab

The `lab` repo is a private Claude Code plugin authored by Olivier Dupuis (Rittman Analytics). It operates at two levels above Wire's current scope: **engagement planning** (deciding what to build and when) and **session productivity** (helping consultants start and end working sessions with full project context).

### 1.1 Shape Up engagement planning

Lab implements Basecamp's **Shape Up methodology** for scoping work before committing to it. The core idea is fixed time, variable scope — you define an *appetite* (1–2 weeks or 6 weeks) and shape a rough-but-solved solution before betting the team's time on it.

The planning workflow produces:

- **Pitch document** — 10 sections: problem, appetite, solution sketch (fat marker, not pixel-perfect), rabbit holes to avoid, hard no-gos, risks, success criteria, timeline, and "the bet" (why this is worth doing now)
- **Release brief** — formal commitment document with deliverable checkboxes and constraints
- **Sprint plan** — epics → stories → tasks with point estimates (1/2/3/5/8 scale, no 13-point stories allowed — must be broken down)

Releases are tracked in `.wire/releases/<NN>-<name>/` folders with a lifecycle state machine: Draft → Ready → Betting → Active → Completed.

### 1.2 Session lifecycle

Two commands that bookend a working session on any engagement:

- **`/lab:session:start`** — enters Plan Mode, asks what you want to accomplish, silently scans the project's status and recent research, then proposes a focused 3–5 step session plan for approval before any work begins
- **`/lab:session:end`** — summarises what was accomplished, records it in the project's status tracker, suggests the focus for the next session

### 1.3 Research persistence

A proactive skill that fires when Claude is about to perform technical research. Rather than discarding findings at the end of a conversation, it saves structured summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/`. Future sessions check this store before re-doing research, and `session:start` surfaces relevant prior findings automatically.

### 1.4 Autonomous delivery pipeline

An experimental two-role system for autonomous code delivery:

- **Planner role** — reads a release brief, explores the codebase, generates a detailed plan file (approach, file changes, tests, acceptance criteria, risks), commits it to a `plan/<slug>` branch, and awaits human approval
- **Engineer role** — picks up an approved plan, implements it on a `crew/<slug>` branch, runs quality gates (lint + test, max 3 attempts), and opens a PR

A `scripts/runner.sh` cron script drives this autonomously.

### 1.5 Other capabilities

- **PKM/Obsidian integration** — retrieves client and product context from a personal knowledge management vault; auto-activates when client names are mentioned
- **Daily/weekly ritual commands** — `daily-briefing`, `end-of-day`, `weekly-strategy-primer`, `journal:daily-summary`
- **Agent teams** — experimental suggestion of parallel Claude Code sessions when a session has 3+ independent workstreams

---

## 2. Decisions from 23 March call with Olivier Dupuis

Four structural decisions were agreed in the call that materially change the original proposal:

### 2.1 Rename "projects" to "releases"

Wire's delivery units are now called **releases** throughout — across the framework specs, all documentation, CLI commands, status templates, and Wire Studio. The term "project" is retired. This aligns with Shape Up terminology and how the RA team already describes scoped units of work in practice.

### 2.2 Two-tier engagement structure

Every Wire engagement uses a **two-tier structure**. Even the simplest engagement has context that belongs to the engagement as a whole — SOW, call transcripts, stakeholders, current-state architecture — which doesn't belong to any specific release. And in practice there is always more than one release, even if only one is planned at the outset.

**Engagement** (top level — one per client engagement)
- Holds engagement-wide context that spans all releases: SOW, call transcripts, org charts, roles and responsibilities, current-state architecture, stakeholder list
- These artifacts don't belong to any specific release — they belong to the engagement as a whole
- Represented by an `engagement/` directory within `.wire/`

**Releases** (second level — one or more per engagement)
- Each release is a scoped, time-boxed unit of work
- The existing Wire release types (full_platform, pipeline_only, dbt_development, etc.) sit here
- A new `discovery` release type is added (see 2.3 below)

```
.wire/
  engagement/
    context.md          ← engagement overview, objectives, key stakeholders
    sow.md              ← statement of work (copied in at engagement setup)
    calls/              ← call transcripts and notes
    org/                ← org charts, roles and responsibilities
  releases/
    01-discovery/       ← new release type
      status.md
      planning/
        problem_definition.md
        pitch.md
        release_brief.md
        sprint_plan.md
    02-data-foundation/ ← existing release types sit here
      status.md
      requirements/
      design/
      development/
      ...
  research/             ← persisted research (universal, engagement-wide)
    sessions/
```

### 2.3 Discovery as a release type, not a standalone project type

The original proposal treated engagement planning as a new standalone project type sitting alongside `full_platform`, `pipeline_only` etc. The call clarified this is better modelled as a **release type**.

Discovery is just another kind of release — it has a different workflow and different outputs, but it follows the same structural pattern. The specific characteristic of a discovery release is that **it ends by generating one or more subsequent delivery releases**, rather than by generating code or dashboards.

This means:
- Release types include: `discovery` (new), `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement` (all existing)
- The `discovery` release type has its own artifact workflow (problem definition → pitch → release brief → sprint plan)
- At the end of a discovery release, a "Create delivery releases" action generates the release folder structure and initial status files for each planned downstream release

### 2.4 Repo setup at engagement creation

During `wire:new`, the user is asked what repo they are currently working in. There are two cases:

**Option A — Current repo is both the delivery repo and the client code repo (default)**
The `.wire/` folder lives directly in the client's code repo. This is the simplest setup and the default for straightforward engagements. No additional configuration is needed.

```
client-code-repo/       ← user is working in this repo
  .wire/                ← Wire artifacts live here
  models/
  ...
```

**Option B — Current repo is a dedicated delivery repo; client code lives elsewhere**
The user is working in a repo that is exclusively for Wire delivery artifacts (not the client's code repo). Wire asks for the details of the client code repo — its GitHub URL, local path, and default branch — in the same way Wire Studio asks the user to specify a repo to clone and open. This information is stored in `engagement/context.md` so that Wire commands can reference the client codebase when needed (e.g. when generating dbt models or pipeline code).

```
client-wire-delivery/   ← user is working in this repo
  .wire/                ← Wire artifacts live here

client-code-repo/       ← separate repo; details stored in engagement/context.md
  models/
  ...
```

This is appropriate for regulated clients (e.g. Liberus, where adding a `.wire/` folder to their code repo is not acceptable) or clients with multiple code repos (e.g. Client M) where it is unclear which repo should hold the Wire artifacts.

---

## 3. What we will incorporate, and why

### 3.1 Session lifecycle commands — universal

`/wire:session:start` and `/wire:session:end` will be added as **universal commands**, available for every release type. They are not tied to the delivery lifecycle of any specific release — they govern how a consultant opens and closes a working session.

**`session:start`** enters Plan Mode, asks what the consultant wants to accomplish, silently scans the current release's `status.md` and the engagement-level research store, then proposes a focused 3–5 step session plan for approval before any work begins.

**`session:end`** summarises what was accomplished, appends a row to the session history table in `status.md`, and suggests the focus for the next session.

**Why:** Consultants context-switch between multiple client engagements daily. Without a session start ritual, Claude begins each conversation cold — re-reading files, re-establishing context, potentially repeating research. `session:start` compresses this to seconds and ensures the first action in any session is intentional and grounded in the current state.

**Not doing:** Personal ritual commands (`daily-briefing`, `end-of-day`, `weekly-strategy-primer`) — personal productivity tools, not consulting delivery tooling.

### 3.2 Research persistence skill — universal

A proactive skill that auto-activates during technical research tasks. Findings are saved to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md` at the engagement level (not within any individual release), checked before new research is initiated, and surfaced automatically by `session:start`.

**Why:** On longer engagements, research about client systems, APIs, and architectural decisions is repeated unnecessarily across sessions and across releases. Persisting it at engagement level means it is available to all releases and all team members on that engagement.

**Not doing:** PKM/Obsidian integration — tied to one consultant's personal setup; not portable across a consulting team.

### 3.3 Discovery release type — new release type

A new release type representing the pre-delivery scoping and discovery phase of a new engagement. It produces the documents that justify and define the subsequent delivery releases.

**Artifact workflow:**

```
Problem Definition → Pitch → Release Brief → Sprint Plan
```

All four artifacts follow the standard Wire generate/validate/review pattern.

**End action:** At the completion of the sprint plan, a `wire:release:spawn` command reads the release brief and creates the folder structure and initial `status.md` files for each planned downstream delivery release. This is the bridge between the discovery release and the delivery releases it produces.

**Why a release type and not a standalone project type:** Discovery is structurally identical to any other release — it has a brief, a plan, a status tracker, and a finite time budget. Treating it as a release type keeps the framework consistent and avoids a two-tier taxonomy that would complicate both the codebase and the user experience.

### 3.4 Engagement-level structure and setup

The `wire:new` command will be extended with the following question flow:

1. **Is the current repo the client code repo, or a dedicated delivery repo?**
   - *Combined (client + delivery)* → `.wire/` goes here, no further repo config needed
   - *Dedicated delivery repo* → ask for client repo GitHub URL, local path, and default branch (stored in `engagement/context.md`)

2. **Where should engagement-wide artifacts be stored?**
   - Call transcripts, org charts, SOW etc. default to `engagement/` (engagement-wide)
   - Ask per artifact type whether it is engagement-wide or specific to a release

3. Copy any provided SOW or context documents into `engagement/`

### 3.5 Autonomous delivery pipeline — future (v3.5.0)

The Planner/Engineer role separation is a cleaner version of Wire's existing `/wire:autopilot`. Deferred to v3.5.0 — most useful once `discovery` releases are producing the briefs that feed the Planner role.

---

## 4. What we will not incorporate, and why

| Lab capability | Decision | Reason |
|---|---|---|
| PKM/Obsidian integration | Exclude | Personal knowledge management tool tied to one consultant's Obsidian vault; not portable across a consulting team |
| Daily/weekly ritual commands | Exclude | Personal productivity tools (`daily-briefing`, `end-of-day`, `weekly-strategy-primer`); not consulting delivery tooling |
| Agent teams | Exclude | Experimental multi-process Claude Code session orchestration; too early and unstable for production use |
| Journal commands | Exclude | Personal journalling; not delivery-relevant |

---

## 5. Open questions before implementation

All open questions resolved.

| # | Question | Resolution |
|---|---|---|
| 1 | **Delivery repo naming convention** | `<client_name>-delivery` — the user is expected to have already named and created the repo before running `wire:new` within it |
| 2 | **Engagement-level vs release-level artifact storage** | Asked as part of the `wire:new` question flow, but only when the user has selected the two-tier (multi-release engagement) option |

---

## 6. Implementation plan

### 6.1 Scope

**v3.4.0** delivers five things:
1. Rename "project" → "release" throughout all framework specs, docs, templates, and Wire Studio
2. `session:start` and `session:end` commands (universal)
3. Research persistence skill (universal, engagement-level storage)
4. `discovery` release type with four artifacts
5. Two-tier engagement structure (standard for all engagements) with repo setup options at `wire:new`

### 6.2 New files

#### Specs

```
wire/specs/session/start.md
wire/specs/session/end.md
wire/specs/discovery/problem_definition/generate.md
wire/specs/discovery/problem_definition/validate.md
wire/specs/discovery/problem_definition/review.md
wire/specs/discovery/pitch/generate.md
wire/specs/discovery/pitch/validate.md
wire/specs/discovery/pitch/review.md
wire/specs/discovery/release_brief/generate.md
wire/specs/discovery/release_brief/validate.md
wire/specs/discovery/release_brief/review.md
wire/specs/discovery/sprint_plan/generate.md
wire/specs/discovery/sprint_plan/validate.md
wire/specs/discovery/sprint_plan/review.md
wire/specs/utils/release_spawn.md       ← creates downstream release folders from a brief
```

#### Skills

```
wire/skills/research/SKILL.md
```

#### Templates

```
wire/TEMPLATES/engagement-context-template.md   ← engagement/context.md template
wire/TEMPLATES/discovery-status-template.md     ← status.md for discovery releases
```

### 6.3 New commands (15 total)

| Command | Description |
|---|---|
| `/wire:session:start` | Enter Plan Mode, gather release and engagement context, propose session plan |
| `/wire:session:end` | Summarise session, update release status.md, suggest next focus |
| `/wire:problem-definition:generate <release>` | Generate structured problem framing |
| `/wire:problem-definition:validate <release>` | Validate problem definition completeness |
| `/wire:problem-definition:review <release>` | Review problem definition with stakeholders |
| `/wire:pitch:generate <release>` | Generate 10-section Shape Up pitch |
| `/wire:pitch:validate <release>` | Validate pitch structure and completeness |
| `/wire:pitch:review <release>` | Review pitch with stakeholders, record appetite decision |
| `/wire:release-brief:generate <release>` | Generate formal release brief from approved pitch |
| `/wire:release-brief:validate <release>` | Validate brief against pitch, check deliverable clarity |
| `/wire:release-brief:review <release>` | Review brief with client, record sign-off |
| `/wire:sprint-plan:generate <release>` | Generate sprint breakdown with point estimates |
| `/wire:sprint-plan:validate <release>` | Validate point totals against appetite budget |
| `/wire:sprint-plan:review <release>` | Review sprint plan with delivery team |
| `/wire:release:spawn <release>` | Create downstream delivery release folders from an approved release brief |

### 6.4 Modified files

| File | Change |
|---|---|
| `wire/specs/utils/new.md` | Extend `wire:new` to ask: new engagement or additional release; in-client-repo or separate delivery repo; copy SOW into `engagement/` |
| `wire/scripts/build-packages.sh` | Add 15 new commands; add research skill; add `discovery` release type |
| `wire/packaging/claude-plugin/CLAUDE.md` | Document session commands, research skill, discovery release type, two-tier structure |
| `wire/TEMPLATES/status-template.md` | Add `session_history` table (universal); add engagement context pointer |
| `README.md` | Add `discovery` to release types table; add session commands and research skill; document two-tier structure and repo options |
| `USER_GUIDE.md` | Add Section 16: Engagement Setup; add Section 17: Discovery Release; add session lifecycle to every release type walkthrough |
| `CHANGELOG.md` | Add `[3.4.0]` entry |
| `RELEASE_NOTES.md` | Add v3.4.0 release notes at top |
| `wire/packaging/claude-plugin/.claude-plugin/plugin.json` | Bump to `3.4.0` |
| `wire/packaging/gemini-extension/gemini-extension.json` | Bump to `1.3.0` |

### 6.5 Wire Studio changes

#### Release types in `artifacts.ts`

Add `discovery` as a new release type with four artifacts in a linear dependency chain:

```
problem_definition → pitch → release_brief → sprint_plan
```

Layout: single column, four rows. The graph is deliberately simple — discovery is a linear process.

#### Engagement-level view

Wire Studio gains an **Engagement** view above the release graph. It shows:
- Engagement name, client, and start date
- Repo storage mode (in-client-repo or separate delivery repo)
- List of all releases with their type, current status, and completion percentage
- Link to open `engagement/context.md` and `engagement/sow.md`

This is the first screen a consultant sees when opening a Wire engagement in Studio, before drilling into a specific release.

#### Release type selector at new engagement setup

The New Engagement dialog (currently New Project) asks:
1. Engagement name and client
2. First release type (typically `discovery` for a new engagement, or any delivery type if joining mid-stream)
3. Repo storage: **In client repo** (default) or **Separate delivery repo**

#### Session toolbar

A persistent session status bar visible at the top of any open release (all release types). Contains:
- Session status indicator: **Idle** / **Active** (with elapsed time)
- **Start Session** button → `/wire:session:start`
- **End Session** button → `/wire:session:end` (enabled only when a session is active)
- Session history accessible via the release's status.md view

#### "Spawn delivery releases" action

On the `sprint_plan` node in the `discovery` release graph: a context menu item — **"Spawn delivery releases…"** — that runs `/wire:release:spawn`, reads the approved release brief, and creates the folder structure and initial `status.md` files for each planned downstream delivery release. The new releases then appear in the Engagement view.

### 6.6 Discovery release artifact graph

```
┌──────────────────────┐
│  Problem Definition  │  generate / validate / review
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│        Pitch         │  generate / validate / review
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│    Release Brief     │  generate / validate / review
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│     Sprint Plan      │  generate / validate / review
│                      │  [Spawn delivery releases →]
└──────────────────────┘
```

### 6.7 `status.md` additions (universal — all release types)

A `session_history` section added to the status template, appended to by `session:end` after each session:

```markdown
## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
```

### 6.8 Version bumps

| Package | Current | v3.4.0 |
|---|---|---|
| Claude Code plugin | 3.3.2 | 3.4.0 |
| Gemini CLI extension | 1.2.2 | 1.3.0 |

A minor version increment (3.3.x → 3.4.0) is warranted because this release introduces a new structural layer to the framework — the two-tier engagement model, a new release type (`discovery`), universal session lifecycle commands, and a framework-wide rename — rather than adding isolated features within the existing model. These changes affect the setup flow, the `.wire/` folder structure, Wire Studio's top-level navigation, and every piece of documentation. Patch releases (3.3.x) are for additive commands or skills within the existing architecture; 3.4.0 represents a meaningful architectural evolution.

---

## 7. Out of scope for v3.4.0

- **`/wire:roadmap`** — cross-release roadmap view across an engagement; target v3.5.0 once discovery releases are in use and the two-tier structure is validated
- **Autonomous delivery pipeline** (Planner/Engineer roles) — depends on discovery releases producing the briefs that feed the Planner; target v3.5.0
- **Release lifecycle state machine** (Draft → Betting → Active → Completed) — valuable once the team is using discovery releases regularly and wants to track release status; target v3.5.0
