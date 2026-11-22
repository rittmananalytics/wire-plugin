---
wire_schema: "1.0"
command: generate
artifact: droughty_dbml
domain: droughty
release_types:
  - droughty
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: droughty_introspect
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Generate a DBML entity-relationship diagram from the live warehouse schema
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Droughty DBML Command

## Purpose

Run `droughty dbml` to produce a DBML entity-relationship diagram from the live warehouse schema. Infers relationships from `_pk` and `_fk` column-naming conventions. The resulting `.dbml` file can be rendered at dbdocs.io or dbdiagram.io and is stored in Wire's artifact directory for reference in subsequent phases.

## Usage

```bash
/wire:droughty-dbml <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete for this release
- Warehouse accessible

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Extract `warehouse`, `schemas`, `profile_name`

### Step 2: Run droughty dbml

```bash
droughty dbml \
  --profile-dir ~/.droughty \
  --project-dir .
```

This writes a `.dbml` file to `droughty_project.yaml → dbml_path`, which is `.wire/releases/[release]/artifacts/droughty/`.

Capture stdout and stderr. If the command exits non-zero, surface the full error output and stop.

### Step 3: Verify Output

Check that a `.dbml` file was written to the artifact directory. If the file is empty or absent:
```
⚠️  droughty dbml ran but produced no output.

Possible causes:
- No tables found in the configured schemas
- All tables were excluded in droughty_project.yaml
- A silent connection error occurred

Check the schemas listed in ~/.droughty/profile.yaml and re-run.
```

### Step 4: Summarise the ERD

Read the generated `.dbml` file and produce a brief summary for the consultant:
- Number of tables in the diagram
- Number of relationships inferred
- Any tables with no inferred relationships (isolated nodes)

### Step 5: Update status.md

```yaml
droughty:
  dbml:
    status: complete
    tables_in_diagram: [n]
    relationships_inferred: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/[filename].dbml
    completed_date: [today]
```

### Step 6: Confirm Output

```
## DBML Diagram Generated ✅

[n] tables, [n] relationships inferred from naming conventions

Artifact: .wire/releases/[release]/artifacts/droughty/[filename].dbml

To render the diagram:
  1. Visit https://dbdiagram.io or https://dbdocs.io
  2. Paste or upload the .dbml file
  3. Share the rendered link with stakeholders

This DBML artifact is available to:
  /wire:problem-definition-generate   — embeds the ERD as supporting evidence
  /wire:requirements-generate         — references the entity structure
```

**Note on relationship inference**: `droughty dbml` infers relationships from `_pk` / `_fk` column naming conventions — it does not read database constraints. Review the diagram for accuracy, especially on tables with non-standard naming.

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/[schema].dbml`
- Updated `droughty.dbml` block in `status.md`
