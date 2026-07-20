---
description: Closed fix-and-re-review loop — auto-apply the deterministic pre-PR-review fixes, re-run the gate, escalate only findings that need a human decision
argument-hint: <release-folder> [--batch N 
---

# Closed fix-and-re-review loop — auto-apply the deterministic pre-PR-review fixes, re-run the gate, escalate only findings that need a human decision

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
description: Closed fix-and-re-review loop — auto-apply the deterministic fixes from the pre-PR review, re-run the gate, and escalate only the findings that genuinely need a human decision
argument-hint: <release-folder> [--batch N | --wave id | --model name] [--base ref] [--max-iterations N] [--dry-run] [--severity LEVEL]
---

# dbt Migration — Fix

## Purpose

The mutation counterpart to `dbt-migration-pre-pr-review`. The review command is read-only by design — it finds the deploy-time defects and emits them as a structured list, but it never edits a model. This command closes the loop: it ingests those findings, **auto-applies every fix that is deterministic and semantically safe**, re-runs the gate, and hands the consultant only the minority of findings that genuinely need a human decision. It exists so a wave of mechanical fixes (add `SAFE_CAST`, prefix `SAFE.`, re-anchor a regex, drop a redundant `TIMESTAMP()` wrap, author a `policy_tags` from the tag map) is not hand-worked model by model.

This is to `dbt-migration-pre-pr-review` what `equivalency-fix` is to `equivalency-validate`: detection stays read-only; fixing is a separate, explicit, re-runnable step.

## What it does and does not touch

- It edits **only** the translated model files under `migration/dbt/` (and re-runs them against the **test** project). It never writes to a source platform or any `data_safety.production_projects` project — same guard as `dbt-migration-generate`.
- It never auto-resolves a finding that needs a decision (see the fix-policy table). Those are escalated, not guessed.
- `--dry-run` classifies and prints the plan (what would be auto-fixed, what would be escalated) without editing anything.

## Flags

- `--batch N` / `--wave <id>` / `--model <name>` — scope, resolved exactly as `dbt-migration-pre-pr-review` resolves them (Step 0w / Step 1w). `--wave` and `--batch` cannot be combined.
- `--models <names>` — narrow a `--wave`/`--batch` to a named subset (the register-driven resume subset — see `dbt-migration-generate`).
- `--base <ref>` — the diff base the findings were taken against; passed through to the review re-runs.
- `--max-iterations N` — cap on the auto-fix loop (default 5, matching `dbt-migration-generate`'s per-model loop). The loop stops earlier when no auto-fixable finding remains or a pass makes no progress.
- `--severity error|warn|info` — minimum severity to act on (default `error`; `warn` to also auto-fix warnings).
- `--dry-run` — classify and print the plan; apply nothing.
- `--config <path>` / `--tag-map` / `--target-dataset` / `--dbt-project-path` — per-run config overlays, mirroring `dbt-migration-generate` exactly.

## Inputs

- The latest `dbt-migration-pre-pr-review` findings report for the scope (`migration/pre_pr_review/*_pre_pr_review.json`). If it is missing or older than the current translated diff, run `dbt-migration-pre-pr-review` first to refresh it.
- Active platform pair — the fix hints and the fix-policy for each pattern come from the pair's rule sections (`translation_guide.md`: Deployment type-divergence patterns, Edge-case runtime-failure patterns, Column governance / masking mechanisms), never hardcoded here.
- Engagement fix-policy overrides at `.wire/engagement/platform_pair_overrides/{pair}/fix_policy.md`, if present — lets an engagement move a pattern between `auto`/`propose`/`decision` with a documented reason.
- The PII tag map (`migration.pii_tag_map_path`) — used to decide whether a governance finding is auto-fixable (a tag-map entry exists) or a decision (it does not).

## Fix-policy classification

Every finding is classified into one of three policies. The default mapping below is driven by the finding's pattern/category; the pair or engagement override may adjust it. The rule is deliberately conservative — a fix is only `auto` when it is deterministic **and** semantically correct regardless of the model's intent.

**`auto` — apply automatically, then re-run the gate.** The fix restores the source's behaviour and cannot be wrong:
- `UNGUARDED_JSON_PARSE` → prefix `SAFE.` (null-on-error matches the source)
- `CAST_BLANK_STRING_NUMERIC` → `SAFE_CAST`
- `UNANCHORED_REGEX` → re-anchor `^(?:...)$`
- `TS_WRAP_ALREADY_TS` → drop the redundant temporal wrap
- `ARRAY_AGG_NULLS` → add `IGNORE NULLS`
- `IMPLICIT_JOIN_COERCION` → explicit `CAST` to the shared deployment type
- `JSON_FN_ON_STRING` / `JSON_FN_ON_JSON` → align the accessor to the deployment column type
- `governance_regression` **when the tag map has an entry** for the source masking policy → author the `policy_tags`

**`propose` — draft the fix, but a human confirms.** Deterministic to write, but intent-dependent, so it is drafted into the escalation queue as a ready-to-apply suggestion rather than committed silently:
- `STRING_FN_ON_NONSTRING` → `CAST(col AS STRING)` **or** remove the string function (a `TRIM()` on an id may be spurious — the consultant decides which)
- `MATERIALIZATION_DRIFT` → restore the source materialisation or declare the override
- `column_order_divergence` → reorder to match source (safe, but positional consumers vary)
- stale companion-YAML descriptions

**`decision` — no safe auto fix; escalate for a human.** The finding needs information or a judgment the loop does not have:
- `dag_registration` — register the model in the target orchestration DAG (a wave/orchestration decision)
- `deployment_type_unconfirmed` — needs the real Bronze column type we do not yet have read access to (the B-side access gap)
- `layer_relocation` — a source/dataset move that must be documented and agreed
- `parity_vs_correctness` — a product decision (accept the more-correct target behaviour, or force strict parity)
- `data_availability` / market gap — "re-verify when the connector lands"
- `governance_regression` **when no tag-map entry exists** — the masking policy is unresolved and must be mapped first

## Workflow

### Step 0 — Load config, resolve scope and pair
As `dbt-migration-pre-pr-review` Step 0. Load any `--config`/discrete overlays (in-memory, never written back, `data_safety.production_projects` never overridable). Resolve the project(s) via `specs/utils/dbt_manifest_parse.md`, the review scope, the platform pair, and the pair + engagement fix-policy tables.

### Step 1 — Ensure current findings
Locate the latest pre-PR review report for the scope. If it is missing, or older than the current translated diff (compare mtimes / the recorded `--base` and reviewed commit), run `dbt-migration-pre-pr-review` for the scope first so the loop acts on current findings.

### Step 2 — Classify
Classify every finding into `auto` / `propose` / `decision` per the table above (pair/engagement overrides applied). In `--dry-run`, print the classified plan and stop here.

### Step 3 — Auto-fix loop (capped)
Repeat up to `--max-iterations`:
1. For each model with `auto` findings, apply the pattern's deterministic fix. Prefer re-invoking `dbt-migration-generate`'s translate/auto-fix step on that model with the findings passed as guidance (so the fix flows through the same translation path and its own compile/run/equivalency loop), rather than a blind text substitution. Record each applied fix (model, pattern, `file:line`, before/after) in the model's `.diff.md`.
2. Re-run the **deterministic** gate on the affected models only — `dbt-migration-lint`, `dbt-migration-validate` (Check 5), and `dbt-migration-pre-pr-review`'s Wire-side checks. Do **not** re-run the client-review (LLM) lens here — it is non-deterministic and token-heavy; it runs once at the end (Step 4).
3. If the re-run surfaces new `auto` findings (a fix exposed another), continue. If only `propose`/`decision` findings remain, or the model is clean, stop for that model.

Stop the loop when no model has an `auto` finding left, or a full pass makes no progress (guards against an oscillating fix), or the iteration cap is hit. A model still carrying `auto` findings at the cap is escalated with reason `auto_fix_not_converged` — never silently left.

### Step 4 — Confirm with the client-review lens (once)
If an engagement client-review profile is configured (`.wire/engagement/client_review_profile.yaml`), run it once over the now-fixed diff (per `dbt-migration-pre-pr-review`'s client-review lens). Any new `auto` findings it surfaces get one more bounded apply pass (Step 3, one iteration); anything else joins the escalation queue. This keeps the expensive lens as a final confirmation, not a loop body.

### Step 5 — Escalation queue
Emit the residue for the consultant — every `propose` and `decision` finding, grouped by policy then model, each with `severity`, `file:line`, the reason it was not auto-fixed, and (for `propose`) the drafted fix ready to apply. This is the **only** manual surface the consultant sees: the mechanical volume is already gone.

### Step 6 — Report and status
Write `migration/pre_pr_review/{scope}_fix_report.md`:
- **Auto-fixed**: per model, each pattern fixed, iterations used.
- **Escalated**: the `propose`/`decision` queue.
- **Residual gate state**: the final deterministic gate result on the scope (clean / remaining findings).
Update `status.md`:
```yaml
artifacts:
  dbt_migration:
    fix:
      last_run_date: "{{TODAY}}"
      auto_fixed: <n>
      escalated_propose: <n>
      escalated_decision: <n>
      iterations_used: <n>
      residual_errors: <n>          # deterministic error-severity findings still open
```
Update the migration register for every re-fixed model (`state`, `last_migrated_commit`) as `dbt-migration-generate` Step 3.7 does.

### Step 7 — Output next step
If `residual_errors == 0` and the escalation queue is empty:
```
All pre-PR findings resolved. Re-run the review to confirm, then open the PR:
/wire:dbt-migration-pre-pr-review $ARGUMENTS --wave <id> --format json --severity error
```
If the escalation queue is non-empty:
```
Auto-fixed N findings. M need a decision — see migration/pre_pr_review/{scope}_fix_report.md.
Resolve the escalated items, then re-run:
/wire:dbt-migration-fix $ARGUMENTS --wave <id>
```

## CI use

`--dry-run --severity error` reports what would be auto-fixed vs escalated without mutating — safe to run in CI to size the fix work. The applying run is a local/consultant step, not a CI mutation, because it edits translated models.

## Notes for the implementer

- The three-way policy is the contract; keep the pattern→policy mapping in the pair/engagement, not here, so a new pair or a client that trusts a pattern less can move it between `auto`/`propose`/`decision` without a framework change.
- Prefer routing an `auto` fix through `dbt-migration-generate`'s translate loop over a raw text edit — the fix then inherits compile/run/equivalency validation instead of being trusted blind.
- Never auto-apply a `decision` finding, and never widen `auto` to cover a pattern whose correct fix depends on the model's intent — a wrong auto-fix that passes the deterministic gate is worse than an escalation.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `fix` as action.
3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration Fix` as artifact_name, and the fix report path as file_path.
4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `fix` as action.

Execute the complete workflow as specified above.
