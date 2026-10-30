---
description: Validate Airflow ingestion DAGs with the Airflow rule lint and a parse check, with no live pipeline-tool call
argument-hint: <project-folder>
---

# Airflow Pipeline Validate

## Purpose

Check the ingestion DAGs the pipeline step built or changed. Two checks, both local: the Airflow rule lint and a parse check. No Fivetran, Airbyte or Airflow API call is made. Whether the change ran in dev is a separate question, answered by `/wire:utils-dev-test-evidence`.

## Called by

`wire/specs/development/pipeline/validate.md` when `pipeline_tool == airflow`

## Workflow

### Check 1: Rule lint

Resolve the rule file (`.wire/conventions/airflow.yml`, else Wire's `conventions/airflow.yml`) and run:

```bash
python3 <wire>/scripts/lint_conventions.py --domain airflow \
  --convention <resolved airflow.yml> --path <dag folder> \
  --changed-from <base branch> --format json
```

PASS when no error-severity finding is left on the changed files. Report every finding with its rule id, and the rules the client file disabled with their reasons (the `convention` block of the output).

### Check 2: Parse

For each changed DAG file, import it the way the scheduler does and confirm it builds at least one DAG with no import error:

```bash
python3 - <<'PY'
import sys
from airflow.models import DagBag
bag = DagBag(dag_folder="<dag file>", include_examples=False, safe_mode=True)
print({"dags": sorted(bag.dag_ids), "errors": bag.import_errors})
sys.exit(1 if bag.import_errors or not bag.dag_ids else 0)
PY
```

`safe_mode=True` matches the scheduler's default, so a file Airflow would skip (rule AF-006) builds no DAG here and fails. If Airflow is not installed locally, say so and use the client's own parse step from their CI (`/wire:utils-ci-parity`) or a container image their CI names. Never report a parse as passed without running one.

### Check 3: Coverage

Every load in `pipeline_connections.md` names a DAG file that exists and a DAG id that Check 2 found.

## Report

Write `.wire/<project_id>/development/pipeline/pipeline_validation.md` with one row per check (PASS / FAIL, evidence), then set `artifacts.pipeline.validate` to `pass` when all three pass, else `fail`.
