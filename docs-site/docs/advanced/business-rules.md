---
sidebar_position: 13
title: Business rules discovery
---

# Business rules discovery

Anyone who has delivered a reporting platform will recognise the moment when a number on the new dashboard fails to match the number on the old one, and the investigation that follows turns up not a bug but two reasonable definitions of the same metric, neither of which anyone had written down. Before this phase existed Wire had no step that established what a metric means before the build started, and the two commands that came closest did not fill the gap: `requirements-generate` reads documents, and `workshops-generate` runs *after* requirements and only resolves the clarification markers already written into them, so that neither looked at the data and neither looked at the competing definitions sitting in the legacy systems.

It follows, therefore, that a definition disagreement had nowhere to surface, and the first place it could appear was a number that did not tie in QA. Business rules discovery is the optional first phase that gives such a disagreement somewhere to surface before the build, and in this page we will look at the case it was built for, how you run it, what a rule and its four statuses hold, how it reads systems Wire cannot read directly, and how the agreed rules reach into the build and are reconciled against the legacy source. Let's start though with the engagement that made the case for it.

## The case it exists for

A requirements document asked for "Gross Sales Order Online" and a channel breakdown including the in-store order channel, and it listed "standardised metric definitions" as a success factor, which sounds like exactly the clarity a build team would want. What it never said was whether in-store orders were inside the figure, or whether returns were deducted.

Eleven months later the number did not match the legacy dashboard. Nobody had been wrong, and nobody had been asked, which is the whole point: the disagreement was not a mistake anyone made but a decision nobody had been given the chance to take.

## Running it

```bash
/wire:business-rules-generate <release-folder> [--domain <name>] [--import <path>]
/wire:business-rules-validate <release-folder>
/wire:business-rules-review   <release-folder>
```

Business rules discovery is available as an optional first phase on `full_platform`, `dbt_development`, `dashboard_first`, `dashboard_extension`, `pipeline_only` and `platform_migration`.

**One domain per run.** You will be tempted to cover the whole business in a single register, and we would advise against it, because a register that tries to cover everything at once goes stale before it is agreed. Instead, run the command once for each domain: `domains_covered` in `status.md` accumulates, and a later run appends to the register rather than replacing it.

`agentic_data_stack` does not get the phase, because that release type already has `ads_metric-audit` plus `ads_governance-design`, which between them split the job of finding conflicts from the job of deciding them.

## What a rule holds

So what does a rule in the register look like? Each one carries the fields below, and the two that matter most are the `id`, which the build cites and which is therefore never renumbered, and the `disagreement`, which has to say what the variants differ on rather than simply noting that they do.

| Field | Rule |
|---|---|
| `id` | `BR-n`, stable for the life of the register. Never renumbered, because the build cites it |
| `statement` | The rule in plain words, readable by whoever approves it |
| `variants[]` | Every competing definition, each with its `source` and `object`. A variant with no `object` does not enter the register |
| `disagreement` | What they actually differ on. Not "definitions vary" |
| `decision`, `approver`, `agreed_date` | The choice and who made it |
| `implemented_by[]` | The dbt models and LookML measures carrying this rule's id |
| `check` | The query that proves it |

## The four statuses

A rule is in one of four statuses at any time, and each status carries its own consequence when `business-rules-validate` runs:

| Status | Meaning | Validate |
|---|---|---|
| `agreed` | Decided, with a named approver and a date | Needs an implementation once the release reaches development |
| `disputed` | Two or more variants, none chosen | Blocks review sign-off unless it has a named owner |
| `assumed` | Chosen without confirmation | Needs a confirmer and a `confirm_by` date, and **fails once that date passes** |
| `unknown` | Nobody has decided, no variant is authoritative | Never a failure on its own |

That `unknown` passes is the whole point of the design. A command that only records what it found cannot record the absence of a decision, and that absence is exactly what the register exists to hold. It is also why the last attempt at this, a wiki page called Business Logic, sat empty: there was nowhere on it to write "we do not know".

## Reading systems Wire cannot read

Where do the competing definitions come from? dbt, LookML and `schema.yml` are text in a repository, so Wire reads them directly, but SAP BW, Hana SQL, SAC and Looker Studio are not, and pretending otherwise is how a register ends up covering only the easy systems. For these you use the import flag:

```bash
--import <path>
```

which takes exported SQL or model text. Each definition it yields records `source`, `object`, `expression` **verbatim**, `export_date` and `exported_by`, and an imported definition is a first-class variant in every respect but one: it does not carry freshness, so validate warns when an import is more than 90 days older than the register that cites it.

Where an export is illegible, the definition is recorded as `unknown` with the evidence attached and the person to ask, rather than being guessed at, because an invented expression is worse than a blank: everything downstream treats it as fact.

## The gate is advisory, not blocking

How does the register make itself felt in the rest of the release? Each of the six release types gains an advisory gate on its first design-phase artifact: `conceptual_model` for `full_platform`, `data_model` for `dbt_development`, `mockups` for `dashboard_extension`, and so on.

Advisory means that the command warns, asks you for a one-line reason, records an `advisory_skip` in `status.md` and the execution log, and then proceeds.

That is deliberate. A hard gate on a team that already skips gates produces a bypass rather than a register, and what matters is that a skip is *visible*: an omitted gate and an overlooked one look identical afterwards, whereas a logged skip does not.

## Reaching into the build

Once a rule is agreed, the dbt model or LookML measure that implements it cites the rule by its id:

```yaml
models:
  - name: wh_commerce__sales_xa
    meta:
      wire_business_rule: BR-1
```

`business-rules-validate` then checks in both directions: every `agreed` rule has an implementation once the release is building, and every citation names a rule that exists. A citation to a missing id usually means a rule was renumbered, which the register forbids, so the same check catches the renumbering as well as the missing implementation.

`wire/scripts/lint_conventions.py` checks the citation format, at warning severity and only where a citation is present, so that a project which has not opted in is never flagged.

## Reconciliation, before the build rather than after

Finally, what settles a dispute? Every rule with a legacy variant gets a generated query comparing both readings against the legacy source, through the existing equivalency machinery, and it runs at generate time rather than at the end of the build.

A disputed gross sales rule therefore produces, on day one, the number each reading gives and which one matches the legacy dashboard. That is usually enough to settle the dispute without a meeting, and it is the same check QA would otherwise have run eleven months later.
