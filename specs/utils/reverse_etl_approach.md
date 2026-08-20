---
description: The closed reverse-ETL migration-approach vocabulary — the four values reverse-etl-audit assigns, what each means, and how every downstream command must treat them
---

# Utils — Reverse ETL Approach Vocabulary

A shared data contract, not a command. Written by `reverse-etl-audit-generate` into `audit/reverse_etl_audit.csv`'s `migration_approach` column; read by `reverse-etl-migration-generate`, `reverse-etl-twin-generate`, `reverse-etl-retire-generate`, and `migration-register-generate`.

## Why this is a contract and not a paragraph in the audit spec

Because the vocabulary drifted, silently, in shipped code. v3.11.6's `reverse-etl-twin-generate` and `reverse-etl-retire-generate` both keyed on `retire`, a value the audit never writes. On a release with 98 `decommission` syncs, the twin command would have authored 98 twins for syncs that are being switched off, and the retirement command would have listed none of them. No error either way: a consumer looking for a token the producer never emits sees an empty match and carries on.

The general lesson is the same one `specs/utils/wave_resolution.md` records for wave ids: when two commands must agree on a token, the token needs one normative home and a producer-side check, not two prose restatements that happen to agree on the day they are written.

## The four values (closed set)

`migration_approach` is one of exactly these. There is no default and no fifth value; an unrecognised value is a hard error at both ends. In particular **there is no `retire` value**: retirement is an action taken on a `decommission`-classified sync, not an approach the audit assigns. Two v3.11.6 commands assumed otherwise, which is why that sentence is here rather than left implicit.

| Value | Meaning | Twinned? | Retired? |
|---|---|---|---|
| `repoint` | Model SQL is portable. The sync re-points to the target-warehouse source with no SQL change | Yes | Only once its twin is proven |
| `rewrite_model` | Model SQL uses source-platform dialect and is translated before re-pointing | Yes | Only once its twin is proven |
| `rebuild` | A Customer Studio audience or Journey. Rebuilt against the target source through the API, not copied as a file | **No** — declined, routed to the runbook's rebuild steps | Not applicable |
| `decommission` | Disabled or unused. Excluded from the migration entirely | **No** — nothing to migrate | **Yes** — this is the classified-retirement ground |

## How each consumer must treat them

| Command | `repoint` / `rewrite_model` | `rebuild` | `decommission` |
|---|---|---|---|
| `reverse-etl-migration-generate` | Plan the translation | Plan the rebuild (schema, audiences, journeys) | Exclude from scope; count under `decommission_count` |
| `reverse-etl-twin-generate` | Author the twin | Decline: `not_authored_reason: rebuild_approach` | Skip: `state: skipped`, reason `decommission_approach` |
| `reverse-etl-retire-generate` | List only when superseded by a proven twin | Not listed | List on the **classified** ground, no replacement evidence required |
| `migration-register-generate` | Seed a `reverse_etl_sync` row | Seed a row | Seed a row, so the retirement is tracked rather than forgotten |

**`decommission` is a retirement ground, not an exclusion from the retirement runbook.** This is the distinction the drift destroyed. A `decommission` sync is out of scope for *migration* and squarely in scope for *retirement*: it is the case where no replacement is expected, so no replacement evidence is owed, and it retires first because nothing is learned by waiting.

## Producer-side check

`reverse-etl-audit-validate` fails when any row's `migration_approach` is outside this closed set, listing the offending sync ids and the values found. A vocabulary a consumer trusts has to be enforced where it is written; enforcing it only in the consumers means every consumer discovers the drift independently, which is how this became four commands' worth of the same bug.

## Consumer-side rule

A command reading `migration_approach` handles all four values explicitly and treats anything else as an error naming the value and the sync. It must not fall through to a default branch: the failure this contract exists to prevent was a silent no-match, and a default branch is a silent no-match with extra steps.

Tests mirror the routing table (`wire/tests/platform_migration/validate_reverse_etl_approach.py`).
