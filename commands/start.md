---
description: Session entry point and Wire co-pilot — orients new users, surfaces the right next action, and helps navigating consultants pick up where they left off
argument-hint: [new/resume/explain]
---

# Session entry point and Wire co-pilot — orients new users, surfaces the right next action, and helps navigating consultants pick up where they left off

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Session entry point and Wire co-pilot — orients new users, surfaces the right next action, and helps navigating consultants pick up where they left off
argument-hint: [new|resume|explain]
---

# Wire Start

## Purpose

`/wire:start` is both the session entry point and the Wire co-pilot. It serves three audiences:

1. **New users** — consultants who have just installed Wire and don't yet understand the framework, release types, or workflow lifecycle
2. **Returning users** — experienced consultants starting a session who need to see what's in flight across all projects and pick what to work on
3. **Navigating users** — consultants who know Wire but aren't sure what to run next, don't understand why certain steps exist, or have lost track of where they are in a project

It is the answer to "I don't know what to do next." It reads project state, asks a small number of focused questions, and produces a specific ranked list of next actions — not a description of the framework in the abstract, but the exact commands to run right now and the reason each one matters.

## When to Run This Command

- You've just installed Wire and don't know where to start
- You're starting a new session and want to see what's in flight
- You've completed an artifact and aren't sure what comes next
- You're about to do something manually (write a doc, create a Jira ticket, send an update to the client) and want to know if Wire has a command for it
- You haven't used Wire in a few days and need to reorient
- You're switching to a different client repo and need to reorient quickly
- You're preparing to introduce Wire to a new team or client
- You think a step (validate, review) is redundant and want to understand why it exists

---

## Phase 1: Plugin Health Check

**This phase runs before anything else, every time.** Plugin version problems are the single most common cause of lost time — outdated versions are missing commands, and the install/update process is non-obvious. Do not skip this phase even if the user seems experienced.

### Step 1.1: Detect Installation State

Run in sequence:

```bash
# Check if Wire plugin is installed at all
ls ~/.claude/plugins/wire/ 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"

# Get installed version (if installed)
cat ~/.claude/plugins/wire/VERSION 2>/dev/null || echo "UNKNOWN"

# Detect legacy project structure (old Gemini/.dp-era layout)
ls .dp/ 2>/dev/null && echo "LEGACY_DP" || echo "NO_LEGACY"

# Get the canonical latest version from the repo
cat "$(git rev-parse --show-toplevel 2>/dev/null)/VERSION" 2>/dev/null \
  || curl -sf https://raw.githubusercontent.com/rittmananalytics/wire-plugin/main/VERSION 2>/dev/null \
  || echo "UNKNOWN_LATEST"
```

### Step 1.2: Evaluate and Output Health Status

Based on the results, output one of the following blocks — always as the very first output, before any other content.

---

**Case A — Wire is not installed:**

```
╔══════════════════════════════════════════════════════════════════╗
║  WIRE NOT INSTALLED                                              ║
╚══════════════════════════════════════════════════════════════════╝

Wire is not installed. Install it now with these three commands
(run each one, wait for it to complete before running the next):

  Step 1:  /plugin marketplace add rittmananalytics/wire-plugin
  Step 2:  /plugin install wire@rittman-analytics
  Step 3:  /reload-plugins

After Step 3, re-run /wire:start and continue from here.

⚠️  Common mistake: running all three commands at once, or skipping
    /reload-plugins. Each step must complete before the next one runs.
    If /plugin install reports "already installed", still run /reload-plugins.
```

**Stop. Do not proceed until the user confirms Wire is installed and /reload-plugins has been run.**

---

**Case B — Wire is installed, version is outdated or unknown:**

