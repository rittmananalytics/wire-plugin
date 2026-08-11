---
description: Internal utility — resolves the dbt project(s), parses a manifest via `dbt parse`, and builds the model/macro dependency graphs consumed by the dbt audit generate and validate commands
---

# dbt Manifest Parse Utility

A shared utility run by the dbt audit **generate** and **validate** commands. It resolves the dbt project(s) at `migration.dbt_project_path`, parses each to a manifest with `dbt parse` (no warehouse connection needed), and builds the model dependency graph, macro dependency graph, and per-model transitive macro-usage set that the calling spec consumes.

This utility replaces the text-scan / `ref_count` heuristics that produced the CAR-362 defects: a stale catalogue silently substituted for an unresolvable project path, ~563 forward-reference batch violations from a depth-then-pack ordering, an undercounted macro layer, and — the fourth in the same family — a manifest resolved under one default var-set silently collapsing a var-driven `enabled` model to permanently disabled. It reads the manifest as ground truth for dependency edges, treats `enabled` as tri-state rather than boolean so a conditional model is never confused with a statically disabled one, and hard-fails rather than substituting anything when the project cannot be resolved.

## Inputs (provided by the calling spec)

- `dbt_project_path` — from `migration.dbt_project_path` in the release's `status.md` (default: `./dbt`)
- `release_folder` — the release folder under `.wire/releases/`

## Procedure

### Step 1: Resolve dbt project(s)

Check `<dbt_project_path>/dbt_project.yml` exists.

- **Exists** — the path is a single dbt project. Record it.
- **Does not exist** — look exactly one level down: list the subdirectories of `<dbt_project_path>` and check each for its own `dbt_project.yml`. Every subdirectory that has one is a distinct **nested project** (e.g. `./dbt/warehouse` itself has no `dbt_project.yml`, but `source_layer/` and `business_layer/` one level down each do). Record all of them.
- **Neither the path itself nor any one-level-down subdirectory yields a `dbt_project.yml`** — **hard-fail**. Print every path checked and stop:

  ```
  🚫 No dbt project found. Paths checked:
    - <dbt_project_path>/dbt_project.yml
    - <dbt_project_path>/<subdir>/dbt_project.yml  (one line per subdirectory)
  Confirm migration.dbt_project_path in status.md and re-run.
  ```

  This utility must **never** substitute a prior artifact, another release's catalogue, or any cached file as a stand-in for a project it could not resolve — that silent substitution is the exact defect this utility exists to fix.

For each resolved project, read its `dbt_project.yml` and record the path plus the `name:` value. The `name:` is the manifest's `package_name` — it is needed for the node filter in Step 3.

### Step 2: Parse each project to a manifest without touching the working tree

For each resolved project:

1. Create a scratch directory **outside the client repo** (e.g. under the system temp directory), one subdirectory per project.
2. Run `dbt deps` then `dbt parse` from the project directory, with both the package install path and the target path redirected to the scratch directory:

   ```
   dbt deps  --project-dir <project_path> --packages-install-path <scratch>/dbt_packages
   dbt parse --project-dir <project_path> --packages-install-path <scratch>/dbt_packages --target-path <scratch>/target
   ```

   Never write to the project's own `target/` or `dbt_packages/`. A naive `dbt deps` in the client repo can pull a package like Elementary into the working tree and inflate the model count by hundreds — the scratch redirect prevents both the pollution and the inflation. `dbt parse` needs no warehouse connection.
3. Read `<scratch>/target/manifest.json`.
4. Delete the scratch directory after all steps below have consumed the manifest. Nothing from this utility may appear in `git status` for the client project.

**Fallback** — if `dbt` is unavailable, or `dbt parse` fails for a reason other than missing deps: build the graphs by text scan instead. Scan each project's `models/**/*.sql` and `macros/**/*.sql` for `ref(...)`, `source(...)`, and macro-call patterns (same fallback shape as `specs/migration/dbt_migration/generate.md` Step 1a). Mark **every count and ordering derived this way as medium confidence** in the audit output, and state explicitly in the audit's Notes that a text-scan fallback was used instead of a manifest.

### Step 3: Filter manifest nodes to project-native models, and classify `enabled`

For each project's manifest:

- From `nodes`, keep only entries with `resource_type == "model"` **and** `package_name` equal to that project's own package name (from Step 1). This drops models belonging to installed packages — dbt_utils, elementary, codegen, etc.
- From the manifest's `disabled` section, collect model nodes with the same package-name filter.

A node's presence in `nodes` vs `disabled` reflects the manifest resolved under whichever `var()` defaults were in effect for **this parse** — it is a snapshot under one var-set, not ground truth for whether a model is legitimately out of scope. A model whose `enabled` config depends on a `var()` that happened to default false lands in `disabled` exactly like a model that is statically, permanently disabled — the manifest alone cannot tell them apart. Classify every model's `enabled` as one of three states, using the source scan in Step 3b (not just manifest presence):

- **`true`** — statically enabled (no `var()` anywhere in the resolution path). Present in `nodes`.
- **`false`** — statically disabled: the resolution path has no `var()` call, and it evaluates false. Present in `disabled`.
- **`conditional:<var_name>`** — the `enabled` config resolves via a `var()` call, regardless of what it evaluates to under this parse's defaults. **Classify a var-driven model as conditional even when it currently resolves to enabled** — a model that defaults on but could be switched off by a flag needs the same visibility as one that defaults off but could be switched on. A `conditional:*` model is **in scope** for the catalogue and for batching — it is never dropped, and never collapsed to `true` or `false`.

