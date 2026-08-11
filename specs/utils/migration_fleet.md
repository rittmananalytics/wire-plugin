---
description: Fleet operating model for platform migrations — one director, one orchestrating session, N flat lanes; the operating rules, lane types, state and resume contract, and the mandatory consolidation pass
---

# Utils — Migration Fleet Operating Model

A shared operating doc, not a command. Referenced by `specs/utils/migration_agent_delegate.md` (fleet mode), `dbt-migration-batch-raise`, and `equivalency-validate`'s lane fan-out. It codifies the operating pattern a live engagement derived by trial and failure, so the next engagement starts from the rules instead of re-deriving them.

## The three tiers

| Tier | Who | Duties |
|---|---|---|
| Release director | One human | Client communications, rulings and waivers, approval gates, judgment catches, fleet-size and budget decisions. The director supervises and decides; the director does not execute tasks. |
| Orchestrating session | One session (highest-capability model available) | Dispatches and monitors lanes, owns the register and verdict log (single writer), runs the consolidation and backstop passes, assembles PR evidence, amends process docs the day a ruling lands. |
| Lane agents | 6 to 12 concurrent | Stage-scoped work: translation slices, per-project build lanes, comparison sweeps, PII passes, PR preparation, reconciliation. |

**Who invokes Wire commands.** In fleet mode, almost nobody types them. The director speaks in intents and rulings ("ship everything that's ready", "option B", "carry on and update me when the lanes finish"); the orchestrating session translates those into Wire command invocations and lane dispatches; lanes run their assigned commands and report back through their state files. Typed-command counts dropping to zero while the execution log fills with Wire runs is the operating model working, not the framework falling out of use.

Consultants not directing move to review and escalation roles. Waves stay the client-facing reporting unit; the fleet assigns work by the stage ladder (translate, validate+lint, build, equivalence, PR), pull-based over the dependency graph — a model advances a rung whenever its inputs allow, whatever its wave, and PR batches assemble by readiness (`dbt-migration-batch-raise`), not by wave membership.

## Fleet rules

Each rule states its enforcement: **mechanical** (a command refuses) or **convention** (stated in every lane brief, checked by the orchestrator). A convention is still binding; the difference is only who catches the violation.

| # | Rule | Enforcement | Why (observed failure) |
|---|---|---|---|
| 1 | Lanes run **flat**: no sub-agent fan-out below a lane | Convention (lane brief) | Nested fan-out multiplied token burn into two hard usage-limit outages in one day |
| 2 | **One dbt build per project** at a time | Mechanical: `dbt-migration-defer-build`'s build-slot lock | Concurrent builds against one project contend and duplicate cost |
| 3 | **Tree ownership declared per lane**: each lane names the directories it may write; no two live lanes overlap | Convention (lane brief; orchestrator checks before dispatch) | A build lane and a reconciliation lane corrupted each other's file sets |
| 4 | Every lane writes **incremental state with a resume contract** (below) | Convention (lane brief template carries it) | Two hard outages resumed with near-zero loss only because every lane had incremental state |
| 5 | Every lane's warehouse spend counts against the release **budget** | Mechanical: `dbt-migration-defer-build`'s cost screen; comparison lanes cite their scan estimates in the lane file | A single unguarded build day cost four figures |
| 6 | **Single register writer**: lanes write only their own verdict/state files; the orchestrator merges | Convention plus the deterministic merge in `specs/migration/equivalency/verdict_schema.md` | Concurrent register writes corrupted rows; per-lane result shapes made merging manual |

## Lane state and resume contract

Every lane brief includes, verbatim:

- **State file**: the lane's own file (verdict JSON per `verdict_schema.md` for comparison lanes; a progress manifest for translation/build/PR-prep lanes) at a path inside the lane's owned tree, rewritten after **each completed item**, never only at the end.
- **Resume contract**: on restart with the same brief, read the state file first and skip every completed item. Losing the session must cost at most the in-flight item.
- **Completion**: the final state-file write marks the lane `complete` with a one-line summary; the orchestrator treats a lane with no writes for 30 minutes as stalled and may re-dispatch its remaining items to a new lane (the resume contract makes this safe).

## The consolidation and backstop pass (mandatory)

After lanes report, the orchestrating session runs a consolidation pass over their output before anything ships: re-check build results against the warehouse (not the lane's claim), scan for the engagement's documented traps, verify register/verdict consistency, and spot-check a sample at full depth. This pass is not optional overhead. The controlled contrast that justifies it: identical lane briefs run on a lower tier produced format-faithful output in which the consolidation pass caught two hard build failures and eight recurrences of a documented trap. Backstop passes stay in the template regardless of which model runs the lanes; the model choice changes how much the backstop finds, not whether it runs.

## Lane types (roster)

| Lane type | Scope | State file | Invokes |
|---|---|---|---|
| Translation slice | N models from the stage ladder | progress manifest | `dbt-migration-generate --models ...` |
| Build lane (per project) | build-ready models, one project | progress manifest + cost lines | `dbt-migration-defer-build` |
| Comparison sweep | one schema/layer/domain | verdict JSON | `equivalency-validate` lane role |
| PR prep | one candidate batch | batch manifest | feeds `dbt-migration-batch-raise` |
| Reconciliation | register vs artifacts vs warehouse | findings list | read-only |

**Carve-out lane additions (v3.11.1).** A `tenant_carveout` release adds three lane types: a **region-tagging evidence lane** (assembles lineage traces and row inspections for the adjudication pile — the ruling itself stays human), an **isolation-verification lane** (regenerates the logical-access UAT plan and executes only the checks runnable with RA-held credentials; checks needing client-side principals become an evidence request to the client, never a guessed result), and a **bulk-copy monitor lane** (watches the two-stage copy and its pilot-partition gate). One extra rule joins the six: **human gates are park points, not lane stalls** — an item pending `region-tagging-review`, `data-residency-assessment-review`, or `logical-access-uat-review` parks in the queue and its lane moves to the next runnable item; nothing idles waiting on adjudication.

## Director's control surface

The register's per-stage columns (`state`, `last_equivalence_result`, `delivery_stage`) replace per-wave progress reports for daily direction; waves remain the reporting label for client-facing status. The orchestrator answers "what are you doing now, what are we waiting on" from lane state files, not from memory.
