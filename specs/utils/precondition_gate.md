---
description: Internal utility — resolves a command's declared preconditions against status.md and blocks by default when unmet; overrides require a recorded name and reason
---

# Precondition Gate Utility

Called at the start of any generate, validate, or review command whose own
front-matter declares a non-empty `preconditions` list. Confirms every
declared precondition is actually satisfied in `status.md` before the
calling spec does any substantive work — the enforcement half of the
`preconditions` field defined in `wire/schemas/command-schema.md`.

By default a consultant cannot skip a step this gate blocks. They can
override it, but the override is always recorded against their name with
their stated reason — never silent.

This is distinct from `stale_artifact_check.md` (asks whether to overwrite
an already-generated artifact) and `migration_preflight.md` (checks a batch
is safe to start). This gate asks a narrower question: is it even legitimate
to run this command yet, given what upstream artifacts have and haven't
completed.

## Inputs (read directly from the calling spec — no params to pass)

- `preconditions` — this command's own front-matter value: a list of
  `{artifact, action, outcome}` entries, the literal string `dynamic` (see
  Step 0), or absent/`[]`. If absent or `[]`, this gate is a no-op: return to
  the calling spec immediately with no output.
- `artifact` and `command` — this command's own front-matter values, used to
  label the override record and to compose the remediation command hint.
- `release_folder` — the release folder path passed to the calling spec.

## Procedure

### Step 0: Resolve `dynamic` preconditions, if declared

A handful of artifacts are shared across multiple release types whose
`wire/release-types/*.yaml` disagree on what gates them (e.g. `dbt-generate`
needs different upstream approval depending on whether the release is
`full_platform` or `dashboard_first`). Those commands declare
`preconditions: dynamic` in front-matter instead of a static list, since a
single static list would be right for one release type and wrong for
another.

If `preconditions` is the literal string `dynamic`:

1. Read `.wire/releases/<release_folder>/status.md` front-matter. Take
   `project_type` if present, else `release_type`. The shipped status
   templates are not consistent about which of the two they write:
   `status-template.md` and `custom-status-template.md` write `project_type`,
   while `discovery-status-template.md`, `droughty-status-template.md` and
   `sop-discovery-status-template.md` write only `release_type`. Reading one
   name resolved to nothing for every release created from the latter three,
   so the gates and the profile silently did not resolve. `autopilot.md`
   Step 4.3a already reads both; this is the same rule in the same words.
2. Load `wire/release-types/<that value>.yaml`. Find this command's own
   `artifact` value under `phases[].artifacts[].id`.

   One value needs translating. The Shape Up discovery release records
   `release_type: discovery`, which is canonical: the v3.5.0 rename to
   `shape_up_discovery` was reverted in v3.5.1 and `migrate.md` Case C
   normalises repos back to it. Its release-type file is
   `discovery_shape_up.yaml`. Treat `discovery` as `discovery_shape_up`.
   No other value needs translating; the rest match a file name directly.

   If the resolved value matches no file, stop and say so, naming the value
   and where it was read from. Do not continue with no gate: an unknown
   release type is a status-file error, and proceeding hides it. This is
   different from rule 4 below, where the release type is known and simply
   does not carry the artifact.
3. If found, use that entry's `depends_on` list as the effective
   preconditions for Step 1 below (an empty `depends_on: []` is a valid
   result — proceed with no gate, same as a static `preconditions: []`).
4. If this artifact doesn't appear in that YAML at all, treat it the same as
   an empty list — proceed with no gate. (Not every release type uses every
   shared artifact — e.g. `dbt_development` has no `mockups` phase at all.)