```
╔══════════════════════════════════════════════════════════════════╗
║  WIRE UPDATE REQUIRED                                            ║
╚══════════════════════════════════════════════════════════════════╝

Installed version:  [installed_version or "unknown"]
Latest version:     [latest_version or "check GitHub"]

An outdated Wire plugin may be missing commands referenced below.
Update now (takes ~60 seconds):

  Step 1:  /plugins
           → navigate to Marketplaces
           → highlight Wire → press U (update marketplace entry)

  Step 2:  Still in /plugins
           → navigate to Installed
           → highlight Wire → press Enter → press U (update plugin files)

  Step 3:  /reload-plugins

  Step 4:  Re-run /wire:start

If the version still shows as unknown after these steps, or if you
see "command not found" errors for /wire:* commands, exit Claude Code
completely, reopen it, and run /wire:start again.

⚠️  Common symptom of outdated plugin: you type /wire:session-plan
    and it says "command not found", or Wire commands return errors
    about missing spec files.

Would you like to update now, or continue with the outdated version?
(Continuing is fine for navigation — you may hit missing commands.)
```

Wait for response. If user says update now, stop and let them do it. If continue, add a note to the Phase 4 output: `⚠️ Running outdated plugin — some commands may be unavailable.`

---

**Case C — Wire is installed, version is current:**

```
✅  Wire [version] — up to date
```

Output this inline as a single line. Proceed immediately to Phase 2 without pausing.

---

**Case D — Legacy project structure detected (`.dp/` directory exists):**

Output this **in addition to** whichever version case applies above:

```
╔══════════════════════════════════════════════════════════════════╗
║  LEGACY PROJECT STRUCTURE DETECTED                               ║
╚══════════════════════════════════════════════════════════════════╝

This repo has a .dp/ directory — the old Wire project structure
from the Gemini CLI era. Current Wire uses .wire/ instead.

Old command syntax:    /wire:dp-requirements-generate
Current syntax:        /wire:requirements-generate

To migrate this project to the current structure:
  /wire:migrate [project_id]

This migrates your .dp/ data to .wire/ and updates the command
references in your status files. The old .dp/ directory is kept
as a backup until you confirm the migration looks correct.

You can continue using old commands if your plugin is also on the
old version, but mixing old and new syntax will cause errors.

Migrate now? (yes/no)
```

If yes, stop and hand off to `/wire:migrate`. If no, note the legacy state and proceed.

---

## Phase 2: Mode Detection

Determine which mode to enter based on two signals:

**Signal 1 — Argument**

| Argument | Mode |
|----------|------|
| `new` | Force new-user onboarding |
| `resume` | Force navigational mode |
| `explain` | Force explanation mode |
| *(none)* | Auto-detect from repo state |

**Signal 2 — Repo state** (used when no argument provided)

```bash
ls .wire/engagement/context.md 2>/dev/null
ls .wire/releases/ 2>/dev/null
git log --oneline -1 -- .wire/ 2>/dev/null
```

