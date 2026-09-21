---
sidebar_position: 11
title: "Tutorial: Tenant Carve-out"
---

# Tutorial: Tenant Carve-out

Not every migration moves a whole platform. When a business unit is divested, what you are asked to move is one tenant's share of a warehouse that several tenants have always used together, and the job is as much about what stays behind as about what moves: every extract, every comparison and every grant has to be scoped to that one tenant, and at the end you have to prove that no other tenant's rows came with it. A scoping mistake on a carve-out is a residency incident rather than a failed test, as we will see when we come to equivalency, and that is the reason the carve-out adds the checks it does.

This walkthrough covers the **tenant carve-out** variant of a platform migration, in which a single tenant's data is extracted from a shared Snowflake platform into a dedicated BigQuery project rather than the whole platform being migrated. It assumes you know the standard migration flow from the [Platform Migration tutorial](./platform-migration), and so here we focus only on what the carve-out adds.

The carve-out is a variant and not a separate release type, so audits, inventory, strategy, dbt migration, equivalency and cutover all run as normal, and what makes the difference is five extra command families together with per-object tenant scoping, which we will look at in turn. The full reference, covering the command sequence by cadence, the data stores, the agentic-delivery files and how to start the agent fleet, is on the [Tenant Carve-out](../release-types/tenant-carveout) page.

## Statement of Work

```
**Rittman Analytics × Meridian Retail**
**Engagement**: Regional-tenant carve-out, Snowflake → BigQuery
**Type**: Fixed price, staged

Meridian Retail runs a shared multi-tenant Snowflake platform. One regional
business unit (`tenant_id = 1042`) is being divested and must move to its own
BigQuery project, isolated from every other tenant's data. The carve-out
covers ~3 years of history. Reporting is on Metabase.

Stage 1 deliverables (gated, part-paid): region tagging, and the GDPR /
data-residency assessment including a legal review of the historical window.
```


:::info New in 4.0: business rules discovery

A migration is the moment at which competing definitions of the same number surface, and they are cheaper to settle before the batches start than at cutover. `/wire:business-rules-generate` is an optional first phase, available on `platform_migration` and so on a tenant carve-out, which records what each number means before the batches start: every competing definition with the file it came from, what they disagree on, the decision and who approved it.

On a migration the legacy system *is* the reference, so every rule with a legacy variant gets a reconciliation query, which is the same comparison that equivalency validation would run later. It follows that running it first turns a definition dispute from a cutover blocker into a day-one finding.

The gate on `migration-inventory-generate` is advisory: it warns, takes a reason, records the skip and proceeds. This walkthrough does not use it.

Reference: [Business rules discovery](../advanced/business-rules.md).
:::

## Setting up the carve-out

Let's start by setting the carve-out up. At [`/wire:new`](../reference/commands#session-and-management-commands), you choose **Platform Migration** as you would for any migration, and then answer the scope question that follows:

```
Migration scope?
  1. Full migration (default)
  2. Tenant carve-out
> 2

Tenant predicate (the WHERE clause / tenant key that scopes the tenant):
> tenant_id = 1042

Reporting / BI tool?  > Metabase
```

Your answers are written to `status.md` as follows:

```yaml
migration:
  scope: tenant_carveout
  tenant_predicate: "tenant_id = 1042"
  reporting_tool: metabase
```

From this point every migration command reads `migration.scope`. With `full_migration` (or with the field absent) nothing described below changes, whereas with `tenant_carveout` the predicate "threads through" equivalency and the security chain, and the four carve-out commands become part of the flow.

:::note
A rebase-and-force-push of the carve-out branch orphans any per-batch branch you have already cut from it, because it moves the commit that the batch branch's merge-base points at. `01-tenant-carveout` tracks a moving parent migration release, so sync it with a periodic `git merge <parent-branch>` rather than a rebase, and once you have cut a per-batch branch from it, do not rebase-and-force-push the carve-out branch. See [Branching strategy](../release-types/tenant-carveout#branching-strategy) for the full reasoning.
:::

With the scope recorded, the carve-out adds the following steps to the standard flow, which at a high level are:

