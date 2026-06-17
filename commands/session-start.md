---
description: DEPRECATED — context loading is now automatic via the engagement-context skill; use /wire:plan for optional structured planning
argument-hint: (optional: release-folder)
---

# DEPRECATED — context loading is now automatic via the engagement-context skill; use /wire:plan for optional structured planning

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
description: "DEPRECATED — session:start has been replaced by the engagement-context skill and /wire:plan"
deprecated: true
replaced_by: "engagement-context skill (auto-fires) + /wire:plan (optional planning ritual)"
since: "3.4.20"
---

# ⚠️ Deprecated: /wire:session:start

This command has been deprecated in Wire v3.4.20.

## Why it was removed

Telemetry analysis across six Wire engagements showed that session:start was rarely run consistently — consultants would begin work without invoking it, losing the planning benefit it was designed to provide. The root problem is that placing session lifecycle management in explicit commands puts the burden on the user to remember to run them. In practice, people just start working.

## What replaces it

**Context loading** is now handled by the **engagement-context skill**, which activates automatically whenever Claude detects a `.wire/` directory and has not yet established engagement context in the current conversation. No invocation required.

**Structured session planning** is available on demand via `/wire:plan`, for consultants who want the 3–5 step session plan before starting work. This is optional, not mandatory.

## Migration

- Remove any `/wire:session:start` invocations from your workflow
- Context will be loaded automatically when you begin work in a Wire engagement
- Run `/wire:plan` at the start of a session if you want an explicit plan before proceeding

Execute the complete workflow as specified above.
