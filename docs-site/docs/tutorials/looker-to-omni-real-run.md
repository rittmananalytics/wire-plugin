---
sidebar_position: 12
title: "Looker to Omni: A Real Run"
---

# Migrating from Looker to Omni with the Wire Framework

The [Looker to Omni Migration tutorial](./looker-to-omni-migration) walks a `bi_migration` release through a fictional engagement. What does the same release look like when it is run for real, against a live Looker estate of 196 dashboards and a shared Omni model that already carries validation errors of its own? Three Looker dashboards, and the LookML behind them, moved to Omni between 21:58 on 6 September 2026 and 22:22 on 7 September 2026, and the warehouse did not change. The Omni model was built on a branch, all 61 dashboard tiles were checked against their Looker originals and 52 rulings by the release director were recorded in files inside a git repo before the dashboards went into a 14-day parallel run with Looker.

The run used the Wire Framework, Rittman Analytics' delivery framework, installed as a Claude Code plugin, against our own Looker estate. This page describes the process as it was run rather than as it was planned: the first two turns went through a headless harness in the engagement repo's `harness/` folder, and the rest went through an interactive Claude Code session. It is the companion to the tutorial, which walks the same release type through a fictional engagement, and this page is what one real run looked like, "warts and all". Prompts are reproduced as typed, and counts, times and ruling numbers are from the release record under `.wire/releases/01-looker-to-omni/`.

:::note
Hostnames, repository names, the warehouse project, model, branch, document and session ids and personal names on this page have been replaced with placeholders. The counts, times, ruling numbers and command output are as recorded.
:::

## Source, target and scope

| | |
|---|---|
| Source | Looker at `looker.example.com`; LookML project `lookml-project` on GitHub; model `analytics.model.lkml` |
| Target | Omni at `example.omniapp.co`; a git-connected shared model, repo `omni-model` |
| Warehouse | BigQuery, project `example-project`, dataset `analytics`. Unchanged. |
| Scope | Three dashboards and every LookML object they reach. Everything else is dropped (R-1, R-7). Extended on 7 September to six more dashboards (R-53), not covered here. |
| Parallel run | 14 days, 7 to 21 September 2026 (R-4, R-52) |
| Parity | Every tile on the three dashboards: 61 tiles compared, 61 passing (run 2) |
| Result in Omni | 3 published dashboards in folder `Looker Migration` on model `analytics_model 2`; 53 query views, 26 topics and 34 relationships added to the shared model |

The three dashboards were these:

| Id | Dashboard | Runs in 90 days | Visual tiles | Merged-results tiles | Explores used | Omni document |
|---|---|---|---|---|---|---|
| 267 | Business Summary | 488 | 17 | 8 | 8 | `d0c00001` |
| 255 | Web Performance and Marketing Attribution | 18 | 28 (27 built, 1 deferred) | 4 | 3 | `d0c00002` |
| 416 | Engagement RAG Status 2026 | 1 | 17 | 0 | 4 | `d0c00003` |

Why only three? The estate is a good deal larger: the audit in turn 1 counted 196 dashboards, 148 Looks, 1,636 tiles, 190 views and 39 explores, and of those 3 of the 196 dashboards carry 80 percent of the runs in the last 90 days while 159 have not been opened in that window. It follows, therefore, that the scope is three dashboards and not the estate.

## Before you start

Before the first directive there are six things to do, each done once, and steps 4 and 5 need admin access to Looker and Omni.

**1. An engagement repo.** Clone an empty repo (ours is `example-migration-delivery`) and open Claude Code in it, because Wire writes its record under `.wire/` here. Do not clone the LookML or Omni repos by hand, since Wire snapshots both itself in turn 1; what you do need to check is that your git credentials can reach them:

```bash
git ls-remote https://github.com/example/lookml-project
git ls-remote https://github.com/example/omni-model
```

Each command should print lines of commit hashes and branch names.

**2. The Wire plugin.** In Claude Code:

```
/plugin marketplace add rittmananalytics/wire-plugin
/plugin install wire@rittman-analytics
/reload-plugins
```

`/wire:help` prints the command list once the plugin has loaded. The build used here was 4.0.0. See [Installation](../getting-started/installation) for the full set-up steps.

**3. Omni's agent skills.** Wire drives Omni through Omni's own open-source skills package, which covers the model builder, the content builder, queries and admin:

```
/plugin marketplace add exploreomni/omni-agent-skills
/plugin install omni-analytics@omni-analytics
/reload-plugins
```

**4. Looker API credentials.** Create an API key in Looker under Admin, Users. The user needs to read content and, for the usage figures, to query System Activity. Export three variables in the shell you start Claude Code from:

```bash
export LOOKERSDK_BASE_URL="https://looker.example.com"
export LOOKERSDK_CLIENT_ID="<client id>"
export LOOKERSDK_CLIENT_SECRET="<client secret>"
```