| State | Mode |
|-------|------|
| No `.wire/` directory, no dbt/LookML files | New-user onboarding |
| No `.wire/` directory, but dbt/LookML files present | Suggest `/wire:adopt` (work done outside Wire) |
| `.wire/` exists, last git commit to it is within 14 days | Navigational |
| `.wire/` exists, last commit is older than 14 days | Navigational, with staleness note |
| `.wire/` exists but no `releases/` subfolder | Suggest running `/wire:adopt` first |
| Wire never used in this repo but Wire is installed | New-user onboarding (aware of Wire, hasn't started) |

**Lightweight session-start mode** (applies in navigational mode): If the user has run `/wire:start` in this repo within the past 48 hours and no new changes have been made to `.wire/` since then, skip the intent questions and go directly to the Phase 4 output block with current state summary and top next action. Users switching between multiple repos multiple times per day need fast reorientation, not a full interactive session.

---

## Phase 3A: New-User Onboarding Mode

### Step A1: Welcome and Framework Overview

Output a concise, plain-language overview of Wire. Do not reproduce the full handbook — keep it to what a new user needs to know in the first five minutes.

```
Welcome to Wire — the RA delivery framework.

Wire organises your analytics delivery work into three things:

  Engagement  — the client project as a whole (SOW, calls, context)
  Release     — a scoped unit of work within that project (e.g. "build the sales dashboard")
  Artifact    — a specific deliverable within a release (requirements, data model, mockup, etc.)

Every artifact follows the same three-step cycle:
  /wire:<artifact>-generate   →  creates the artifact from your context and RA standards
  /wire:<artifact>-validate   →  checks it against standards and your requirements
  /wire:<artifact>-review     →  gets sign-off and formally closes the stage

Skipping steps (especially review) means stages never formally close, and you'll keep revisiting the same work.

The framework's most important commands for day-to-day work:
  /wire:new             — start a new release (always start here)
  /wire:playbook-generate — generates your step-by-step plan for a release
  /wire:session-plan    — proposes a focused plan for the current session
  /wire:start           — this command — surfaces what to do next
  /wire:status          — shows where you are across all releases
  /wire:adopt           — catches up Wire to work already done outside the framework
```

### Step A2: First-Time Setup Check

Ask:

```
Are you starting a brand new client engagement, or joining one that's already in progress?

  1. New engagement (no project work has started yet)
  2. Joining an in-progress project (work has been done, possibly some Wire usage)
  3. I just want to understand how Wire works before doing anything
```

Wait for response.

**If (1) — New engagement**: Proceed to Step A3.

**If (2) — Joining in progress**: Explain that `/wire:adopt` will scan the repo and external sources, then ask whether they'd like to run it now. If yes, hand off: `Run /wire:adopt to catch up Wire to the current state of the project. That command will guide you through the rest.` Stop.

**If (3) — Exploration only**: Proceed to Step A5 (explanation mode).

### Step A3: Release Type Selection

Ask:

```
What kind of work is this release for?

  1. dashboard_first    — You're building dashboards and working backwards to the data model
  2. dbt_development    — You're building dbt models and a semantic layer
  3. full_platform      — End-to-end: pipelines, dbt, BI, and enablement
  4. discovery          — Scoped discovery sprint (Shape Up style)
  5. sop_discovery      — RA canonical discovery: stakeholder interviews, findings playback
  6. pipeline_only      — Data pipeline development only
  7. dashboard_extension — New dashboards on an existing working platform
  8. enablement         — Training and documentation only
  9. Not sure

If not sure, answer these:
  → Are you starting with dashboards and mocks, or with requirements and data first?
  → Will you be writing dbt code?
  → Is this a full delivery or just one layer (e.g. just dashboards)?
```

Wait for response. If "not sure", ask the clarifying questions and infer the release type. Present the inferred type and ask for confirmation.

**Output the recommended release type** with a one-sentence explanation of why it fits, then:

```
Next step: run /wire:new

When prompted for release type, choose: [release_type]

After /wire:new completes, run /wire:playbook-generate to get your step-by-step delivery plan.
```

### Step A4: Explain the Three-Step Cycle

Before handing off to `/wire:new`, explain the cycle once — because issues with skipping review or thinking validate is redundant stem from never understanding the purpose of each step:

```
The generate → validate → review cycle:

  Generate  Creates the artifact. The LLM drafts it from your project context, RA templates,
            and any supporting documents you've provided. Output quality depends on input quality.

  Validate  Checks the artifact against Wire standards AND your original requirements.
            This catches LLM drift — cases where the model went off on a tangent, invented
            a metric that wasn't in scope, or ignored a constraint. Validate also builds the
            evidence trail that the artifact was quality-checked. Even when it passes cleanly,
            that pass is recorded.

  Review    Formally closes the stage. This is where client or internal sign-off happens.
            If the artifact is synced to Confluence and the client has left comments, review
            reads those back in and incorporates them. Without completing review, the stage
            stays open — you'll keep revisiting the same artifact because there's no formal
            "done" recorded.

Rule: never start the next artifact until the previous one's review is complete.
If you skip review, stages pile up in uncertain states and iteration never ends.
```

### Step A5: Explanation Mode

If the user wants to understand the framework without starting work, answer questions in plain language. Use the following intent-to-explanation mapping:

| User asks | Explain |
|-----------|---------|
| "What are release types?" | The eight release types and when each fits (table from Step A3) |
| "What's the difference between generate and validate?" | The three-step cycle explanation from Step A4 |
| "Why do I need to do the review step?" | Review is what formally closes a stage. Without it, work piles up in uncertain states. |
| "What is Wire:adopt?" | Catch-up command for in-progress projects. Scans the repo and external sources, maps existing work to Wire artifacts, sets up the `.wire/` structure. |
| "What commands should I run first?" | `/wire:new` → `/wire:playbook-generate` → follow the playbook |
| "How do I know when to raise a PR?" | See Phase 3B Step B5 (PR checkpoints) |
| "What is a release vs. a task?" | See Phase 3B Step B6 (task vs. release) |

---

## Phase 3B: Navigational Mode

Used when Wire is already set up in the repo and the user needs to see what's in flight and decide what to do next.

### Step B1: Load Current State

Read the following in parallel:

1. `.wire/engagement/context.md` — client name, engagement lead, release structure
2. All `.wire/releases/*/status.md` files — artifact states per release
3. The most recently modified `status.md` — treat this as the active release
4. The active release's `planning/*_playbook.md` if present — use as the expected sequence
5. The active release's `execution_log.md` — last 10 rows (most recent first)

Read the installed plugin version:
```bash
cat ~/.claude/plugins/wire/VERSION 2>/dev/null || echo "unknown"
```

From the status files, build a state picture:

```
Active release: [folder] ([release_type])
Wire version: [installed_version]
Artifacts:
  [artifact]: generate=[state] validate=[state] review=[state]
  ...
```

**Execution log summary**: If `execution_log.md` exists, read the last 10 rows. Format them as a compact table for display in the Phase 4 output block (see below). If fewer than 10 rows exist, show all of them. If the file does not exist, show "No activity recorded yet."

Identify:
- The **last completed artifact** (all three steps done: review = approved)
- The **in-progress artifact** (generate done, but validate or review not complete)
- The **blocked artifact** (validate = fail or review = changes_requested)
- The **next artifact** (first one with generate = not_started, whose prerequisites are complete)

**Next Action Logic** — for each artifact, check lifecycle steps in order: `generate → validate → review`

Completion states:
- `generate`: complete = done
- `validate`: pass = done (fail/pending/not_started = incomplete)
- `review`: approved = done (changes_requested/pending/not_started = incomplete)
- `not_applicable`: skip (artifact is out of scope)

The first incomplete step across the sequence becomes the primary "Next Action".

### Step B2: Present Project Overview and Ask Intent

Invoke `/wire:status` (no argument) to present the current project overview, then ask:

```
Current state: [active release] — [N] of [M] artifacts complete

  Last completed: [artifact] ✅
  In progress:    [artifact] — [stage] done, [stage] pending
  Next up:        [artifact]

What would you like to do?

  1. Continue where I left off
  2. I finished something and need to know what comes next
  3. I want to understand what a specific step does before running it
  4. I did work outside Wire and need to bring it in sync
  5. Create a new release or project
  6. Run Wire Autopilot (autonomous end-to-end execution)
  7. I'm not sure / something else
```

Wait for response.

### Step B3: Intent Resolution

Map the user's intent (or free-text response) to a specific recommended action:

| User says or selects | Recommended action |
|---------------------|-------------------|
| Continue / "1" | Run the next pending step on the in-progress artifact |
| Finished something / "2" | Proceed to Step B4 (next-action logic) |
| Want to understand a step / "3" | Proceed to explanation (Step A5 mapping) |
| Did work outside Wire / "4" | Recommend `/wire:adopt` |
| Create new release / "5" | Invoke `/wire:new` to run the interactive project creation workflow |
| Wire Autopilot / "6" | Invoke `/wire:autopilot` — it will ask a small set of clarifying questions, then autonomously generate, validate, and self-review every artifact |
| "What do I do next" (free text) | Proceed to Step B4 |
| "Where am I" (free text) | Run `/wire:status` and present output |
| "I want to create a plan" | Recommend `/wire:session-plan` |
| "I want to raise a PR" | Proceed to Step B5 (PR checkpoint guidance) |
| "Should this be a release?" | Proceed to Step B6 (task vs. release) |
| "The client commented on the doc" | Recommend `/wire:[artifact]-review [release_folder]` |
| "Validate keeps passing but nothing changes" | Explain validate purpose (Step A4) |
| "Do I need to do the review step?" | Explain review purpose (Step A4) |
| "How do I show Wire to a new team?" | Proceed to Step B7 (team intro mode) |
| "I don't know what commands exist" | Output command catalogue (Step B8) |

For any free-text intent not matched above, interpret charitably and map to the closest matching action. If genuinely ambiguous, ask one clarifying question before proceeding.

### Step B4: Next-Action Logic

Determine and present the next action based on artifact state:

**If there is a blocked artifact** (validate = fail or review = changes_requested):

```
⚠️  Blocked artifact: [artifact]
    State: [validate/review] = [fail/changes_requested]

    Before moving forward, resolve this first:
    → /wire:[artifact]-validate [release_folder]    # re-run after fixing the issue
      or
    → /wire:[artifact]-review [release_folder]      # incorporate client feedback and re-generate

    Why this matters: leaving an artifact blocked means the next artifact's prerequisites
    aren't met. You can generate the next one, but it won't be grounded in approved outputs.
```

**If there is an in-progress artifact** (generate = complete, validate or review pending):

```
In progress: [artifact]
  ✅ generate complete
  [pending step] not yet run

Next: /wire:[artifact]-[pending-step] [release_folder]

[If the pending step is validate:]
  This checks the generated output against Wire standards and your project requirements.
  Even a clean pass is worth running — it creates the quality-check evidence trail.

[If the pending step is review:]
  This formally closes the [artifact] stage. Without it, this stage stays open.
  [If Confluence is configured:] Check whether the client has commented on the Confluence page
  before running — their comments will be read back in automatically.
```

**If all artifacts are complete** (all review = approved):

```
✅ All artifacts in [release_folder] are complete.

This release is ready for:
→ PR — raise a pull request to merge [release_folder] branch to main
→ /wire:status — full project status across all releases
→ /wire:new — add a new release to this engagement
```

**If the next artifact is not started**:

```
Next artifact: [artifact]
Prerequisite status: [list prerequisites and their states]

[If all prerequisites approved:]
Ready to start: /wire:[artifact]-generate [release_folder]

[If a prerequisite is pending:]
Before starting [artifact], complete: [prerequisite] → [pending step]
```

### Step B5: PR Checkpoint Guidance

Output when the user asks about raising a PR, or when the guide determines that a PR is the appropriate next action:

```
When to raise a PR in Wire:

  ✅ After the data model artifact is complete (review = approved)
     Reason: the data model defines what gets built downstream. Having it in main
     means the next person starting dbt work has an agreed target.

  ✅ After validate or review catches issues and you've fixed them
     Reason: fixes are reviewable changes — they should be on a PR, not merged silently.

  ✅ After a full release is complete (all artifacts approved)
     Reason: the release branch represents a finished deliverable.

  ❌ Not after generate alone
     Reason: generated artifacts aren't approved yet. Merging them before validate
     and review means unreviewed content lands in main.

  ❌ Not mid-iteration on a single artifact
     Reason: iterate on the branch; PR when the artifact stage is closed.

Current state: [assess whether a PR is appropriate right now based on artifact states]
[If appropriate:] Recommendation: raise a PR now for [artifact(s) completed since last PR].
[If not:] Complete [next pending step] first, then raise a PR.
```

### Step B6: Task vs. Release Decision

Output when the user is unsure whether something is a release or just a small task:

```
Is this a release or a task?

A release is appropriate when:
  • It has a milestone or client-visible deliverable at the end
  • It involves more than one artifact (e.g. data model + dbt + dashboard)
  • It will be tracked separately in Jira / billed separately in Harvest
  • It will have a PR and a branch of its own

A task (not a release) is appropriate when:
  • It's a small change to something already built (add a filter, fix a metric)
  • It's a single-artifact change that doesn't need a full lifecycle
  • It will be done in a single session with no client sign-off required

[Assess the user's described work and give a specific recommendation:]

Based on what you described ("[summarise what user said]"):
→ This looks like a [task / release].

[If task:] No need to create a Wire release. Do the work directly on the feature branch
           and raise a PR when done.

[If release:] Run /wire:new to set up the release structure. Choose release type:
              [recommended release type based on what they described].
```

### Step B7: Team Introduction Mode

Output when the user is preparing to introduce Wire to a new team:

```
Preparing to demo Wire to a new team:

A simple, effective demo sequence (20–30 minutes):

1. Show the problem Wire solves
   "Without Wire, every engagement starts from scratch. Requirements live in Confluence,
    data models in someone's head, review feedback in email. Wire makes the process repeatable."

2. Run /wire:new and pick dashboard_first (most visual, easiest to understand quickly)
   Walk through the questions Wire asks — this shows how much context Wire captures.

3. Run /wire:playbook-generate — show the BPMN diagram and step-by-step plan that comes out.
   This is the most impactful moment: the team can see what they're about to do.

4. Run /wire:mockups-generate — show the generated HTML mockup.
   Compare to what they'd produce manually.

5. Run /wire:status — show how Wire tracks progress across the release.

6. Explain the three-step cycle (generate → validate → review) in 90 seconds.
   Use Step A4 language: "validate catches LLM drift, review closes the stage."

What NOT to show in a first demo:
  • Don't show all 66+ commands — it creates the "you're lost in a massive thing" feeling
  • Don't show autopilot mode — too abstract without prior context
  • Don't show Jira/Confluence integration — explain it exists but skip the demo
  • Don't start with discovery release types — dashboard_first is more immediately tangible

Keep it to: new → playbook → generate one artifact → status. That's the loop.
```

### Step B8: Command Catalogue (Curated)

Output when the user doesn't know what commands exist. Present by phase, not alphabetically — the full list of 66+ commands is overwhelming.

```
Wire commands by phase — the ones you'll actually use regularly:

SETUP
  /wire:new                     Start a new engagement or add a release
  /wire:adopt                   Catch up Wire to an in-progress project
  /wire:playbook-generate       Generate your step-by-step delivery plan for a release

NAVIGATION
  /wire:start                   This command — what do I do next?
  /wire:session-plan            Propose a focused plan for the current session
  /wire:status                  Show where you are across all releases
  /wire:engagement-context      Summarise the current engagement context

DASHBOARD-FIRST RELEASE (most common for RA)
  /wire:mockups-generate        Generate an HTML dashboard mockup
  /wire:mockups-validate
  /wire:mockups-review
  /wire:data-model-generate     Generate the data model from the approved mockup
  /wire:data-model-validate
  /wire:data-model-review
  /wire:dbt-generate            Generate dbt staging/integration/warehouse models
  /wire:dbt-validate
  /wire:dbt-review
  /wire:semantic-layer-generate Generate LookML views, explores, dashboards
  /wire:semantic-layer-validate
  /wire:semantic-layer-review

DISCOVERY RELEASE
  /wire:requirements-generate   Generate requirements specification
  /wire:requirements-validate
  /wire:requirements-review
  /wire:conceptual-model-generate  Generate conceptual data model
  /wire:pipeline-design-generate   Generate pipeline architecture design

UTILITIES
  /wire:utils-jira-sync         Sync Wire artifact states to Jira tickets
  /wire:utils-docstore-sync     Sync artifacts to Confluence/Notion
  /wire:utils-delivery-forecast Forecast delivery timeline and flag risks

For the full list, see wire/packaging/claude-code/claude_code_plugin/commands/.
```

---

## Phase 4: Output Format

After completing the relevant phase, output a structured summary:

```markdown
## Wire Start — [Mode: Onboarding / Navigation / Explanation]

**Project**: [client_name or "not set up yet"]
**Active release**: [folder ([release_type]) or "none"]
**Plugin**: Wire [installed version] [✅ up to date / ⚠️ outdated — update before continuing]

[If plugin is outdated, insert here:]
> ⚠️ Plugin is outdated. Commands listed below may not be available until you update.
> Run: /plugins → Marketplaces → Wire → U, then /plugins → Installed → Wire → U, then /reload-plugins

---

### Where You Are
[1–3 sentence plain-language summary of current state]

### Recent Activity

[Show last 10 rows from execution_log.md as a compact table. Omit the Timestamp column for space;
show Date | Command | Result | Detail instead. If no log exists: "No activity recorded yet."]

| Date | Command | Result | Detail |
|------|---------|--------|--------|
| 2026-06-15 | /wire:dbt-audit-generate | complete | 84 models — 12 simple, 48 moderate, 24 complex |
| 2026-06-15 | /wire:dbt-audit-validate | pass | 7 checks passed, 0 failed |
| ... | ... | ... | ... |

### What to Do Next

**Run this now**:
```
/wire:[command] [args]
```
Why: [one sentence — WHY this step, not what it does]

**After that**:
```
/wire:[next-command] [args]
```

---

### Things to Know
[Only include if relevant to current state — do not pad:]
- [Cycle explanation if user has been skipping validate or review]
- [PR checkpoint note if a PR is due]
- [Staleness note if .wire/ hasn't been touched in >14 days]
- [Legacy structure note if .dp/ was found]
```

**Session plan handoff** (navigational mode only — skip for onboarding and explanation modes):

After outputting the summary block, ask:

```
Would you like to build a focused session plan before starting work? (y/n)
```

- **y**: hand off to `/wire:session-plan [release_folder]` — it will enter Plan Mode, ask what you want to accomplish, and propose a 3–5 step plan for approval before any work begins.
- **n**: end `/wire:start` here. The consultant proceeds directly to the Priority 1 command.

Do not ask this question if the user has already expressed a clear intent to start work immediately (e.g. "continue where I left off" with no hesitation, or if the lightweight session-start mode applies).

---

## Edge Cases

### Wire Not Installed

Handled in Phase 1 (Case A). If Phase 1 was somehow skipped and the user reaches this point with Wire not installed, output the Phase 1 Case A block and stop.

### Repo Has No .wire/ but Work Has Been Done

If the repo has dbt models, LookML, or dashboard files but no `.wire/` directory, surface this:

```
This repo has [dbt models / LookML files / dashboard files] but no Wire structure.
It looks like work has been done without Wire.

Recommended: run /wire:adopt — it will scan what exists and map it to Wire artifacts,
so you can continue with the framework from where the project actually is.
```

### Multiple Releases in Flight

If more than one release has in-progress artifacts:

```
Multiple releases are in progress:
  [release_1]: [artifact] — [pending step]
  [release_2]: [artifact] — [pending step]

Which release are you working on right now? (enter number or name)
```

Wait for confirmation before generating next-action output.

### No Projects Found

If no status files are found in `.wire/`:

```
No Wire releases found in this repo.

Would you like to start your first release?
```

Then use AskUserQuestion with:
- "Create first release" → invoke `/wire:new`
- "I have existing work to bring in" → invoke `/wire:adopt`
- "Just exploring" → acknowledge and exit

### All Projects Complete

If all releases have all artifacts at review = approved:

```
All releases complete.

Would you like to create a new release or review a completed one?
```

### User Asks for Something Wire Does Not Do

Wire does not: run audits, attend workshops, resolve open questions with clients, write Looker/dbt code without commands, send emails, or create Jira tickets without being asked.

If the user asks for something outside Wire's scope, be direct:

```
Wire doesn't do [X] automatically. That's work for you or the team.

What Wire can do here: [closest relevant command, if any]
```

Execute the complete workflow as specified above.
