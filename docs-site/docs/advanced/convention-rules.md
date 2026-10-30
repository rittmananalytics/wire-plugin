---
sidebar_position: 16
title: Convention rules
---

# Convention rules

Wire checks code against rule files, one per domain: `dbt`, `lookml`, `cube`, `dbtcharts` and `airflow`. A script, `lint_conventions.py`, runs the rules that can be checked without an AI call. The rest are advice the skills apply. Wire's files are in `conventions/<domain>.yml`.

A client can keep its own rules in `.wire/conventions/<domain>.yml`. There are two ways to write that file.

## Replace Wire's rules

A client file without `extends` replaces Wire's file for the domain. Only the client's rules run. This is how client files have always worked.

## Add to Wire's rules: `extends: wire`

A client file with `extends: wire` keeps Wire's rules and adds the client's:

```yaml
schema_version: 1
domain: airflow
description: Our additions to Wire's Airflow rules.
extends: wire

configuration:
  - id: EX-001
    description: "No project name written into Python; read it from config."
    check: literal_value
    literal_patterns: ['^example-data-']
    severity: error

disable:
  - id: AF-103
    reason: "Our sensors run on a dedicated pool sized for long waits."
```

How the two files combine:

1. A client rule with a new id is added after Wire's rules.
2. A client rule with an id Wire already has replaces Wire's rule.
3. Settings (key and value sections) merge, the client's value winning.
4. Each entry in `disable` removes the Wire rule with that id. The reason is required.

The lint output names the rules the client switched off, with their reasons, so a reviewer can see them:

```text
Convention: .wire/conventions/airflow.yml extends Wire's conventions/airflow.yml
  Disabled by the client: [AF-103] Our sensors run on a dedicated pool sized for long waits.
```

`extends: wire` works for every domain. Switching off a rule is a decision: record it in the engagement's `decisions.md` with the same reason. The full field reference is in `wire/schemas/convention-schema.md`.

## Running the lint

```bash
# Whole folder: every finding listed as a warning, to see what to fix
python3 wire/scripts/lint_conventions.py --domain airflow \
  --convention .wire/conventions/airflow.yml --path dags/

# A branch: files it changed are held to each rule's severity
python3 wire/scripts/lint_conventions.py --domain airflow \
  --convention .wire/conventions/airflow.yml --path dags/ --changed-from main
```

Add `--format json` for a machine-readable report.
