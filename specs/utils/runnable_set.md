---
description: Internal utility — computes, for every artifact in a release, whether it is runnable, parked, blocked, not applicable or complete, from the release-type YAML, the active profile, status.md and decisions.md
---

# Utils — Runnable Set

A shared, deterministic procedure, not a command. Given a release, it answers
one question for every artifact in that release's graph: **what, if anything,
can be done to this artifact right now?**

Callers:

- `specs/autopilot.md` Step 4.3a, which used to hold its own copy of this
  topological read.
- `specs/start.md` Phase 3B, to compute the next action.
- `specs/delegate.md` Step 2, to decide what to dispatch and what can go in
  parallel.
- The `release-director` skill, on every directive.

There is one implementation of this rule so the orchestrator, Autopilot and
`/wire:start` cannot disagree about what comes next. In 3.x the sequence was
prose and every consumer kept its own copy, which is how Autopilot's
`full_platform` sequence lost the `orchestration` artifact.

## Inputs

| Input | Where from |
|---|---|
| Release type | `.wire/releases/<release>/status.md` front-matter: `project_type` if present, else `release_type`. Both are read because the shipped status templates are not consistent about which they write. `discovery` resolves to `discovery_shape_up.yaml`; every other value matches a file name directly. |
| The graph | `wire/release-types/<release_type>.yaml` — every `phases[].artifacts[]` entry, each carrying `id`, `command`, `required`, `sequence` and `depends_on`. Never fetched live; the synced local copy is the source. |
| Active profile | The field named by the release type's `profile_field`, read from `status.md`. Absent or blank falls back to `default_profile`. A value not in `profiles[]` is an error — stop and name the valid ids, do not fall back. |
| Artifact state | `status.md`'s `artifacts.<id>.{generate,validate,review}` values. |
| Rulings | `.wire/releases/<release>/decisions.md`, parsed per `specs/utils/director_operating_model.md` ("Rulings"). |

If the release type resolves to no YAML file, stop and say which value was
read and where from. Do not continue with no graph: an unknown release type is
a status-file error, and proceeding hides it.

## Output

For each artifact in the graph, exactly one state:

| State | Meaning |
|---|---|
| `runnable: generate` | `/wire:<command>-generate <release>` can be run now. |
| `runnable: validate` | `/wire:<command>-validate <release>` can be run now. |
| `runnable: review` | Never produced. See rule 4. |
| `parked: needs ruling` | A director decision is required before anything runs. Carries the question. |
| `blocked: <unmet precondition>` | A blocking `depends_on` entry is unmet. Carries the entry and the actual recorded value. |
| `not applicable` | The artifact is not part of this release under the active profile. |
| `complete` | Nothing left to do: generate complete, validate pass (or no validate command), review approved (or no review command). |

## Procedure

### Step 1: Resolve the graph and the profile

1. Read `project_type`, else `release_type`, from `status.md` front-matter.
   Translate `discovery` to `discovery_shape_up`. Load the YAML.
2. Read the profile field named by `profile_field` (if the release type
   declares one), falling back to `default_profile`. Validate it against
   `profiles[]`.
3. Apply the profile:
   - Every artifact in a phase listed in the profile's `disable_phases[]` is
     **`not applicable`**. It is removed from the graph for every purpose,
     including as a dependency of something else (see Step 3, rule 6).
   - A `phase_overrides[]` entry whose `id` matches a phase, naming an artifact
     under `artifacts[]`, **replaces** that artifact's `depends_on`. An
     override replaces the gate; it does not merge with it.
   - A phase in `enable_phases[]` is applicable even where its YAML entry says
     `required: false`.
4. Collect every remaining `phases[].artifacts[]` entry into one flat list.

This is the same resolution `specs/utils/precondition_gate.md` Step 0 performs
for a single command. Both read the same YAML with the same rules; this one
does it for the whole graph at once.

### Step 2: Classify each artifact's own progress

For each artifact, read `artifacts.<id>` from `status.md` and determine which
lifecycle steps the artifact has and which are done:

Which steps an artifact has comes from the command registry, not from the
artifact's name. Most artifacts carry a `generate`/`validate`/`review` triad
registered as `<command>/<step>`. A few — the `droughty/*` commands — are
registered as a single command with no lifecycle suffix; those have a
`generate` step and nothing else, which is what their `depends_on` entries
already assume (`action: generate`).

- `generate` is done when the recorded value is `complete`.
- `validate` is done when the recorded value is `pass` (case-insensitive). An
  artifact with no `validate` command has no validate step. Whether a validate
  command exists is read from the command registry, not guessed from the
  artifact name.
- `review` is done when the recorded value is `approved`. An artifact with no
  `review` command has no review step.
- An artifact whose `status.md` entry records `not_applicable` for a step skips
  that step.

An artifact whose every present step is done is **`complete`**. Stop there for
that artifact.

### Step 3: Resolve dependencies

For each not-yet-complete artifact, evaluate its (possibly profile-overridden)
`depends_on` list. Each entry is `{artifact, action, outcome}` plus an optional
`enforcement` of `blocking` (the default) or `advisory`.

An entry is **met** when `artifacts.<dep_artifact>.<dep_action>` in `status.md`
holds the required outcome, under the same comparison the precondition gate
uses: `complete` matches `complete`, `PASS` matches `pass` case-insensitively,
`approved` matches `approved`.

Rules, applied in order:

