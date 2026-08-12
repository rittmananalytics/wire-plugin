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

**Chunk ledgers with deterministic job ids (#179).** A lane moving data in chunks (a bulk copy, a history bring-in) keeps a **chunk ledger** — one row per chunk: boundary keys, row count, load-job id, state — and derives each load-job id deterministically from the release, table, and chunk boundary (e.g. `wire_<release>_<table>_<chunk_floor>`), never from a timestamp or a random suffix. A deterministic id makes the re-run idempotent: re-submitting a completed chunk is rejected by the warehouse as a duplicate job instead of loading the rows twice. Observed failure: a copy killed by a credential expiry mid-table could only be resumed row-safely because the ledger plus deterministic ids let the re-run skip completed chunks; without them the options are re-copy-all or diff-by-hand.
- **Staged runbooks before credential stops.** When a lane can predict losing its credentials (an expiring ADC token, a scheduled MCP re-auth), it writes the remaining steps as a staged runbook in its state file *before* the stop, so the resume — by the same lane or its replacement — starts from a plan rather than a reconstruction.
- **Resume-by-message.** A paused or killed session resumes by sending the same lane brief to a fresh agent; the state file carries the context. No lane may hold essential state only in conversation memory.

## Report-once protocol (#179)

Progress lives in ledgers and state files; the conversation gets **terminal reports only** — a lane reports when it completes, stalls, or hits a decision it cannot make, never a running commentary. The orchestrator reads progress from state files (and answers the director from them); it does not poll lanes with "how is it going" messages, and lanes do not emit unprompted status updates that bury the signal. Observed failure: polling chatter between the orchestrator and busy lanes consumed context and tokens while adding nothing the state files did not already hold.

Outward-facing publishes (a PR raise, a client post, a merged-state update) are **`&&`-gated chains**: every local step must succeed before the publish step runs — build `&&` compare `&&` parity `&&` raise — so a failed precondition stops the chain instead of publishing a claim the evidence does not back. A publish that happened is reported once, with its reference; it is never re-narrated.

## Cost governance (#179)

Rule 5 above states that every lane's spend counts against the release budget (`migration.cost_controls`). The mechanics:

- **The dry-run bound is the authorisation figure.** A build or comparison authorises the cost its dry-run estimated; the actual is recorded next to it. An overrun (actual above the authorised estimate) is **disclosed in the lane's report**, never silently absorbed — repeated overruns mean the estimation method is wrong, which is itself a finding.
- **Views and external tables are estimated from object sizes, never a 0-byte dry-run.** A dry-run against a view or an external (e.g. Iceberg/BigLake) table can report 0 bytes while the real scan bills the full underlying object. Estimate from the referenced objects' storage metadata instead, and treat a 0-byte estimate on a non-trivial object as "unknown", not "free". Observed failure: an unguarded build day billed four figures, with one model accounting for a mid-three-figure scan a 0-byte dry-run had waved through.
- **Shared-credential attribution by destination dataset.** When several lanes run under one service account, attribute spend by each job's destination dataset (which rule 3's tree ownership makes unambiguous), so the per-lane budget lines stay meaningful under a shared credential.

## Contention rules (#179)

- **Worktree-per-branch, never the main checkout.** A lane that needs a branch checkout (a batch raise, a CI-parity run) works in its own `git worktree`; the main delivery checkout is never switched under a running fleet. Observed failure: a branch switch in the shared checkout changed every other lane's view of the tree mid-run.
- **Acquire-per-build locks, released between builds.** A build lane holds `migration/locks/build_{project}.lock` for one build and releases it before its next item, rather than holding it for the lane's lifetime — other lanes' occasional builds interleave instead of starving (the lock and its 60-minute staleness rule are `dbt-migration-defer-build`'s).
- **File-scoped commits only.** A lane commits exactly the files it owns (rule 3), named explicitly — never `git add -A`/`git commit -a`, which under a fleet commits other lanes' in-flight work. Observed failure: a broad commit from one lane swept up another's half-written state file and corrupted both lanes' resume points.

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