5. **Apply the active profile's overrides, if the release type declares any.**
   Some release types offer more than one route through the same pillars, and
   the routes disagree on order — `sop_discovery`'s `modelling_led` profile
   signs the roadmap off *at* the playback, where `diagnostic` produces it
   *after*. A release type expresses that with a `profiles:` block and a
   `default_profile`, and a release records its choice in `status.md`.

   Resolve it in this order:

   a. Read the profile field named by the release type's `profile_field`
      (`sop_discovery` uses `discovery_profile`) from `status.md`
      front-matter. If the field is absent or blank, use `default_profile`.
   b. If the resolved profile id is not in `profiles[]`, stop and report the
      mismatch naming the valid ids. Do not fall back to the default: a
      release recording a profile the release type does not define is a
      status-file error, and guessing hides it.
   c. If that profile has a `phase_overrides[]` entry whose `id` matches the
      phase this artifact sits in, and that entry names this artifact under
      `artifacts[]`, use the override's `depends_on` **in place of** the list
      from step 3. An override replaces the gate; it does not merge with it.
   d. A phase in the profile's `disable_phases[]` is not applicable to this
      release. If the artifact being gated sits in a disabled phase, stop and
      report that the artifact is not part of the active profile, naming the
      profile and the phase. This is not a precondition failure and it is not
      overridable — running it would produce an artifact nothing downstream
      reads.
   e. A phase in `enable_phases[]` is applicable even though its YAML entry
      says `required: false`. `required` describes the default; the profile
      decides applicability.

Then continue to Step 1 using the resolved list in place of the front-matter
value.

**Phases that are off, versus artifacts that are merely optional.** An
optional artifact (`required: false`) that the active profile has not enabled
is skippable and not an error — `/wire:status` reports it as not applicable
rather than not started, and nothing downstream gates on it. A *disabled*
phase is stronger: the profile has ruled it out, so the command refuses in
step (d) above.

### Step 1: Check each precondition against status.md

Read `.wire/releases/<release_folder>/status.md`. For each `{artifact, action,
outcome}` entry in the (possibly Step-0-resolved) `preconditions`:

1. Look up `artifacts.<artifact>.<action>` in status.md.
2. Compare against the required `outcome`:
   - `outcome: complete` → recorded value must be `complete`
   - `outcome: PASS` → recorded value must be `pass` (case-insensitive)
   - `outcome: approved` → recorded value must be `approved`
3. Record whether each precondition is **met** or **unmet**. For unmet ones,
   capture the actual recorded value (or `not_started` if the key is absent)
   for the blocker message.

If every precondition is met, return to the calling spec immediately with no
output — this gate adds no friction to the compliant path.

### Step 1b: Separate blocking preconditions from advisory ones

A `depends_on` entry may carry `enforcement: blocking` (the default, and the value
assumed when the key is absent) or `enforcement: advisory`.

An advisory precondition is one where running without it is a real choice a
consultant may legitimately make, and where blocking would produce a skipped gate
rather than a met one. `business_rules` is the case that introduced it: agreeing
what the numbers mean before design is right, and making it a hard gate on a team
that already skips gates yields a bypass, not a register.

Sort the unmet preconditions into two lists. If every unmet precondition is
advisory, go to Step 2a. If any unmet precondition is blocking, go to Step 2 and
report the advisory ones alongside as context.

### Step 2: Block by default

If any precondition is unmet, stop and output:

```
🚫 Precondition not met — <artifact>/<command> requires:
  - <dep_artifact>.<dep_action> = <required_outcome>   (currently: <actual_value>)
  [one line per unmet precondition]

This step is gated by default. Run the blocking command(s) first:
  /wire:<dep-artifact-with-dashes>-<dep_action> <release_folder>

A consultant can override this gate, but the override is recorded against
their name with a reason — it is never silent.

Override and proceed anyway? (yes / no)
```

- **no** — output `Stopping — clear the blocker(s) above, then re-run.` and do
  not proceed with the calling spec's workflow.
- **yes** — continue to Step 3.

### Step 2a: Advisory — look for a ruling first

Before asking anything, read
`.wire/releases/<release_folder>/decisions.md` for a ruling that covers this
advisory precondition. Rulings are written by the release director the moment
they are given, in the structured form specified in
`specs/utils/director_operating_model.md` ("Rulings"):

```markdown
## R-3 | 2026-09-02 14:12 | Mark Rittman | skip business_rules
Applies to: conceptual_model.depends_on.business_rules (advisory)
Ruling: skip. Reason: agree metric definitions at kickoff, 2026-09-09.
```

A ruling **matches** an unmet advisory precondition when all three hold:

1. Its `Applies to:` line names **this** artifact (the one being gated) as the
   first element, and **this** unmet precondition's dependency artifact as the
   `depends_on.<dep_artifact>` element. A ruling for a different artifact's
   gate on the same dependency does not match — a decision to skip
   `business_rules` before `conceptual_model` says nothing about skipping it
   before `data_model`.
