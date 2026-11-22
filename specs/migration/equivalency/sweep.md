---
wire_schema: "1.0"
command: utility
artifact: equivalency
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Estate-wide defect-class sweep — given one root-caused defect pattern, enumerate every occurrence across the delivery tree, the client main, and open PRs, classify each site, and close by encoding the pattern as a lint rule
argument-hint: <release-folder> --pattern <rule-id> [--dry-run]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

## Data Safety — Read Before Proceeding

The sweep's static scan writes nothing anywhere. Its probe queries (DEFECT-MERGED quantification) are SELECT-only, against the target platform. Fixes land only in the delivery tree; anything merged is escalated to a fix-forward PR via `dbt-migration-batch-raise`, never edited in the client repo directly.

---

# Equivalency — Sweep

## Purpose

`equivalency-investigate`/`-fix` handle one model. But a root-caused defect is rarely alone: the same translation pattern that broke one comparison is usually sitting in every model that shares the shape — some still in the delivery tree, some already merged to the client's main. The loop that kills a defect class in one day is: root-cause one failing comparison → encode the rule → **statically sweep every translated model in both trees** → classify each site → fix, escalate, or clear with evidence → re-verify. This command is that loop as a gate (#179). A sweep that does not end in a lint rule is incomplete: the rule is what blocks the class prospectively.

## Input — the defect-class definition

`--pattern <rule-id>` names a rule carrying:

- a **detection pattern** — regex or AST-shaped match over source+target SQL pairs (what shape to find);
- a **semantic rule** — the condition that makes a hit an actual defect (e.g. "row-selecting window `ORDER BY` over a nullable key without a `NULLS` qualifier"), since a pattern hit in a harmless position is CORRECT, not a defect.

The rule id resolves against the active platform pair's lint rules and the engagement's own additions (`migration/lint_rules.md`). A `--pattern` naming no known rule aborts with the known rule ids listed; a brand-new class is first written down as an engagement rule, then swept — the definition is the input, not the output.

## Workflow

### Step 1 — Enumerate the estate

Collect every (source, target) SQL pair in scope, across **three locations**:

1. the **delivery tree** (`migration/dbt/` translated models);
2. the **client main** — a fresh read of each `migration.client_repos` checkout's base branch (live state, never the register's memory of it);
3. **open PRs** — each unmerged batch branch's files (`gh pr list --state open`).

### Step 2 — Detect and classify (deterministic)

Tests mirror this classification exactly (`wire/tests/platform_migration/validate_equivalency_sweep.py`). Per model, per location, apply the detection pattern, then the semantic rule:

| Pattern hit | Semantic rule violated | Location | Classification | Action |
|---|---|---|---|---|
| no | — | any | **CORRECT** | None. Recorded so the sweep's coverage is provable |
| yes | no | any | **CORRECT** | The shape is present but harmless here; recorded with the reason |
| yes | yes | delivery tree / open PR (not merged) | **DEFECT-FREE-MODEL** | Fix in the tree now, mark the model **re-verify owed** (its standing verdict is void) |
| yes | yes | client main (merged) | **DEFECT-MERGED** | **Quantified probe** — a SELECT that measures the defect's real impact (rows affected, delta size) — then escalate to a **fix-forward batch** via `/wire:dbt-migration-batch-raise`, the probe figures in the PR body |
| yes | yes | source only — model not yet translated | **NOT-TRANSLATED-YET** | Note for the translation guide: the pattern must be handled when this model is translated |

### Step 3 — Apply the tree fixes

For each DEFECT-FREE-MODEL site (unless `--dry-run`): fix the delivery-tree file, re-run the deterministic gate over it (`dbt-migration-lint`), and record the fix in the sweep report. Open-PR sites are fixed on their branch only when the PR is ours and unmerged; otherwise they classify as merged for safety.

### Step 4 — Register integration

- Every DEFECT-FREE-MODEL and DEFECT-MERGED model's standing verdict is **superseded**: blank `last_equivalence_result` (the register's audit note in `notes` names this sweep and the pattern id). The verdict log is untouched — history is history; the blanking says "no longer current evidence", not "never happened".
- DEFECT-MERGED escalations carry their probe figures into the fix-forward batch (`dbt-migration-batch-raise` derives them as candidates once fixed and re-verified).
- Re-verify-owed models re-enter the equivalency loop; the sweep is not complete until they carry fresh verdicts.

### Step 5 — Close with the lint rule

Confirm the pattern is encoded as an error-severity rule in the engagement lint rules (`migration/lint_rules.md`), firing in `dbt-migration-lint` — so the class is blocked at translation time from now on. **A sweep whose pattern is not in the lint rules at the end is incomplete**; the report's final line states the rule id and where it landed.

### Step 6 — Write the sweep report and update status

`.wire/releases/$ARGUMENTS/migration/equivalency_sweep_<rule-id>.md`: the pattern and semantic rule; per-location site counts by classification; the fixes applied; the probe figures and escalations; the re-verify-owed list; the closing lint rule.

```yaml
artifacts:
  equivalency:
    sweeps:
      - pattern: "<rule-id>"
        date: "{{TODAY}}"
        sites_correct: N
        defect_free_model: N
        defect_merged: N
        not_translated_yet: N
        reverify_owed: N
        lint_rule_landed: true
```

## Cross-release note (tenant carve-out, #180)

When the swept release has carve-outs relocated **from** it, the sweep's DEFECT-MERGED and DEFECT-FREE-MODEL model lists feed the carve-out's drift gate: relocated copies of a hit model are re-verify-owed in the carve-out too, resolved via the register's `parent_release`/`parent_model` linkage (`migration-drift-generate` Step 5c).

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `sweep` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `sweep` as action.
