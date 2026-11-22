---
wire_schema: "1.0"
command: validate
artifact: launch_gate
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: eval_suite
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Per-domain accuracy gate — confirm all cleared domains meet launch threshold before announcement
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Launch Gate Validate

## Purpose

Final accuracy check before the agent is announced to the business. Only domains that meet their eval target are cleared. This is not a negotiation — if a domain is below target, it is not announced. Users who receive wrong answers lose trust that is very difficult to rebuild.

## Usage

```bash
/wire:ads_launch-gate-validate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `eval_suite.review: approved` (or `approved_with_conditions`)
- All domain fixes from eval_suite review have been applied and re-run
- **If `adversarial_config.client_decision: enabled`** (check status.md — this is the client's own recorded decision from `ads_adversarial-config-generate`): `adversarial_config.validate: complete` and `adversarial_config.review: approved` (or `approved_with_conditions`) must both be true. A release cannot reach launch with adversarial review configured but never validated or signed off — see Step 2.5.
- If `adversarial_config.client_decision: disabled`, or the artifact doesn't exist yet (older release, adversarial review never configured), skip the Step 2.5 check entirely — there is nothing to gate on.

## Validation Steps

### Step 1: Re-run Full Eval Suite

Run the eval suite from scratch (not cached results):

```bash
cd <dbt_project_path> && ./.claude/eval/run_evals.sh all 2>&1 | tee eval_results_$(date +%Y%m%d).txt
```

### Step 2: Check Per-Domain Pass Rates

For each domain, compare current pass rate against `eval_targets.yaml` threshold.

### Step 2.5: Check Adversarial Calibration Gate (if enabled)

Read `adversarial_config.client_decision` from status.md.

**If `enabled`:** read `adversarial_config.calibration_pass_rate` (written by `ads_adversarial-config-generate`, confirmed by `ads_adversarial-config-validate`'s own bar of "at least 4/5 calibration tests passed"). This is a distinct signal from the per-domain eval pass rates above — eval_suite measures whether the agent answers *good* questions correctly, calibration measures whether the adversarial reviewer actually *catches* bad ones. Both must clear independently; one cannot compensate for the other.

- **`calibration_pass_rate` < 80% (i.e. fewer than 4/5 calibration tests passed):** the adversarial safety net is not reliable. **Block the entire launch** (not per-domain — a miscalibrated adversarial reviewer is a cross-domain risk, since it runs on every query regardless of which domain it belongs to), regardless of how the per-domain eval numbers look. Record this in the report and do not proceed to Step 3's "cleared" table until recalibrated and re-validated via `ads_adversarial-config-validate`.
- **`calibration_pass_rate` >= 80%:** proceed normally to Step 3.

**If `disabled`, or the artifact isn't present:** skip this check — note in the report that adversarial review was not configured for this engagement, so this gate does not apply.

### Step 3: Compile Launch Gate Report

```markdown
## Launch Gate Report

**Date:** YYYY-MM-DD  
**Agent version:** [git SHA of agentic-data-stack-SKILL.md]

### Domain Status

| Domain | Pass Rate | Target | Status | Action |
|---|---|---|---|---|
| orders | 94% | 90% | ✅ CLEARED | Announce |
| customers | 91% | 85% | ✅ CLEARED | Announce |
| marketing | 78% | 80% | ❌ BLOCKED | Fix active_customers_region gap first |
| finance | 88% | 90% | ❌ BLOCKED | 2 revenue reconciliation questions failing |

**Cleared for launch: 2/4 domains**  
**Blocked: 2/4 domains**

### Adversarial Calibration Gate

| Adversarial review | Calibration pass rate | Threshold | Status |
|---|---|---|---|
| Enabled | 100% (5/5) | 80% (4/5) | ✅ CLEARED |

If blocked here, this overrides the per-domain table above — **no domain launches** until recalibrated, since the adversarial reviewer runs on every query regardless of domain. If adversarial review is disabled for this engagement, state that explicitly instead of this table ("Adversarial review: not configured for this engagement — gate not applicable").

### Blocked Domain Issues

**marketing — 78% (target: 80%)**  
Failing questions:
- marketing_007: active customers by region — missing region dimension on active_customers metric
- marketing_012: campaign ROAS including affiliate channel — affiliate not in fct_ad_spend

Required actions:
1. Add region dimension to active_customers_30d semantic model
2. Confirm affiliate channel treatment with marketing team — may need separate metric

**finance — 88% (target: 90%)**  
...
```

### Step 4: Update Status

```yaml
launch_gate:
  validate: complete
  validate_date: YYYY-MM-DD
  domains_cleared: ["orders", "customers"]
  domains_blocked: ["marketing", "finance"]
  overall_pass_rate: X%
  adversarial_calibration_gate: cleared   # cleared | blocked | not_applicable
  adversarial_calibration_pass_rate: X%   # omit or null if not_applicable
```

**If `adversarial_calibration_gate: blocked`**, `domains_cleared` must be empty regardless of what the per-domain eval numbers say — the adversarial gate blocks the whole launch, not individual domains.

## What To Do With Blocked Domains

Blocked domains need targeted fixes — not a full re-do. Common fixes:
- Missing dimension on a metric → add to semantic model, re-run `ads_semantic-layer-generate`
- Deprecated table still being queried → update DOMAIN_REFERENCE.md, re-test
- Plausibility bounds too tight → adjust in adversarial_config.yaml, re-validate

After fixing, re-run `ads_eval-suite-validate` for the affected domain only, then re-run this launch gate.