1. Region tagging, once the five audits are approved, to classify every in-scope item by whether it belongs to the tenant.
2. The data-residency assessment, alongside strategy, which is the Stage 1 contractual deliverable.
3. The Metabase reporting layer, audited and migrated alongside the warehouse work.
4. Bulk copy of the tenant's history in place of re-ingestion, together with dbt model relocation in place of dbt migration where the carve-out is staged after its parent migration has already landed.
5. Logical-access UAT before cutover, to prove that the isolation holds.

Let's now take a look at each of these steps in more detail, after which we will look at how equivalency changes under the carve-out and at how the carve-out is shipped and verified.

## Step 1 — Region tagging (after the audits)

The first question a carve-out has to answer is which of the items the audits found belong to the tenant being carved out and which belong to everyone. Once the five audits are approved, therefore, you classify every in-scope item by whether it belongs to the regional tenant being carved out, with [`/wire:region-tagging-generate`](../release-types/tenant-carveout#phase-1-run-once-up-front).

```
/wire:region-tagging-generate 01-tenant-carveout --region north
```

The command reads the audit CSVs and writes `migration/region_tags.csv`, sorting each item into one of three "buckets", as follows:

| Bucket | Signal | Example |
|---|---|---|
| confident-region | name suffix / destination / WHERE-clause match | `stg_orders_north`, a sync to the regional Salesforce |
| shared-row-level | carries the tenant key but serves all tenants | `dim_customers` keyed by `tenant_id` |
| global-deferred | no market tag at all | `dim_date`, currency reference tables |

Note that what the command produces are **candidates, not decisions**: it never emits an include/exclude flag and it never removes anything, because the ruling on each item belongs to a person, as we will see in a moment. Validation confirms that all three buckets are populated and that every in-scope item is classified exactly once:

```
/wire:region-tagging-validate 01-tenant-carveout
✓ Check 1 — all three buckets populated
✓ Check 2 — 412 in-scope items, each classified exactly once
```

`-review` is the human adjudication gate, and it is where those candidates become rulings. The reviewer "works the pile": every shared-row-level item gets a lineage trace and a row sample, and then a ruling, which is one of carve in (with the row-level predicate), split or defer.

```
/wire:region-tagging-review 01-tenant-carveout
```

## Step 2 — Data-residency assessment (alongside strategy)

Moving roughly three years of a divested tenant's history into a project of its own raises questions that are legal as much as technical, and Meridian's statement of work makes answering them the Stage 1 contractual deliverable. RA prepares it **as data processor** with [`/wire:data-residency-assessment-generate`](../release-types/tenant-carveout#phase-1-run-once-up-front), which structures the GDPR and residency questions together with the legal review of the roughly three-year window, and flags every legal determination for the client's DPO.

```
/wire:data-residency-assessment-generate 01-tenant-carveout
```

The resulting `data_residency_assessment.md` leads with a "processor-not-counsel" banner and then works through GDPR scope and lawful basis, residency constraints for the target region, the historical-window review, the processor safeguards RA implements and a consolidated list of `[CLIENT DPO/LEGAL]` items. RA does not assert the lawful basis, and `-validate` fails if it does, or if the required-client-input section is empty:

```
/wire:data-residency-assessment-validate 01-tenant-carveout
✓ all seven sections present and non-empty
✓ processor-not-counsel framing present
✓ lawful basis and retention ruling flagged [CLIENT DPO/LEGAL], not asserted
```

`-review` is the client DPO/legal sign-off gate, and it is one that RA cannot self-approve, because the lawful basis and the retention ruling on the historical window are the controller's to make.

## Step 3 — Metabase reporting layer

So what happens to the reports? Because the engagement recorded `reporting_tool: metabase`, you audit and migrate the reporting layer alongside the warehouse work with [`/wire:metabase-audit-generate` and `/wire:metabase-migration-generate`](../release-types/platform-migration#metabase-reporting-layer-migration).

```
/wire:metabase-audit-generate 01-tenant-carveout
/wire:metabase-migration-generate 01-tenant-carveout
```

The audit catalogues collections, dashboards, cards (SQL, template tags, snippets, card references), connections, permission groups and sandboxing, as well as the card-to-dashboards reverse index. Shared cards are the trap here: editing a card on one dashboard changes it on all of them, and so every write decision reads the index. The migration then translates native cards across all five surfaces in dependency order (snippets first), gated by a signed-off card manifest, while MBQL cards are "repoint-only".

Under the carve-out, `/wire:metabase-carveout-*` scopes the tenant's report estate first, taking layer decisions (sandboxing, warehouse view, dashboard parameter) before any card edits, drawing its filters from the predicate registry and pruning dashcards where a card has no tenant data, and `/wire:metabase-equivalency-validate` then proves each card at the card grain before the connection repoints. It will not run without a client-supplied query inventory.

## Step 4 — Bulk copy, in place of re-ingestion

Why copy rather than re-ingest? The tenant's history already exists on the shared platform, so a carve-out copies that existing history rather than re-ingesting it, and [`bulk-copy-migration`](../release-types/tenant-carveout#phase-2-the-iterative-carve-out-loop-repeated-per-wave) replaces [`ingestion-migration`](../release-types/platform-migration#ingestion-migration-mcp-driven-execution) in the flow.

```
/wire:bulk-copy-migration-generate 01-tenant-carveout
```

The runbook copies each in-scope table via the BigQuery Data Transfer Service or a GCS-staged path, with every extract filtered by `tenant_id = 1042`, and it runs under a service account scoped to the tenant's target project only, together with a "tenant guard" that refuses any extract missing the predicate or pointed at a production project. The copy is two-stage, with an equivalency gate between the stages:

```
Stage 1 — pilot partition (one month) → equivalency check 1 (row count) + check 6 (checksum)
          gate: both pass, tenant-scoped, on source and target
Stage 2 — remainder
```

`-review` here is a safety gate: written approval authorises the first copy execution, and that for Stage 1 only.

## Step 4a — dbt model relocation, when the carve-out is staged after its parent migration

Meridian's carve-out as described above runs **alongside** the parent Snowflake→BigQuery migration, which means the tenant's dbt models still need translating, and so [`dbt-migration`](../release-types/platform-migration#dbt-migration-parallel-agents-batches-and-folder-structure) stays in the sequence exactly as shown in Step 4 above and in the "Where the carve-out lands" diagram below.

But what if the parent migration has already finished? A different and common shape is for the carve-out to be scoped as a **second release, after the parent platform migration has already landed**, so that the whole estate is already on BigQuery and the tenant's dbt models are already correct, already-translated target-dialect SQL sitting in the parent release's dbt repo. Re-running `dbt-migration`'s translate-and-equivalency loop against SQL that is already correct is pointless work re-deriving the same answer, and this is where [`dbt-carveout-relocate`](../release-types/tenant-carveout#phase-2-the-iterative-carve-out-loop-repeated-per-wave) replaces `dbt-migration` in the sequence: it relocates the already-correct SQL into the carve-out's own dbt project instead of re-translating it, injecting the tenant row filter only where a model is genuinely shared:

```
/wire:dbt-carveout-relocate-generate 02-tenant-carveout --wave B01 \
    --source-dbt-project-path ../01-lift-and-shift/dbt \
    --target-dbt-project-path ../tenant-north-dbt \
    --target-project meridian-north-data-playground
```

For each model in the wave, the command reads the bucket that `region-tagging-review` adjudicated it into (`migration/region_tags_adjudicated.csv`, filtered to `adjudicated_ruling: carve_in`) and treats it accordingly:

- **`confident-region`** (tenant-exclusive, for example `stg_orders_north`): the `.sql` and its companion schema YAML are copied unchanged.
- **`shared-row-level`** (for example `dim_customers`): copied, and then the model's own filter from the predicate registry is injected at the point the resolution ladder identifies.

#### The resolution ladder (v3.11.3)

So where exactly does the filter go? Until v3.11.3 this step injected where the injection point was obviously clean and flagged everything else `manual_review_required`, which was correct but one step short. On one engagement's wave that queue was **128 models**, and working through it by hand showed that almost none of it needed open-ended judgement: it decomposed into named patterns, one repeatable data check and one graph traversal accounting for 102 of the 128.

The command now walks a "ladder" over each shared model, and, as we will see, the order of the rungs matters more than any individual rung:

| Rung | Shape | What it does |
|---|---|---|
| 0 | Tenant column matched inside a comment | Strips `/* … */` and `-- …` before scanning. A commented-out filter was reading as a live one |
| 1 | Depth-0 `OR` in the existing `WHERE` | Parenthesises the existing body unconditionally. Precedence-safe either way, so it removes the category instead of adding a case to detect |
| 2 | `WHERE` inside `{% if is_incremental() %}` | Pulls the tenant filter out to an unconditional top-level `WHERE`, re-nests the original as an `AND (…)` inside its own `{% if %}`. The tenant filter applies on every run |
| 3 | Tenant column is a SELECT-list alias | Substitutes the alias's defining expression, since BigQuery cannot resolve a flat query's own alias in its `WHERE` |
| 4 | Two candidate columns, or a hardcoded market with a per-row signal elsewhere | Probes the row distribution and **proposes** a disposition with the query and result |
| 5 | Top-level `UNION ALL`, or no tenant column at all | Resolves by inheritance from a covered upstream, using the graph |

Why does the order matter? **Step 1.7 builds the wave's `ref()`/`source()` graph before any of this**, which is the opposite of the intuitive order, and the reason is that a `UNION ALL` branch cannot be classified, and a model with no tenant column cannot be confirmed to inherit one, without knowing whether its upstream is already resolved. Those two buckets were 119 of the 128, and with the graph in hand they are one traversal rather than 119 judgement calls. Triaging them last, which per-model ordering encourages, is therefore the expensive way round.

Rung 4's output is evidence and not a decision. Each proposal lands in the registry at medium confidence with its query and result, and `-review` Step 3b is where the reviewer accepts it or rules otherwise. Reject is a real answer here, since a distribution that is 100% one market today does not prove that the column is the tenant boundary, and a probe result that contradicts an existing object-level ruling is routed back to `region-tagging-review` rather than settled at this step.

```
/wire:dbt-carveout-relocate-validate 02-tenant-carveout --target-dbt-project-path ../tenant-north-dbt
✓ Check 1  — every carve_in model has a relocated file
✓ Check 2  — every injected model's file independently re-derives its registry filter
✓ Check 2b — every inherited model's resolving chain terminates at a resolved node
✓ Check 2c — registry complete and internally consistent (5 checks)
✓ Check 3  — no confident-region model carries an unexpected predicate
✓ Check 4b — every probe proposal has a reviewer ruling
✓ Check 5  — target project compiles cleanly
```

Check 2 re-reads the relocated file's own text rather than trusting the generate run's manifest, which is the same "re-derive, don't trust the report" posture that `dbt-audit-validate` and `migration-batching-validate` use elsewhere, and it strips comments before re-deriving for the same reason that rung 0 does. `-review` is the human approval gate: it blocks on any unresolved `manual_review_required` model and on any unruled proposal, and it presents a diff sample of the injected filters so that the reviewer confirms them by eye and not just by check result.

Re-running is cheap and "monotonic": once an upstream model gains a mechanism, its descendants resolve by inheritance on the next run without anyone re-triaging them, and registry rows carrying a human ruling are read and never overwritten.

From v3.11.4, relocation is also gated on the parent's own proof. With `migration.parent_release` set, the generate step reads each model's verdict in the parent register before copying anything, so that a model the parent release has proven wrong (`fail`) is refused with the parent reference, and every relocated row carries the cross-release linkage columns (`parent_release`, `parent_model`, `parent_verdict_ref`). Similarly, the relocate-mode comparison described below will not treat the parent target as a trusted basis until the parent verdict is `pass`/`pass_qualified`.

```
/wire:dbt-carveout-relocate-review 02-tenant-carveout
```

You run this once per environment: playground first, and then production once playground equivalency passes, by re-running `-generate` with `--target-project meridian-north-data-source` (or wherever production resolves).

## Step 5 — Logical-access UAT (before cutover)

Everything so far has been about moving the right rows, but the question at cutover is a different one: can anyone working in the tenant's new project still reach another tenant's data? Before cutover, therefore, you prove that the isolation actually holds with [`/wire:logical-access-uat-generate`](../release-types/tenant-carveout#phase-3-run-once-at-the-end).

```
/wire:logical-access-uat-generate 01-tenant-carveout --region north
```

The plan derives its tests from the IAM boundaries in `target_setup_scripts/04_security.sql` (tenant-scoped grants, the RLS predicate, the scoped service account and PII masking), and every boundary gets a positive test and at least one negative test:

```
| Test | Boundary | Role | Type | Expected |
| T-04 | tenant grant | tenant_north_analyst | negative | query another tenant's project → permission denied |
| T-07 | RLS predicate | tenant_north_analyst | negative | shared table → only this tenant's rows, zero other-tenant rows |
```

`-validate` is strict, and it fails unless every IAM boundary in `04_security.sql` has at least one negative test.

```
/wire:logical-access-uat-validate 01-tenant-carveout
✓ every IAM boundary has ≥1 negative test
```

`-review` executes the matrix, captures the evidence and takes the three-attestation sign-off. A negative test that returns another tenant's data fails the gate regardless of how many positives pass, and it routes back to `target-setup` to fix the boundary.

## How equivalency changes

### One predicate per item, not one for the release (v3.11.3)

So how does equivalency know which rows are the tenant's? Before any of the below, you need to know which filter each object actually needs. `migration.tenant_predicate` is a single string, whereas a real carve-out needs several mechanisms at once; on one engagement there were five on the same release: a plain row predicate on most models, a differently-named column on a handful of globalised ones, an object-level schema-prefix carve on the Bronze layer where no row predicate exists at all, an enumerated advertising-account id list where the source platform carries no market column and a derived expression over a composite key.

As such, `region-tagging-generate` now seeds `migration/tenant_predicate_registry.csv` with one row per classified item, and `region-tagging-review` is where a seeded default becomes a ruling. Each row carries its mechanism (`row_predicate`, `derived_expr`, `account_cascade`, `object_carve`, `inherited` or `unresolved`), the expression, how it was resolved, its provenance and the date it was last verified against live data or a human decision.

Four commands read the registry rather than the global string: `equivalency-validate`, `bulk-copy-migration-generate`, `dbt-carveout-relocate-generate` and `dbt-migration-defer-build`. All four apply the same rule to an item with no established mechanism, which is to **flag it, never proceed unfiltered**. Why spell "unfiltered" out? Because it is the one wrong answer that looks like a real finding. A source-side query with no tenant filter returns every tenant's rows, so a row-count comparison against a single-tenant target fails for a reason that has nothing to do with the migration, and in a bulk copy the same mistake moves another tenant's data into the tenant's own project, which is a residency incident rather than a test failure, because deleting the rows afterwards does not undo the crossing.

You do not run a different equivalency command. Instead, the existing checks gain each object's resolved filter on both source and target, so that the carve-out validates only the carved-out tenant's rows: row count, value sampling, freshness, checksum and aggregate control totals all scope to `tenant_id = 1042`, while schema stays structural and unchanged, since there is no row data for a predicate to act on. No new check types were added.

From v3.11.1 there are two additions. The first is **relocate-mode comparison**: models that the relocate step copied from the parent migration (`origin: relocate` in the register) no longer compare against the source platform, since that would re-prove the parent's work and not the carve-out's. Their source side is instead the **parent target project's production relation with the tenant predicate applied** (`migration.parent_target_project`), and their target side is the tenant project's relation, unscoped, while freshly-translated models in the same carve-out keep the standard both-sides-predicated comparison. The second is **verdict provenance**: every carve-out verdict records `scope: tenant_carveout` together with a hash of the exact predicate applied, so that a carve-out verdict can never be mistaken for a full-estate one.

### Declared windows and known differences (v3.11.4)

What happens when the target does not yet hold the history the comparison expects? Meridian's carve-out hits the classic "availability wall": the tenant's Bronze connectors are weeks old, so a full-history comparison on `orders` reads 96% short for a reason that has nothing to do with translation. With a **declared window** the verdict states that structurally instead of a PR body arguing it: the floor auto-derives from the target Bronze `MIN(loaded_at)`, the connector's initial-load day is excluded with its reason and the cap is the run's pinned as-of. The verdict then comes back `diff_availability` with mechanism `declared_window_availability` and the window as structured fields, and it is claimable only because the in-window comparison passed **exactly**. One missing row inside the window and the verdict is `fail`.

The **known-differences registry** (`migration/known_differences.yaml`) handles the other recurring argument, which is a connector behaviour class such as the target-side ads connector emitting zero-impression filler days that the source connector never wrote. Proven once with a detection query, the entry classifies every future match `pass_qualified` with the citation, but only when the query accounts for the entire delta; a partial match, or any unregistered surplus, still fails.

### Sync twins get real verdicts (v3.11.4)

With Hightouch in scope, `/wire:reverse-etl-equivalency-validate` replaces the register's hardwired `n/a` for syncs: tier 1 runs the old sync's model query on the parent warehouse and the twin's on the tenant project, and compares the two at the sync grain (row set by primary key, changed-field hashes and differing keys named). Sync promotion requires an exact tier-1 `pass`, because sync output leaves the warehouse and so `pass_qualified` is not enough.

## Shipping and verifying the carve-out (v3.11.1)

Once a model is relocated or translated, how does it reach the client's repository? The v3.11.0 ship-and-verify pipeline runs under the carve-out with four adaptations, and the same fleet framing applies, in that you direct and the agent invokes:

- **`dbt-carveout-relocate-generate` now feeds the pipeline**: it upserts relocated models into the migration register and chains the downstream gates (validate, lint, fix, pre-PR review; `--no-chain` opts out), so relocated models arrive at `dbt-migration-batch-raise` eligibility like any translated model.
- **`dbt-migration-defer-build` guards the tenant boundary**: every write must land inside the tenant project (`tenant_write_guard`, no override), and the defer state falls back to the parent migration's prod manifest when the tenant project has no production state yet.
- **`dbt-migration-batch-raise` respects the residency gates**: `ship_then_verify` refuses to run until the region-tagging adjudication and the DPO/legal residency review are complete. The default stays `equivalence_before_pr`, since a carve-out's deliverable is an isolation proof.
- **`utils-ci-parity --scaffold-from`** covers the brand-new tenant repo: parity checks derive from the parent repo's pipeline until the new repo grows its own CI, and the extracted check list doubles as the starting point for that pipeline.

Human gates stay human: adjudication, residency sign-off and the isolation UAT are **park points** for the fleet, meaning that an item waiting on a ruling parks and the lanes move on to the next runnable item (`specs/utils/migration_fleet.md`).

Three v3.11.4 additions round the operating model out. `/wire:migration-status` is the answer to "where are we": per-wave exclusive stages derived live from the manifest, the register and a fresh read of the client repos, with a provenance header so that a quoted number is always traceable, and merged state comes from the repos and never from a committed rollup. `/wire:utils-client-watch` runs as a scheduled tick, so that client replies land in the answers ledger verbatim and a merged PR advances the register and fires post-merge verification automatically. And if the carve-out reached delivery before its register existed, `migration-register-generate --from region-tagging` seeds it from the adjudicated carve-in set while `--ingest-merge-state` backfills delivery state from live `gh` reads, so that the folder's stale status never wins over what the repos actually show.

### Batches do not stack (v3.11.2)

Raise each batch off the client's own base branch. From v3.11.2 `dbt-migration-batch-raise` refuses to cut a batch branch from a branch that has not merged yet, and the run stops with `stack_depth_exceeded` and prints the base chain with each branch's merge state. `--allow-stack-depth N` permits up to N unmerged ancestors, and a run that uses it must publish the chain's merge order both in the PR body and in the post to the client.

Why so strict? The rule exists because two migration engagements a month apart each built a deep chain of dependent PRs, and both ended the same way: review stalled on the base of the chain, nothing below it could merge and the chain was consolidated late, one of them closing five PRs unmerged. A carve-out is the more tempting case, because relocated models arrive in clusters that look naturally sequential. Prefer "drop-on-defect" batches instead, in which a model that is not ready is dropped and picked up by the next run, which raises independently, while the register carries the state between runs. When two batches genuinely touch the same file, raise the first, wait for the merge and let the next run re-derive the second from the register.

## Where the carve-out lands in the sequence

```
audits → region-tagging → inventory
       → strategy + data-residency-assessment
       → target-setup (tenant-scoped GRANTs + RLS in 04_security.sql)
       → bulk-copy-migration   (in place of ingestion-migration)
       → dbt-migration → metabase-migration
       → equivalency (tenant-scoped)
       → logical-access-uat → cutover → migration-report
```

If the carve-out is staged **after** its parent migration has already landed (Step 4a), `dbt-carveout-relocate` takes `dbt-migration`'s place in that line, and everything else in the sequence is unchanged:

```
       ...
       → bulk-copy-migration   (in place of ingestion-migration)
       → dbt-carveout-relocate (in place of dbt-migration) → metabase-migration
       → equivalency (tenant-scoped)
       ...
```

Everything not listed here runs exactly as in the standard [Platform Migration tutorial](./platform-migration), which is the place to return to for the steps the carve-out inherits unchanged.