Check them:

```bash
python3 -m pip install looker-sdk
python3 -c "import looker_sdk; sdk = looker_sdk.init40(); print(sdk.me().display_name)"
```

**5. Omni CLI, token and model id.** Install the Omni CLI (source: `github.com/exploreomni/cli`), create an API key in Omni with model write and admin scope and set up a named profile:

```bash
omni config init
omni config show
omni models list
```

The last command lists every model with its id, and the id you need is the UUID of the shared model on the warehouse connection.

:::note
The model id is not the API key, and it is not a workbook id. In our run the directive carried a string in API-key format by mistake; the session did not guess, it parked the question with the two candidate models listed, and target setup waited on the answer.
:::

**6. Check everything.**

| Check | Command | Expect |
|---|---|---|
| Wire loaded | `/wire:help` | Command list |
| Omni skills loaded | `/plugin` | `omni-analytics` enabled |
| Looker API | The Python one-liner above | Your display name |
| Omni CLI | `omni models list` | The target model in the list |
| Repos reachable | `git ls-remote` on both | Refs print |

## How Wire runs a migration

### The release type

Before we look at the turns themselves, it helps to know what Wire is working from. Every Wire engagement has one or more releases, and every release has a release type: a YAML file listing the phases of the work, the artifacts (documents and data files) each phase produces and the conditions each artifact needs before it can be produced. The release type for this work is `bi_migration`, with the tool pair `looker_to_omni`.

| Phase | Artifact | Commands | Can start when |
|---|---|---|---|
| Audit | `looker_audit` | `/wire:looker-audit-generate`, `-validate`, `-review` | Sources registered and refreshed |
| Plan | `bi_migration_plan` | `/wire:bi-migration-plan-generate`, `-validate`, `-review` | Audit review approved |
| Target setup | `omni_target_setup` | `/wire:omni-target-setup-generate`, `-validate`, `-review` | Plan review approved |
| Model | `omni_model` | `/wire:omni-model-generate`, `-lint`, `-validate`, `-review`, per batch | Target setup review approved |
| Content | `omni_content` | `/wire:omni-content-generate`, `-validate`, then `--write`, per batch, then `-review` | Model review approved |
| Parity | `bi_equivalency` | `/wire:bi-equivalency-validate`, repeatable (run twice here) | Content batch created |
| Cutover | `cutover` | `/wire:cutover-generate`, `-validate`, `-review` | Every in-scope tile passes parity |

Two optional phases sit either side of these: business rules discovery before the audit, and training and documentation after cutover. Neither was used here.

Each command takes the release folder name as its argument, for example `/wire:looker-audit-generate 01-looker-to-omni`, and each writes its files under `.wire/releases/01-looker-to-omni/`, updates `status.md` in that folder and appends one row to `execution_log.md`. The "can start when" column is enforced by the command itself: run the plan before the audit is approved and it stops and says which condition is unmet.

In Claude Code each `/wire:` command is a skill, that is, a markdown file in the plugin holding the command's full specification, which the session loads and follows step by step. The Omni-side steps inside those specifications call Omni's own skills, installed in step 3, for model YAML, documents, queries and admin.

### The Looker to Omni pair

Where do the translation rules come from? They live in one folder of the plugin, `bi_pairs/looker_to_omni/`, and two pieces of it matter most.

**The translation guide** lists every LookML construct with the Omni construct it becomes and one of three classes:

| Class | What the converter does | What the agent does |
|---|---|---|
| mechanical | Writes the Omni YAML. Nothing to review. | Nothing |
| assisted | Writes a best effort and records a `needs_human` item. Where a wrong translation would change a number, writes nothing and records why. | Confirms or corrects before the batch is validated |
| redesign | Writes nothing. Records the Omni alternative. | Applies the plan's ruling or parks a decision |

