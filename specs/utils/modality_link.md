---
wire_schema: "1.0"
command: utility
artifact: modality_link
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: path
      description: "--path <dir> the directory holding modality_project.yaml, when it cannot be found automatically"
produces:
  - type: status_update
    path: "status.md"
    description: "Records model_source: modality and modality_path"
preconditions: []
description: Locate the client's Modality model and record it on the release, so the design commands read the existing model instead of deriving one
argument-hint: <release-folder> [--path <dir>]
---

# Modality Link

## Purpose

Point a release at a Modality model that already exists, so
`conceptual_model-generate`, `logical_model-generate` and
`pipeline_design-generate` read it instead of deriving entities from scratch.

Sets two fields on `status.md`: `model_source: modality` and `modality_path`.

## Workflow

### Step 1: Find the model

Search in this order, stopping at the first hit:

1. `--path <dir>`, if given. A `--path` that holds no `modality_project.yaml` is a
   hard stop naming the path, not a fall-through to searching: the consultant has
   said where it is and being wrong about that is worth reporting.
2. `client_repo_local_path` from `status.md`, if set. Dedicated delivery repos keep
   the model in the client's own repository, not in the Wire repo.
3. The Wire repo root and one level down.

Report which of the three found it.

### Step 2: Confirm it is a model, not an empty scaffold

Read `modality_project.yaml`. Resolve its globs and count what actually exists:

```
Modality model found at <path>

  conceptual entities  : N across M domains
  relationships        : N explicit, N inline
  sources              : N
  entity resolutions   : N
  logical relationships: N

  cardinality readable from: logical_relationships.mml | relationship blocks | inline verbs | nowhere
```

The last line matters. Follow `specs/utils/mml_import.md`, "Cardinality
resolution". A model with zero conceptual entities is a scaffold, not a model, and
linking it would make the design commands produce empty documents: stop and say
so.

### Step 3: Record it

Update `status.md`:

```yaml
model_source: modality
modality_path: <path relative to the repo root, or absolute for a client repo>
modality_linked_date: [today]
```

Then report what changes as a result, so the consultant is not surprised later:

```
Linked. From now on in this release:

  conceptual_model-generate   reads entities, attributes and relationships
  logical_model-generate      reads sources, cardinality and entity resolutions
  pipeline_design-generate    reads the source list

  Each still reads the requirements, and each validate now runs the
  modality_coverage check in both directions.

  To unlink: set model_source: derived in status.md.
```

Follow `specs/utils/execution_log.md`.

## Unlinking

Setting `model_source: derived` is the whole of it. Nothing is deleted, and
documents already generated from the model keep their content and their citations.
