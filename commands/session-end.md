---
description: DEPRECATED — session state is now written automatically after each Wire command completes
argument-hint: (optional: release-folder)
---

# DEPRECATED — session state is now written automatically after each Wire command completes

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
description: "DEPRECATED — session:end has been replaced by automatic state capture at the end of each Wire command"
deprecated: true
replaced_by: "Automatic session history rows written by each generate/validate/review command on completion"
since: "3.4.20"
---

# ⚠️ Deprecated: /wire:session:end

This command has been deprecated in Wire v3.4.20.

## Why it was removed

Telemetry analysis showed that `/wire:session:end` was almost never run. The command that was intended to close sessions and record what was done was the most-skipped command in the framework — meaning session history was almost never written. The design placed the responsibility for state persistence on the user, at a moment (end of session) when motivation is lowest.

## What replaces it

Every Wire generate, validate, and review command now **automatically appends a session history row** to `status.md` as its final step. State is written incrementally — after each artifact action — rather than batched at session end. This means session history is always up to date, even if the consultant closes their laptop without explicitly closing out.

The `execution_log.md` (which every command has always written to) remains the authoritative audit trail of all commands run.

**Research saving** — previously prompted by session:end — is now handled by the research persistence skill, which auto-activates when you perform significant technical research.

## Migration

- Remove any `/wire:session:end` invocations from your workflow
- Session state will be written automatically after each Wire command completes
- No action needed to preserve session history

Execute the complete workflow as specified above.
