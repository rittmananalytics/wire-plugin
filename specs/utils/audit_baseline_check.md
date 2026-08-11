---
description: Internal utility — confirms a declared audit baseline exists, has substantive content, and reconciles cited figures before an audit-generate command builds on it
---

# Audit Baseline Check Utility

Called at the start of an audit-generate command whenever the release declares a baseline (prior-audit) path for that artifact. Confirms the baseline actually exists and has substantive content before the new audit is allowed to build on it, and reconciles any figures the release's brief, SOW, or `status.md` cites against what the baseline actually contains — surfacing a mismatch before generation, not after a client reads the report.

This exists because of a real client migration ([wire#113](https://github.com/rittmananalytics/wire/issues/113)): a security-audit brief pointed at an empty prior-release baseline folder and cited role/PII figures that didn't match reality. Only a human consultant caught it before delivery — nothing in the framework did. This is distinct from `stale_artifact_check.md` (which asks whether to overwrite *this run's own* already-generated output) and from `migration_preflight.md` (which gates build-time readiness of sources/targets for `dbt_migration`/`reverse_etl_migration`). This gate is about whether the *input* being cited or built upon — a prior audit or artifact — is actually there and actually says what it's assumed to say.

## Inputs (provided by the calling spec)

- `artifact_id` — the key in `status.md` under `artifacts` (e.g. `security_audit`)
- `baseline_path` — read from `artifacts.<artifact_id>.baseline_path` in `status.md`. This is the settled field name for "a prior audit/artifact this generate run is meant to build on or compare against" — set it under the artifact it applies to, e.g.:
  ```yaml
  artifacts:
    security_audit:
      baseline_path: ../release-04-lift-and-shift/audit/security_audit.md
  ```
  A path may point at a single file or a folder (e.g. a prior release's whole `audit/` directory). `null` or absent means no baseline is declared for this run — the check does not run at all (see Step 0).
- `cited_figures` — the specific figures (role count, PII field count, user count, model count, etc.) that the release's brief, SOW, or `status.md` narrative cites as already-known facts about the baseline this run is meant to support or compare against. Pull these from `.wire/releases/<release_folder>/engagement_brief.md` (or `brief.md`) if present, and from any narrative note in `status.md` under the artifact's block or `notes`.

## Procedure

### Step 0: Determine whether this check applies

Read `artifacts.<artifact_id>.baseline_path` from `status.md`.

- Absent or `null` — this run has no declared baseline. Return to the calling spec immediately with no output. Do not invent a baseline check for a release that isn't using one.
- Present — continue to Step 1.

### Step 1: Baseline path exists and has substantive content

- Confirm `baseline_path` resolves to something that actually exists — a file or folder on disk, or at the configured docstore location if the path is a docstore reference rather than a filesystem path.
- **FAIL** if the path does not exist.
- If it resolves to a folder, confirm it contains at least one file with substantive content — non-zero bytes, and not just a placeholder or README stub. **FAIL** if the folder is empty or contains only stub files.
- If it resolves to a single file, confirm it has substantive content — not an unrendered template (unfilled `{{PLACEHOLDER}}` tokens throughout) and not a near-empty stub. **FAIL** if the file is empty, all-placeholder, or otherwise has nothing to compare against.

Do not proceed to Step 2 or to generation on a Step 1 failure — go straight to the Gate step below.

### Step 2: Cited figures reconcile against the baseline's actual content

Skip this step if no `cited_figures` were found — nothing in the brief, SOW, or `status.md` cites a specific number against this baseline. Record that in the log and continue to the Gate step.

For each cited figure (e.g. "42 roles", "12 PII fields", "230 models"):

- Locate the corresponding count inside the baseline artifact itself — its summary table, its own `artifacts.<artifact_id>` status block if the baseline's source release is reachable, or narrative counts in its body.
- Compare the cited figure against what the baseline actually contains.
- **WARN** (do not fail the gate) on any mismatch — record the cited value, the baseline's actual value, and the source of the citation (brief / SOW / status.md notes).

A mismatch here is a warning rather than a hard fail because the cited figure, not the baseline, may be the one that's wrong — the point is to put the discrepancy in front of a person, not to guess which side to trust. Surface every mismatch found; never silently pick one side and proceed as if it were resolved.

### Step: Log the result

Append a record to `.wire/releases/<release_folder>/execution_log.md`, capturing: timestamp, `artifact_id`, `baseline_path`, Step 1 PASS/FAIL, whether Step 2 ran, the count of cited-figure mismatches found, and the mismatch list.

### Step: Gate

**Step 1 FAILS** — output the blocker under a heading and **stop**:

```
🚫 Baseline check failed — not generating <artifact_id> from <baseline_path>:

  - <reason: path does not exist | folder is empty | file has no substantive content>

Supply a valid baseline at <baseline_path>, or clear
artifacts.<artifact_id>.baseline_path in status.md if no baseline comparison
is intended, then re-run.
```

Do not generate off a missing or empty baseline. The caller does not proceed until a valid baseline is supplied, or `baseline_path` is deliberately cleared, and the check is re-run.

**Step 1 PASSES** — output `[wire] Baseline check passed for <artifact_id> — using <baseline_path>.`

If Step 2 found one or more mismatches, also output, before returning to the calling spec:

```
⚠️  Baseline figures do not match the brief/SOW/status.md citation for <artifact_id>:

  Cited: <figure> = <cited_value>  (source: <brief | SOW | status.md>)
  Found in baseline: <figure> = <baseline_value>

Resolve which figure is correct before generating — a report that repeats a
wrong cited figure will not be independently caught downstream. (use baseline
figure / correct the citation / stop and investigate)
```

Wait for the user's direction on how to proceed. Only return to the calling spec to continue generating once the mismatch has been acknowledged or resolved.

If Step 2 found no mismatches (or did not run), return to the calling spec immediately to continue generating.
