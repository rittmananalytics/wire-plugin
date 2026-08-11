---
description: Internal utility — detects whether an artifact was already generated and prompts before overwriting
---

# Stale Artifact Check Utility

Called at the start of any generate command before doing substantive work. Detects whether the artifact has already been generated and prompts the user before overwriting.

## Inputs (provided by the calling spec)

- `artifact_id` — the key in `status.md` under `artifacts` (e.g. `ingestion_migration`)
- `artifact_file_path` — the expected output file path (e.g. `migration/ingestion_migration_runbook.md`)

## Procedure

### Step 1: Check for prior generation

Read `.wire/releases/<release-folder>/status.md`. Look up `artifacts.<artifact_id>`.

If `generate: complete` is present, extract:
- `generated_date`
- `file` (the recorded output path)

Also check whether the file at `artifact_file_path` exists on disk.

### Step 2: Prompt if already complete

If `generate: complete` in status.md **or** the output file exists on disk:

```
⚠️  This artifact was already generated.

  Artifact:   <artifact_id>
  Generated:  <generated_date>  (or "unknown" if date not recorded)
  File:       <artifact_file_path>

Re-generate? The existing file will be overwritten. (yes / no)
```

Wait for the user's response.

- **no** — output `Skipping — existing artifact is current.` and stop. Do not proceed with the calling spec's workflow.
- **yes** — output `Re-generating <artifact_id> — previous output will be overwritten.` and return to the calling spec to continue.

### Step 3: First-time generation

If `generate` is not `complete` and the file does not exist, return to the calling spec immediately with no output. The check adds no friction to the first-time path.
