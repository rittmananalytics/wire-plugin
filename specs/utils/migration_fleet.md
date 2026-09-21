---
description: Platform-migration profile of the release director operating model — the fleet's lane roster, carve-out lane additions, and the director's migration control surface
---

# Utils — Migration Fleet Operating Model

A shared operating doc, not a command. Referenced by
`specs/utils/migration_agent_delegate.md` (fleet mode),
`dbt-migration-batch-raise`, and `equivalency-validate`'s lane fan-out.

**This is the `platform_migration` profile of
`specs/utils/director_operating_model.md`.** The operating model owns the
rules; this file owns what is specific to a migration: the lane roster, the
carve-out additions, and the director's migration control surface. It codifies
the operating pattern a live engagement derived by trial and failure, so the
next engagement starts from the rules instead of re-deriving them.

## What lives in the operating model

These sections moved to `specs/utils/director_operating_model.md` when the
fleet model was generalised to every release type. Their content is unchanged;
read them there.

| Section | Where |
|---|---|
| The three tiers (director, orchestrating session, lanes) and who invokes Wire commands | `director_operating_model.md` — "The three tiers" |
| The six operating rules and their enforcement | "Operating rules" |
| Lane state, the resume contract, chunk ledgers with deterministic job ids, staged runbooks, resume-by-message | "Lane state and resume contract" |
| The lane brief template | "Lane brief template" |
| The report-once protocol and `&&`-gated publishes | "Report-once protocol" |
| Cost governance (dry-run bound, views and external tables, shared-credential attribution) | "Budget — Cost governance" |
| Contention rules (worktree-per-branch, acquire-per-build locks, file-scoped commits) | "Contention rules" |
| The consolidation and backstop pass | "The consolidation and backstop pass" |
| The release claim, sessions, parked decisions, co-existence controls | "The release claim" onwards |

Two things a migration reads differently:

- **Rule 2 (one build per warehouse project) is mechanical here**, enforced by
  `dbt-migration-defer-build`'s build-slot lock. On other release types it is a
  convention.
- **Rule 6's single writer** covers the migration register and the verdict log
  as well as `status.md` and `execution_log.md`. Lanes write their own verdict
  and state files; the orchestrator merges them by the deterministic rule in
  `specs/migration/equivalency/verdict_schema.md`.

## How the fleet assigns work

Consultants not directing move to review and escalation roles. Waves stay the
client-facing reporting unit; the fleet assigns work by the stage ladder
(translate, validate+lint, build, equivalence, PR), pull-based over the
dependency graph — a model advances a rung whenever its inputs allow, whatever
its wave, and PR batches assemble by readiness
(`dbt-migration-batch-raise`), not by wave membership.

This is where a migration differs from a linear release type. On a
`dbt_development` or `dashboard_first` release the runnable set comes from the
release-type graph (`specs/utils/runnable_set.md`) and parallelism is bounded by
the graph's shape. On a migration the graph is thousands of independent models
and parallelism is bounded only by the budget, so the fleet uses the stage
ladder below instead.

## Lane types (roster)

| Lane type | Scope | State file | Invokes |
|---|---|---|---|
| Translation slice | N models from the stage ladder | progress manifest | `dbt-migration-generate --models ...` |
| Build lane (per project) | build-ready models, one project | progress manifest + cost lines | `dbt-migration-defer-build` |
| Comparison sweep | one schema/layer/domain | verdict JSON | `equivalency-validate` lane role |
| PR prep | one candidate batch | batch manifest | feeds `dbt-migration-batch-raise` |
| Reconciliation | register vs artifacts vs warehouse | findings list | read-only |

**Carve-out lane additions (v3.11.1).** A `tenant_carveout` release adds three
lane types: a **region-tagging evidence lane** (assembles lineage traces and row
inspections for the adjudication pile — the ruling itself stays human), an
**isolation-verification lane** (regenerates the logical-access UAT plan and
executes only the checks runnable with RA-held credentials; checks needing
client-side principals become an evidence request to the client, never a
guessed result), and a **bulk-copy monitor lane** (watches the two-stage copy
and its pilot-partition gate). One extra rule joins the six: **human gates are
park points, not lane stalls** — an item pending `region-tagging-review`,
`data-residency-assessment-review`, or `logical-access-uat-review` parks in the
queue and its lane moves to the next runnable item; nothing idles waiting on
adjudication. That rule generalised: it is the operating model's parked-decision
list, and a migration's park points are these three reviews.

## Director's control surface

The register's per-stage columns (`state`, `last_equivalence_result`,
`delivery_stage`) replace per-wave progress reports for daily direction; waves
remain the reporting label for client-facing status. The orchestrator answers
"what are you doing now, what are we waiting on" from lane state files, not
from memory.
