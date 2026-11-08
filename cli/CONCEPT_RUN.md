# Concept run: one real release, three harness and model combinations

Item 5 of wire#408. Measured on 3 and 4 November 2026 on one machine (Apple
M5 Max, 64 GB) with the Wire CLI at `feature/wire-cli-5.0`. The numbers are
one run per leg on one release; a direction, not a benchmark.

## Setup

- **Release:** `07-unified-developer-activity` (`dbt_development`, Rittman
  Analytics internal) from `ra_data_warehouse_production`, a local clone at
  `~/wire-concept/ra_data_warehouse_production`. The real repository was not
  touched.
- **Two tasks, one baseline each**, so every leg starts from the same commit:
  - **A, `data_model-generate`:** `data_model` reset to not started; the
    approved specification moved aside as the reference; ruling R-1 skips the
    advisory business-rules gate; ruling R-2 (added after the first Codex
    lane asked) states that the two-source design the requirements describe
    stands. The Claude leg ran before R-2 existed and did not ask.
  - **B, `dbt-generate`:** `dbt` reset to not started; the two release-07
    model files still in the repository removed; the dbt summary moved aside
    as the reference. No `dbt` and no warehouse profile on this machine, so
    task B measures the code a lane writes, not a compile.
- `budget: lanes_max 1, warehouse_spend none` in both baselines.
- **Legs:** `claude` (Claude Code `-p`, the account's default model, API key),
  `codex-openai` (Codex 0.166.0, the key's default model), `qwen` (Codex
  with LM Studio, `qwen/qwen3.6-35b-a3b`, 35B mixture of experts, local).
- **Measured by** `wire/cli/tools/concept_measure.py` (no model call): the
  log row the CLI wrote (result, tokens, duration), the status outcome, the
  status-file check, hook refusals, and the output. Task A: the specification's
  size, `Grain:` lines, an ER diagram, the model names it proposes and how
  many of the reference's 12 model names it covers. Task B: SQL files written,
  `lint_conventions.py` findings, overlap with the reference model list.
- **Tokens** are what each harness reports: Claude Code sums input tokens
  across every turn including cache reads, Codex reports the turn's totals.
  Cost is Claude Code's own figure; Codex reports none.

## Task A: regenerate the data model specification

| Leg | Result | Time | Tokens | Cost | Spec | Grain lines | ERD | Models named | Covers reference (of 12) |
|---|---|---|---|---|---|---|---|---|---|
| claude | complete, merged | 6m 55s | 2,306,940 | $2.05 | 62 KB | 9 | yes | 22 | 12 |
| codex-openai (first run, before R-2) | needs_ruling, parked as PD-1 | 1m 10s | 355,201 | n/a | none | | | | |
| codex-openai (with R-2, run 1) | stalled: a hook refused a write it held in scope; parked | 3m 48s | 671,927 | n/a | none | | | | |
| codex-openai (with R-2, hook fixed) | complete, merged | 6m 41s | 796,575 | n/a | 76 KB | 16 | yes | 19 | 12 |
| qwen (32k context) | no report: the turn ended mid-work after 51 commands | 1m 17s | 511,001 | n/a | none | | | | |
| qwen (96k context, hook fixed) | complete, merged | 3m 21s | 1,057,615 | n/a (local) | 42 KB | 15 | yes | 17 | 12 |

Notes:

- The first Codex lane stopped on a real discrepancy: the approved
  requirements describe a Wire plus Claude Code design, the repository's
  current models are Claude Code only. It reported `needs_ruling` as JSON
  with the question, the CLI parked it as PD-1 and stopped. That is the
  designed stop. It also showed that lanes must see the director's rulings,
  which the CLI now puts in every lane prompt.
- The Claude lane did not ask; it reconstructed the two-source design and
  left "naming form and scope" for the director in its detail.
- The second Codex lane (with R-2 in its brief) worked for 3m 48s, then
  reported `stalled` because the ownership hook refused a write it held in
  scope. The lane transcript was overwritten by the next leg (lane logs were
  named per lane, not per run) and the hook log recorded only "deny", so the
  refused path is unknown; both are fixed and the leg is rerun.
- With reasons logged, the refusal was the hook's own bug: both Codex lanes
  wrote files with `cat > path <<'EOF'` heredocs, and the redirect scanner read
  a `>` inside the body (markdown quotes, Python `->`) as a second redirect
  outside the tree. The scanner now drops heredoc bodies and tokenises with
  shlex. With that fix the OpenAI lane completed, merged, and its
  specification covers all 12 reference models with 16 grain lines.
- The Qwen lane ran with LM Studio's default 32,768-token context. The lane
  prompt alone is about 11,000 tokens (the data model spec is 42 KB) before
  Codex's own prompt and the files the lane reads, so the turn ended after 51
  commands with no report. Rerun at 96k context.
- At 96k context and with the heredoc fix, the Qwen lane completed in
  3m 21s with a 42 KB specification covering all 12 reference models. The
  hook refused it five times for reading other releases' `status.md` with
  `2>/dev/null`: a second hook false positive (the stderr redirect read as a
  write), fixed after the leg. The lane worked around the refusals.
- All three task A legs produced a specification that names every model the
  engagement built. Size, grain lines and the extra models proposed differ;
  which specification is better is a review question this run does not
  answer.

## Task B: regenerate the dbt models

### First baseline: the repository as it is

| Leg | Result | Time | Tokens | Cost | What it found |
|---|---|---|---|---|---|
| claude | needs_ruling, parked as PD-1 | 1m 11s | 1,426,635 | $0.84 | "Release 07 needs Wire models deleted on purpose in 31775a1 (May 2026). Pick one: restore them first; build only from Claude Code data; treat /wire: prompts as the Wire events." |
| codex-openai | blocked | 1m 01s | 602,793 | n/a | "Required upstream Wire event and lifecycle models are missing; restore them before generation." |
| qwen | complete, merged | 8m 01s | 3,670,197 | n/a (local) | Wrote "15 dbt models (3 staging, 4 integration, 8 warehouse)" under the release's `dev/` tree, because the lane's `Owns:` did not include `models/` (refused once for `models/staging/...`, a CLI defect fixed after the leg); tried `sed -i` on `status.md` and was refused (rule 6, correct); 5 lint notes handed back. It did not notice the missing Wire layer. |

Both lanes read the repository, found that commit 31775a1 ("Scope down to
coding_agent_prompts_fact only", 9 May 2026, 47 files, 3,707 deletions) had
removed the Wire-source staging and integration models the approved data
model builds on, and stopped with the decision instead of inventing sources.
The Claude lane named three options as a `needs_ruling` report, the OpenAI
lane reported `blocked`; the CLI parked the first as PD-1 and kept the
second's worktree. Same correct stop on two harnesses, in about a minute
and under a dollar each.

### Second baseline: the Wire layer restored

Ruling R-3 (the director's answer to PD-1, applied as the concept run's
director): restore the Wire-source layer that 31775a1 removed, keep the
release-07 target models removed, and build from both sources as the
approved design says.

| Leg | Result | Time | Tokens | Cost | SQL files | Models named | Covers reference (of 12) | Lint errors / warnings | Hook refusals |
|---|---|---|---|---|---|---|---|---|---|
| claude | complete, merged | 10m 10s | 8,830,252 | $4.13 | 12 in `models/` plus 1 test | 12, the approved names | 12 | 12 / 144 (the 12 errors are the file-name rule: the approved names are single-underscore; 17 YAML indentation warnings) | 2 (one in-scope write refused by the brief-parser defect below, one `sed -i` on status.md, correct) |
| codex-openai (first run) | needs_ruling, parked as PD-1 | 1m 40s | 845,038 | n/a | none | | | | 0 |
| codex-openai (with R-4) | complete, merged | 11m 43s | 3,741,417 | n/a | 12 in `models/` plus tests (its detail says 380 tests) | 12, the approved names | 12 | 12 / 107 (the same 12 file-name errors R-4 accepts; 85 YAML line-length warnings) | 0 |
| qwen | complete, merged | 10m 47s | 4,154,469 | n/a (local) | 12 under the release's `artifacts/dbt/` | 12, convention-form names (`wh_performance__developer_sessions_fact`) | 0 by name; the same 12 models by role | 0 / 1 | 2 (the same two as Claude) |
| codex + bridge (Claude Sonnet through Codex), task A | harness error after 5m 45s | | | | | | | | |
| codex + bridge, task A runs two and three | the same error after 15m 19s and 8m 32s | | | | | | | | |
| codex + bridge, task A run four (shim reorders tool groups) | complete, merged | 13m 16s | 3,004,640 | n/a (Codex reports none; billed on the Anthropic key) | 47 KB | 16 | yes | 23 | 12 |

Notes on the second baseline:

- The three harnesses handled the same conflict three ways. The data model
  (approved in May) names models in the older single-underscore form; the
  dbt conventions adopted in 4.1.2 want `wh_<group>__<entity>`. Claude kept
  the approved names and recorded the 12 file-name lint errors as accepted
  against the specification. The OpenAI lane stopped and asked whether to
  add a convention override, which the CLI parked as PD-1 (answered as
  ruling R-4 for the rerun). Qwen renamed everything to the convention form,
  which passes lint and matches nothing by name.
- Both completed lanes were refused once for a write to `models/` that the
  CLI had granted: the brief parsers (the Codex hook and the Claude mod's
  `lanes.ts`) dropped a bare tree name such as `models` after stripping a
  trailing slash. Claude's lane went on to write `models/` with other
  commands; Qwen's moved to the release's `artifacts/dbt/` tree. Fixed in
  both parsers after the legs.
- Both completed lanes tried to update `status.md` themselves with `sed -i`
  and were refused by rule 6. The CLI wrote the record.
- No `dbt` on this machine, so neither lane compiled; Claude's detail says so.
- With R-4 in its brief the OpenAI lane completed in 11m 43s: the same 12
  models under the approved names, 380 tests, and the same 12 accepted
  file-name findings as the Claude lane. Three harnesses, the same 12 models.
- The Claude bridge leg failed inside the bridge after 5m 45s of work:
  Anthropic's 5.x models reject a conversation that ends with an assistant
  turn, and Codex's input can end with a reasoning item. The shim now closes
  such a conversation with a user turn; the leg is rerun.
- Runs two and three failed the same way further in. The shim's diagnostics
  showed the real cause: Codex places an assistant message between a
  function call and its output, and translated for Anthropic that ends with
  an assistant turn. The shim now moves such messages ahead of the call. Run
  four completed: Claude Sonnet through Codex produced a specification
  covering all 12 reference models in 13m 16s. One refusal: the lane ran
  `cd <release dir> && sed -i ... decisions.md`, and the hook, which does not
  follow `cd`, resolved the file against the worktree root and refused it
  under rule 3 (best effort; noted).

## Roadmap phase 3: Claude through wire-agent's native provider (4 November 2026, evening)

Task A again, on the same baseline, through the forked agent's Anthropic
Messages API provider (`--harness codex --provider anthropic --model
claude-sonnet-5-5`; fork branch `wire/brand-0.166.0`), with no proxy.

| Leg | Result | Time | Tokens | Cost | Spec | Grain lines | ERD | Models named | Covers reference (of 12) | Hook refusals |
|---|---|---|---|---|---|---|---|---|---|---|
| wire-agent, native Anthropic provider | complete, merged | 13m 52s | 3,486,541 | about $2.05 (computed; see below) | 50 KB | 16 | yes | 22 | 12 | 0 of 80 calls |

- Cache: 3,235,254 of 3,383,213 input tokens were cache reads (95.6 percent),
  147,881 cache writes, 103,328 output tokens. At Claude Sonnet 5.5's prices
  ($2 input, $10 output, $0.20 cache read per million; cache writes at the
  standard 1.25 times input, $2.50) that is about $0.65 + $0.37 + $1.03 =
  $2.05, against $2.05 for the Claude Code leg on the account's default
  model. The phase 3 acceptance ("the Claude leg's cost within 10 percent of
  Claude Code's for the same lane") is met on this one lane.
- Time matches the bridge leg (13m 16s) and is about twice the Claude Code
  leg (6m 55s). The difference is the harness (Codex's tool loop and its
  turn structure), not the transport.
- Codex reports no cost for a non-OpenAI provider; the CLI's cost cell stays
  n/a until the CLI prices Claude tokens itself (phase 6).

## What the run says about the design

(filled in when the legs are done)
