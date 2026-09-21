---
sidebar_position: 9
title: The Process and Data Model Registries
---

# The Process and Data Model Registries

**Introduced**: v4.0.0

If you have gone looking for a release type's YAML in this repo in order to change it, or wondered why the data model command sometimes proposes an industry model and sometimes says nothing, the answer in both cases begins in the same place. Wire depends on two different kinds of specialised knowledge to do its job, and as of v4.0.0 both live outside this repo, in their own private GitHub repos.

The first is about *how Wire works*: the exact sequence a release type follows, and what each command actually does. The second is about *what Wire knows*: canonical data models built from RA's collective experience across real client engagements, which a new engagement can optionally draw on for a head start instead of starting from a blank page.

Those two can look alike from the outside, since both are private repos and both get pulled into this repo as a local copy, but they exist for opposite reasons, which is exactly why they are treated so differently once they are here. The process knowledge is Wire's own operating procedure. Nothing about it is secret, but now that it can actually *enforce* a release's process rather than just describe it (see the [precondition gate](../getting-started/core-concepts#the-precondition-gate)), a mistake in it does not just look wrong in a doc, it breaks a real engagement, and so changing it now goes through a proper review, in a repo dedicated to exactly that. The data model knowledge is the opposite case: it is built from real client work, so it is genuinely confidential, and handing it to anyone who installs the public Wire plugin would be a real leak, not a rounding error. As such, it never ships inside the plugin at all, and only RA staff can pull it, only onto their own machine, using their own GitHub access.

The rest of this page covers both in detail, the process registry first and then the data model registry, before finishing with the one thing the two have in common.

## wire-process-registry: how Wire defines itself

Before v4.0.0, release-type sequencing (`full_platform` runs artifacts in this order, `dashboard_extension` in that order) and the command specs themselves lived directly inside this repo's `wire/release-types/` and `wire/specs/` directories, edited in place and built straight into the plugin.

As of v4.0.0, both directories are a **synced, pinned mirror** of the private [`rittmananalytics/wire-process-registry`](https://github.com/rittmananalytics/wire-process-registry) repo, which is the single source of truth for what a release type's phases and dependency graph look like, and for what each command actually does. Editing happens there, via a branch-protected PR (one required approval, admin enforcement on), not directly in this repo. (It is a private repo, accessible to RA staff with GitHub org access, and the link is here for reference even if you cannot open it.)

```mermaid
flowchart TB
    subgraph priv["Private: rittmananalytics/wire-process-registry"]
        RT["release-types/*.yaml<br/>phases, artifacts, depends_on, sequence"]
        SP["specs/**/*.md<br/>what each command does"]
    end

    subgraph wire["This repo (rittmananalytics/wire)"]
        SYNC["wire/scripts/sync-process-registry.sh<br/>rsync mirror, pinned SHA"]
        LOCAL["wire/release-types/*.yaml<br/>wire/specs/**/*.md<br/>(local mirror)"]
        BUILD["wire/scripts/build-packages.sh"]
    end

    subgraph pub["Public: wire-plugin / wire-extension"]
        CMDS["commands/*.md (specs inlined)<br/>release-types/*.yaml (bundled)"]
    end

    RT -->|PR, 1 approval required| RT
    SP -->|PR, 1 approval required| SP
    RT --> SYNC
    SP --> SYNC
    SYNC -->|"wire/process_registry/pinned_sha.txt"| LOCAL
    LOCAL --> BUILD
    BUILD -->|"release-types/ bundled -<br/>Wire's own public operating procedure"| CMDS

    style priv fill:#fce4ec,stroke:#c62828
    style pub fill:#e8f5e9,stroke:#2e7d32
```

### What a release-type definition actually looks like

So what does one of these definitions contain? Here is `pipeline_only.yaml` in full, one of the smaller release types, which makes it a good example, and it is real content from `wire-process-registry`, not illustrative:

```yaml
wire_schema: "1.0"
id: pipeline_only
name: "Pipeline Only"
description: "Data pipeline development only — ingestion architecture, pipeline implementation, and data quality testing, without a dbt/semantic-layer/BI build."
applicable_when:
  - "Client needs a data pipeline built but transformation/BI is out of scope or handled separately"
  - "Scope is limited to getting data reliably into the warehouse"

phases:
  # Optional. Discover, define and agree what the numbers mean before design
  # bakes a definition in. Warning-level: the gate on the artifact below asks and
  # records a skip reason rather than blocking, because a hard gate on a team that
  # skips gates produces a skipped gate.
  - id: business_rules
    name: "Business Rules Discovery"
    description: "Extract and agree the business rules for the domain in scope, from legacy systems and from the people who own the definitions"
    required: false
    requires_phase: null
    artifacts:
      - id: business_rules
        command: business-rules
        required: false
        sequence: 1
        depends_on: []

  - id: requirements
    name: "Requirements"
    description: "Capture and sign off the requirements specification from the SoW and stakeholder input"
    required: true
    requires_phase: null
    artifacts:
      - id: requirements
        command: requirements
        required: true
        sequence: 1
        depends_on: []
      # Optional. Runs when requirements carry [NEEDS CLARIFICATION] markers or a
      # design choice needs a stakeholder decision. It was in 3.11.9's
      # full_platform sequence and fell out of every release type when the
      # sequences became YAML (wire#248), so no release type could produce it.
      - id: workshops
        command: workshops
        required: false
        sequence: 2
        depends_on:
          - artifact: requirements
            action: review
            outcome: approved

  - id: design
    name: "Design"
    description: "Design the pipeline architecture"
    required: true
    requires_phase: requirements
    artifacts:
      - id: pipeline_design
        command: pipeline_design
        required: true
        sequence: 1
        depends_on:
          - artifact: requirements
            action: review
            outcome: approved
          - artifact: business_rules
            action: review
            outcome: approved
            enforcement: advisory

  - id: development
    name: "Development"
    description: "Implement the pipeline"
    required: true
    requires_phase: design
    artifacts:
      - id: pipeline
        command: pipeline
        required: true
        sequence: 1
        depends_on:
          - artifact: pipeline_design
            action: review
            outcome: approved

  - id: testing
    name: "Testing"
    description: "Data quality tests on the pipeline output"
    required: true
    requires_phase: development
    artifacts:
      - id: data_quality
        command: data_quality
        required: true
        sequence: 1
        depends_on:
          - artifact: pipeline
            action: review
            outcome: approved

  - id: deployment
    name: "Deployment"
    description: "Deploy the pipeline to production and sign off"
    required: true
    requires_phase: testing
    artifacts:
      - id: deployment
        command: deployment
        required: true
        sequence: 1
        depends_on:
          - artifact: data_quality
            action: validate
            outcome: PASS
```

Each element has a job, and the table below sets out what each one is for:

| Element | Meaning |
|---|---|
| `wire_schema` | Which version of `release-type-schema.md` this file conforms to, which lets the schema itself evolve without breaking every existing release type at once. |
| `id` | The machine-readable identifier used everywhere else in Wire: `status.md`'s `project_type` field, `/wire:new`'s release-type selector, the precondition gate's and Autopilot's lookup key (`wire/release-types/<id>.yaml`). |
| `name` / `description` | Human-readable label and one-line summary, shown when a consultant is choosing a release type in `/wire:new`. |
| `applicable_when` | Plain-language guidance on when this release type fits. Not machine-enforced, just documentation baked into the same file rather than living separately. |
| `phases[]` | The ordered top-level stages, Requirements → Design → Development → Testing → Deployment here. Coarser-grained than artifacts; mainly organisational. |
| `phases[].requires_phase` | Which phase must fully complete before this one can start: phase-level ordering, one level up from the artifact-level dependencies below. |
| `phases[].artifacts[]` | The actual deliverables produced in that phase. This is the part with real teeth. |
| `artifacts[].id` | The artifact's identifier, matching what appears in `status.md` (e.g. `pipeline_design`, `data_quality`). |
| `artifacts[].command` | Which command family handles this artifact, resolving to `/wire:{command}-generate`, `-validate`, `-review`. |
| `artifacts[].required` | Whether this artifact must be completed for the release type to be considered done. (Some artifacts elsewhere, like `mockups` in `full_platform`, are `false`, meaning optional.) |
| `artifacts[].sequence` | A tie-breaker: when two artifacts in the same phase have no dependency relationship between them, `sequence` decides which runs first. |
| `artifacts[].depends_on[]` | **The actual dependency graph.** Each entry names an upstream `artifact`, the gate (`action`: `generate`/`validate`/`review`) it must have passed, and the required `outcome` (`complete`/`PASS`/`approved`). `pipeline_design` here cannot start until `requirements`' review is `approved`; `deployment` cannot start until `data_quality`'s validate is `PASS`. |

This `depends_on` graph is precisely what the [precondition gate](../getting-started/core-concepts#the-precondition-gate) checks before letting a command run, and what [Autopilot](./autopilot) topologically sorts to decide execution order. Nothing else in Wire needs a separate copy of "what comes after what", because it is all right here.

**Why externalise it at all?** There are two reasons. First, release-type YAML and command specs are the actual mechanism now: the [precondition gate](../getting-started/core-concepts#the-precondition-gate) reads `wire/release-types/<type>.yaml` at runtime to know what an artifact depends on, and [Autopilot](./autopilot) reads the same file to resolve execution order. Getting this wrong is no longer a documentation slip, it is a broken engagement, and a branch-protected repo with mandatory review is a stronger guarantee than "someone remembers to be careful editing YAML in the main repo." Second, it separates *what Wire's process is* from *how Wire is packaged and distributed*, so that the same release-type definition produces identical behaviour whether you are running the framework's own dev copy or an installed plugin three versions behind.

**Never fetched live.** `wire/scripts/sync-process-registry.sh` is the only sync point: it mirrors both directories via `rsync --delete` and records the resolved commit SHA in `wire/process_registry/pinned_sha.txt`. Every build works offline against whatever was last explicitly synced and committed, and there is therefore no risk of a Wire command silently changing behaviour because someone merged a PR in the registry repo five minutes ago, since that merge has zero effect until the next sync.

**Fully public once bundled.** Unlike the data model registry below, there is no confidentiality concern here, because release-type sequencing and command instructions are Wire's own public operating procedure, already visible to anyone reading the plugin's `commands/*.md` files. `build-packages.sh` bundles `wire/release-types/*.yaml` straight into both the Claude Code plugin and the Gemini CLI extension.

See [`wire/schemas/release-type-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/release-type-schema.md) and [`wire/schemas/command-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/command-schema.md) for the exact contract each file follows.

## wire-data-model-registry: what RA has learned, made available to every engagement

When RA builds a data model for a client in a familiar industry (SaaS, retail, insurance, manufacturing, education, subscription commerce), it is rarely the first time RA has solved this kind of problem. There is a good instinct for what a solid `Customer` entity looks like for a SaaS business, what a `Policy` and `Claim` model needs to capture for insurance, and what grain makes sense for subscription revenue. None of that experience has been available to Wire itself, though, and every new engagement started from a blank page, even when the shape of the answer was already well understood.

[`wire-data-model-registry`](https://github.com/rittmananalytics/wire-data-model-registry) is where that experience now lives: a private library, organised by industry, of the entities RA typically expects to see, the kind of structure and grain that has worked well before, and real worked examples of how a similar model was actually built. It is not code to copy and paste but a reference to learn the pattern from. (It is a private repo, accessible to RA staff with GitHub org access.)

**The value to a consultant**: when you start a data model for a client in one of these industries, Wire recognises the fit and offers this as a starting point, which is a genuine head start instead of reasoning up the whole thing from nothing. You can take it, adapt it or ignore it entirely, because it is always a suggestion and never something applied automatically. Nor is this limited to an exact industry match: if nothing in the registry is a confident fit for the client's actual business (there is no dedicated `saas` vertical yet, for instance), Wire will still propose the closest available analogue, explicitly labelled as approximate, and it separately checks for relevant cross-industry patterns (reconciling contacts across a CRM and a marketing tool, revenue recognition, and so on) regardless of whether any industry matched at all. Furthermore, once the model is built, Wire can flag if something standard for that industry looks like it is missing, in the way a colleague glancing over your shoulder might say "don't you normally need something for that in this kind of business?"

Because this comes from real client work, it is genuinely confidential, part of what makes RA's delivery experience valuable and not something to publish for anyone who installs the Wire plugin. As such, it is kept out of the public plugin entirely: it is never bundled in, and instead each RA consultant fetches it themselves onto their own machine.

**Setup is automatic, and you should not need to think about it.** `/wire:new` and Autopilot both attempt this on your behalf, silently, the first time you start an engagement whose release type would actually use it (`full_platform`, `dbt_development`, `dashboard_first`), and at most once per machine. If you have GitHub access to the private repo, it just works from then on; if you do not, nothing happens and nothing changes about how Wire behaves for you. You can also run `/wire:utils-data-model-registry-setup` yourself any time, either to set it up ahead of your first engagement or to `git pull` and refresh it later.

```mermaid
flowchart TB
    START["/wire:new or Autopilot starts an engagement\n(release type that uses data_model)"]
    AUTO["Attempts setup automatically\n(once per machine) - or run\n/wire:utils-data-model-registry-setup yourself, any time"]
    CHECK{"RA staff with<br/>registry access?"}
    YES["Clone succeeds →<br/>saved to your machine"]
    NO["Clone fails -<br/>reported plainly, not an error"]
    GEN["Any future engagement:<br/>data_model-generate runs"]
    PROPOSE["Proposes a matching or closest-adjacent<br/>industry model, and/or cross-vertical<br/>patterns - never auto-applied"]
    SKIP["Skips the proposal -<br/>Wire behaves exactly the same otherwise"]

    START --> AUTO --> CHECK
    CHECK -->|Yes| YES --> GEN --> PROPOSE
    CHECK -->|No| NO --> GEN --> SKIP

    style YES fill:#e8f5e9,stroke:#2e7d32
    style NO fill:#ffebee,stroke:#c62828
    style PROPOSE fill:#e8f5e9,stroke:#2e7d32
    style SKIP fill:#f5f5f5,stroke:#999
```

### Why it isn't just part of the plugin

`wire-plugin` and its extension counterpart are **public** repos, and anyone can install them. Bundling this registry into the plugin the way Wire's own process definitions are bundled (see above) would hand confidential, client-derived content to every installer, RA staff or not, with no way to gate access after the fact. That is a real leak, not an edge case, hence the separate, one-time setup step instead.

If the setup command fails, that is normal, not a bug: it just means you do not have access to the private repo, and Wire continues to work exactly as it does for anyone else without it.

### Walkthrough: what this actually looks like on a real engagement

What does all of this look like in practice? Here is a worked example, start to finish, of a `full_platform` engagement for **Core Dynamics, Inc.**, a B2B SaaS company selling facility/asset management software. It is written to illustrate the harder case, in which we suppose that no vertical currently in the registry is a confident match for this client's exact industry, since that is the case the adjacent-match and cross-vertical behaviour exists for. (Whether that is true for "B2B SaaS" specifically at any given moment depends on what is actually in the registry when you read this, because it grows independently of Wire's own release cycle. The mechanism below is the same either way, and a confident match just skips straight to the easier path.)

For the version of this same client and scenario with a confident vertical match, run start to finish with the actual `/wire:data_model-generate` command and output at each step, see [Tutorial: Using the Data Model Registry](../tutorials/data-model-registry).

**1. Enabled, without anyone asking for it.** The consultant running this engagement is RA staff with GitHub access to `wire-data-model-registry`. Nothing about setting up this engagement mentions the registry: there is no question at `/wire:new` and no flag to remember. The first time a `data_model`-using release (this one, `full_platform`) is reached, Wire quietly attempts the clone in the background, and since this consultant already ran `/wire:utils-data-model-registry-setup` on a previous engagement, `~/.wire/data-model-registry/` is already there and nothing needs to happen at all.

**2. The proposal.** Once `conceptual_model` is approved, the consultant runs `/wire:data_model-generate`. Step 1.5 fires automatically and reads the approved requirements: "B2B SaaS", "MRR", "NRR", a subscription-based revenue model. It lists whichever verticals actually exist in the registry right now (suppose, for this example, none is a confident match for B2B SaaS specifically) but judges `subscription-commerce` a plausible **adjacent** match, because its entities (`subscriber`, `subscription`, `subscription_event`, `monthly_retention`, `subscription_revenue`) are structurally close to what an MRR/NRR model needs, even though that vertical's own content was built from a pet-product box and a meal-kit business, not software. Separately, and regardless of that vertical match, it also notices that the requirements describe a 12% Salesforce/HubSpot contact-mismatch problem from discovery, and flags the cross-vertical `crm_identity_resolution` pattern as relevant. Two proposals appear, not one:

```
No vertical currently in the registry is an exact industry match for B2B SaaS.
The closest available entity shape is subscription-commerce - built from a
pet-product box and a meal-kit subscription business, not software.
Entities: subscriber, subscription, subscription_event, monthly_retention, subscription_revenue

This may still be a reasonable starting point for Core Dynamics' MRR/NRR model.
Worth using loosely, or skip entirely? (yes / adapt / no)
```
```
Also potentially relevant: crm_identity_resolution - built for an agency's own CRM
reconciliation, but the same technique (union multiple CRM sources, resolve identity
by email/domain matching) applies to Core Dynamics' own Salesforce/HubSpot contact
records, which show a 12% mismatch rate per discovery findings.
Worth using loosely, or skip entirely? (yes / adapt / no)
```

Note what did not happen here. Wire did not reject `crm_identity_resolution` just because its own description talks about "an agency's own CRM operations" and Core Dynamics is not an agency. It looked past that framing and asked whether the underlying entities and technique were still the same problem, and since they were, it proposed the pattern anyway, labelled plainly as a reframe rather than an exact fit, which is the same principle behind the adjacent vertical match above, applied to cross-vertical patterns too.

**3. The decision.** The consultant answers each independently:
- `subscription-commerce` → **adapt**: keeps the shape but renames to match Core Dynamics' own terminology (`subscriber` → `account`, `subscription_event` → `billing_event`), drops `monthly_retention` as out of scope for this phase, and keeps `subscription` and `subscription_revenue` as they are.
- `crm_identity_resolution` → **yes**: adopted unmodified, since it maps directly onto the actual reconciliation problem.

Wire records both decisions in `.wire/engagement/context.md`:
```yaml
data_model_registry:
  vertical: subscription-commerce
  cross_vertical_schemas: [crm_identity_resolution]
```

**4. What it contributes to the release.** The accepted entities become the starting structure for the rest of `data_model-generate`: `account_dim`, `subscription_fct`, `billing_event_fct` and `subscription_revenue_fct` get modelled with the registry's suggested grain and columns, adjusted to Core Dynamics' real source systems (Salesforce, HubSpot, Stripe). The accepted cross-vertical pattern contributes something requirements alone would not have produced, a `contact_identity_map` integration model resolving Salesforce/HubSpot contact IDs to one canonical identity, and it is the registry's proposal that put this model on the plan at all.

For each of these, the entity's `generation_constraints` (rules the model must satisfy, e.g. "`subscription_revenue_fct` must reconcile to the sum of `billing_event_fct` amounts for any given period") and `reference_implementation` pointer (a path into the registry's own worked-example dbt code demonstrating the pattern) carry forward into `data_model_specification.md`. `dbt-generate` needs no changes at all to pick this up, because it already reads that file as its primary input, so the constraints and reference pointers are simply there when it runs, available to read and adapt, never to copy verbatim.

**5. What it contributes to validation.** Later, `/wire:data_model-validate` reads `data_model_registry.vertical`/`cross_vertical_schemas` back out of `context.md` and diffs the generated model list against what was proposed, in this case noting that `subscription-commerce`'s canonical schema also usually expects a `churn_event_fct` model that Core Dynamics' actual data model does not have yet. This appears in a clearly labelled, advisory-only "Canonical Vertical Comparison" section of the validation report: worth a look, never a blocker, and never affecting whether `data_model-review` can proceed.

## The one thing they share

Both follow the same "pin, don't fetch live" philosophy for the copies that live inside this repo: a sync script, a pinned commit SHA and an explicit re-run whenever the maintainers want to pull in changes. The difference is entirely about what happens *after* that, since one gets compiled straight into a public package while the other stops at a private mirror and reaches an end user, if at all, through a completely separate, individually gated path.