2. It is marked `(advisory)`.
3. Its `Ruling:` line says to proceed (`skip`, `proceed`, `waive`). A ruling
   that says to wait does not satisfy the gate; it is a decision to stop.

If a matching ruling exists for **every** unmet advisory precondition:

- Do not ask for a reason. Use the ruling's own `Reason:` text as the recorded
  skip reason.
- Record the skip in `status.md` under `advisory_skips` exactly as Step 2b
  does, with `ruling: R-<n>` added to the entry.
- Write the `override` row to `execution_log.md` per
  `specs/utils/execution_log.md`, with the ruling id in the Detail string:
  `<dep_artifact>.<dep_action> required <outcome>, was <actual> — ruling R-<n>
  (<director name>): <reason>`.
- Output one line, `⚠️  Advisory precondition waived by ruling R-<n> —
  <reason>.`, and proceed to the calling spec's workflow.

If some unmet advisory preconditions have a matching ruling and some do not,
apply the rulings that matched and continue to Step 2b for the rest. Ask only
about the ones no ruling covers.

**Rulings never satisfy a blocking precondition.** This step runs only on the
advisory branch. A blocking precondition reached Step 2, and the only way past
it is the recorded override in Steps 3 to 5 — a real person's name and a real
reason, given at the time. A ruling in `decisions.md` is not a substitute for
that and is ignored there.

If no ruling matches, continue to Step 2b.

### Step 2b: Advisory — warn, ask for a reason, proceed

Where every unmet precondition is advisory and no ruling covers it, do not
block. Output:

```
⚠️  Advisory precondition not met

  business_rules review: not_started
    Recommended before conceptual_model, so a definition is agreed before the
    design bakes one in.

  Proceeding without it is allowed. Skipping is recorded, not assumed.

  Reason for proceeding (one line):
```

Take the consultant's one-line reason. Then record the skip in `status.md` under
`advisory_skips`, and write an `advisory_skip` entry to `execution_log.md` naming
the artifact, the unmet precondition, the reason and the date.

A blank reason is not accepted. Ask once more, and if it is blank again, record
`reason: none given` rather than looping — the record of the skip matters more
than the quality of the reason, and a consultant in a hurry should not be trapped
by a prompt.

Then proceed to the calling spec's workflow.

**Why a reason at all.** Recommendation R6 in the Hunkemöller usage review found
seven releases with no recorded review and a reverted change that had gone in
without one, and concluded that a deliberate skip should be visible rather than
absent. An advisory gate that logged nothing would be indistinguishable from a
gate nobody had thought about.

### Step 3: Capture the override

Prompt:

```
Overriding requires your name and a reason. Both are required.

Your name:
Reason for overriding:
```

Both fields must be non-empty. Re-prompt on a blank answer — there is no
anonymous or unexplained override path.

### Step 4: Record the override

Update `.wire/releases/<release_folder>/status.md`:

1. Append one entry per unmet precondition to a top-level `precondition_overrides`
   array in the front-matter (create the array if it doesn't exist yet):

```yaml
precondition_overrides:
  - artifact: <artifact>
    action: <command>
    unmet_precondition: "<dep_artifact>.<dep_action> required <required_outcome>, was <actual_value>"
    overridden_by: "<consultant name>"
    reason: "<reason>"
    date: "{{TODAY}}"
```

2. Set `artifacts.<artifact>.gate_overridden: true` so the override is visible
   on the artifact's own status entry, not just in the override log.

3. Add or update a `## Precondition Overrides` section in the body of
   `status.md` (same visibility pattern as the existing `## Blockers`
   section):

```markdown
## Precondition Overrides

| Date | Artifact | Action | Unmet Precondition | Overridden By | Reason |
|------|----------|--------|---------------------|---------------|--------|
| {{TODAY}} | <artifact> | <command> | <dep_artifact>.<dep_action> required <required_outcome>, was <actual_value> | <consultant name> | <reason> |
```

### Step 5: Log and proceed

Append a row to `.wire/releases/<release_folder>/execution_log.md` following
`specs/utils/execution_log.md`, using `override` as the Result and a Detail
string of `<dep_artifact>.<dep_action> required <outcome>, was <actual> —
overridden by <name>: <reason>` (truncate to keep the row under 120
characters; replace any `|` with `—`).

Output `⚠️  Proceeding with override — recorded against <name>.` and return
control to the calling spec to continue its normal workflow.
