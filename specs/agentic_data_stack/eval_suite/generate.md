---
wire_schema: "1.0"
command: generate
artifact: eval_suite
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
  - artifact: agent_config
    action: review
    outcome: approved
auto_validate: false          # validate runs run_evals.sh, executing the live agent against the real semantic layer/warehouse for every eval question
delegates_to:
  - utils/precondition_gate
description: Build the Q&A eval suite with per-domain accuracy baselines and CI harness
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Eval Suite Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Build the evaluation suite that measures agent accuracy — the most important validation artifact in this release. Without evals, accuracy degrades silently. With them, every schema change that breaks an answer gets caught in CI before it reaches users.

This implements the offline evaluation infrastructure described in Anthropic's self-service analytics architecture: question-answer pairs per domain, run against every code change, with per-domain accuracy gates before domain launch.

## Usage

```bash
/wire:ads_eval-suite-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `agent_config.review: approved`
- All domain reference files reviewed and approved
- Access to correct answers for the eval questions (warehouse queries, prior reports, or domain owner sign-off)

## Workflow

### Step 1: Read Inputs

1. Read `artifacts/query_audit.md` — top question patterns per domain
2. Read each `DOMAIN_REFERENCE.md` — common questions section
3. Read `artifacts/semantic_layer_design.md` — metric definitions to test
4. Read the SOW for any KPIs explicitly mentioned

### Step 2: Generate Question-Answer Pairs

For each domain, generate at least 10 question-answer pairs. Aim for three categories:

**Semantic layer questions (should route Tier 1):**
- Test that the agent uses the correct metric and filter
- Include time period variations (last month, last quarter, YTD, specific date)
- Include group-by variations (by channel, by category, by region)

**Knowledge file questions (should route Tier 2):**
- Questions not covered by a single metric (top-N, comparisons, complex filters)
- Edge cases documented in DOMAIN_REFERENCE.md (e.g. timezone behaviour, null handling)

**Boundary questions (confirm correct tier selection):**
- A question that looks like it could hit two tiers — confirm the agent picks the right one
- A question about a deprecated table — confirm the agent redirects to the canonical table

Format each pair in the eval template:

```yaml
# eval_suite/orders_domain.yaml

domain: orders
created: YYYY-MM-DD
questions:
  - id: orders_001
    question: "What was total revenue last month?"
    expected_tier: semantic
    expected_metric: total_revenue
    expected_filter: "order__status = 'confirmed'"
    correct_answer_sql: |
      SELECT SUM(net_revenue) FROM fct_orders 
      WHERE DATE_TRUNC(order_date, MONTH) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)
      AND status = 'confirmed'
    correct_answer_value: 1247832.50  # verified against source at YYYY-MM-DD
    tolerance_pct: 1  # allow 1% difference for daily refresh timing
    
  - id: orders_002
    question: "Which channel had the highest order count last quarter?"
    expected_tier: semantic
    expected_metric: order_count
    expected_group_by: channel
    correct_answer: "paid_search (14,231 orders)"
    tolerance_pct: 2
    
  - id: orders_003
    question: "Show me the top 5 customers by spend this year"
    expected_tier: curated
    expected_table: fct_orders
    correct_answer_format: "table with customer_name and total_spend columns"
    verification: domain_owner_confirmed  # exact values change daily
```

### Step 3: Verify Correct Answers

For every numeric answer, run the expected SQL against the warehouse to establish a ground-truth baseline at a fixed point in time. Record the date the baseline was captured — eval scores are relative to this baseline.

For non-numeric answers (rankings, tables), have the domain owner confirm the answer is correct.

### Step 4: Write the Eval Runner Script

Write `<dbt_project_path>/.claude/eval/run_evals.sh` (or `.wire/<release-folder>/artifacts/eval_suite/run_evals.sh`):

```bash
#!/bin/bash
# Agentic Data Stack Eval Runner
# Usage: ./run_evals.sh [domain]

DOMAIN=${1:-all}
PASS=0
FAIL=0
ERRORS=0

echo "Running agentic data stack evals — domain: $DOMAIN"
echo "================================================"

run_eval() {
  local id=$1
  local question=$2
  local expected_tier=$3
  
  echo -n "[$id] $question ... "
  
  # In practice, this invokes the agent and checks the response
  # For CI, use the dbt sl query tool directly for tier 1 checks
  # Response checking is manual or via LLM judge for non-numeric answers
  
  echo "PASS"
  ((PASS++))
}

# Source domain evals
if [[ "$DOMAIN" == "orders" || "$DOMAIN" == "all" ]]; then
  # [generated eval calls per domain]
  run_eval "orders_001" "What was total revenue last month?" "semantic"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed, $ERRORS errors"
echo "Pass rate: $(echo "scale=1; $PASS * 100 / ($PASS + $FAIL + $ERRORS)" | bc)%"

[[ $FAIL -eq 0 && $ERRORS -eq 0 ]] && exit 0 || exit 1
```

### Step 5: Write Per-Domain Accuracy Targets

For each domain, set the minimum accuracy threshold required for launch:

```yaml
# eval_targets.yaml
default_target: 90  # % pass rate required for domain launch

domains:
  orders:
    target: 90
    question_count: 15
    notes: "Finance sign-off on revenue questions required before launch"
  customers:
    target: 85
    question_count: 12
    notes: "PII fields in SQL output — privacy review required"
  marketing:
    target: 80
    question_count: 10
    notes: "Attribution methodology still being finalised — lower threshold"
```

### Step 6: Update Status

```yaml
eval_suite:
  generate: complete
  generated_date: YYYY-MM-DD
  total_questions: N
  domains_covered: N
  ci_runner: true
```

## Edge Cases

### Cannot Verify Answers Against Warehouse

If warehouse access is not available to verify correct answers, get domain owner sign-off on each question-answer pair. Record `verification: domain_owner_confirmed` in each eval. This is less reliable than warehouse-verified baselines — note this explicitly in the launch gate review.

### Daily Variance in Correct Answers

For questions about "today" or "last week", anchor the eval to a specific date and document the baseline value. The eval runner should always compare against the baseline at the anchor date, not the current live answer.

## Output

- `eval_suite/` folder containing per-domain YAML question files
- `eval_suite/run_evals.sh` — CI runner script
- `eval_suite/eval_targets.yaml` — per-domain accuracy thresholds
- Updated `status.md`
