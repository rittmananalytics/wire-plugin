---
sidebar_position: 3
title: Advisory Engagements on Discovery
description: How to run an advisory engagement, where the deliverables are documents and the client builds, on the existing Shape Up discovery release type, with three worked examples.
---

# Advisory Engagements on Discovery

Some engagements produce documents, not a build: a target architecture, a decision log, a roadmap, a review of an existing dbt project. The client's own team builds from them. These engagements run on the existing [Shape Up discovery](../release-types/discovery-shape-up) release type. No separate release type is needed.

## When this fits

Use this pattern when the engagement is:

- Time-boxed, often in hours (10 hours over 2 weeks, 48 hours over 4 weeks).
- Documents only. The statement of work rules out hands-on changes to the client's systems.
- Defined by named deliverables in the statement of work.
- Not expected to spawn delivery releases, though it can.

## How to set it up

Create a discovery release as usual. Use its four steps as the spine of the engagement, and keep the deliverables as files beside them.

| Step | What it holds on an advisory engagement |
|---|---|
| Problem definition | The client's open problems, in their words. On a time-boxed review these are often the engagement's agenda. |
| Pitch | The appetite (the hours bought), the shaped approach, and the boundaries. Record "no build" as a no-go and any topic deliberately left out as a rabbit hole. |
| Release brief | The commitment: each statement of work deliverable listed by name, with what done means for it. |
| Sprint plan | The schedule. With no build to plan, write it as the week-by-week order in which the deliverables are drafted and reviewed. |

Then:

- **Write each deliverable as a file in the release folder**, for example `target-state-architecture.md` or `02-platform-architecture.md`. These are content files, not Wire artifacts.
- **Track the deliverables in the body of `status.md`**, as a checklist or a table (deliverable, owner, state). The front matter tracks the four discovery steps; the body tracks what the client paid for.
- **Keep blockers and outside inputs in the body of `status.md`** as a blockers and risks table, for example an introduction to a vendor's product team that gates week 2.

Do not build a parallel set of deliverable codes (D01 to D12, say) in place of the four steps. An engagement that did this ended up with two records that disagreed and had to be retrofitted. Use the four steps for the engagement and content files for the deliverables.

## Hours and decisions

Two things the original proposal asked for already exist in other forms:

- **Budget.** `status.md` has an optional `budget:` block, described in [The Release Director Model: Budget](../advanced/release-director#budget). It limits what agents may do (concurrent lanes, model tier, warehouse spend, where to stop). It does not count consultant hours. On a time-boxed engagement, state the hours in the pitch's appetite and track hours used in the body of `status.md`.
- **Decisions.** Rulings go in the release's `decisions.md`, written the moment a decision is given, in the form described in [The Release Director Model: Rulings](../advanced/release-director#rulings). Where decisions are themselves a deliverable (a decision log for the client), write that log as a content file in the release folder, one heading per decision with its status, owner and target date. An engagement-wide log of architectural decisions can sit at `.wire/engagement/decisions.md`, beside the engagement context rather than inside one release.

## Worked examples

**Small, recommendations only.** 10 hours over 2 weeks, 3 deliverables, and an explicit "no hands-on-keyboard changes" in the statement of work. The pitch set the appetite as a small batch and listed "building or implementing anything" as a rabbit hole. A three-phase plan mapped each deliverable to the phase where it was drafted. `status.md` tracked the three deliverables as a must-have and nice-to-have checklist in its body. It ran on discovery without changes.

**Large, spawning delivery.** 4 months, 6 deliverables, and 10 delivery releases spawned from it. The four discovery steps were completed and approved as the engagement's spine. The deliverables (executive summary, organisational context, platform architecture, stakeholder interviews, current issues, dashboard backlog) sat as numbered content files in the release folder, tracked in a deliverables table. Architectural decisions ("the semantic layer lives in dbt, not the BI tool") went into an engagement-wide decisions log, owned by the engagement rather than by one release.

**Time-boxed blueprint.** 48 hours over 4 weeks, pre-paid, with four deliverables: a target state architecture, a decision log, a refined dbt project structure and an AI integration roadmap. The scope was "the what, not the how": the client's team builds against the blueprint. The problem definition framed five open problems (storage, transformation, semantic layer, AI access, cross-site integration). The pitch set the 48-hour appetite and the no-build boundary. The release brief listed the four deliverables. The sprint plan was the 4-week schedule. Each open decision was a row in the decision log deliverable, and outside inputs that gated week 2 sat in the blockers table in `status.md`.

## See also

- [Discovery (Shape Up)](../release-types/discovery-shape-up)
- [Running a Discovery](../using-wire/running-discovery)