1. **Every entry met** → the artifact's gate is satisfied. Go to Step 4.
2. **Any blocking entry unmet** → `blocked: <dep_artifact>.<dep_action>
   required <outcome>, was <actual>`. List every unmet blocking entry, not just
   the first. Advisory ones are reported alongside as context.
3. **Only advisory entries unmet, and a matching ruling exists** → treat those
   entries as met. A ruling matches when its `Applies to:` line names this
   artifact **and** this dependency artifact, and it is marked `(advisory)`.
   Record the ruling id against the artifact; the precondition gate cites it in
   the override row when the command actually runs.
4. **Only advisory entries unmet, and no matching ruling** → `parked: needs
   ruling`, with the question "proceed without `<dep_artifact>`?". The
   orchestrator asks the director; a consultant typing the command by hand gets
   `precondition_gate.md` Step 2b instead, which is the same decision asked a
   different way.
5. **A ruling for a blocking entry is ignored.** A blocking gate is never
   satisfied by a ruling. It stays `blocked` until the upstream artifact
   actually reaches its required state, or a person takes the recorded override
   path in `precondition_gate.md` Step 3.
6. **A dependency on an artifact in a profile-disabled phase is met.** Under
   the `live_data` profile of `dashboard_first` the `seed_development` phase is
   disabled, so `dbt`'s dependency on `seed_data` cannot ever be satisfied by
   `seed_data` reaching a state. The profile's own `phase_overrides` normally
   replace the gate; where they do not, a dependency on an artifact the profile
   has ruled out is met rather than permanently blocking.

   **This covers disabled phases only, not merely optional artifacts.** An
   optional artifact nobody enabled is reported `not applicable`, but a
   dependency on it is resolved on its recorded state like any other, so an
   advisory gate on it still parks for a ruling. `business_rules` is the case:
   it is optional on every release type that carries it, and if being optional
   also satisfied its own advisory gate, the gate would never ask anything and
   the decision to skip it would never be recorded. That is the outcome the
   advisory enforcement level exists to prevent. `precondition_gate.md` Step 2b
   asks the same question of a consultant typing the command by hand.

### Step 4: Pick the runnable action

For an artifact whose gate is satisfied:

1. Generate not done → **`runnable: generate`**.
2. Generate done, validate present and not `pass`:
   - The generate command carries `auto_validate: false` → **`runnable:
     validate`**.
   - Otherwise validate has already run as part of generate
     (`specs/utils/auto_validate.md` chains it on 77 of 87 generate commands),
     so a validate that is not `pass` means it ran and failed. That is
     **`runnable: generate`** again, not a validate to re-run on its own.
3. Generate done, validate done (or absent), review present and not `approved`
   → **`parked: needs ruling`**, kind `review`, question "Approve now, request
   changes, or park for client sign-off?".

**Rule 4: a review edge is never `runnable`.** Reviews are not run without a
director ruling, in orchestrated mode or out of it. `runnable: review` is
listed in the output vocabulary only so that a caller reading this spec knows
the value exists and is never produced.

### Step 5: Order and parallelism

1. Order the runnable artifacts topologically by `depends_on`. Within a phase,
   and between artifacts with no dependency relationship, break ties by
   `sequence`.
2. Two runnable artifacts with **no dependency path between them** may run in
   parallel, up to `budget.lanes_max` (default 4; see
   `specs/utils/director_operating_model.md`). Beyond the limit, take them in
   the order from step 1 and queue the rest.
3. **Interactive artifacts run in the foreground, never as a lane.** An
   interactive artifact is one whose generate spec waits on the user mid-run —
   `mockups` in `dashboard_first` mode is the case that defines it. The
   artifact's own spec says so; an artifact whose generate spec has no
   user-input step is not interactive. An interactive artifact occupies the
   director, so nothing else is dispatched into the foreground alongside it,
   but non-interactive lanes continue in the background.
4. **Optional artifacts** (`required: false`) that the active profile has not
   enabled are `not applicable` and are not dispatched. They stay runnable on
   request: a director who asks for one gets it, and the request is what
   enables it.

## Worked example

`dashboard_first`, `seeded` profile, requirements approved and nothing else
started, with ruling R-1 on record: *skip business_rules, agree at kickoff*.

| Artifact | State | Why |
|---|---|---|
| `business_rules` | `not applicable` | Optional, not enabled. Its advisory gate on `conceptual_model` still had to be ruled on: see R-1. |
| `requirements` | `complete` | generate complete, validate pass, review approved |
| `workshops` | `runnable: generate` | Optional but requested by the director; gate (requirements approved) met |
| `conceptual_model` | `runnable: generate` | Blocking gate met; advisory `business_rules` gate met by R-1 |
| `mockups` | `runnable: generate` (foreground) | Gate met; interactive |
| `viz_catalog` | `blocked` | `mockups.review required approved, was not_started` |
| `data_model` | `blocked` | `viz_catalog.generate required complete, was not_started` |
| `seed_data` | `blocked` | Same |
| everything downstream | `blocked` | Same |

Two lanes and one foreground task: `conceptual_model` and `workshops` dispatch
as lanes, `mockups` runs with the director. Under `budget.lanes_max: 1`,
`conceptual_model` goes first (lower `sequence` in an earlier phase) and
`workshops` queues.

Under the `live_data` profile the same release resolves differently:
`seed_data` and `data_refactor` are `not applicable`, and `dbt`'s gate is the
override — `data_model.review approved` — so approving the data model releases
`dbt` directly.
