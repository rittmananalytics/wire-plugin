---
sidebar_position: 8
title: Testing Wire Itself
---

# Testing Wire Itself

If you are changing Wire itself rather than using it on an engagement, sooner or later you will want to know what stands between a mistaken edit to a spec and that mistake reaching a consultant's machine. This page documents Wire's own automated test suite: how the framework tests itself, not how to test a client's data platform. Every spec change, every new command and every release goes through the same tiered suite described below.

The full suite lives under `wire/tests/` and runs via a single entry point:

```bash
bash wire/tests/run_all.sh
```

This is the same command that `.github/workflows/spec-lint.yml` runs on every push and pull request, and the same command that `wire/scripts/release.sh` refuses to cut a release without passing first.

## Why Wire has a test suite at all

Why test a set of Markdown files? Wire's specs are markdown files that an LLM reads and follows, and there is no compiler to catch a broken cross-reference, a contradictory naming rule or a missing command registration. Left unchecked, specs "drift": two files state a naming convention differently, a template is missing a field a command tries to write, a command is documented but never registered so that `/wire:foo-generate` does not actually install. The test suite exists to catch exactly that class of bug, through structural corpus-wide checks (Tier 0) together with real, runnable Python that re-implements a spec's own decision logic and checks it against fixtures (Tier 1), rather than relying on manual review to notice when 333 command specs drift out of sync with each other.

## The four tiers

The suite is arranged in four tiers, each catching a class of problem the one before it cannot, and we look at each in turn.

### Tier 0 — spec-corpus lint

**What it checks**: every spec file in `wire/specs/`, corpus-wide, for structural correctness: not what a command *does*, but whether the file itself is well-formed and consistent with the rest of the repo.

- Frontmatter validity (`description:`, `argument-hint:` where required)
- The generate/validate/review triad shape: every artifact should have all three commands, unless it is a documented exception (see `known_exceptions.yaml` below)
- Cross-references that actually resolve (a spec referencing `specs/utils/foo.md` must have that file exist)
- Command registration in `wire/scripts/build-packages.sh`: a spec file with no corresponding entry in the `COMMANDS` array will never actually install as a slash command
- Version consistency: `docs-site/docs/intro.md`'s homepage version badge must match `plugin.json`'s version. This check exists because the badge silently drifted for four straight releases (v3.10.3–v3.10.6) before anything caught it; `release.sh` now bumps it automatically, and this check is the backstop if that step is ever skipped or the badge is edited by hand
- Client-name leakage: every file that ships in a plugin package, or lives in this repo's specs/skills/docs/changelogs, is scanned against `wire/tests/known_client_names.yaml`, a curated (deliberately non-exhaustive) blocklist of real client names, engagement codenames and client-side individual names confirmed to have leaked into shipped content before. A hit fails the build. Add an entry here the moment a real name is confirmed to have leaked, but do not add speculative names, since an over-broad blocklist trains people to ignore Tier 0 failures

**How it runs**: `wire/tests/lint_specs.py`, invoked as part of `run_all.sh`.

**`known_exceptions.yaml`**: not every artifact fits the generate/validate/review triad. `mockups` has no validate step, `viz_catalog` has neither validate nor review and `uat` is a human acceptance exercise with no automated validate step at all. Rather than have the linter silently ignore these or hard-code them inline, `wire/tests/known_exceptions.yaml` documents each intentional deviation explicitly, with a reason, and the linter cross-checks against this file, so that an undocumented deviation is a real Tier 0 failure while a documented one passes.

### Tier 1 — deterministic-logic behavioural tests

**What it checks**: where a spec embeds a genuine decision algorithm in its prose (a classification rule, a graph-selection grammar, a gating condition, a tagging scheme), that logic is extracted into small, runnable Python and checked against hand-built fixtures with known-correct expected outputs. This catches the class of bug Tier 0 cannot: the *rule itself* being wrong, self-contradictory or ambiguous, not just the file being malformed.

Each release-type namespace under `wire/tests/<release_type>/` follows the same shape:

- `validate_specs.sh`: a bash structural check specific to that namespace (frontmatter, section presence, command registration), using a `check()` helper and PASS/FAIL counters
- `validate_<topic>.py`: the actual behavioural test, which is stdlib-only Python with no LLM calls, reading a `fixture/<topic>.json` (or similar) input and an `expected/<topic>.json` known-correct output and diffing the two
- `README.md`: what the suite covers, how to run it, how to interpret a failure and how to update the fixtures when the underlying spec changes

