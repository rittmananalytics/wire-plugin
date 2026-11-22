---
wire_schema: "1.0"
command: utility
artifact: session
domain: session
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: "DEPRECATED — session:start has been replaced by the engagement-context skill and /wire:session-plan"
deprecated: true
replaced_by: "engagement-context skill (auto-fires) + /wire:session-plan (optional planning ritual)"
since: "3.4.20"

---

# ⚠️ Deprecated: /wire:session-start

This command has been deprecated in Wire v3.4.20.

## Why it was removed

Telemetry analysis across six Wire engagements showed that session:start was rarely run consistently — consultants would begin work without invoking it, losing the planning benefit it was designed to provide. The root problem is that placing session lifecycle management in explicit commands puts the burden on the user to remember to run them. In practice, people just start working.

## What replaces it

**Context loading** is now handled by the **engagement-context skill**, which activates automatically whenever Claude detects a `.wire/` directory and has not yet established engagement context in the current conversation. No invocation required.

**Structured session planning** is available on demand via `/wire:session-plan`, for consultants who want the 3–5 step session plan before starting work. This is optional, not mandatory.

## Migration

- Remove any `/wire:session-start` invocations from your workflow
- Context will be loaded automatically when you begin work in a Wire engagement
- Run `/wire:session-plan` at the start of a session if you want an explicit plan before proceeding
