---
sidebar_position: 7
title: Release Notes
---

# Release Notes

Recent release history for the Wire Framework. For full changelog detail from v3.0.0 onwards, see [CHANGELOG.md](https://github.com/rittmananalytics/wire-plugin/blob/main/CHANGELOG.md).

---

## v3.11.9 — Three carve-out closes from live client review

**Released**: August 2026

Three issues closed, all raised from the same live tenant carve-out engagement in the week after v3.11.8, two of them found by the client's own review rather than Wire's gates.

**The transported card that still read shared data.** The Metabase carve-out transport rewrote four kinds of ids but never the SQL text itself, and a BigQuery card usually names its table in full — `project.dataset.table` — straight in the query. That literal ignores the card's connection, so a transported card kept reading the shared project while the record said `transported`, and equivalency could not see it because both sides read the same literal table. Transport is now a plan, check, write pipeline (#221): `metabase-carveout-transport-generate` writes a complete dry-run plan including a SQL-text rewrite map (each source-project reference mapped to the tenant project, or `no_change_needed` with a recorded reason); `metabase-carveout-transport-validate` re-scans every card independently of the plan and fails on any unaccounted reference; the write step refuses a plan the validate has not passed and applies the SQL rewrites as its fifth rewrite item. One human gate as before — the rewrite is mechanical once the database mapping is confirmed, so it needed deterministic validation, not a second sign-off.

**A topology for destinations that were never shared.** The reverse-ETL migration offered three topologies, all assuming the new sync's destination is either the same live object the old sync writes to (hence the decoy mechanic and a three-PR cutover) or a from-scratch destination needing full re-auth. A carve-out's actual shape — dedicated destinations provisioned by the client before any sync exists — fitted none of them, forcing undocumented overrides. The fourth topology, `additive_dedicated_destination` (#220), points new syncs at the real destination id from the start (still authored paused), skips the decoy mapping outright, and collapses cutover to one PR. Eligibility is gated per destination by the same complete-destination-set machinery the validate already builds: membership in any existing sync's destination set refuses that sync to the decoy path, and an unreadable set refuses everything rather than assuming.

**Seven silent-pass defect classes, encoded.** Wave 1 of the carve-out shipped 88 models through every RA gate — parse, compile, lint, tests, pre-raise equivalency — and the client's reviewer still pushed eight fixing commits before approval. Each fix was a defect class Wire did not encode, and all seven now are (#219): a semantics check on derived tenant predicates (a column can be named like a tenant column and mean something else — one filtered a global app's install geography, tenant share zero); entity-grain predicates on SCD tables, with static lint rules for the two latent forms; a verified-reduction protocol for models that read foreign-market sources the sovereign project discards; `EXPECTED EMPTY` markers so zero-row models pass explicitly rather than vacuously; a `declared_deviations` record and `pass_declared_deviation` verdict for the case where the target is right and the source is provably wrong; project-hygiene checks (unread sources.yml entries, models falling through to the profile-default dataset); and a new-project coverage gate in batch-raise that checks the client's project-enumerating CI gates actually enumerate the new project and every enabled model is reachable from a DAG — the gap that would have merged 86 models as dead code.

---

## v3.11.8 — Eight field-raised closes: status reconciliation, reference legibility, and the carve-out gaps

**Released**: August 2026

Eight issues closed in one release, all raised from live engagements: two cross-cutting conventions from a custom-release build, three defects and three capability gaps from the tenant carve-out series (#191, #199 to #204 companion set).

**Status maintenance decoupled from command runs.** Wire's status tracking updates only when work runs through a command; conversational and agent-assisted delivery, the normal case in `custom` releases, left `status.md`, the execution log, and the sprint plan behind — two stale-status incidents in one engagement's first week, both caught by the consultant rather than the framework. `/wire:status-sync` (#204) is the repair path: it diffs the recorded state against evidence from git, disk, and the log, classifies the drift deterministically (`record_behind`, `record_ahead`, `fields_incomplete`, `last_updated_stale`, `totals_stale`, `history_gap`), and repairs the record only on explicit confirmation. A drift report alone is a valid, side-effect-free outcome; history is append-only; the record is never downgraded on absence of evidence alone.

**Reference legibility.** Wire artifacts mint codes (`FR-1`, `D3`, `PD-2`) and cite them across document boundaries, and nothing required a reader-facing definition anywhere. The convention (#205, `specs/utils/reference_legibility.md`) has two rules: every code is expanded in plain language at first mention, and any document citing codes defined in other artifacts carries a Reference key table (code, meaning, defining-document path). Eight document-chain validate commands run the named `reference_legibility` check at Major severity; a document read in isolation now resolves every code it contains without opening another file.

**The sync-verdict path is reachable.** `reverse-etl-equivalency-validate` expected register rows that `migration-register-generate` could not create and `migration-register-validate` rejected as orphans — 621 compliance checks and 8 tier-1 verdicts on one engagement, none with a row to land on. The register now seeds one `reverse_etl_sync` row per audit row, keyed on the normalised sync id (the raw-string join matched 6 of 609; the normalised join 575 of 643), and validate joins sync rows to the reverse-ETL audit (#191).

**Registry expressions survive commas.** 3.11.x registry writers truncated `expression` values at the first comma — every semi-join and regex predicate in the estate, 18 of 88 wave-1 models, all passing schema checks because the column count still looked right. Writers now quote at the CSV-writer level (RFC 4180, stated once in the registry contract), and every consuming validate blocks on a non-empty expression that fails a superficial well-formedness check: balanced parentheses, closed quotes, no dangling Jinja (#200).

**Physical targets are resolved, never guessed.** The register's `bq_target` was dbt-relative, so post-merge verification guessed physical tables and failed three ways in one run, including a 70,229-row false divergence from a wrong-dataset guess. `bq_target` is now the fully qualified `project.dataset.table` resolved from the manifest's schema + alias; a consumer that cannot resolve a target exactly reports `unresolved_target` instead of comparing, and `/wire:upgrade` backfills legacy registers (#201).

**Readiness-aware batching for staged carve-outs.** For a carve-out staged after a parent migration, neither the domain cut nor build order answers the scheduling question: which models are allowed to ship right now. The third partition mode, `readiness_waves` (#199), assigns waves from the rule's state in the predicate registry, the parent-release delivery state, and per-rule-group client approvals, with strict dependency closure, `B00` preserving shipped history, and named `PEN-*` holding pens — generalising the documented deviation that re-partitioned 1,494 models after the domain cut drifted within days.

**CI parity becomes environment-faithful.** The pre-raise gate re-ran the client's CI commands but in the operator's environment, and operator-env `dbt parse` and CI-env `dbt --warn-error parse` over every project dir are different checks — a raise bounced on exactly that. Each check now runs in a clean environment carrying only the config's variables plus `CI=true`, with the repo's toolchain pins and the config's own iteration scope; a pass with a recorded deviation is `pass_with_env_deltas`, never a bare `pass` (#202).

**Metabase carve-out transport.** All four Metabase command families were written against one instance; a live carve-out's target was a separately-provisioned deployment, and getting a signed-off card there was hand work. `/wire:metabase-carveout-transport` (#203) takes the signed-off manifest as its worklist and creates the objects on the target instance: source strictly read-only, target writes additive-only, database ids mapped through a consultant-confirmed table, idempotent by recorded target id, with cross-instance equivalency via the transport manifest's id map.

---

## v3.11.7 — A shipped token defect, two written contracts, and the post-merge sweep

**Released**: August 2026

Three items, ordered by what bites soonest, so the shipped defect leads (#195).

**A consumer keyed on a token the producer never emits.** Both `reverse-etl-twin-generate` and `reverse-etl-retire-generate` looked for a `migration_approach` value of `retire`. The producer, `reverse-etl-audit-generate`, writes a closed set of `repoint`, `rewrite_model`, `rebuild`, `decommission`, and has never written `retire`. On live releases that meant the twin command would have authored twins for all 182 syncs classified `decommission` (98 on one release, 84 on another), and the retirement command would have listed none of them. Neither command errored, because a consumer looking for a token the producer never emits sees an empty match and carries on: no exception, no warning, a plausible-looking empty result. This is the same defect class as the v3.11.6 rule that could not fire.

The fix is a written contract plus producer-side enforcement. `specs/utils/reverse_etl_approach.md` states the closed set, what each value means, the per-consumer routing table, and that there is no `retire` value. Both commands now key on `decommission`, which is a retirement ground rather than an exclusion from retirement: out of scope for migration, in scope for retirement, listed with no replacement evidence owed. `reverse-etl-audit-validate` Check 9 fails any row outside the closed set, because enforcing only in consumers means each consumer rediscovers the drift independently, one release at a time.

**The wave contract, and a correction to the premise.** The issue reported that the specs disagreed on wave-id form. They did not: `migration-batching/generate.md` documents `batch_id` as zero-padded (`B01`) and every consumer expected that. What happened is that a produced CSV carried `b1` through `b10` and nothing checked the token form, so a documented rule with no gate behind it drifted at the first opportunity. `specs/utils/wave_resolution.md` now records the canonical form (`B0N`, plus the reserved `NO-DEP`), the normalisation table, and the resolution steps. `migration-batching-validate` Check 2b enforces the form at the gate that writes it. Matching stays case- and pad-insensitive on both sides, so a release already holding a non-canonical CSV is not bricked mid-flight while still failing validate. The 18 specs that each restated the rule now reference the contract instead of being the only record of it.

**The post-merge sweep becomes a step with a state.** After a model's PR merges, the version on the client's default branch can differ from the delivery tree's copy: a CI fix applied in the PR, a reviewer's change, a conflict resolved at merge. Nothing carried that back, so the delivery tree that the next wave translates against, and that every later lint and comparison treats as the authored truth, quietly stopped being true. On one release 86 of 94 models had drifted this way, because the sweep existed only as a habit in an engagement process document. `/wire:dbt-migration-reverse-port` makes it a command with a recorded state.

It is a different axis from the drift gate. That gate compares the live source platform against `last_migrated_commit`, asking whether the thing we translated has changed underneath us. This asks whether the thing we shipped changed after we shipped it. Both can be true at once and neither substitutes for the other.

Classification is four-way against a common ancestor: `in_sync` (recorded, nothing written), `client_ahead` (the client's version is copied into the delivery tree), `delivery_ahead` (flagged, never written), `diverged` (flagged as a conflict, both diffs emitted, resolved by a person). `delivery_ahead` has no override flag, deliberately: the drift is a stale copy of something that also exists in the client repo, while an unraised local edit exists nowhere else, so a sweep that overwrote it would destroy more than the drift cost. A register row at `merged` whose file is absent from the client branch is reported as `merge_state_stale` and skipped rather than classified, since that is a register correction and not a port. Nothing is normalised before comparing, not even whitespace: a change the client's formatter made in CI is a real change to the authored file. A port supersedes the model's standing equivalence verdict and emits the re-verify as owed, because the verdict was bound to the file version the port replaced. The register gains `last_reverse_ported_commit`, and `migration-status exceptions` lists both merged models never swept and verdicts a port superseded.

---

## v3.11.6 — The reverse-ETL path closes at both ends

**Released**: August 2026

The reverse-ETL commands covered the middle of the process well — audit, plan, equivalence, PR — and stopped at both ends. Nothing authored the target-warehouse copies, nothing retired the superseded syncs, and the one rule guarding the worst failure mode was written down somewhere no command could evaluate it (#193).

**Nothing authored the twins.** `reverse-etl-migration-generate` produced the plan: topology, target source connection, decoy mapping, the additive first PR. Then a person wrote the copies. On one engagement, 575 of 643 were written directly, one file at a time, across unmerged branches — the single largest cost in the path and the only step in the sequence with no command behind it. The compounding problem is that because nothing generated them, nothing validated them either. `/wire:reverse-etl-twin-generate` authors them: one new config per in-scope sync, alongside the existing one, which is never opened for writing and stays the rollback until cutover. Each twin is paused, points at the same-type decoy from the plan's mapping, and carries the model translation the approved runbook already recorded rather than re-deriving it. It does not enable anything — that is the client's decision and the issue asks explicitly for it to stay outside the command set.

Four things make the command decline to author rather than improvise, because in each case the obvious fallback is worse than stopping: a missing or wrong-type decoy (never substitute a different type, never fall back to the production id), a Customer Studio `rebuild` approach (not a file copy), an unresolved tenant predicate under a carve-out, and a `primaryKey` that cannot be resolved against the target's actual columns. Each is recorded with its reason in the manifest.

The manifest keys on the **normalised sync id** — basename, extension stripped, trailing `-bq`/`-bigquery` marker stripped, lower-cased. That rule is pinned in one place because a raw-string join between authored twins and the audit matched 6 of 609 on one engagement, where the normalised join matched 575 of 643 with the residual explained (syncs classified `retire` never get a twin).

**A rule at error severity that nothing evaluated.** An engagement rule set carried `primaryKey` casing on BigQuery-source Hightouch syncs at **error** severity: any upper-case character makes the sync run successfully and send nothing. Green run, zero rows, no alert — the failure mode indistinguishable from success, whose only symptom is a destination quietly going stale. The command that loads engagement rules is `dbt-migration-lint`, which operates on the dbt project and contains no reverse-ETL path, so it never opened a sync config. The rule was written down, carried error severity, and could not fire. A later by-hand sweep of 621 authored twins found **22 with upper-case keys**, including every sync in one open PR; all 22 would have sent nothing. It is now Check 13 of `reverse-etl-migration-validate`, over the configs actually on the branch — which is what covers hand-authored twins, the population the defects came from — and it runs again at authoring time.

The generalisation matters more than the instance. Engagement rules may now declare `applies_to`, and `dbt-migration-lint` reports every loaded rule outside its own scope under **Rules not evaluated here**, naming the command that does evaluate it. A rule naming no evaluator raises `RULE_HAS_NO_EVALUATOR` at its own severity. People stop checking once they believe a rule exists, so a rule set loaded by a command that cannot evaluate part of it has to say so out loud.

**Destination safety is a set comparison, not a list.** Nothing answered "is this new copy pointed somewhere safe", and doing it by inspection produces the wrong rule. The first attempt on one engagement was a fixed list of Google Sheets destination ids: correct for 151 of 776 syncs and silently passing the other 625, which went to Google Ads customer match, DV360, Salesforce, Facebook custom audiences, Slack and Iterable. Check 14 now builds the complete destination set of every source-warehouse sync on the client repo's default branch **once**, then tests each twin against it. Per-file lookups are banned because they cannot see the whole. No destination type appears anywhere in the check — a destination type is not a safety property, membership of the live set is — and the test asserts that no type name leaks into the decision. An unreadable default branch makes the check `unverified`, never `pass`: an unknown set cannot clear a twin. Destinations shared between two twins are reported as information, since fan-in is legitimate in some designs and a copy-paste mistake in others, and the check cannot tell which.

**Nothing retired a superseded sync.** After switchover both the old sync and its copy exist, and nothing removed the old one or tracked what was owed retirement — 84 of 643 were classified `retire` outright, before counting those superseded by their own copies. The estate quietly doubles: two syncs per destination, one live and one dormant, with no record of which is which. `/wire:reverse-etl-retire-generate` produces the runbook. Eligibility is deterministic: classified `retire`, or superseded by a twin that is `production_verified` with a latest verdict of exactly `pass` and a clean-run window (`--min-clean-days`, default 7). `pass_qualified` is not sufficient, for the same reason it is not sufficient at `batch-raise`: a sync's output leaves the warehouse, and retiring the predecessor on a qualified verdict removes the rollback while the qualification is unexplained. Clean running is read from the sync-run history rather than inferred from the absence of a complaint, so a replacement that has never run cannot be clean however good its verdict. Order is classified-first then longest-clean-first, grouped so no destination is left served by a mix of old and new. Where the source warehouse has already been decommissioned, the runbook says per sync that there is no rollback, rather than describing a revert that would restore a sync pointing at nothing. Execution stays a client action throughout.

**Which syncs are blocked on an unmerged table.** A Hightouch model reads a warehouse table; if that table is not migrated and merged, the sync cannot be worked at all — and nobody could answer which syncs those were without deriving it by hand each time, so the answer was recomputed, inconsistently, by whoever was asked. `migration-status` gains a `blocked` sync partition, and a `blocked-syncs` subcommand that names every blocked sync with its blocking objects, grouped by the blocking object. That grouping is the useful direction: it turns a list of blocked syncs into a ranked list of tables worth merging next. Blocked is a partition rather than a stage, the same treatment `drifted` gets for models, because "where is this sync" and "can this sync be worked" are different questions and collapsing them loses one.

---

## v3.11.5 — Metabase reports become first-class migration objects

**Released**: August 2026

This release implements the Metabase gap review in full: cards and dashboards stop being a side-channel and join the migration estate.

**A BI-tool audit category, with the reverse index that makes card writes safe.** `metabase-audit` now connects via the Metabase MCP server where available (REST and serialization fallbacks produce the same catalog), and catalogues what the downstream commands actually need: per-card template tags with their field ids, snippets, card references, sandboxing policies, and the card-to-dashboards **reverse index**. Cards are shared objects — editing a card on one dashboard changes all of them — so no write decision is made without the index.

**Dialect migration behind a manifest gate.** Native cards transform across all five surfaces (the query as a transpiler draft, the connection id, template-tag field remaps, snippets, card references) in dependency order — snippets first, referenced cards before referrers — with MBQL cards split out as repoint-only. Every write is gated by a signed-off row in the card manifest, shared cards carry an explicit edit-vs-clone decision, and bulk write-back prefers serialization export/transform/import.

**A tenant carve-out path for the report estate.** `/wire:metabase-carveout-*` scopes the tenant's reports with the mechanical card edit as the last resort: data sandboxing, a warehouse-layer tenant view, or a dashboard parameter come first, recorded and adjudicated as layer decisions. Where cards must be edited, the filter resolves from the tenant predicate registry and is injected via AST at the outermost SELECT — never string-appended — and an unresolved card is flagged, never carved unfiltered. Cards with no tenant data lose their dashcards; the card always stays in its collection.

**Card-level equivalence gates the cutover.** `/wire:metabase-equivalency-validate` proves a migrated or carved card returns the same rows, in the model verdict taxonomy — a full migration compares the source-dialect query on the source connection against the translated query on the target; a carve-out compares the parent connection (registry-filtered) against the tenant connection. The production connection repoint requires every in-scope card at `pass`/`pass_qualified`.

Metabase objects now appear in the migration inventory (with model-to-card edges), the register, the verdict log, region tagging, the wave schedule, and `migration-status`. Four new commands, three behavioural test suites, and the 90-day carve-out example plan regenerated with per-wave card carve/migrate/prove rows.

---

## v3.11.4 — The migration gap backlog closes

**Released**: August 2026

This release implements every remaining item of the two migration gap reviews (#179 for `platform_migration`, #180 for `tenant_carveout`), closing both.

**Divergence with a proven benign cause stops being re-argued per PR.** Two structured qualifiers land in `equivalency-validate`. A **declared availability window** handles the target that holds less history than the source: the floor auto-derives from the target Bronze `MIN(loaded_at)` or partition metadata (or is declared explicitly with reasoned exclusions), the cap is the run's pinned as-of, and the verdict binds to it — `diff_availability` with mechanism `declared_window_availability` and the floor, cap, and exclusions carried as structured fields on the verdict row. It is claimable only when the in-window comparison passes exactly; an in-window divergence is never availability. A **connector-emission known-differences registry** (`migration/known_differences.yaml`) records each proven connector behaviour class once, with a detection query; a divergence classifies `pass_qualified` with the entry cited only when the query accounts for the entire delta. An unregistered surplus still fails.

**The carve-out and its parent release are now machine-linked.** Three register columns (`parent_release`, `parent_model`, `parent_verdict_ref`) tie every relocated model to the parent verdict that proves its SQL. The relocate step refuses to relocate a model whose parent verdict is `fail` — copying proven-wrong SQL into the tenant project is a defect transfer, not a relocation — and the relocate-mode comparator will not use the parent target as a comparison basis until the parent verdict is proven. `cross_release_triggers` in status.md make parent-to-carve-out dependencies ("closes when the parent completes its Bronze backfill") a condition the drift gate evaluates each run, and a parent defect-class sweep marks the relocated copies re-verify-owed through the linkage.

**One root-caused defect sweeps the whole estate.** `/wire:equivalency-sweep <release> --pattern <rule-id>` enumerates a defect pattern across the delivery tree, the client main (live read), and open PRs, classifying each site CORRECT, DEFECT-FREE-MODEL (fixed in tree, re-verify owed), DEFECT-MERGED (a quantified probe, then a fix-forward batch), or NOT-TRANSLATED-YET. A sweep that does not end with the pattern encoded as a lint rule is incomplete.

**Syncs get real verdicts.** `/wire:reverse-etl-equivalency-validate` compares the old sync's model output against its target twin at the sync grain — row set by primary key plus changed-field hashes, pinned vintage, differing keys named — with a tier-2 decoy-destination diff where a read-back path exists. Sync promotion requires an exact tier-1 pass.

**The status question gets one answer.** `/wire:migration-status` derives per-wave exclusive model and sync stages live from the dbt manifest, the register, and a fresh read of the client repos, never from a committed rollup — including the **authored-on-branch** sync stage that a main-only count misreads as not started, and a provenance header on every invocation. `--json` feeds reports and charts.

**The client-facing tail is productised.** `/wire:utils-client-watch` runs as a headless tick: channel replies land in the answers ledger with the client's words quoted verbatim, and a merged PR advances the register and fires post-merge verification. `/wire:utils-ask-list-generate` drafts the capped top-N ask list from the register's blocker taxonomy with a mechanical re-ask guard — anything the ledger already answers is refused a slot. Drafts only; nothing is auto-posted.

**History with no re-ingestion path moves safely.** `bulk-copy-migration-generate --mode bring-in` sizes every candidate table read-only, classifies against a configurable gate (COPYABLE chunk-ledgered copies with deterministic load-job ids, resumable mid-table; EXPORT client-run execute-packs — writes on the source platform are never run by the consultancy; CONNECTOR-ONLY skipped), and stamps register rows with the vintage pin and promotion route.

Rounding it out: `migration-register-generate --from region-tagging` bootstraps a carve-out register from the adjudicated carve-in set, `--ingest-merge-state` backfills delivery state from live repo reads (which always beat stale folder status) and ingests PR-body verdicts as marked, re-verify-owed evidence; and the fleet operating spec gains the rules the packaging fix alone did not carry — the report-once protocol, chunk ledgers, cost governance including the never-trust-a-0-byte-dry-run rule, and the worktree/lock/file-scoped-commit contention rules.

---

## v3.11.3 — A tenant predicate per item, and the carve-out review queue shrinks

**Released**: August 2026

Two more `tenant_carveout` gaps closed.

**One tenant predicate is not enough.** `migration.tenant_predicate` is a single string, and a real carve-out needs several mechanisms at the same time. One engagement's needed five on one release: a plain row predicate over most models, a differently-named column on a handful of globalised ones, an object-level schema-prefix carve on the Bronze layer where no row predicate exists at all, an enumerated advertising-account id list where the upstream platform carries no market column, and a derived expression over a composite key. Pinning that variety as prose inside one config field means every consumer re-parses it and reaches a different answer. `migration/tenant_predicate_registry.csv` resolves one item at a time across five mechanisms — `row_predicate`, `derived_expr`, `account_cascade`, `object_carve`, `inherited` — each with its expression, how it was resolved, its provenance and the date it was last verified. `region-tagging-generate` seeds it from the buckets, `region-tagging-review` is where a seed becomes a ruling, and four commands read it: `equivalency-validate` resolves the comparison filter per object, `bulk-copy-migration-generate` per copy step, `dbt-carveout-relocate-generate` injects from it, and `dbt-migration-defer-build` drops what it cannot resolve. `migration.tenant_predicate` stays, with a narrower job: the default value the seed uses, never something a consumer reads directly.

**An unresolved item is flagged, never compared or copied unfiltered.** This is the same rule in all four consumers, and it exists because unfiltered is the one wrong answer that looks like a real finding. A source-side query with no tenant filter returns every tenant's rows, so a comparison against a single-tenant target fails for a reason that has nothing to do with the migration and a reviewer spends the afternoon on a phantom. In a bulk copy the same mistake moves another tenant's data into the tenant's project, which is a residency incident rather than a test failure, and deleting the rows afterwards does not undo it.

**The relocate step now resolves the ambiguity it used to only flag.** `dbt-carveout-relocate-generate` detected shapes it could not safely inject into and emitted `manual_review_required` — correct, but it stopped one step short. On one wave that queue was 128 models, and triaging it by hand showed almost none needed open-ended judgment: it decomposed into named patterns, one repeatable data check, and one graph traversal that accounted for 102 of them. Step 1.8 is now a six-rung ladder: strip SQL comments before scanning (a commented-out column name was reading as a live one), parenthesize the existing `WHERE` body unconditionally (precedence-safe either way, so it removes depth-0 `OR` as a category rather than adding a case to detect), restructure a `WHERE` trapped inside a Jinja conditional so the tenant filter does not inherit the incremental condition, substitute a SELECT-list alias's defining expression where BigQuery cannot resolve the alias, probe the row distribution where live evidence is what decides, and resolve models with no tenant column of their own by inheritance from a covered upstream. Step 1.7 builds the wave's `ref()`/`source()` graph before any per-model work, because the two largest buckets are graph lookups and resolving them one model at a time re-derives the same graph each time. What falls off the end is `manual_review_required`, and on the reference wave that is single digits.

Rung 4's probes are evidence, not decisions: each is written to the registry at medium confidence with its query and result, ruled on at `dbt-carveout-relocate-review`, and checked by `-validate`. A probe result that contradicts an existing object-level ruling is routed back to `region-tagging-review` rather than settled in place. Registry rows carrying a human ruling are read and never overwritten by a re-run. Re-running after an upstream model gains a mechanism resolves its descendants without anyone re-triaging them.

Region tagging also gains a sibling-naming cross-check: a model named for an already-excluded family (a re-platform variant, a deprecated parallel build) is flagged as a scope question at tagging time, instead of falling through classification and adjudication to surface as an injection failure that looks like a SQL-shape problem. `/wire:upgrade` backfills the registry for a carve-out release created before v3.11.3.

---

## v3.11.2 — Shared specs actually ship, and batches stop stacking

**Released**: August 2026

Two gaps logged against the 3.11.1 migration release types, closed.

**The shared specs now ship.** A Wire command's own spec is inlined into its command file, so it needs no file on disk. The shared docs are different: specs say "follow `specs/utils/commit.md`", or cite the schema in `specs/migration/equivalency/verdict_schema.md`, and until now the build shipped none of them. It copied `TEMPLATES/`, `platform_pairs/` and `docs-site/`, and skipped `specs/` entirely, so all 30 shared paths dangled in an installed plugin. `specs/utils/migration_fleet.md` was the one that surfaced it — three references shipped across v3.11.0 and v3.11.1 with the file in neither package. Both the Claude plugin and the Gemini extension now carry the shared specs under `specs/`, in the same path form the references use, and every generated command's Path Configuration block says where they resolve (`${CLAUDE_PLUGIN_ROOT}/specs/` in the plugin; the extension folder in Gemini). The shipped set is derived by rule — referenced as `specs/<path>.md`, not registered as a command — so it cannot fall behind a new shared doc. Tier 0's lint gained check 8 to hold both halves: the build wiring, and the committed `wire/dist/` output.

**Batches do not stack.** `dbt-migration-batch-raise` now refuses to cut a batch branch from a branch that has not merged yet. `stack_depth` is the number of unmerged branches in the base chain, walked outward to the client's configured base branch; above `--allow-stack-depth` (default `0`) the run stops with `stack_depth_exceeded` and prints the chain branch by branch with each merge state. A merged ancestor counts for nothing — its commits are already in the base. An unmerged client branch counts the same as an unmerged RA one, because the deadlock comes from the dependency rather than the author. Overriding is allowed, on condition the chain's merge order goes in the PR body and in the post to the client: a stack whose order the client cannot see is a stack the client cannot merge. Two engagements a month apart each built a deep chain of dependent PRs and both ended the same way, with review stalled on the base of the chain and the whole thing consolidated late, one of them closing five PRs unmerged. Drop-on-defect batches are the replacement: an unready model is dropped and picked up by the next run, which raises independently, and the register carries the state between runs.

---

## v3.11.1 — Ship-and-verify for the tenant carve-out

**Released**: August 2026

Brings the v3.11.0 ship-and-verify machinery to the `tenant_carveout` variant, adapted to what a carve-out actually delivers: an isolation proof.

**Relocate-mode equivalency.** Models the carve-out relocated from an already-landed parent migration (`origin: relocate` in the register) no longer compare against the source platform — that re-proves the parent's translation, not the carve-out. Their comparison is now parent target project (tenant-predicate-scoped, from the new `migration.parent_target_project` key) against the tenant project's relation. Freshly-translated carve-out models keep the both-sides-predicated comparison, and every carve-out verdict records its scope and a hash of the exact predicate applied.

**Relocate feeds the pipeline.** `dbt-carveout-relocate-generate` now upserts relocated models into the migration register and chains the downstream gates by default (validate, lint, fix, pre-PR review; `--no-chain` opts out) — previously relocated models were invisible to `batch-raise` candidate derivation and the delivery stage ladder.

**Carve-out guardrails on the shipping commands.** `defer-build` gains a mechanical `tenant_write_guard` (every write lands inside the tenant project, no override) and a defer-state fallback chain ending at `--no-defer` when neither the tenant nor the parent has a usable prod manifest. `batch-raise` refuses `ship_then_verify` until the region-tagging adjudication and the DPO/legal residency review are complete. `utils-ci-parity --scaffold-from` derives parity checks from the parent repo's pipeline when the tenant repo has no CI yet.

**Fleet and spec debt.** Carve-out lane roster (region-tagging evidence, isolation verification scoped to RA-held credentials, bulk-copy monitor) with the park rule: human gates park items, they never stall lanes. And the region-tagging roles rule — a role with no name-suffix signal classifies by grant scope — closes the documented Step 2/Step 3 ambiguity; the test fixture that deliberately skipped it is now fully scored.

---

## v3.11.0 — The pipeline beyond "migrated": ship, verify, and the fleet operating model

**Released**: August 2026

The `platform_migration` release type used to end at "migrated" in the register; everything from a passing verdict to verified code on the client's main was free-form. v3.11.0 productises that tail, generalised from the first engagement to run the release at fleet scale — with the operating model itself written down: the director types intents and rulings, the orchestrating agent invokes the Wire commands and dispatches fleets of lane agents that report back through incremental state files (`specs/utils/migration_fleet.md`, including the mandatory consolidation/backstop pass over lane output).

**Four new commands.** `/wire:dbt-migration-defer-build` (cost-guarded sandbox builds: refs deferred to prod state, scratch-dataset writes only, exact-name selectors with graph operators refused by default, dry-run cost screen against per-run/daily budgets, per-project build-slot lock). `/wire:dbt-migration-batch-raise` (register-driven client PRs: deterministic eligibility table over gate policy x verdict x external-output exactness, smoke-build from the branch's own checkout, pre-raise comparison, drop-on-defect, evidence-first PR body). `/wire:utils-ci-parity` (detect the client repo's CI system and replicate its locally-runnable checks with the client's own config — the final pre-raise gate). `/wire:equivalency-post-merge-verify` (wait for the client pipeline to materialise merged models, compare production at the full bar, advance the register to `production_verified`).

**Verdict taxonomy and history.** `equivalency-validate` verdicts are now `pass` / `pass_qualified` / `diff_vintage` / `diff_availability` / `diff_schema_type` / `fail` — explanations qualify a fail, never upgrade it; every divergence is drilled to a named mechanism; verdicts bind to exact file versions and carry a run point (`standard` / `pre_raise` / `post_merge_prod`). An append-only verdict log (`migration/migration_verdict_log.csv`) preserves the dated history the current-state register cannot. Lane fan-out writes one JSON contract per lane with a deterministic single-writer merge. The register gains `delivery_stage` and `pr_url`, orthogonal to `state`.

Everything is additive: existing releases pick the new keys and columns up via `/wire:upgrade`, legacy `pass`/`fail` verdicts stay valid, and a release that never sets `gate_policy` or budgets behaves as before, minus the prose ending — `dbt-migration-fix` and `pre-pr-review` now hand off to `batch-raise` instead of "open the PR".

---

## v3.10.19 — Catch migration defects earlier, measure where they're caught, and fix the version check

**Released**: July 2026

Three changes, all following on from the widened migration gate (#150).

**Shift-left auto-fix in `dbt-migration-generate` (#167).** The per-model translation loop used to auto-fix only when the three-check equivalency comparison *failed* — so a defect that didn't break the sampled data (a bare `PARSE_JSON`, a `DIV0` NULL-coercion, an unpinned `SELECT *`, a dropped policy tag) passed and was left for a later gate, or the client, to catch. The loop now proactively applies the active pair's full deterministic rule set during translation and auto-rewrites the deterministic-and-safe ones inline, using the `dbt-migration-fix` auto/propose/decision policy — semantic, intent-dependent patterns are still only flagged, never rewritten. Four residual rules join the set: `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` (a new model missing from the deployment orchestrator's selection manifest — a documented no-op, never a false pass, when the manifest pointer isn't configured), `HARDCODED_TARGET_DATABASE_XPROJECT`, `CDC_SOURCE_NO_SOFT_DELETE_FILTER`, and `STALE_NULL_PAD_BRONZE_PRESENT` (in `migration-drift`, flag-for-restore only). And `generate` now chains `validate → lint → fix → pre-pr-review` by default (opt out with `--no-chain`), so a run leaves the gates already applied rather than stopping at "recommended next steps" — the skip that let defects reach the client on the early waves.

**Defect-provenance report (#168).** A new `migration-report-generate --lens defects` aggregates the structured findings every gate already emits into a per-wave view: which stage caught each defect (earliest of generate-inline / lint / validate / equivalency / pre-PR review), the auto-fixed vs escalated split, a client-caught count (explicitly `"not tracked"` when the optional client-review input is absent — never a silent zero), and a wave-over-wave trend so the leftward shift is visible at a glance. It surfaces a class that keeps reaching the client as a rule *candidate*; deciding to encode it stays a human call.

**`/wire:start` plugin version check fixed (#170).** The Phase 1 health check never actually detected anything — it looked for `~/.claude/plugins/wire/` and a `VERSION` file, neither of which exists, so it always reported "unknown" and never flagged an outdated plugin. It now reads the installed version from `~/.claude/plugins/installed_plugins.json` and the latest from the published plugin manifest, compares them with proper semver (so `3.10.9` reads as older than `3.10.18`), never nags when it simply couldn't reach the network, and hands you the correct current update commands.

---

## v3.10.18 — dbt snapshots migrate as a first-class object type

**Released**: July 2026

The migration commands only ever processed `models/` — dbt snapshots under snapshot-paths fell through, never audited, translated, or tested. That blocked downstream models that read them and risked silently losing SCD-2 history: re-running `dbt snapshot` from empty against the target keeps only the current state and drops every closed version. Snapshots are now a first-class migration object type across the `platform_migration` and `tenant_carveout` release types — catalogued, strategy-assigned, history-copied, translated, continued, tested, and ordered like any other object. Everything is dialect-agnostic; the SCD meta-column types and the `dbt_scd_id` hash computation are declared per platform pair.

Each snapshot is catalogued (`dbt-audit-generate` / `migration-inventory-generate`) with its strategy, keys, and dependency edges; assigned `copy_and_continue` (default) or `rebuild_from_T` (signed-off) in the strategy and register; history-copied to the exact target relation with the four `dbt_*` meta columns preserved (`bulk-copy-migration-generate`, frozen at baseline `T`); translated with its config kept byte-identical so `dbt_scd_id` doesn't re-hash and orphan the copied history, then continued with a single `dbt snapshot` run (`dbt-migration-generate`); and gated by a three-layer snapshot test — copy-parity, continuation, SCD integrity — that explicitly rejects a SELECT-only row-equivalence as sufficient (`dbt-migration-validate` / `equivalency-validate`). Batching orders each snapshot after its upstream ref and before its dependents.

**A `--snapshots` scope** (modelled on `--macros`) runs the snapshot-processing commands over snapshots alone. It makes the retrofit case clean: on a project whose models were already migrated wave-by-wave before snapshot support existed, re-run the catalog/strategy/batching steps (additive — models aren't re-translated), then migrate the snapshots on their own with `--snapshots` rather than re-running whole waves. The snapshot-history copy runs in both release types — tenant-filtered under carve-out, whole-history unfiltered in a full migration — while `bulk-copy`'s raw-table path stays carve-out-only. See the platform-migration guide for the full retrofit walkthrough.

---

## v3.10.17 — `column_order_drift` is now auto-fixed

**Released**: July 2026

Reordering a translated model's output projection back to source ordinal order is deterministic and parity-restoring — the column set is unchanged, only the order differs — so `dbt-migration-fix` now applies it automatically instead of drafting it for a consultant to confirm.

To keep that safe, `column_order_drift` is now reserved strictly for a **pure reorder**: the schema-equivalence check emits it only when the set already matches (all source columns present, every tail column allow-listed) and only the sequence differs. A set mismatch — an unexpected non-allow-listed column, or a missing source column — is the schema check's existing extra/missing-columns failure and stays escalated, since adding or dropping a column is intent-dependent. A `column_order_waived` reason still suppresses the finding, so an intentional reorder is never auto-reverted. `UNPINNED_SELECT_STAR` (W6a) stays a drafted suggestion.

---

## v3.10.16 — Column-order parity and the end of the unpinned `SELECT *`

**Released**: July 2026

In a lift-and-shift the target model's output schema is a contract — the column set *and* their order must match the source. Two gaps let that contract slip. The schema-equivalence check compared column *sets*, so a reordered projection passed clean while breaking positional consumers — UNION/INSERT by position, CSV/SAR exports, BI and reverse-ETL pinned to column order. And nothing banned an unpinned `SELECT *`, which silently gains, loses, or reorders columns as the upstream evolves. Both close the same way as the rest of the equivalency-gate work: declare the rule in the platform pair, enforce it in the command.

**W6a — unpinned `SELECT *` is now a lint error.** A model's final output projection must be an explicit column list. `SELECT *`, `SELECT <alias>.*`, and `SELECT * EXCEPT(...)` on the output projection are all `error` in `dbt-migration-lint` (`UNPINNED_SELECT_STAR`). Import and staging CTEs may `SELECT *` internally — detection tracks parenthesis depth, so only the model-producing projection is flagged, not a `*` inside a CTE, subquery, or `COUNT(*)`.

**W6b — the schema check now compares column order, not just the set.** The existing schema-equivalence check (`equivalency-validate` / `dbt-migration-generate`) reads both sides `ORDER BY ordinal_position` and compares the sequences. Source columns must come first in source order; a migration's own additions — audit/load-timestamp columns, then region/surrogate globalize keys — are allowed at the tail via a pair-declared allow-list. A positional mismatch fails as `column_order_drift`. An intentional, data-owner-signed-off reorder is recorded per model as `column_order_waived: <reason>` — mandatory by default, waivable per model, never globally off.

`dbt-migration-pre-pr-review` surfaces both before a PR is opened, and `dbt-migration-fix` drafts the fixes (reorder to source order; expand a banned `*` into the explicit source column list) as reviewable suggestions rather than committing them blind. Completes the W2–W6 equivalency-gate widening tracked on #150.

---

## v3.10.15 — Catching every spelling of the DIV0 NULL-coercion trap

**Released**: July 2026

Snowflake's `DIV0(a, b)` zeroes a zero divisor but propagates NULL inputs; `DIV0NULL(a, b)` also zeroes a NULL divisor. The faithful BigQuery forms are `IF(b = 0, 0, SAFE_DIVIDE(a, b))` and `IF(b = 0 OR b IS NULL, 0, SAFE_DIVIDE(a, b))`. Three wrong forms turn up in translated models — bare `SAFE_DIVIDE` (returns NULL on a zero divisor) and the two NULL-coercing wrappers `IFNULL(SAFE_DIVIDE(…), 0)` and `COALESCE(SAFE_DIVIDE(…), 0)` (both coerce NULL inputs to 0). The translation rule previously named only the `IFNULL` spelling, so the `COALESCE` spelling slipped through — and it is a silent divergence, so no row-level equivalency check catches it.

**The translation guide and reference now name all three wrong forms** for both `DIV0` and `DIV0NULL`, and state the faithful `IF(...)` forms explicitly.

**The divergence moved into the gate, not just the docs.** A new `DIV0_NULL_COERCION` pattern joins the snowflake_to_bigquery pair's edge-case runtime-failure set — the set `dbt-migration-pre-pr-review` reads. It is classified a silent divergence at severity `error`, because it corrupts NULL-sensitive downstream logic such as checksum and data-quality guards with no runtime error. `dbt-migration-fix` treats it as an `auto` fix: the `IF(...)` form is a deterministic, always-correct rewrite, so a flagged model is auto-corrected rather than hand-worked. Documented-but-not-enforced was the gap; the pattern set is what the automated gate actually consumes.

---

## v3.10.14 — Automating the pre-PR fix loop, so consultants adjudicate rather than hand-fix

**Released**: July 2026

The pre-PR faithfulness review (v3.10.12) finds the deploy-time defects and emits them as a structured list, but it is read-only by design — so acting on them meant a consultant hand-fixing each one and re-running the gate. That is mechanical toil for the majority of findings, which have deterministic fixes.

**A new `dbt-migration-fix` command** closes the loop. It ingests the pre-PR review findings, classifies each into one of three policies, and acts accordingly:

- **`auto`** — deterministic *and* semantically safe regardless of intent (prefix `SAFE.`, `SAFE_CAST`, re-anchor a regex, drop a redundant `TIMESTAMP()` wrap, add `IGNORE NULLS`, author a `policy_tags` when the tag map has an entry). Applied automatically, then the deterministic gate re-runs — looping, capped, until no auto-fixable finding remains.
- **`propose`** — deterministic to write but intent-dependent (a `TRIM()` on an `INT64` id might need a cast or might be spurious). Drafted into the escalation queue as a ready-to-apply suggestion, never committed silently.
- **`decision`** — needs information or judgment the loop does not have (DAG registration, an unconfirmed Bronze type, a parity-versus-correctness product call). Escalated, never guessed.

The consultant is left with only the `propose`/`decision` residue — the genuine decisions — instead of a wall of mechanical fixes. It mirrors `equivalency-fix`: detection stays read-only, fixing is a separate, explicit, re-runnable step. The expensive LLM client-review lens runs once at the end as confirmation, not inside the loop. The auto/propose/decision mapping lives in the platform pair and engagement overrides, so a client that trusts a pattern less can move it without a framework change. `--dry-run` reports the plan without editing. Ships with a behavioural test.

---

## v3.10.13 — Two more pre-PR translation guards from live migration review

**Released**: July 2026

Two additive checks in the migration pre-PR gate, both banked from a live Snowflake→BigQuery migration review where they slipped past the v3.10.12 checks. This is the feedback loop working as intended — a reviewer finding that a deterministic rule missed becomes a new rule, so the next migration inherits it.

`UNGUARDED_JSON_PARSE` now covers every unguarded JSON accessor — `JSON_VALUE`, `JSON_QUERY`, `JSON_EXTRACT*`, not just `PARSE_JSON`. An unguarded `JSON_VALUE` fails the whole incremental build on the first malformed or NULL row, where Snowflake simply returned NULL. Prefixing `SAFE.` restores the source's tolerance.

A new `STRING_FN_ON_NONSTRING` deployment type-divergence pattern flags a string function — `TRIM`, `UPPER`, `SUBSTR`, `SPLIT`, and the like — applied to a column that lands as a non-string type at the real deployment warehouse. The trigger case is a bare `TRIM()` on an id that arrives as `INT64`: it compiles fine against a validation warehouse where the column is a string, then errors at first run on the real Bronze. Only columns whose type was actually verified against deployment are safe to assume.

Both patterns are declared in each platform pair's `translation_guide.md` rule sections, so every migration inherits them, and both ship with behavioural tests.

---

## v3.10.12 — Closing the gap between "equivalent" and "deploys cleanly"

**Released**: July 2026

Wire's migration equivalency gate proves one thing well: the same rows come out, for the sampled data, on one default code path, in the validation warehouse. Deployment then fails on the surfaces that gate never exercises — a Jinja branch gated on `target.name` that a single full-refresh build never compiles, a generic test that `dbt run` never executes, an edge-case input row absent from the sample, a validation warehouse whose column types differ from the real deployment target, or a column masked at source that lands unprotected at target. A model Wire reported as equivalent could still come back from a client's PR review with defects that only fail at deploy time. This release widens the gate to cover that surface. Every check is driven by the active platform pair, so it generalises across every migration.

**`dbt-migration-validate` now exercises every rendered code path, not just one.** It compiles each model under every target profile the project defines — discovered from `profiles.yml`, never hardcoded — builds incremental models twice so the `is_incremental()` branch actually runs, and runs `dbt build` rather than `dbt run` so generic and singular tests execute. A per-model coverage report shows what was exercised rather than leaving a reviewer to assume it. A dev-only branch, an incremental-only predicate, or an unported test is now failed before a PR is opened.

**A deployment-warehouse type pre-flight**, shared by `dbt-migration-generate` and `equivalency-validate`, reads the real deployment warehouse's column types — not the scratch or sample warehouse a model was validated against — and flags the type-divergence patterns the platform pair declares: a `TIMESTAMP()` wrap on an already-typed column, a JSON function on a STRING-versus-JSON mismatch, an implicit cross-type join coercion. When the validation and deployment warehouses differ at all, it warns explicitly rather than passing silently.

**A column governance equivalence check**, separate from row-level equivalency. Row-level checks compare data and cannot see column-level security — a column masked at source but unprotected at target produces identical rows, so equivalency passes while the security posture regresses. The new check (equivalency check type 8) compares each column's protection at target against the source masking policy and fails when protection was dropped in translation.

**A new `dbt-migration-pre-pr-review` command** — a faithfulness review over the translated diff, run before a PR is opened. It composes the checks above plus the pair's edge-case runtime patterns — an uncast blank-string-to-numeric, an unguarded JSON parse, an unanchored regex — into a structured findings list with severity, `file:line`, and a suggested fix, so the defects are resolved locally instead of in the client's PR queue. Run it with `--format json --severity error` to gate CI.

Every enhancement ships with behavioural tests. The type-divergence patterns and masking mechanisms live in each platform pair's `translation_guide.md`, so a new pair inherits all four checks automatically.

---

## v3.10.11 — Catching a BigQuery clustering conflict before it ever reaches a build

**Released**: July 2026

BigQuery rejects a model that combines `cluster_by` with a top-level trailing `ORDER BY` on a full table rebuild (`Result of ORDER BY queries cannot be clustered`) — a pure static SQL-shape defect, deterministic every time the model goes through a real `CREATE TABLE ... CLUSTER BY (...) AS (...)`. Nothing caught it before this release. A model carrying the pattern could pass `dbt-migration-generate`'s inline materialisation step and `equivalency-validate`'s row-count/schema/sampling checks in one session and still fail outright the next time the same SQL ran through a real `dbt-bigquery` CTAS — whether it surfaced depended on incidental DDL-wrapping choices in how a given session executed the write, not on anything about the data. That was never a gap in equivalency validation (it correctly validates data that already materialised); it was a gap in what got checked before materialisation was attempted at all.

**New `CLUSTER_BY_ORDER_BY_CONFLICT` rule in `dbt-migration-lint`**, same category as the existing `MATERIALIZATION_DRIFT` rule — a pure static check, no BigQuery connection required. It reads `cluster_by`/`materialized` from the model's resolved manifest config (the same resolution `dbt-migration-generate` already uses), applying to `materialized: table` directly and to `incremental` too, since its first-run/full-refresh path issues the same CTAS shape. It does not grep for the `ORDER BY` keyword — it tracks parenthesis depth over the compiled SQL and only flags an `ORDER BY` at depth 0, the query's own outermost, unwrapped trailing clause. An `ORDER BY` nested inside a window function (`OVER (...)`), `QUALIFY ... OVER (...)`, an ordered aggregate like `ARRAY_AGG(x ORDER BY y)`, or a CTE's own subquery never reaches depth 0 and is correctly left alone. The fix is fully deterministic (strip the outer `ORDER BY` — clustering doesn't preserve physical row order, so it was never doing anything), surfaced as a suggested rewrite the same way every other rule in the catalogue is: never auto-applied, since `dbt-migration-lint` stays read-only.

Documented as a named gotcha in [`translation_reference.md`](https://github.com/rittmananalytics/wire-plugin/blob/main/wire/platform_pairs/snowflake_to_bigquery/translation_reference.md) — a BigQuery dialect quirk, not engagement-specific, so it fires for any migration that sets `cluster_by`.

---

## v3.10.10 — A BigQuery MCP fallback, so a known auth failure stops being handled inconsistently

**Released**: July 2026

`"Incompatible auth server: does not support dynamic client registration"` is a known, recoverable OAuth/dynamic-client-registration failure with a working alternative — the `bq` CLI, authenticated separately, does the same read/write job. Nothing in the spec told an agent to use it, so identical failures got handled inconsistently: some sessions improvised the CLI fallback and finished the batch, others hard-aborted or deferred to a manual checklist, with no record of which happened without reading every model's `.diff.md` by hand.

**New `specs/utils/bigquery_mcp_fallback.md`, referenced the same way as `migration_preflight.md` or `execution_log.md`.** It probes before every call, not once per batch — the connection has been observed to flap mid-run (works, breaks, works again), so a failed probe at the top of a batch isn't grounds to fall back the whole batch, and a fallback on one call isn't grounds to assume MCP is dead for the rest. On a probe failure it falls back to the `bq` CLI automatically — no user prompt, no silent defer — mapping compile-only checks to `bq query --dry_run`, real data reads to `bq query --format=json`, writes to `bq query` (no dry-run), and schema/listing calls to `bq show`/`bq ls`. It always passes `--location` explicitly, read from `migration.target_location` in status.md, never the CLI's own default — which caused silent US/EU dataset mismatches before this existed. Fallback usage is recorded as a per-run summary (`mcp_fallback_count`) folded into the calling artifact's own status.md/execution-log entry, not a separate log row per call. Only a genuine dual failure (MCP and the `bq` CLI both down) is still a hard abort.

**Wired into the three commands with a real hard-blocker BigQuery MCP dependency**: `dbt-migration-generate` (its MCP connectivity check and its per-model compile/run/equivalency queries), `target-setup-generate` (whose old "skip and defer to a manual checklist" behaviour on MCP failure is now the last resort, only after the `bq` CLI fallback also fails), and `equivalency-validate`. `dbt-carveout-relocate-generate`'s compile step uses local `dbt parse`/`compile` rather than the MCP directly, so it wasn't a candidate.

---

## v3.10.9 — `--wave` scoping across every migration execution command

**Released**: July 2026

`dbt-migration-generate` and `dbt-carveout-relocate-generate` were the only commands that could scope a run to one execution wave (`migration_batching.csv`'s authoritative build schedule) — despite that CSV assigning a wave to every object type it partitions, not just dbt models. `ingestion-migration-generate` and its siblings loaded every in-scope connector in one pass with no scoping flag at all.

**`--wave <id>` added to `ingestion-migration`, `reverse-etl-migration`, `orchestration-migration`, and `bulk-copy-migration`** (generate/validate/review), resolved identically to `dbt-migration-generate`'s existing wave logic but filtered to each command's own object type — connectors, reverse-ETL syncs, and orchestration jobs respectively. `orchestration-migration`'s "all dbt batches approved" prerequisite is now wave-aware too: a `--wave` run only needs that wave's dbt models approved, not the whole estate, which is what actually unblocks running orchestration migration per wave rather than only at the very end.

**`equivalency-validate` gained `--wave` alongside its existing `--batch`.** A wave spans every object type together (connectors, warehouse objects, dbt models, orchestration jobs, reverse-ETL syncs); `--batch` stays dbt-model-only, reading `dbt_audit.csv`'s topological scheme. The two are mutually exclusive. `migration-acceptance-pack-review` and `dbt-migration-review` now formally document `--wave` too — it was already usable in practice (the wave id substitutes directly into the same `batch_{N}` filename template) but had never been specified as a flag.

**Fixed a bug surfaced while doing this work**: `dbt-carveout-relocate-generate`'s manifest output was never wave-suffixed, so running it across multiple waves — the exact pattern its own tutorial worked example shows — would have silently overwritten the prior wave's manifest.

**Tenant Carve-out tutorial and reference updates.** A new tutorial section (Step 4a) walks through `dbt-carveout-relocate` for a carve-out staged after its parent migration has already landed, and every command mentioned in the tutorial now links to its definition in the [Platform Migration reference](../release-types/platform-migration#tenant-carve-out-variant).

---

## v3.10.8 — dbt-carveout-relocate, for a tenant carve-out staged after its parent migration

**Released**: July 2026

A tenant carve-out scoped **after** its parent platform migration has already landed doesn't need `dbt-migration`'s translate-and-equivalency loop — the target-dialect SQL for the carved-out tenant's models is already correct, sitting in the parent migration's dbt repo. This release adds the command that relocates it instead of re-deriving it.

**New `dbt-carveout-relocate-generate`/`-validate`/`-review` command triple.** Scope resolution mirrors `dbt-migration-generate`'s `--wave`/`--batch`/`--select` grammar, then filters to `region-tagging`'s adjudicated output (`item_type=dbt_model` and `adjudicated_ruling=carve_in`). Tenant-exclusive (`confident-region`) models are copied unchanged; models shared across every tenant (`shared-row-level`) get a `WHERE {tenant_predicate}` clause injected into their outermost `SELECT` — but only where the injection point is genuinely unambiguous (exactly one top-level `SELECT`, no top-level `UNION`/`INTERSECT`/`EXCEPT`). Anything more ambiguous is flagged `manual_review_required` rather than guessed, and any bucket that shouldn't have reached this scope at all aborts instead of being silently relocated. `-validate` re-derives every claim independently from the adjudicated CSV and the files actually on disk, never from the generate run's own report; `-review` is the human approval gate, blocked until every `manual_review_required` model is resolved.

**`region-tagging-review` now formalizes `region_tags_adjudicated.csv`** (`adjudicated_ruling`: `carve_in`/`split`/`defer`/`reassign`) as a real output artifact — this was previously only a manual spreadsheet convention on live carve-out engagements, and is now `dbt-carveout-relocate-generate`'s actual, checked input contract.

Ships with new Tier 1 behavioural tests covering the scope filter, the bucket-routing decision, and the round trip between generate's predicate injection and validate's independent re-derivation from the relocated file's own text — see [Testing Wire Itself](./testing).

---

## v3.10.7 — A tiered automated test suite for Wire itself

**Released**: July 2026

Wire's own workflow specs had never been tested against anything but eyeballing — this release builds a tiered automated test suite (Tier 0–3) covering every release type, fixes the dozen-plus spec bugs that testing immediately surfaced, aligns dbt conventions repo-wide against the company's canonical framework, and closes out a full verification pass of a real-engagement migration remediation.

**Tier 0 and Tier 1 now run on every push and PR, and gate `release.sh` itself.** Tier 0 (`wire/tests/lint_specs.py`) lints the whole spec corpus — frontmatter validity, the generate/validate/review triad shape, cross-references that actually resolve, and command registration in the packaging build script. Tier 1 extracts the deterministic logic embedded in spec prose (a coverage-classification rule, a tagging rule, a graph-selection grammar, a gating condition) into runnable Python fixture + expected-output tests, covering eight release types end to end — 28 checks in total via `wire/tests/run_all.sh`. `release.sh` now refuses to cut a release unless the full suite passes, and CLAUDE.md mandates a test for every new command, artifact, decision rule, or skill change going forward.

**That testing work surfaced and fixed a dozen-plus real spec bugs.** The dbt-development skill and all eight `dbt_*` workflow specs were quietly using a simpler, incomplete naming convention than the company's own canonical `ra_fw_core` dbt framework — realigned repo-wide, ~17 files. `droughty/generate.md` had a mode-determination bug that ignored an explicitly-set context; `workshops_review.md` was missing a meeting-context step every sibling spec has; `sprint_plan/validate.md` had two contradictory point-ceiling checks; four stub `validate.md`/`generate.md` templates had never been filled in with real content. Plus a command-registry cleanup (8 real commands added, 5 phantom ones removed) and several smaller typo/placeholder fixes.

**A real-engagement platform-migration remediation (wire#113) got a full verification pass.** All 23 tracked Wire-side fixes (W-1 through W-23) were checked against the actual codebase rather than trusting changelog prose — 21 confirmed fully implemented, 1 correctly not started and tracked separately (W-20, gated on a client decision), and the 2 that verification found partial were completed in this release.

**Two new Tier 0 regression guards close out gaps this release's own drafting process exposed.** The docs-site homepage version badge had silently drifted from the actual package version across four straight releases, because nothing in `release.sh` ever touched it — fixed at the root, and `lint_specs.py` now fails the build if the badge and the plugin manifest ever disagree again. Separately, a real client's name and engagement codename briefly leaked into this changelog, several skill files, and GitHub wiki pages during drafting — scrubbed throughout, and `lint_specs.py` gained a second permanent check that greps shipped content against a curated blocklist of confirmed-real client names so a leak like this can't ship unnoticed again. See [Testing Wire Itself](./testing) for how both checks fit into the full Tier 0–3 suite.

---

## v3.10.6 — Migration-lifecycle hardening from a real platform-migration delivery

**Released**: July 2026

A hardening pass across the platform-migration lifecycle, closing gaps a live client migration surfaced: validation order, orphan-connector handling, batching idempotency, and execution against the authoritative build schedule.

**dbt-audit-validate now catches a stale catalogue before anything else can pass against it.** Disk reconciliation — comparing the catalogue against the model files actually on disk — now runs as Check 1, first, instead of last. A substituted or stale catalogue used to be able to pass several count-based checks before the reconciliation check caught it; now nothing downstream runs against bad data.

**Orphan connectors and warehouse objects no longer default into wave 1.** `migration-batching-generate` previously fell back to placing any non-dbt object with no model consumer into wave/batch 1 — on one estate that put 105 of 168 connectors into wave 1 when only 31 belonged there, and wave 1 is what the client authenticates against first. Objects with no real model dependency now route to an explicit `NO-DEP` "no model dependency — review" bucket for human triage instead, in both partition modes. The command and its `review` companion also gained an idempotency guard, so a hand-corrected batching CSV is never silently overwritten by a blind re-run, plus a shared-reference build-priority rule, a secondary cutover-partition view, and configurable connector-alias normalization for its single-SCC build-ordered-waves fallback.

**dbt-migration-generate/lint/validate gain a `--wave` flag, resolving scope directly from `migration_batching.csv`'s build waves** — the authoritative execution schedule — instead of `dbt_audit.csv`'s finer-grained topological batches, which previously had no clean mapping to a wave. They also gained a `--config` overlay for isolated/validation runs without editing `status.md`, monorepo-aware manifest resolution via `dbt_manifest_parse.md`, a guard routing long-running builds through dbt instead of the `execute_sql` MCP tool (which enforces a hard ~3-minute timeout), a preference for `ref()` over `source()` when a source is already a migrated model, and a Bronze-schema column-existence check that substitutes `CAST(NULL AS type)` instead of emitting a reference that errors the build.

**New connective-tissue utilities**: `audit_baseline_check` fails loudly when an audit-generate command is handed a missing or empty baseline instead of silently generating off it; `utils-git-workflow` and `utils-session-summary` close the two largest "done by hand in chat" clusters from the engagement (branch-per-artifact + commit/PR sequencing, and drafting a Slack-shaped session summary from the execution log); `jira_sync` gained an opt-in full sync mode reconciling acceptance criteria and assignee. `ingestion-audit-generate` extended to Kleene, Funnel, and Amplitude, and `lineage-generate` — written but never registered in the package build — is now actually installable.

---

## v3.10.5 — Batch-zero macro & UDF pass, single-SCC batching fallback

**Released**: July 2026

Completes the batch-zero pass that `dbt-audit` has planned all along but nothing consumed, and makes migration batching reproduce the build-ordered plan that SCC-heavy estates always needed by hand.

**`dbt-migration-generate --macros` translates the shared macro layer.** The batch-zero macro plan (`audit/batch_zero_plan.json`) is the tiered list of shared macros and UDFs that must be translated before model batch 1 — a widely-used macro reaches models scattered across every batch, so it can't sit inside one. The new `--macros` scope mode reads that plan and translates the `layer: macro` Jinja/dispatched macro *definition* files in tier order (tier 0 first), mirroring the source `macros/` tree, reusing the same platform-pair guides and macro-first strategy as model translation. It's a standalone scope — not combinable with `--batch`/`--model`/`--select`, and it does not overload `--batch 0`. There's no row-equivalency loop: a macro is validated when the models that expand it compile, so it's a compile-only pass checked by `dbt-migration-validate --macros`.

**`target-setup-generate` now deploys the UDF layer.** UDFs (`create_udfs`, `fn_*` → `CREATE FUNCTION`) are warehouse DDL, not Jinja, so they belong with the other target objects rather than in `dbt-migration`. Each plan entry carries a `layer` field (`macro` | `udf`) that routes it; `target-setup-generate` translates the `layer: udf`, `action: translate` entries into tier-ordered `CREATE FUNCTION` statements in a new `05_udfs.sql`, run as target-setup Phase 1. A UDF with no direct target equivalent (`action: redesign`) is not mechanically translated — it surfaces in the MANIFEST's "UDF redesign decisions" section as an architecture choice (BigQuery ML / Vertex AI / remote UDF / in-model rewrite) that the `target-setup-review` safety gate must sign off before the affected models are translated.

**`migration-batching-generate` falls back to build-ordered waves for single-SCC estates.** When every domain cross-references every other — the domain graph is one strongly-connected component — no domain grouping can be both acyclic and declare every cross-batch edge, so the domain partition can never validate. The command now detects that and switches `partition_mode` to `build_ordered_waves`: it topologically sorts the model graph, cuts it into `--target-batches N` waves (default: the domain-group count), and makes each wave depend on the full prefix of earlier waves — trivially acyclic and edge-complete. The domain tag stays on every row for client and milestone rollup even though it's no longer the build order, and the fallback is recorded in the narrative and `status.md` (`scc_fallback: true`). `migration-batching-validate` reads `partition_mode` and applies mode-aware checks.

---

## v3.10.4 — Cube, Omni, and OAC semantic-layer options; Wire Studio and agentic_commerce removed

**Released**: July 2026

Three new semantic-layer/reporting-tool options, a real bug fix from live migration feedback, and a cleanup pass removing two low-usage features and their remaining references.

**Cube.dev, Omni Analytics, and Oracle Analytics Cloud (OAC) join LookML as semantic-layer options.** Each ships as a `wire/skills/` entry activated when the engagement's semantic layer is that tool rather than Looker: `cube` encodes RA's own Cube modeling conventions and coding standards alongside Cube's core concepts and MCP server; `omni` wraps the official `exploreomni/omni-agent-skills` and adds `omni-audit`/`omni-migration` reporting-layer migration commands (gated on `migration.reporting_tool: omni`); `dbt-to-smml` and `smml-semantic-modeling` generate and hand-author OAC's SMML (Semantic Modeler Markup Language) semantic model from a dbt project, with `oac-audit`/`oac-migration` commands for reporting-layer migration (gated on `migration.reporting_tool: oac`). OAC's dialect-specific SQL concentrates in the physical layer (connection pools, physical tables, physical joins), so its migration classification happens at the physical-table level, mirroring how Omni's classification happens at the model-view level rather than per-tile.

**`dbt-audit-generate` no longer misclassifies conditionally-enabled models as disabled.** Models whose `enabled` config resolves from a `var(...)` — in-model `config()` blocks or folder-level `+enabled` in `dbt_project.yml` — are now classified `conditional:<var_name>` and kept in migration scope regardless of the var's default resolution, with dependency edges resolved via a flags-on re-parse or a documented fallback rule. `dbt-audit-validate` independently re-scans for var-driven config to catch a model still marked `true`/`false`/null-batch that should be `conditional`.

**Wire Studio (the `wire-web-ui` browser interface) and the `agentic_commerce` release type are removed entirely**, along with every reference across docs, build scripts, and tests — both showed effectively no engagement usage against BigQuery telemetry. `USER_GUIDE_droughty.md` and `USER_GUIDE_platform_migration.md`, which duplicated content already in `USER_GUIDE.md`, are also removed, along with three stale feature-design docs for work that had already shipped.

---

## v3.10.3 — dbt audit hardening, migration batching, PII/equivalency fixes

**Released**: July 2026

A round of fixes and a new command trio, each traced back to specific feedback from a live Snowflake → BigQuery migration. Additive and backward compatible.

**`dbt-audit-generate` hard-fails on an unresolvable project** — no more silently substituting a prior release's catalogue, the failure mode that produced a stale, wrong audit undetected. It resolves nested dbt projects one level down when the configured path has no `dbt_project.yml` of its own, orders batches with a real topological sort over a parsed manifest (replacing a `ref_count` heuristic that produced hundreds of forward-reference violations), scans the macro layer for platform-specific SQL — classifying each hit macro `translate` / `redesign` / `manual-review-out-of-scope` — and produces a tiered **batch-zero macro translation plan** as a first-class artifact. `dbt-audit-validate` gains a disk-reconciliation check that independently re-derives the catalogue rather than trusting generate's self-report.

**New `/wire:migration-batching-*` trio** — partitions the migration inventory into named domain batches (independently-schedulable, multi-layer slices, distinct from `dbt_audit`'s translation batches) checked against the real dependency graph. `-review` is the client adjudication gate for composition and schedule; `-validate` re-derives the graph independently, catching a batch plan drifting out of sync with reality the way a hand-drawn plan can once the true dependencies are known.

**PII policy tags resolve automatically** — `dbt-migration-generate` looks up a tag map with a case-normalised lookup instead of requiring manual per-column authoring, flagging unresolved policies `MANUAL REVIEW REQUIRED` rather than dropping them silently.

**Equivalency pins relative-date models in live mode too** — not just under the opt-in `--baseline` freeze — closing a false-divergence gap that cost a real investigation cycle on a pilot migration. Reports are now organised at the table level with explicit column-completeness and value-match lines per table.

**Housekeeping** — Atlassian MCP endpoint updated from the deprecated `/v1/sse` path to `/v1/mcp`.

---

## v3.10.2 — Platform-migration hardening

**Released**: June 2026

Hardening from a Snowflake → BigQuery lift-and-shift: migrate models faithfully, validate them deterministically, and keep them in sync with a moving source. Additive and backward compatible.

**Faithful materialisation + override hook** — `dbt-migration-generate` now preserves each model's resolved materialisation (incremental stays incremental with its strategy/partition/cluster; table stays table), instead of a blanket `materialized: table`. An engagement can diverge via a declarative override file (`migration.materialization_overrides_path`: `default: preserve` + `overrides[]` with `select`/`exclude`/`force_materialized`); the framework ships no path, no layer names, no rules.

**Deterministic, frozen-baseline equivalency** — `migration-strategy` defines the frozen baseline (instant `T`, Snowflake zero-copy clone, BigQuery Bronze watermark, expected type-translation allow-list). `equivalency-validate` gains a baseline-pin mode (`--baseline`), a deterministic-build switch, a tier-3 value-level comparator (per-column fingerprints + normalised cross-platform row hash), run-metadata capture, and `--batch` fan-out. `migration.equivalency_baseline` is a release-level field.

**Per-model register + scheduled drift gate** — `/wire:migration-register-*` records per model: source path, last-migrated commit, BigQuery target, state, and last equivalence result. `/wire:migration-drift-*` diffs the live source against each model's last-migrated commit (`dbt ls --select state:modified`), classifies new/modified/removed, flags downstream Hightouch syncs (via a new `model_sync_map.json` from `lineage-generate`), and triggers a policy-tag regeneration when a source `meta.masking_policy` changes. Ships with on-change and scheduled CI templates.

**Housekeeping** — client engagement records relocated out of the framework repo; the client name removed from all specs, docs, templates, and fixtures.

---

## v3.10.1 — Tenant carve-out variant + Metabase reporting layer

**Released**: June 2026

A tenant carve-out variant for the platform migration release type, plus Metabase reporting-layer support. Both are additive and backward compatible — a full migration with no Metabase behaves exactly as before.

**Tenant carve-out variant** — platform migration now runs in `tenant_carveout` scope as well as the default `full_migration`, set by `migration.scope` with a `migration.tenant_predicate` captured at `/wire:new`. The carve-out reuses the whole migration command set and threads tenant scoping through equivalency — the existing checks gain the predicate on both source and target, with no new check types (min/max already lives in value sampling; checksum and aggregate totals already exist; schema stays structural) — and through the security/IAM chain: tenant-scoped vs shared role classification → a two-project / tenant-scoped IAM model with a row-level security predicate → tenant-scoped GRANTs and the RLS policy in `04_security.sql`, reusing the existing PII policy-tag taxonomy.

**New carve-out commands** — `/wire:region-tagging-*` classifies in-scope items into confident-region / shared-row-level / global-deferred buckets (candidates for adjudication, never a binary include/exclude or auto-removal; `-review` is the human adjudication gate). `/wire:data-residency-assessment-*` produces the GDPR and data-residency assessment including the legal review of the historical data window — RA prepares it as data processor and flags every point needing the client's DPO/legal determination, with `-review` as the client sign-off gate. `/wire:bulk-copy-migration-*` does a Snowflake → BigQuery bulk historical copy (BigQuery Data Transfer Service / GCS-staged) in place of re-ingestion, two-stage with an equivalency gate between pilot partition and remainder, under a scoped service account with a tenant guard. `/wire:logical-access-uat-*` proves region-scoped access isolation — `-validate` requires at least one negative test per IAM boundary in `04_security.sql`, and `-review` is the isolation-proof sign-off before cutover.

**Metabase reporting-layer support** — Wire's reporting-layer support was Looker-only. Set `migration.reporting_tool: metabase` to enable `/wire:metabase-audit-*` and `/wire:metabase-migration-*`, a general capability for any migration where the client uses Metabase, not gated by `migration.scope`. The audit catalogues collections, dashboards, cards (with SQL), database connections, and permission groups; the migration translates card SQL to BigQuery, remaps permission groups, validates on a throwaway decoy collection, and repoints the Metabase database connection from Snowflake to BigQuery in two stages with per-stage rollback (it requires a client-supplied query inventory). Both build on the imported `metabase` skill, wrapping the upstream `metabase/agent-skills`.

---

## v3.10.0 — Platform-migration hardening

**Released**: June 2026

Platform-migration hardening ahead of a full Snowflake → BigQuery migration. A series of pilot calls turned up ways the reverse-ETL and dbt-migration commands would have misfired at estate scale; this release fixes them. All changes are additive and backward compatible.

**Reverse-ETL topology — additive PR-gated syncs in the existing repo** — the default was a parallel workspace, which is wrong when Hightouch is managed by GitHub Sync: GitHub Sync carries models and syncs but not destinations, so a new workspace forces re-authenticating every destination. The default is now additive — branch the existing config repo, add target-warehouse syncs alongside the source-warehouse ones, reuse destinations in place, and stage every change as a pull request the client reviews and merges. RA never enables/disables syncs directly. Cutover is two client-merged PRs (disable source-origin, enable target-origin). Parallel-workspace and in-place re-point remain documented alternatives.

**Decoy destination mapping** — destination safety is now a decoy ID-mapping table plus a scoped credential, not a "disabled" flag. Each test sync carries a decoy destination of the same type; production destination IDs are absent until the cutover PR swaps them back; the credential can write to decoy targets only.

**Drift-aware translation** — the command reads a per-release drift manifest and won't apply the generic `VARIANT → JSON` / `JSON_VALUE` mapping to a column that lands as `STRING` under BigLake Iceberg, mirroring any reconciliation a `dbt_migration` diff already recorded.

**Re-verified audit tags and scope gate** — approach tags are re-checked before translating (re-scanning `repoint` syncs for `::`, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, and variant-path access, reclassifying to `rewrite_model` when found), and any sync whose source model isn't built on target is deferred rather than silently included.

**Reverse-ETL audit — table/custom source resolution** — `table` and `custom` model types now have their source objects resolved (previously only some `rawSql` models did, leaving ~37% of active syncs with no recorded object). The audit reports source-resolution coverage and lists unresolved syncs explicitly.

**dbt-migration — per-model transformation log to BigQuery** — a structured record per migrated object (object, batch, dialect changes, manual-review flags, confidence) is persisted to a configurable BigQuery audit table. The `.diff.md` output is unchanged; this is additive.

**New — shared migration pre-flight gate** — a shared spec referenced by both migration generate commands confirms, before a batch starts, that the source dbt project was freshly re-synced for this batch, source objects exist and have data on target, the target environment is prepared (not a playground), and (reverse-etl) the decoy mapping and scoped credential are in place. Any failure stops the command before generating.

---

## v3.9.9 — Iterative migration loop, source registration, batch DAGs, acceptance packs

**Released**: June 2026

Four improvements to the platform migration release type, driven by observations from a live engagement pilot.

**Iterative translation+equivalency loop** — `/wire:dbt-migration-generate` now embeds a per-model closed loop directly. For each model: translate → compile-check (LIMIT 0) → run on target → three equivalency checks (row count ±0.5%, schema, 1000-row column value sampling) → auto-diagnose and fix on failure → repeat up to 5 iterations. Both source and target platform MCPs must be connected before the command starts. No mid-loop manual review prompts — the loop runs autonomously for all models in the batch, then prints a results table.

**Source repository management** — two new commands manage the source dbt project snapshot: `/wire:migration-source-register <release>` records the git repo URL (or local path), branch, and models path in `status.md`. `/wire:migration-source-refresh <release>` pulls or clones the repo into a local cache. `dbt-migration-generate` checks `migration_source.last_refreshed` at startup and warns if the snapshot is older than 24 hours.

**Mermaid batch DAGs** — `/wire:migration-strategy-generate` now generates one Mermaid flowchart per batch at `artifacts/migration_strategy/dag_batch_N.md`. Initial state: all nodes grey (not started). As `dbt-migration-generate` processes each model, nodes update in-place: orange = translated/in-progress, green = equivalency passed, red = failed after 5 iterations. DAG files are embedded in the strategy document.

**Migration acceptance packs** — after all models in a batch reach terminal state, `dbt-migration-generate` auto-generates `acceptance_pack_batch_N.md` with a per-model results table, confirmation statements, Mermaid DAG embed, and sign-off block. New command `/wire:migration-acceptance-pack-review <release> [--batch N]` presents the pack for stakeholder sign-off (Approve/Reject/Hold), appends the completed sign-off to the document, and syncs to Jira and the document store.

---

## v3.9.8 — dbt node selectors for migration translation; quieter telemetry

**Released**: June 2026

`/wire:dbt-migration-generate` gains `--select` and `--exclude` flags accepting dbt's full node-selection grammar — graph operators (`+vehicles`, `vehicles+`, `+vehicles+`, `2+vehicles`, `@vehicles`), space-separated unions, comma-separated intersections, and `tag:` / `config.materialized:` / `path:` set selectors. This scopes which models a migration translates by their graph relationships — for example `--select +vehicles` translates `vehicles` plus everything upstream of it, the natural shape for a lift-and-shift pilot slice.

Wire resolves the selector itself over the source project's dependency graph — **no dbt binary is required**. The graph is read from the source project's `target/manifest.json` (a plain JSON artifact, no warehouse connection), with a fallback that parses `ref()`/`source()` and YAML config when no manifest is present. Before translating, Wire prints the resolved model list for confirmation and aborts if the selector matches nothing. `--select` cannot be combined with `--batch`/`--model`/`--models`; a bare `--select vehicles` behaves exactly like `--model vehicles`.

**Quieter telemetry** — anonymous usage tracking no longer runs as visible Bash tool calls inside every command. On the Claude Code plugin it moves to a `UserPromptExpansion` hook that fires when a `/wire:` command runs, so nothing clutters the console. Behaviour is unchanged: still anonymous, still opt-out with `WIRE_TELEMETRY=false`. The Gemini CLI extension, which has no hook system, uses a single backgrounded call instead.

---

## v3.9.7 — Migration reliability: post-execution hooks, stale artifact detection, Data Safety blocks, ingestion pre-flight

**Released**: June 2026

Post-execution hooks are now on every migration spec. All 16 migration generate and 16 migration validate commands run execution log → Jira sync → docstore sync → auto-commit after every run, bringing them into line with non-migration commands. A new `specs/utils/commit.md` utility handles the git commit step.

**Stale artifact detection** — all 16 migration generate commands now prompt before overwriting an already-complete artifact. If `generate: complete` is set in `status.md` or the output file already exists, the command asks for confirmation. First-time runs see no friction.

**Data Safety blocks** — `/wire:dbt-migration-generate`, `/wire:ingestion-migration-generate`, `/wire:equivalency-validate`, and `/wire:reverse-etl-migration-generate` now emit a named READ ONLY reminder before starting, listing blocked production project IDs from `data_safety.production_projects`. Production project IDs are collected during `/wire:new` setup for `platform_migration` releases.

**Ingestion pre-flight expanded** — `/wire:ingestion-migration-generate` now probes all ingestion tools in scope before starting, not just Fivetran. It reads the audit for every distinct tool with `include_in_migration: true` connectors and checks each one's MCP server or API credentials. Coverage: Fivetran, RudderStack, Coupler.io (MCP); Airbyte, Segment (API env vars); Stitch/other (runbook-only). Auth failures halt the run; unconfigured tools fall to the runbook path.

**`/wire:mcp` simplified** — `update` and `auth` subcommands removed (wrappers around `claude mcp` with no Wire-specific value). Now `list`, `view`, and `check` only. New `check [release-folder]` subcommand probes all MCP servers required by a release and reports CONNECTED / AUTH_REQUIRED / UNAVAILABLE / NOT_CONFIGURED per server. The platform_migration playbook session start sequence is now: `/wire:start` → `/wire:mcp check` → next command.

Other improvements: `/wire:start` adds a Recent Activity table from `execution_log.md`; `/wire:new` detects duplicate releases before creating; `/wire:target-setup-generate` outputs a `~/.dbt/profiles.yml` block to the console; Jira `state_mapping` in `status.md` overrides default workflow transition labels.

---

## v3.9.6 — MCP-driven ingestion migration, parallel dbt agents, Looker mockup refinements

**Released**: June 2026

**Ingestion migration is now MCP-driven.** `/wire:ingestion-migration-generate` probes the relevant ingestion tool's MCP server (Fivetran, Airbyte, etc.), creates new connectors on the target destination, and generates connect card URLs for credential entry — no manual UI steps beyond opening each link. Wire always creates new connectors; it never edits or re-points a source connector mid-parallel-run. The runbook fallback applies when the MCP server is unreachable.

**dbt migration now uses parallel agents within each batch.** Models are split into groups of ~5 and one `wire:migration-specialist` agent is spawned per group simultaneously — a 20-model batch runs as 4 agents in parallel. Translated models preserve the source project's folder structure (`models/staging/stripe/stg_x.sql` → `migration/dbt/staging/stripe/stg_x.sql`).

**Looker dashboard mockup** visual refinements: PNG image assets replace SVG placeholders for the logo, Create button, and toolbar strip; chart colours use the Google standard palette (`#4285F4`, `#EA4335`, `#FBBC04`, `#34A853`, `#FF6D00`, `#7E57C2`); font weight 400 globally on labels, tabs, table headers, and chart axes; KPI tile accent bars removed; tiles centred; no freshness label; no filter count badges.

---

## v3.9.5 — Auto-delegation for all generate commands + docs expansion

**Released**: June 2026

Every generate command now auto-delegates to its specialist agent — not just migration commands. v3.9.5 extends the delegation protocol to all 44 remaining generate specs across requirements, discovery, design, development, testing, deployment, and enablement.

**Key changes**:
- 11 new shared utility specs (`specs/utils/*_delegate.md`) — same 4-step protocol as the migration delegate: check agent definition, re-entrancy guard, dispatch to specialist, inline fallback
- Auto-delegation preamble added to all 44 non-migration generate specs
- Docs site: [How Wire Works](../getting-started/how-wire-works) page added to Getting Started
- Docs site: mermaid diagrams now centred sitewide
- Docs site: "First release?" info admonition added before `/wire:new` block in all 12 release-type tutorials
- Docs site: [Platform Migration](../release-types/platform-migration) `## MCP server connections` section — Snowflake, BigQuery, Fivetran, RudderStack, Coupler.io, Segment, Airbyte, Hightouch, VPC tunnel
- Homepage colour updated to `#4F60FF`, feature highlights corrected to 50+ slash commands
- `LICENSE` now included in the wire-plugin dist package

---

## v3.9.4 — Docs cleanup and bundling fix

**Released**: June 2026

Version strings and documentation pages updated to reflect v3.9.3/v3.9.4 changes. Docusaurus docs-site bundled into the plugin release via `build-packages.sh`. No spec or behaviour changes beyond v3.9.3.

---

## v3.9.3 — Migration generate commands auto-delegate to `migration-specialist`

**Released**: June 2026

All 16 migration `generate` commands now check for the `wire:migration-specialist` agent definition and dispatch to it automatically — closing the gap where `delegate.md` documented per-command auto-delegation but no individual migration spec implemented it.

**Key changes**:
- New shared utility spec `specs/utils/migration_agent_delegate.md` — 4-step delegation protocol: check for agent definition, re-entrancy guard, dispatch to `wire:migration-specialist`, inline fallback
- Auto-delegation preamble added to all 16 migration generate specs: `target-setup`, `dbt-migration`, `ingestion-migration`, `migration-strategy`, `migration-inventory`, `cutover`, `db-object-audit`, `dbt-audit`, `ingestion-audit`, `orchestration-audit`, `orchestration-migration`, `reverse-etl-audit`, `reverse-etl-migration`, `security-audit`, `migration-report`, `lineage`
- `utils/migration-agent-delegate` compiled as a registered command in the plugin so installed instances resolve the spec reference at runtime

See [Wire Agents](../advanced/wire-agents) and [Platform Migration](../release-types/platform-migration) for full details.

---

## v3.9.2 — `dashboard-mock-developer` and `mock-data-developer` agents

**Released**: June 2026

Two new specialist agents activate exclusively for `dashboard_first` releases, bringing the total to 14.

**`dashboard-mock-developer`** owns the interactive mockup phase. It generates an HTML mock immediately from requirements, iterates with you until approved, then produces three derived artifacts atomically: `dashboard_visualization_catalog.csv`, `dashboard_spec.md`, and `data_model_requirements.md`. The last file is the primary input for `data-designer` and `mock-data-developer`.

**`mock-data-developer`** handles seed data and data refactor — two time-separated phases. Phase 1: CSV seed files with referential integrity and domain-realistic distributions, allowing `dbt seed && dbt run` before any client data access. Phase 2: repoints staging models from seeds to real client sources once access is confirmed, with a written refactor plan before any code changes.

See [Wire Agents](../advanced/wire-agents) and [Dashboard-First](../release-types/dashboard-first) for full details.

---

## v3.9.1 — Fan-out parallelism for large dbt model sets

**Released**: June 2026

`/wire:delegate` gains fan-out parallelism: when a dbt layer has more than 5 models, it splits the layer into batches of 5 and runs one `dbt-developer` agent per batch in parallel. Layers remain sequential (staging → integration → warehouse); agents within each layer wave run concurrently. The same fan-out applies to `semantic-layer-developer` (by explore) and `migration-specialist` (by source system).

---

## v3.9.0 — Wire Agents Phase 1: 12 Specialists + `/wire:delegate`

**Released**: June 2026

The agent taxonomy expands to 12 specialists covering every Wire release type. The orchestration command is rewritten for local execution — no managed agents API required, no external API key beyond the user's existing Claude Code subscription.

### New specialist agents

| Agent | Release types |
|---|---|
| `discovery-analyst` | discovery, sop_discovery |
| `data-designer` | full_platform, pipeline_only, dbt_development |
| `pipeline-engineer` | full_platform, pipeline_only |
| `dbt-developer` | full_platform, pipeline_only, dbt_development |
| `semantic-layer-developer` | full_platform, dbt_development |
| `orchestration-engineer` | full_platform, pipeline_only |
| `data-quality-engineer` | full_platform, dbt_development |
| `migration-specialist` | platform_migration |
| `delivery-lead` | all release types |
| `agentic-data-stack-developer` | agentic_data_stack |
| `agentic-commerce-developer` | agentic_commerce |
| `qa-agent` | all release types |

### Key changes

- **`/wire:delegate`** replaces `/wire:orchestrate` — dispatches pending release work to specialist subagents using Claude Code's native Agent tool. Runs on the user's workstation, using their existing API key. No managed agents service needed.
- Each agent appends non-obvious decisions to `decisions.md` as it works — downstream agents and human reviewers use this as a lightweight audit trail.
- **Auto-delegation**: individual generate and validate commands now delegate to the appropriate specialist automatically. Review commands stay in the main session.
- All 12 agent definitions are bundled into the distributed plugin under `agents/`.

See [Wire Agents](../advanced/wire-agents) for full usage.

---

## v3.8.6 — Wire Agents Phase 1: Initial Eight Agents

**Released**: June 2026

First cut of the specialist agent system. Superseded by v3.9.0 which expanded the taxonomy and replaced the orchestration model.

- Eight initial agents: `dbt-developer`, `lookml-developer`, `dashboard-prototyper`, `migration-auditor`, `qa-agent`, `data-quality-agent`, `stakeholder-interviewer`, `playbook-generator`
- `/wire:orchestrate` command (replaced by `/wire:delegate` in v3.9.0)
- `status.md` gains an agents block: mode, active sessions, completed sessions
- `/wire:upgrade` surfaces `/wire:orchestrate` for releases created before v3.8.6

---

## v3.8.5 — Wire-Aware PR Template

**Released**: June 2026

- New **`/wire:utils-pr-create`** command — reads `execution_log.md` and `status.md` to auto-populate a pull request body
- `/wire:new` Step 10.5 now scaffolds `.github/pull_request_template.md` at engagement setup
- PR template sections: release folder, artifacts changed, Wire commands run, Wire commands next, Jira/Linear links

---

## v3.8.4 — dbt Migration Companion YAML Coverage

**Released**: June 2026

`dbt-migration-generate` and `dbt-migration-validate` now cover the companion schema/properties YAML alongside the model SQL.

- Explicit repointing of `sources.yml` to the target namespace (parameterised `database`/`schema`)
- Translation of source-dialect SQL inside singular tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments
- Column-level `policy_tags`/`meta` authored into the YAML when column protection is dbt-managed
- New validate **Check 7**: enforces companion-YAML coverage — un-repointed `sources.yml`, untranslated test SQL, or dropped policy-tag config all fail

---

## v3.8.3 — Reverse ETL Parallel-Workspace Migration

**Released**: June 2026

Hightouch migration defaults changed to reduce production risk during warehouse migrations.

- **Parallel-workspace topology** (new default): clone the Hightouch config repo into a fresh workspace pointed at the target warehouse, validate with syncs disabled, then enable — leaving the source-backed workspace untouched until cutover. In-place source re-point retained as a fallback.
- Validation is now **preview-based against a frozen source baseline**: destination connections present but disabled; sync previews and record-level inspection only.
- Added **sync-level transformation review**: field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion per sync — a matching model output doesn't guarantee a matching sync.

---

## v3.8.2 — `/wire:upgrade` and Wire Adoption Review

**Released**: June 2026

### `/wire:upgrade`

Brings an existing release `status.md` up to date with the current plugin version's schema.

- Adds missing YAML sections and keys from the canonical template for the release type
- Stamps `wire_plugin_version` and `last_upgraded_at`
- Surfaces new commands that weren't available when the release was created
- `--dry-run` flag to preview changes without modifying files
- Idempotent — safe to re-run. Complements `/wire:migrate` (which handles layout changes); `/wire:upgrade` handles schema drift within an already-correct layout.

### `cowork-wire-adoption-review` skill

New Wire Work plugin skill — generates structured Wire and Claude Code adoption reports from BigQuery telemetry (`ra-development.analytics.coding_agent_prompts_fact`).

Three report types:
- **Project-level**: adoption rate, command usage, session lifecycle compliance, discovery phase gap analysis, recurring manual patterns, recommendations
- **Consultant-level**: individual usage patterns across engagements, comparison to RA average
- **Company-wide**: cross-engagement analysis — what worked, what didn't, standardisation progress

Enriches from GitHub delivery repos, Jira, and Fathom meeting context when available.

---

## v3.8.1 — Platform Migration Translation Improvements

**Released**: June 2026

- Two new platform-pair translation examples: array-membership joins (`FLATTEN` / `IN UNNEST` / `ARRAY_CONTAINS`) and `ARRAY_AGG` null and struct-array semantics
- New `dbt_neutral_translation.md`: macro-first hierarchy (dbt built-in → `dbt_utils` → dispatched macro → `target.type` last) and equivalence-testing backbone for dual-target projects
- New `snowflake_to_bigquery/translation_reference.md`: exhaustive deep reference with a 25-item silent-behaviour-change checklist
- New **`/wire:dbt-migration-lint`**: static, offline pre-warehouse equivalence lint (dialect parse-check + silent-behaviour-change rules) run before the live equivalency loop
- New feature-detection tags: `flatten_join`, `array_agg`, `in_unnest`

---

## v3.8.0 — Droughty Integration

**Released**: June 2026

Integrates the Droughty schema-introspection toolkit as a first-class Wire release type. Droughty is a bottom-up, schema-driven complement to Wire's top-down document-driven workflow.

Nine new `/wire:droughty-*` commands:

| Command | What it does |
|---|---|
| `/wire:droughty-setup` | Install pinned Droughty, generate `profile.yaml` and `droughty_project.yaml` |
| `/wire:droughty-introspect` | Schema inventory: tables, columns, estimated row counts, PK/FK coverage |
| `/wire:droughty-dbml` | DBML entity-relationship diagram from live warehouse schema |
| `/wire:droughty-docs` | AI-generated field descriptions for all warehouse columns (requires OpenAI key) |
| `/wire:droughty-qa` | LangGraph data quality agent report (requires OpenAI key) |
| `/wire:droughty-stage` | dbt staging SQL + `sources.yml` from a BigQuery dataset |
| `/wire:droughty-dbt-tests` | Pattern-based `schema.yml` tests from deployed table schema |
| `/wire:droughty-lookml` | Base LookML views from deployed dbt tables; writes to `views/generated/` |
| `/wire:droughty-generate` | Full Droughty phase in sequence |

Two operating modes: **discovery/audit** (maps an existing warehouse — no dbt deployment needed) and **post-dbt** (generates the base LookML and test layer from deployed dbt models, feeding into `/wire:semantic_layer-generate`).

See the [Droughty release type](../release-types/droughty) for a full walkthrough.

---

## v3.7.x — Platform Migration, Agentic Data Stack, Snowflake

**Released**: June 2026

Major features added across the v3.7 series:

- **v3.7.7** — Full Snowflake support: estate audit via Snowflake MCP server; all Snowflake-native object types catalogued (Dynamic Tables, Streams, Tasks, Pipes, Semantic Views, masking/row-access policies). Hightouch reverse ETL audit added as a sixth `platform_migration` audit track.
- **v3.7.5** — Interactive lineage visualisation: `/wire:lineage-generate` produces a self-contained HTML dependency explorer showing the full dbt graph from raw source to warehouse object. Six layers: Ingestion → Seeds → Staging → Integration → Warehouse → DB Objects.
- **v3.7.4** — `agentic_data_stack` gains an explicit LookML views step (`/wire:ads_lookml-views-generate/validate/review`) between canonical models and the semantic layer build.
- **v3.7.3** — **Agentic Data Stack** release type: 41 new `ads_` commands across five phases (Audit, Design, Build, Validate, Deploy). Addresses governance failures — accuracy failures in analytics agents are almost always caused by too many tables or conflicting metric definitions.
- **v3.7.0** — **Platform Migration** release type: full warehouse-to-warehouse migration lifecycle (BigQuery ↔ Snowflake ↔ Databricks) with six parallel audit tracks: database objects, dbt models, dashboards, pipelines, orchestration, and reverse ETL.

---

## v3.5.x — Agentic Commerce, Droughty Preview

**Released**: May 2026

- **v3.5.0** — **Agentic Commerce** release type: AI-powered ecommerce storefront delivery. Uses Lovable for rapid base storefront generation (React 18 + Vite + Tailwind + Shopify Storefront API), GitHub bidirectional sync, and Supabase as the backend. Nine feature commands: `storefront`, `semantic_search`, `conversational_assistant`, `virtual_tryon`, `visual_similarity`, `llm_tools`, `personalisation`, `ucp_server`, `demo_orchestration`.

---

## v3.4.x — Discovery SOP, Jira/Linear, Dashboard-First

**Released**: March–May 2026

- **v3.4.9** — Dashboard-First release type: rapid Looker dashboard development from business questions without full upstream dbt build
- **v3.4.3** — Discovery SOP (canonical) release type: structured discovery following the RA Standard Operating Procedure
- **v3.4.0** — Jira and Linear issue tracking integration: one Epic per project, Tasks per artifact, Sub-tasks per lifecycle step; `/wire:utils-linear-create` for Linear project setup

---

## v3.3.x — Document Store Integration

**Released**: January–February 2026

- **v3.3.0** — Confluence and Notion document store integration: all generate commands publish artifacts to the configured store; review commands surface reviewer comments and document edits as review context. Configured at engagement setup via `/wire:new` Step 9.5.

---

## v3.0.0 — Initial Release

**Released**: October 2025

Wire Framework initial release.

- Six-phase delivery lifecycle: Requirements → Design → Development → Testing → Deployment → Enablement
- 12 release types covering the full data platform delivery scope
- Claude Code (Anthropic) and Gemini CLI (Google) runtimes
- Artifact generate/validate/review pattern with execution log and decision audit trail
- Fathom MCP integration for surfacing meeting context during reviews