Node IDs are already project-qualified (`model.<package_name>.<model_name>`). Use the **full node ID** as the join key wherever model names could collide across nested projects — never the bare model name. A multi-project estate migration surfaced dozens of duplicate name-pairs across two nested projects; a bare-name key silently merges them.

### Step 3b: Detect var-driven `enabled` from source

The manifest resolves `enabled` under one default var-set — it cannot distinguish "statically false" from "false only because a flag defaulted off." Detect the `var()` dependency from source instead, on two surfaces, for every model found in either `nodes` or `disabled`:

**(a) In-model config.** Scan each model's `.sql` `{{ config(...) }}` block (or `.py` `dbt.config(...)` call) for an `enabled` argument whose right-hand side contains `var(`. Match on the presence of `var(` inside the `enabled` expression — do not pattern-match a specific coercion form, it will miss variants. Both of these must be caught by the same check:

  - `enabled = var('run_weekly_models', false)` (bare boolean form)
  - `enabled = (var('enable_elementary', false) | lower == 'true')` (string-coerced form)

  Extract the var name — the first argument to `var(` — for the `conditional:<var_name>` tag.

**(b) Folder-level `+enabled` in `dbt_project.yml`.** Scan the `models:` config tree in each resolved project's `dbt_project.yml` for a `+enabled` key whose value contains `var(` (typically `+enabled: "{{ var('x', false) }}"`). This gates every model under that path prefix — including an entire vendored package (e.g. an `elementary: +enabled: ...` block switches the whole Elementary package on or off in one place). Attribute the conditional to every project-native model under the gated prefix; package-internal models under the same gate are out of scope regardless and don't get a row.

**Precedence.** dbt resolves most-specific-wins: model-level config overrides folder-level config overrides the project default. A model with its own static `enabled` (no `var()`) overrides a folder-level conditional above it; a model with its own var-driven `enabled` overrides a folder-level static config. Resolve model-level before folder-level — never let a folder-level conditional override a model that explicitly hardcodes its own `enabled`.

**Completeness.** After the scan, the set of `conditional:*` models should be exactly the project-native models gated by a `var()` — confirm no in-scope model gated by the same var(s) was missed. Package-internal models gated by the same var (e.g. Elementary's own models, switched by the same flag as the folder-level gate) are expected to fall outside this set — they're out of scope on their own terms, not because of the conditional.

### Step 4: Build the model dependency graph

For every model classified `true` or `conditional:*` in Step 3, take `depends_on.nodes` and keep only edges pointing to other `model.*` nodes in the buildable (`true` or `conditional:*`) set. Drop edges to `seed.*`, `source.*`, and `snapshot.*` nodes.

**Conditional models have no resolved `depends_on.nodes` in this parse** — a `conditional:*` model sits in `disabled` under default vars, so the manifest never computed its edges. Resolve them one of two ways, in order of preference:

1. **Flags-on re-parse (preferred).** For each distinct conditional var found in Step 3b, re-run `dbt parse` once more with that var forced true (`--vars '{<var_name>: true}'`), read the resulting manifest's `nodes` for just the models gated by that var, and take their real `depends_on.nodes`. This is one extra parse per distinct conditional var — not per model, not per combination of vars — so it stays cheap even with several conditional flags in play.
2. **Dependency-rule fallback**, when re-parsing isn't available (no dbt install, no vendored `dbt_packages/`, no reachable warehouse for auth): scan the conditional model's own SQL for `ref()`/`source()` calls (the same text-scan approach as the Step 2 fallback). Place it one batch after the highest batch number among its **in-scope** dependencies; if none of its dependencies are in scope (e.g. its only `ref()` is an out-of-scope package-internal node), place it in batch 1. This is exact for a single-parent leaf node and an approximation otherwise — record in the calling spec's output which mode was used.

The result is the real parent-edge graph, covering both unconditional and conditional buildable models. It feeds the topological sort in `dbt_audit/generate.md` and the batch-ordering check in `dbt_audit/validate.md`.

### Step 5: Build the macro-usage and macro-dependency graphs

- For every model node, regardless of `enabled` classification (`true`, `false`, or `conditional:*`), `depends_on.macros` gives the macros it calls directly. A model's macro calls are static in its SQL body and don't depend on which vars were in effect for this parse, so the default parse's data is sufficient here even for `conditional:*` models — no re-parse needed for this step.
- For every macro node in `manifest.macros`, its own `depends_on.macros` gives macro-to-macro calls.
- Compute, per model, the **transitive closure**: direct macro calls plus everything reachable from them via macro→macro edges. This closure is what "direct or transitive" macro usage means in the calling specs.

**Caveat (carry into any output built from this graph):** this only sees Jinja macro calls. A schema-qualified SQL function call written directly in model SQL — e.g. `schema.fn_x(...)`, backing a UDF defined via `CREATE FUNCTION` DDL inside a macro — is invisible to `depends_on.macros` and to a macro-name text scan. Any per-macro model-reach count built from this graph for such macros is a **floor, not exact**.

## Output

This utility returns to the calling spec, in memory:

- The resolved project list (path + package name per project)
- The per-model `enabled` classification (`true` / `false` / `conditional:<var_name>`)
- The merged model dependency graph (full node IDs, `true` and `conditional:*` models only), including conditional models' edges resolved per Step 4's flags-on-reparse-or-dependency-rule handling, and which mode was used per conditional model
- The macro dependency graph (macro→macro edges)
- The per-model transitive macro-usage set

It writes nothing to disk itself. The calling spec decides what to persist.
