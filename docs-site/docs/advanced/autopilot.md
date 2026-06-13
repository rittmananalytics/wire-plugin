---
sidebar_position: 2
title: Wire Autopilot
---

# Wire Autopilot

Wire Autopilot runs Wire commands non-interactively — you give it a release folder and a target phase, and it executes the generate → validate → review cycle for every artifact in that phase, pausing only when it encounters a validation failure or a review decision that requires human input.

Autopilot is designed for the "known path" phase of an engagement — once the requirements artifacts are approved and the shape of the work is stable, you can hand the development and testing phases to Autopilot and return for the review gates.

## Starting Autopilot

```
/wire:autopilot <release-folder> --phase <phase-name>
```

Examples:

```
/wire:autopilot 20240115_barton_peveril_full_platform --phase development
/wire:autopilot 20240115_barton_peveril_full_platform --phase testing
/wire:autopilot 20240115_barton_peveril_full_platform --from requirements --to testing
```

`--from` and `--to` run all phases between two named phases, inclusive. Phases are ordered: `requirements` → `design` → `development` → `testing` → `deployment` → `enablement`.

## How it works

For each artifact in the phase, Autopilot runs:

1. `generate` — creates the artifact
2. `validate` — runs automated checks
3. If validation passes: records the result and moves to the next artifact
4. If validation fails: pauses, presents the failures, and waits for instruction

At review gates (`-review` commands), Autopilot presents the artifact and pauses for explicit human approval. You can:
- **Approve** — Autopilot marks it Approved and continues
- **Request changes** — provide feedback inline; Autopilot re-generates with the feedback incorporated and presents it again
- **Delegate** — Autopilot emails the artifact link to the named stakeholder and monitors for a reply

## Handling validation failures

When a validation failure occurs mid-run, Autopilot presents a triage menu:

```
VALIDATION FAILURE: dbt-models-validate (students domain)
  ✗ not_null test on student_pk failing (14 rows)

What would you like to do?
  [1] Auto-fix — apply the recommended fix and re-validate
  [2] Skip and continue — mark as known issue, continue to next artifact
  [3] Pause here — stop Autopilot and return control
  [4] Edit fix — show the recommended fix before applying it
```

Option 1 is available when Wire has a high-confidence fix (single-cause failures with a clear remediation). Options 2–4 are always available.

## Progress display

While running, Autopilot shows a live progress board:

```
Wire Autopilot — 20240115_barton_peveril_full_platform / development
─────────────────────────────────────────────────────────────────────

  ✓  ingestion-generate          completed  12:34
  ✓  ingestion-validate          completed  12:36
  ✓  ingestion-review            approved   12:41 (Mark Rittman)

  ✓  dbt-models-generate (students)     completed  13:02
  ⚠  dbt-models-validate (students)     1 failure — awaiting decision
  …  dbt-models-generate (finance)      queued

  Time elapsed: 47 min   Artifacts remaining: 7
```

## Resuming after a pause

If Autopilot is interrupted — by a validation failure, a browser close, or a session timeout — it can resume from where it stopped:

```
/wire:autopilot 20240115_barton_peveril_full_platform --resume
```

Autopilot reads the execution log, identifies the last completed artifact, and picks up from the next one. Completed artifacts are not re-run unless you pass `--force`.

## Review delegation

For review artifacts, Autopilot can delegate to a named stakeholder rather than waiting for your approval:

```
/wire:autopilot 20240115_barton_peveril_full_platform --phase requirements \
  --delegate-reviews "jane.smith@client.com"
```

With this flag, each `-review` command emails the artifact to `jane.smith@client.com` with a review link. Autopilot monitors for a reply and continues once the artifact is marked Approved. If no reply arrives within the configured timeout (default 24 hours), Autopilot pauses and notifies you.

## Dry run mode

Preview what Autopilot would execute without running anything:

```
/wire:autopilot 20240115_barton_peveril_full_platform --phase development --dry-run
```

This prints the full execution plan — every command in order, with estimated duration — and exits without running anything.

## Configuring Autopilot

Autopilot settings live in `.wire/releases/<release>/autopilot.yaml`:

```yaml
auto_fix: true                  # apply high-confidence fixes automatically
review_timeout_hours: 24        # how long to wait for delegated reviews
notify_on_failure: mark.rittman@rittmananalytics.com
skip_known_issues: false        # re-run artifacts with previously recorded failures
```

## What Autopilot cannot do

- Make judgment calls about stakeholder feedback — a stakeholder reply that contains conflicting instructions will cause Autopilot to pause and ask you to arbitrate
- Execute destructive deployment steps (database drops, Fivetran connector deletions, cutover) — these always require manual confirmation regardless of Autopilot mode
- Approve its own review artifacts — every `-review` command requires a human approval, even in fully automated runs