Liquid (Looker's templating language), parameters, persistent derived tables (PDTs: tables Looker builds and stores in the warehouse) and `html` blocks are all redesign, because there is no automatic translation from Liquid to Mustache, Omni's templating language.

**The converter** is a Python script, `lookml_to_omni.py`, shipped with the plugin. It reads LookML and writes Omni view files, topic files (a topic is Omni's equivalent of an explore: a base view plus its joins) and a relationships file, and it gives the same output for the same input, with no AI call. The agent never hand-writes anything the script can emit, so that every emitted field can be regenerated and tested.

Alongside these sit a content mapping (tile types to Omni chart types, dashboard filters to controls), a file of Omni idioms for the constructs the converter refuses and six worked before-and-after examples that the plugin's tests check on every build.

### Who types the commands

So who types the commands? You describe what you want in plain words, and a skill in the plugin turns that into command runs, so the commands above are run for you rather than typed by you. It activates in any repo with a `.wire/` folder, or when your first message asks to start an engagement.

On every message it re-reads three files before acting: the release's `status.md` (the state of each artifact and the decisions waiting), the release-type YAML (the table above) and `decisions.md` (the rulings on record). From those it works out which artifacts can run now, which are blocked and on what and which are waiting for a decision.

Then it does four things:

- **Says what it is about to do, and names the commands that ran.** The reply says in plain words what will happen ("Auditing the Looker estate: every LookML construct classified, every dashboard ranked by use") and ends with a line naming the commands, for example "Ran: looker-audit-generate, looker-audit-validate", so that you learn the command behind each step without it becoming the headline. At the time of this run the command name came first; the record is the same either way.
- **Runs them.** Small steps run in the session. A model batch, a content batch or a parity sweep can be handed to a specialist agent from the plugin, called a "lane", with a written brief. In this run the first two turns ran headless through the harness, and from turn 3 one interactive session did every step itself, with the repeatable parts written as scripts under `audit/scripts/` so that a batch, a document build or a parity run can be re-run from the record. A second, headless continuation that had started writing model batches in parallel was stopped on the director's ruling so that one session drove (R-31).
- **Writes the record.** Only the orchestrating session writes `status.md` and `execution_log.md`, while lanes write their own artifact files and their own state file. Before the session reports a lane's work as ready, it checks the files exist, checks validate ran and matches the lane's claim and spot-checks a sample.
- **Parks decisions instead of guessing.** Anything that needs a ruling becomes an entry in `status.md` with the exact question, and a review step never runs without your say-so. The first line of every reply is the count of decisions waiting.

Your rulings go into `decisions.md` the moment you give them, numbered R-1, R-2 and so on, with your name, the time and your reason, and the plan and every later command read them from the file rather than from the conversation, so a ruling survives the session ending.

You can type any `/wire:` command yourself at any point, after which the session re-reads the files and carries on. Saying "you drive" hands control back for the rest of the session, and saying "I'll drive", or giving any instruction, hands it forward again. Both are logged.

## The walkthrough

Open Claude Code in the engagement repo; no slash command is needed to begin. Turns 1 and 2 ran through the headless harness (`harness/run_test.sh`, prompts in `harness/turns/`), and turns 3 onwards ran in an interactive session, because the model batches raised questions faster than a scripted turn could answer them.

### Turn 1: the opening directive (6 September, 21:58 to 22:43)

```
I want to migrate part of our Looker estate to Omni. Set up the engagement and drive it;
I am the release director, park anything that needs a ruling.

Source: the Looker instance at https://looker.example.com, LookML in
https://github.com/example/lookml-project, model analytics.model.lkml.

Target: the Omni instance at https://example.omniapp.co, model id <MODEL_ID>.
The git-connected Omni model repo is
https://github.com/example/omni-model.

Scope ruling: migrate only what these three dashboards need, including the dashboards
themselves:
- Business Summary, https://looker.example.com/dashboards/267
- Engagement RAG Status 2026, https://looker.example.com/dashboards/416
- Web Performance and Marketing Attribution, https://looker.example.com/dashboards/255
That means every explore, view and other LookML object they reference from the analytics
model, plus the views those explores join. Everything else in the Looker estate is the
drop list, no exceptions. Tier 1 is these three dashboards; parity scope is all their
tiles; parallel run 14 days.

Register both repos as migration sources, refresh them, run the Looker audit, and bring
me the migration plan with the parked decisions.
```

The line "I am the release director" tells the session that you decide and it operates, and the rest of the directive supplies every answer engagement setup would otherwise ask for: source, target, scope, tier, parity scope and the parallel-run window.

What ran, from the execution log:

| Command | Result | Time |
|---|---|---|
| `/wire:new` | Engagement and release `01-looker-to-omni` created | 2m 06s |
| `/wire:migration-source-register`, twice | LookML repo and Omni model repo registered as sources | |
| `/wire:migration-source-refresh`, twice | Both repos cloned into the release's snapshot folder (165 LookML files at commit `1a2b3c4`; 1,000 Omni YAML files) | 39s |
| `/wire:looker-audit-generate` | Audit report, two catalogues, dependency graph | 27m 24s |
| `/wire:looker-audit-validate` | 8 of 8 checks passed | 1m 52s |
| `/wire:bi-migration-plan-generate` | Plan, batches, register with 156 rows, baseline `b001` | 4m 40s |
| `/wire:bi-migration-plan-validate` | 9 of 9 checks passed | 30s |

The turn took 46 minutes and cost $25.55 in API usage.

Setup wrote five rulings to `decisions.md`, R-1 to R-5: the scope, the tool pair, tier and parity scope, the parallel run and the engagement settings it derived from the directive.

The audit read the LookML snapshot and the Looker API, and it classified 3,945 model constructs: 3,548 mechanical, 265 assisted, 132 redesign. On the content side it recorded 196 dashboards, 148 Looks, 1,636 tiles, 6 schedules, 3 alerts and 64 folders, with 90-day usage per dashboard from System Activity. Note that the audit does not decide what to migrate; instead, it records what is there and what each thing would cost to move.

For the three in-scope dashboards it recorded what each one reaches:

| Id | Explores | Filters | Merged-result tiles | Tiles with table calculations | Custom visualisations |
|---|---|---|---|---|---|
| 267 | 8 | 4 | 8 | 13 | 1 |
| 416 | 4 | 3 | 0 | 0 | 0 |
| 255 | 3 | 8 | 4 | 23 | 0 |

Merged results, table calculations and custom visualisations are the three things the content step cannot rebuild directly from the Looker definition, and so those counts sized the hand work before anything was built. As we will see in turn 4, every one of them ended up either as a query view on the model or as a measure.

The plan has a blocking condition, which is that the audit review must be approved. The directive asked for the audit and the plan in one turn, so the session recorded a gate override in `status.md` under the director's name, quoting the directive as the reason, generated the plan and parked both reviews for a ruling.

### What the plan contains

The plan does five things.

1. **Ranks content by usage.** Tier 1 is the smallest set of dashboards carrying 80 percent of runs, tier 2 is the rest with any runs and stale is zero runs in 180 days. Business Summary alone carries 48 percent of all dashboard runs in the window. The ranking is recorded so that the cost of the scope ruling is visible: Project Profitability (234 runs) and Utilisation (102 runs), the second and third most used dashboards, were not in scope.
2. **Applies rulings, or parks them.** Rulings already in `decisions.md` are applied: parity for tier 1, the drop list, the 14-day parallel run and the all-tiles parity scope. Every other question is parked with its exact wording.
3. **Decides model scope.** Every view and explore any in-scope dashboard references, plus every view those explores join. Here that is 73 views, 15 explores and 1,643 fields. Every other view is listed under "Model not carried" with the reason "no in-scope content references it": 117 views and 24 explores.
4. **Cuts batches.** One permissions batch, six model batches (b02 to b07) in join order and three content batches, one per dashboard in usage order. Each content batch names the model batch it depends on.
5. **Bootstraps the register and pins the baseline.** One pending row per in-scope object in `migration_register.csv`, 156 rows here. A `baseline.yaml` records the LookML commit, the converter version and the parity as-of instant, `2026-09-05T23:59:59Z`, and every later parity verdict names this baseline.

One finding from the scope step shaped the parked questions. Business Summary reaches the `companies_dim` explore, which has 65 joins, and carrying every joined view, as the scope ruling says, brings in 49 views the tiles never touch; the tiles use fields from 18 of them.

The turn ended with 12 decisions waiting:

| Id | Question, shortened | Ruled by |
|---|---|---|
| PD-1 | Confirm the Omni model is `9f1e2d3c`, the one git-connected to the target repo. The id in the directive was in API-key format and matched nothing. | R-6 |
| PD-2 | Approve the Looker audit | R-23 |
| PD-3 | Permission map: carry the All Users group and one access grant, nothing else? | R-10, later R-40 |
| PD-4 | 11 views pick their BigQuery dataset with a user attribute. Bind them to one schema and drop per-user switching? | R-16 |
| PD-5 | Parameter-driven tiles: rebuild as Omni field-selection controls, or as fixed measures? | R-21 |
| PD-6 | 12 merged-results tiles: rebuild each as a query view, or split into side-by-side tiles? | R-22 |
| PD-7 | Keep all 73 joined views, or trim the 65-join explore to the views the tiles use? | R-17, R-35 |
| PD-8 | Confirm the proposed treatment of each redesign construct | R-18 |
| PD-9 | View naming: 42 of the 73 view names already exist in the target model. Second view per table, or extend the existing ones? | R-9, then R-20 |
| PD-10 | Run the optional audit of existing Omni content, or skip? | R-24 |
| PD-11 | Run the optional business rules phase, or skip? | R-25 |
| PD-12 | Approve the migration plan | R-12 |

Nothing was written to Looker or Omni, and nothing was committed to git.

### Turn 2: rule on the plan; target setup (6 September, 22:43 to 22:52)

```
Rulings:
- Omni model (PD-1): 9f1e2d3c-4b5a-4c6d-8e7f-0a1b2c3d4e5f, the shared model 'analytics_model 2'.
- Drop list: confirmed, drop everything not needed by the three dashboards.
- PDTs: rebuild as Omni query views unless the plan proposes a dbt model; park any you are unsure about.
- View naming: keep LookML view names (the converter default).
- Groups and user attributes: carry only what the three dashboards' access needs.
- Parallel run: 14 days. Parity: every tile on all three dashboards.
Approve the plan. Continue: target setup, then the model batches. Stop at the first decision.
```

Rulings R-6 to R-12 went into `decisions.md`, and the approval ran `/wire:bi-migration-plan-review` under the director's name. "Continue" ran `/wire:omni-target-setup-generate`, the first command that writes to the live Omni instance, and its specification lists exactly what it writes:

| Action | What happened |
|---|---|
| Verify the connection | The Omni model's connection reads `example-project.analytics`, the same as Looker's. |
| Create a model branch | `wire-01-looker-to-omni`, id `a1b2c3d4`. Every model write in the release went here. |
| Refresh the schema | 3 in-scope datasets soft-refreshed (job `c3d4e5f6`). |
| Create groups and user attributes | None created. All Users maps to the organisation default; the Omni CLI cannot create user attributes. |
| Derive a dashboard theme | `migration/omni_dashboard_theme.json`, applied to every document built later. |

Validate failed 2 of 7 checks: the shared model already had 10 validation errors of its own (a stale column, `start_end_ts`, on 10 auto-generated views), and the user attribute the plan's permission map wanted did not exist. Both were parked (PD-13, PD-14) and the session stopped, as the directive said.

### Turn 3: model batches (6 September 22:53 to 7 September 07:54)

```
Approved. Continue to the next batch. Show me each batch's needs_human items with your
proposed resolution before you apply them.
```

"Approved" ruled PD-13 and PD-14 as recommended (R-13: remove the 10 stale dimensions on the branch only; R-14: bind the access grant to Omni's system group attribute) and approved target setup (R-15). Then the model batches ran, one at a time, each as generate, lint, validate:

```
/wire:omni-model-generate 01-looker-to-omni --batch b02
/wire:omni-model-lint 01-looker-to-omni --batch b02
/wire:omni-model-validate 01-looker-to-omni --batch b02
```

Generate runs the converter over the batch's views and explores and writes `needs_human.json` beside the output: every construct it did not emit, or emitted with a flag, with its class, the LookML file, the reason and the Omni alternative. The batch was not written to the branch until the director had seen that list and ruled, and the pattern was the same for every batch: the reply grouped the items, proposed one treatment per group and asked one question per group with options. The rulings, in order:

| Batch | Converter output | needs_human | What the director ruled |
|---|---|---|---|
| b02, engagement health (for 416) | 4 views, 4 topics | 8 | Looker `always_filter` windows become topic `default_filters` (R-19); html RAG status blocks are emitted without colour, colour returns at content stage (R-18). |
| b03, web analytics (for 255) | 11 views, 3 topics, 8 relationships | 23 | 9 timeframes with no Omni equivalent dropped (R-26); cross-view measures and measures over measures kept as emitted for validate to prove (R-27, R-28); an mm:ss format kept as seconds (R-29); primary keys set on 3 joined views after a uniqueness query (R-30); 16 warehouse-drift fixes accepted, 11 of them fields whose columns no longer exist (R-33). |
| b04, targets, forecast, financials (for 267) | 10 views, 5 topics, 5 relationships | 27 | 16 `period_over_period` measures left out of the model, rebuilt as Omni period comparison at content stage; 3 parameters and 3 Liquid fields become dashboard controls; 2 stale columns removed and 2 renamed keys followed (R-34). |
| b05, companies core, NPS, delivery team (for 267) | 15 views, 2 topics, 16 relationships | 20 | Looker's aliased joins (`contacts_dim` joined five ways) become model-level relationships with `join_to_view_as` (R-36); two joins whose keys are not unique in the warehouse are kept without a primary key, as in Looker, and the defect reported to the dbt owners (R-37); STRING date columns cast to TIMESTAMP so timeframes work (R-38); Looker link URLs with Liquid dropped (R-39); access grants not migrated at all (R-40). |
| b06, business operations part 1 | nothing written | | Emptied by the trim: the 17 views existed only as joins of `companies_dim` that no tile uses (R-17, R-35). |
| b07, business operations part 2 and the `companies_dim` topic | 2 views, 1 topic, 6 relationships | | The topic trimmed from 65 joins to the 7 the Business Summary tiles use; 14 more views removed (R-35, R-41). |

Three things happened in this turn that the plan had not predicted, and we take them in turn.

**The converter output needed a patch layer.** Lint failed on b02 with 11 self-references: the converter names a measure after its column and then writes the column as `${name}`, which in Omni points the measure at itself. Rather than hand-edit, the session wrote a deterministic post-converter patch (`audit/scripts/patch_converter_output.py`) that re-applies after every converter run and logs each change with the rule that made it. By the end of the model work it had 25 rules, among them: P1 self-reference, P2 dataset binding to `analytics` (R-16), P5 query-view binding (R-20), P6 director-confirmed primary keys, P7 label whitespace (LookML used leading spaces to order menus; Omni would turn them into folder names), P8 stale columns removed with evidence from the warehouse, P13 fiscal timeframes, P21 alias joins re-rooted on their base view, P24 topic trim.

**Every view became a query view (R-20).** The converter's default binds a view to its table with `schema` and `table_name`, but on a git-connected Omni model that file path already belongs to Omni's own auto-generated schema view for the same table, so the write collided. Tested on the branch and shown as PD-15, the ruling was to bind every view as a query view, `SELECT * FROM` the table, filed as `<view>.query.view` at the model root, and the LookML view names and every field reference survive.

**Two sessions were writing the same branch (R-31).** A headless continuation of the turn-1 harness session was still running and wrote b03, b04 and b05 to the branch while the interactive session was showing the b03 items. The director ruled that one session drives. The harness was stopped, its writes were kept and a consolidation pass listed every change it had made without a ruling (16 to b03, 27 items in b04, 20 in b05) for the director to accept or reverse (R-32 to R-35). b05 was taken off the branch until it had been reviewed, then rebuilt.

Each batch was validated the same way before it was reported: `omni models validate` on the branch with 0 blocking issues, every mechanical or assisted field in the audit catalogue present in the emitted YAML, one smoke query per topic through the Omni CLI, the register rows moved to `migrated` and a manifest per batch with the hash of every file written.

The model review (R-42, 07:54 on 7 September) approved 42 query views, 15 topics and 34 relationships on branch `a1b2c3d4`, with 31 views removed under the trim and 0 open items. Two data-model defects went to the dbt owners: `meeting_contact_lines_fact.meeting_contact_line_pk` and `delivery_projects_dim.delivery_project_pk` are not unique.

### Turn 4: content (7 September, 08:27 to 11:01)

```
Model batches approved. Build the three dashboards as Omni documents on the branch, then
run tile parity against a pinned as-of and bring me the equivalency report.
```

Content ran in two steps per dashboard, on purpose. `/wire:omni-content-generate --batch c01` wrote a plan and touched nothing in Omni: the dashboard read from the Looker API, every tile's fields mapped to the Omni views on the branch, filters mapped to controls, the layout laid out and a list of what the tiles need that the model does not yet have. `/wire:omni-content-validate` then checked the plan against the branch, the plan was shown to the director, and only after the ruling did the same command with `--write` create the document.

What the three plans asked for, and what the rulings (R-43, R-44, R-46) approved:

| Batch | Tiles | Controls | Skipped | Model additions written first | Hand-finish items |
|---|---|---|---|---|---|
| c01, 267 Business Summary | 17 | 4 | 1 empty text tile | 7 query views with one-tile topics (one per merged-results tile, R-22); 9 measures on 5 views | 9 |
| c02, 255 Web Performance | 27 | 8 | 3 text tiles; 1 tile whose calculation reads across rows (deferred) | 4 query views with one-tile topics; 12 measures on 3 views | 6 |
| c03, 416 Engagement RAG Status | 17 | 3 | 0 | none | 11 |

Three Looker constructs account for almost all of that work.

**Merged results (12 tiles).** Looker merges two or more queries in the browser, and Omni has no equivalent. Under R-22 each such tile became one Omni query view whose SQL performs the join, with a one-tile topic, so that one Looker tile stays one Omni tile and parity compares tile to tile. Before any of them was written, each view's result was compared with Looker's own merge, month by month, by rebuilding Looker's merge in Python from its source queries. Looker fills missing months on date dimensions, and so the views carry a month spine to make the row sets match.

**Table calculations (36 tiles).** Every calculation that a tile needs became a measure on the model, on the view it reads from (margin percentages, rates, running totals, period comparisons), so that the number is defined once and a query can be checked without the dashboard.

**Parameters and Liquid (4 fields).** Each became a dashboard control that selects the field or period (R-21).

The documents were created through Omni's v2 documents API: create the document by name; patch its draft with the layout and the `branchId` so that the draft runs against the branch; then let validation run every tile's query on the workbook model (17 of 17, 27 of 27, 17 of 17). The post-write checks resolved every field the first two documents use against the branch (77 and 135 fields) and ran every tile query of the third for one engagement.

The director's next message was not a ruling but a question: "when will I be able to see something in Omni?", then "those dashboards are empty". A draft bound to a branch publishes nothing until the branch merges, so the published shells were empty. The answer was an interim merge (R-45): the branch merged into the shared model ahead of cutover, 79 files added and 0 removed, the branch kept and the two drafts published. Business Summary and Web Performance were visible in folder `Looker Migration` at 09:17, and Engagement RAG Status followed the same way at 11:01 (R-46). From then on, every later model change went through the branch, validated and merged on a ruling.

### An unplanned finding: two Omni models (7 September, 11:00 to 14:19)

A teammate had run a separate Looker-to-Omni migration in June 2026 on a different model, `analytics_model` (`2b3c4d5e`), model-led rather than dashboard-led, with no dashboards. The director asked for a comparison of the two approaches, written up as a document in the engagement repo. Five topics existed in both models under the same name with different joins, so users who can see both would get two answers.

The first ruling made the June model the model of record and asked for a plan to move the Wire additions into it (R-47), then a design to converge the two models' views (R-48), and both plans were written and shown. On the director's question "Why do you need to change the analytics_model model when we're working with analytics_model 2?", it was clear the first answer had been a mis-click between two similar names. R-49 withdrew R-47 and R-48, confirmed `analytics_model 2` as the model of record, kept both plans as record and parked the overlap as PD-16 for a ruling before cutover. Nothing had been written to the June model.

### Turn 5: parity (7 September, 15:10 to 17:00)

```
Walk me through every tile that is not PASS, with your proposed fix or an
accepted-difference justification. Do not mark anything ACCEPTED_DIFFERENCE without my ruling.
```

`/wire:bi-equivalency-validate` ran each of the 61 tiles twice: the Looker element's saved query through the Looker API with its cache bypassed, and the Omni tile's query, read from the published document, through the Omni CLI. Both sides bound the dashboard filters at their defaults, ran without display fill, under the same row limit, in UTC, with the as-of pin from the baseline. Results are CSV pairs under `migration/parity/results/run_N/`, one contract per tile under `parity/contracts/` and a verdict per tile with the comparator's mechanism.

Run 1: 35 pass, 19 pass_qualified (rounding), 7 fail. The report grouped the 7 into four causes and the director ruled on each (R-50, then R-51 on the question "can you not fix those issues?"):

| Cause | Tiles | Ruling | Fix |
|---|---|---|---|
| Omni turns an empty SUM into 0; Looker leaves it blank | 1 | fix | The sum measures on the 11 merged-tile query views redefined so an empty group stays null |
| Query-view tiles ignored the dashboard's 90-day date default, because the view's SQL had no filter to bind | 4 | fix | A templated filter on each view (`session_start_date`), the dashboard's date control mapped to it |
| A top-10 table sorted on a hidden column in Looker, on a visible one in Omni | 1 | fix | The hidden sort column selected, sorted on and hidden in the Omni tile |
| Looker's visitor-value measure uses a symmetric aggregate keyed on `web_events_pk`, which is not unique in the dbt table, and under-counts (Direct channel 64 against Omni's 25,877) | 2 | accept | Recorded in `migration/parity/accepted_differences.yaml` under the director's name; the key defect reported to the dbt owners |

The fixes went through the branch, validated and merged (16:59), and the Web Performance document was re-patched and re-published. Run 2: 61 of 61 tiles passing, 37 pass, 22 pass_qualified for rounding, 2 pass_declared_deviation. All three dashboards roll up pass_qualified.

Omni behaviours found during content and parity that shaped the build:

| Behaviour | Consequence |
|---|---|
| A field name must be unique across a view's dimensions and measures | Row-level columns behind a measure are hidden dimensions with a different name |
| `N complete months ago` for `N months` reproduces Looker's month-aligned window; plain `N months ago` is day-based | Used in every topic default filter and query-view spine |
| A `timestamp()` cast inside a dimension's `sql` stays a string for filters | Casts go in the view's SQL |
| An empty SUM is 0 | Null-preserving measures on the query views (R-50) |
| A templated filter on a query view renders no constraint when unset | Dashboard date controls map to `view.filter_field` |
| A document draft patched with a `branchId` publishes nothing until the branch merges | Interim merges on ruling (R-45, R-46, R-50) |
| `resultType: json` returns labels for topic queries and empty rows for ad-hoc SQL | Parity reads results as Arrow |

### Turn 6: content review and the parallel run (7 September, 22:22)

The content review (R-52) approved the three dashboards as built: 61 of 61 tiles with a passing verdict, 26 hand-finish items open (colour bands, column labels, value labels, a second axis, an in-cell bar, two KPI value checks, the burn-up overlay), none of which changes a number. The 14-day parallel run started the same day, with Looker and Omni both live until 21 September 2026 and Looker the rollback path.

Cutover has not run. `/wire:cutover-generate` refuses while any in-scope tile is not passing and, when it runs, writes a runbook about access and content, because the warehouse did not change: parity gate confirmed from the register; access switched group by group; schedule 91 and alert 3 recreated against the Omni dashboards; Looker set read-only at the end of the parallel run; decommission as a separate scheduled step. Before it runs, these remain: the hand-finish items, PD-16 (the June model overlap), the dbt defect report and one more parity run at the end of the parallel window.

The same process ran again from 7 to 8 September for six more dashboards (R-53): three model batches, six content batches and a third parity run took the release to nine dashboards and 129 tiles at parity, in a parallel run to 22 September.

## At any point

Whichever turn you are in, the following always apply:

| You type | What happens |
|---|---|
| `/wire:status` | Where the release is, what is blocked, what is waiting |
| `/wire:status-sync 01-looker-to-omni` | Reconciles the record with the files on disk |
| Any `/wire:` command | Runs. The session re-reads state afterwards. |
| `you drive` | Control comes back to you for the rest of the session; the session answers questions and runs what you ask, and dispatches nothing |
| `I'll drive`, or any new instruction | Hands control forward to the session again |
| `Stop. Park everything and summarise where we are` | Ends early. Nothing merges to the shared model or touches Looker without a ruling. |

## The record

Where did all of this end up? At the content review the release folder held:

```
.wire/
  engagement/context.md
  execution_log.md
  releases/01-looker-to-omni/
    status.md                         one block per artifact; 9 session-history rows
    decisions.md                      R-1 to R-52
    execution_log.md                  73 rows
    audit/
      looker_audit.md
      looker_model_catalog.csv        3,945 rows
      looker_content_catalog.csv      2,053 rows
      dependencies.jsonl
      model_dependencies.jsonl
      raw/dashboard_<id>.json         the three dashboards as read from the Looker API
      scripts/                        audit, plan, batch, patch, lint, write, content and parity scripts
    migration/
      bi_migration_plan.md
      bi_migration_batches.csv
      migration_register.csv          156 rows: 73 views, 15 topics, 3 dashboards, 62 tiles, permissions, schedule, alert
      baseline.yaml
      omni_target_setup.md
      omni_dashboard_theme.json
      omni_model/
        omni_model.md                 batch reports, needs_human tables, consolidation pass, review
        b02/ .. b07/                  emitted YAML, needs_human.json, patch_log.json, manifest.json per batch
      omni_content/
        omni_content.md               per-batch plan, write, validation, hand-finish list, review
        c01/ .. c03/                  plan.json, bodies/<id>.json, source/merge_<id>.json, model_additions/
      omni_target_repoint/            R-47 and R-48 plans, marked withdrawn (R-49)
      parity/
        contracts/<dashboard>/<key>.yaml
        results/run_1/, run_2/        source and target CSV per tile
        accepted_differences.yaml     2 entries, approver and ruling named
        evidence.csv
      verdicts/run_1/, run_2/         per-tile and per-batch verdict files
      bi_equivalency_report_1.md, bi_equivalency_report_2.md
      source_snapshot/lookml/         gitignored
      source_snapshot/omni_model/     gitignored
```

Two execution log rows from the run, showing the shape:

```
| 2026-09-06 21:58 | /wire:new                   | created  | Release created (type: bi_migration, profile: looker_to_omni); PD-1 parked | Jane Smith | orchestrator [0a1b2c3d] | 2m 06s  |
| 2026-09-07 17:00 | /wire:bi-equivalency-validate | pass   | run 2: 61 tiles, 37 pass, 22 pass_qualified (rounding), 2 pass_declared_deviation (R-50, R-51), 0 fail | Jane Smith | orchestrator [4e5f6a7b] | n/a |
```

The session column says who ran it: `orchestrator [id]` for work the session ran, `typed` for a command you typed yourself. Two session ids appear: `0a1b2c3d`, the harness session of turns 1 and 2, and `4e5f6a7b`, the interactive session from turn 3.

## Where a person decided

Finally, here is every point at which a person, rather than Wire, decided something, together with the rulings that record it:

| Point | Decisions | Rulings |
|---|---|---|
| Turn 1 | Scope, tier, parity scope, parallel-run window | R-1 to R-5 |
| After turn 1 | Approve the plan; confirm the Omni model id; drop list; PDTs; view naming; permissions | R-6 to R-12 |
| Target setup | Fix the shared model's own errors on the branch; bind the access grant; approve | R-13 to R-15 |
| Model batches | Dataset binding; trim the 65-join explore; redesign treatments; per-batch needs_human groups; query-view binding; parameters as controls; merged results as query views; one driver; the stopped harness's changes; alias joins; non-unique keys; date casts; link URLs; access grants dropped; model review | R-16 to R-42 |
| Content batches | Each plan and its model additions; the interim merge; publish | R-43 to R-46 |
| Model of record | Two rulings given and withdrawn, then confirmed | R-47 to R-49 |
| Parity | Fix or accept, per cause; then fix five of the six | R-50, R-51 |
| Content review | Approve; hand-finish during the parallel run | R-52 |
| Still open | PD-16 (June model overlap); cutover ruling; decommission date | |