Coverage spans every release type: `platform_migration` (feature detection, materialization preservation, region tagging, dbt node-selection grammar, migration-batching SCC/wave topology), `agentic_data_stack` (metric/query audit coverage classification, canonical-models deprecation tagging), `core` lifecycle commands, `development` (dbt naming conventions, Fivetran sync-frequency tiers), `discovery` (sprint-plan capacity/appetite math), `sop_discovery` (the four-tag stakeholder-interview rule, the sponsor-validation checklist gate, requirements traceability), `droughty` (PK/FK inference, `generate.md`'s mode/step orchestration) and `misc_release_types` (kickoff-deck validation, the deployment cutover-order dependency rule).

**Since v4.0.0, six of these cover the release director model** (`wire/tests/core/`), because it is entirely deterministic rule-following of the kind a spec can state ambiguously:

| Test | What it pins down |
|---|---|
| `validate_runnable_set.py` | One fixture per shipped release type, plus profile resolution, rulings, review edges, `auto_validate: false` and `lanes_max`. Reads the real `wire/release-types/*.yaml` and the live command registry, so it fails if the rule and the graph drift apart. |
| `validate_release_claim.py` | claim / resume / ask-to-join / offer-take-over, the 30-minute stall boundary and `dispatch_allowed` asserted separately from the outcome, because what the rule stops is the point of it. |
| `validate_active_release.py` | Named release, branch match, single recent write and the ask cases the old "most recently modified" rule got wrong. |
| `validate_ruling_gate.py` | Including a ruling that names a blocking gate precisely and is still ignored. |
| `validate_execution_log_order.py` | Row ordering, unparseable timestamps and legacy four-column rows staying valid. |
| `validate_orchestration_mode.py` | Full precedence, both override directions and a typo in `orchestration.mode` falling through to the default rather than switching the model off silently. |

Two of those tests found genuine ambiguities in the specs as first written, and these were fixed at source rather than encoded as an expected value: an over-broad rule that let an optional artifact satisfy its own advisory gate, and an unstated answer to where an artifact's lifecycle steps come from.

**A genuine ambiguity is not a bug.** Where a spec's prose is read literally but two equally-defensible interpretations exist, and the spec itself never states a precedence, the test fixture marks that case `"ambiguous": true` (or prints it as `SKIP`) rather than guessing an answer to make the test pass. The fixture's own note explains the ambiguity and what would need to change in the spec for it to be resolved. It follows that forcing a scored answer onto a genuinely undecided rule would encode a guess as if it were ground truth, which is worse than not testing it at all.

### Tier 2 — scenario tests (planned)

This tier will be DuckDB "golden-fixture" scenario tests: a full sample project (documents, a small warehouse, expected end states) run through a release type end-to-end. It is not yet built, and it is tracked as a future tier in the original testing-strategy issue (wire#116).

### Tier 3 — release gating

`wire/scripts/release.sh` runs the full `run_all.sh` suite as its first step, unconditionally, including under `--dry-run`, and a failing test aborts the release before any version bump, changelog write or push to a distribution repo happens. This is what makes Tiers 0 and 1 "load-bearing" rather than advisory: a spec regression cannot ship.

## Running the suite

```bash
# Everything (what CI and release.sh run)
bash wire/tests/run_all.sh

# A single release type's structural checks
bash wire/tests/platform_migration/validate_specs.sh

# A single behavioural test
python3 wire/tests/platform_migration/validate_region_tagging.py
```

`run_all.sh` prints a `✓`/`✗ FAIL` line per structural check and a `PASS`/`FAIL`/`SKIP` line per fixture case, with a per-suite summary and a final pass/fail rollup across all tiers. Exit code 0 means that every non-ambiguous check passed, and non-zero means that at least one genuine failure needs investigating before merging.

## Adding a test for a new feature

What does this mean for you when you add something to Wire? Per the project's own contribution rules (see the root `CLAUDE.md`), every new command, new release-type artifact, new piece of embedded decision logic or new skill must ship with a test, not just the feature itself:

- **Structural**: it must pass Tier 0, meaning valid frontmatter, the generate/validate/review triad (or a documented exception), resolvable cross-references and command registration.
- **Behavioural**: if the feature embeds a deterministic algorithm or classification scheme, extract it into a small runnable Python test under `wire/tests/<release_type>/`, following the existing pattern of a fixture file, an expected-output file and a README explaining what is covered. If part of the logic is genuinely ambiguous as written, mark that fixture case as ambiguous and document why, rather than inventing an answer.

Finally, wire the new test script into both `wire/tests/run_all.sh` and `.github/workflows/spec-lint.yml`, as the two are meant to stay in sync and CI only catches what is actually registered in the workflow file.

:::note
A test added to `run_all.sh` but not to `.github/workflows/spec-lint.yml` runs on your machine and never in CI. Register it in both.
:::
