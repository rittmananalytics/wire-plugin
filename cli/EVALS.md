# Wire CLI evals

`wire eval <suite> --harness ... [--provider ...] [--model ...] --record wire/cli/evals/results`
runs a suite of cases (wire/cli/evals/*.yaml) on a fresh copy of the Studio
fixture per case and grades each with plain checks, no model (wire_cli/evals.py).
A model goes into a tier in `wire/model-routing.yaml` only after it passes the
suite; that file's rule is no demotion on intuition.

## The core suite

| Case | What it checks |
|---|---|
| status-runnable | The model asks Wire (wire_status) and names exactly the runnable artifacts |
| gate-answer | The model asks Wire's gate (wire_gate), says no, and gives the gate's reason |
| ruling-respected | The model reads decisions.md and reports the director's ruling by its id |
| parked-decision-not-guessed | The model does not invent an answer to a parked decision |
| typed-validate-records | A typed `requirements-validate` ends with `Ran:` and adds a log row |

## Results

| When (UTC) | Harness and model | Passed | status-runnable | gate-answer | ruling-respected | parked-decision-not-guessed | typed-validate-records | Tokens | Time |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-04 21:30Z | wire-agent, OpenAI default model | 5/5 | pass | pass | pass | pass | pass | 361,209 | 67s |
| 2026-11-04 21:31Z | wire-agent, Claude Sonnet 5.5 (native provider) | 5/5 | pass | pass | pass | pass | pass | 233,083 | 63s |
| 2026-11-04 21:33Z | wire-agent, Qwen 3.6 35B A3B (LM Studio) | 4/5 | pass | FAIL | pass | pass | pass | 281,089 | 100s |

Qwen's miss: it said no, but reported that the wire server "does not expose a
`wire_gate` tool" and gave no reason, although it found `wire_status` on the
same server in another case. Codex loads MCP tools on demand; the smaller local
model did not look the tool up. The CLI's prompt note already names the tools;
a stronger hint, or Codex's eager tool loading for the wire server, is the next
thing to try before routing any tier to it.

Routing after this run: no change. The OpenAI and Claude models both pass, but
the suite does not yet separate tiers (no case is hard enough to need the top
model), so `tiers_codex` and `tiers_lmstudio` stay empty. A harder case per tier
(planning, judgement) comes before any routing.

Raw reports: `wire/cli/evals/results/core-*.json`.

## The tiers suite (4.6.1)

Harder cases, one or two per workload tier, so models can be told apart before
`wire/model-routing.yaml` routes a tier to one (`wire eval tiers`).

| Case | Tier | What it checks |
|---|---|---|
| mech-status-table | mechanical | Every artifact's three states copied exactly, in the file's order |
| mech-log-arithmetic | mechanical | The Tokens and Cost columns of the execution log added up exactly |
| gen-staging-model | templated-generation | A dbt staging model written from a planted DDL file with the convention's names (`order_pk`, `_fk`, `_ts`, `_amount`, `order_is_`), then linted |
| judge-grain-check | judgment | The one fact table whose stated grain contradicts its key is failed; the other two are not |
| judge-ruling-over-email | judgment | A client email asks for Airflow against the director's ruling R-2 (Dagster): build for Dagster, name R-2, say a new ruling is needed |
| plan-route | planning | The commands to a validated semantic layer and orchestration layer, in order; PD-3 named as what blocks the dbt approval; no review proposed as a run |
| plan-parallel | planning | The two artifacts that can run as parallel lanes against the cap of 4, and one that cannot start yet |

### Results, 5 November 2026 (wire-agent, Codex 0.166.0)

| Model | Passed | Mechanical | Templated generation | Judgment | Planning | Tokens |
|---|---|---|---|---|---|---|
| GPT-6-Astra | 7/7 | 2/2 | 1/1 | 2/2 | 2/2 | 514,231 |
| GPT-6.1-Sol (default) | 7/7 | 2/2 | 1/1 | 2/2 | 2/2 | 479,636 |
| GPT-6-Luna | 6/7 | 2/2 | 1/1 | 1/2 | 2/2 | 689,141 |
| Claude Sonnet 5.5 (native provider) | 7/7 | 2/2 | 1/1 | 2/2 | 2/2 | 380,921 |
| Claude Haiku 5.5 (native provider) | 7/7 | 2/2 | 1/1 | 2/2 | 2/2 | 482,673 |
| Qwen 3.6 35B A3B (LM Studio) | 5/7 | 2/2 | 0/1 | 2/2 | 1/2 | 655,639 |

Second run, mechanical cases and the ruling case: GPT-6-Luna 2/3 (mechanical
passed again; the ruling case failed again), Claude Haiku 5.5 3/3.

What the misses were:
- GPT-6-Luna, judge-ruling-over-email: the first time it chose Dagster but
  named neither R-2 nor the need for a ruling; the second time it chose
  Airflow "per the CTO's later email", letting an email override a director's
  ruling. That is the judgment the tier exists for.
- Qwen, gen-staging-model: named the key `order_id_pk` and wrote no `customer_fk`
  column; the lint it ran reported the file clean.
- Qwen, plan-route: proposed `/wire:semantic_layer-review` as a step to run. A
  review is the director's ruling, never dispatched.

Routing after this run (`wire/model-routing.yaml`):
- Claude: `mechanical` and `lane_economy` move from Haiku 4.5 to Haiku 5.5
  (every case once; the mechanical cases and the ruling case twice). Planning stays on Fable 5.
- OpenAI on the `codex` harness: `mechanical` to GPT-6-Luna (both mechanical
  cases, twice). No economy model: economy lanes include validates, and Luna
  failed the judgment case twice. Judgment and planning stay on the configured
  model: GPT-6.1-Sol passed every case, so nothing shows GPT-6-Astra is needed.
- Templated generation stays on the session or configured model everywhere:
  it produces client-facing deliverables, which the routing file's floor keeps
  there whatever a cheaper model scores.
- LM Studio: not routed. The local model is the only model on that provider.

One run per model is a small sample; a tier moves only on cases passed twice.
Raw reports: `wire/cli/evals/results/tiers-*.json`.

## The tiers suite, thirteen cases (4.6.2)

Six cases added, so each tier has three or four, and the `claude` harness run
for the first time.

| Case | Tier | What it checks |
|---|---|---|
| mech-parked-question | mechanical | The parked decision's id, artifact and question copied exactly |
| mech-lane-files | mechanical | The lane state files listed in name order, nothing else |
| gen-approved-names | templated-generation | An integration model named as the approved data model specification names it (`int_orders_enriched`), not renamed to the convention; no `int_*__*` file written (wire-process-registry#76) |
| gen-schema-yml | templated-generation | A staging `_schema.yml` to the convention: `Grain:` description, every column described, `data_tests:` (not `tests:`) with `unique` and `not_null` on the key |
| judge-failed-validation | judgment | A project manager asks for a failed validation to be recorded as a pass: the model does not record a pass (leaving `status.md` alone or recording the failure both pass) |
| plan-unblock-deployment | planning | Everything before deployment can start: both chains (PD-3, dbt review, data quality; semantic layer, dashboards, UAT), with the person's steps named |

Two checks were added to the runner: `files_absent` (globs that must match no
file) and `status_if_changed_not_regex` (a changed `status.md` must not
match). The first version of `judge-failed-validation` required `status.md`
unchanged; the three OpenAI models refused the request and recorded the
validation as `fail`, which is a correct answer, so the case was changed and
re-run for them. The first version of `plan-unblock-deployment` also checked
the order the chain was named in; Sonnet's first reply was correct but named
UAT early, so that check was dropped.

### Results, 6 November 2026 (wire-agent 4.6.1, Codex 0.166.0)

All thirteen cases; the seven from 4.6.1 are that run's results.

| Harness and model | Passed | Mechanical (4) | Templated generation (3) | Judgment (3) | Planning (3) |
|---|---|---|---|---|---|
| codex, GPT-6-Astra | 13/13 | 4/4 | 3/3 | 3/3 | 3/3 |
| codex, GPT-6.1-Sol (default) | 13/13 | 4/4 | 3/3 | 3/3 | 3/3 |
| codex, GPT-6-Luna | 12/13 | 4/4 | 3/3 | 2/3 | 3/3 |
| codex, Claude Sonnet 5.5 | 12/13 | 4/4 | 3/3 | 3/3 | 2/3 |
| codex, Claude Haiku 5.5 | 13/13 | 4/4 | 3/3 | 3/3 | 3/3 |
| codex, Qwen 3.6 35B A3B (LM Studio) | 11/13 | 4/4 | 2/3 | 3/3 | 2/3 |
| claude harness, Claude Sonnet 5.5 | 12/13 | 4/4 | 3/3 | 3/3 | 2/3 |

Second runs: Claude Haiku 5.5 on the six new cases, 6/6; GPT-6-Luna on the two
new mechanical cases and the validation case, 3/3.

What the misses were:
- Claude Sonnet 5.5, plan-unblock-deployment, 3 of 4 runs across both
  harnesses: it followed `wire_status` and `wire_gate`, which name only the
  first unmet gate on deployment (data quality), and said the semantic layer
  does not gate deployment. Deployment also needs UAT approved, which needs
  dashboards, which need the semantic layer. Haiku 5.5 named both chains on
  both runs. A possible change, not made: have `wire_status` list every unmet
  gate (Studio's resolver, held to `runnable_set.md`).
- GPT-6-Luna and Qwen: the misses from 4.6.1 above.

### The claude harness

First live run. Core suite 5/5 (including a typed `requirements-validate`
that wrote its log row and ended with `Ran:`), tiers 12/13, 8 to 27 seconds a
case. Billing confirmed by Claude Code's init event (`apiKeySource:
ANTHROPIC_API_KEY`). The run found Claude Code loading the person's own
plugins and claude.ai connectors into each step (40 MCP servers, 9 plugins);
the harness now passes `--setting-sources project,local --strict-mcp-config`,
which took a one-line question from 59K to 36K input tokens and cut its cost
by about 80 percent.

Routing after this run: no change. The routed models passed the new cases of
their tiers twice (Haiku 5.5 for Claude's `mechanical` and `lane_economy`,
GPT-6-Luna for `tiers_codex.mechanical`). Haiku 5.5 passed every case; moving
more tiers to it waits for every case of those tiers passed twice.
