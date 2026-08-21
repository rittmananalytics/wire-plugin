---
description: The canonical wave-id form and --wave resolution rule — the token migration_batching.csv carries, how every consuming command normalises it, and the producer-side check that keeps the two in step
---

# Utils — Wave Resolution

A shared contract, not a command. `migration-batching-generate` writes the token; `migration-batching-validate` enforces its form; every command with a `--wave` flag resolves against it. That is currently 18 spec files, which is the reason this exists as one normative home rather than 18 restatements.

## The canonical form

`migration_batching.csv`'s `batch_id` column carries **zero-padded, upper-case `B` + digits**: `B01`, `B02`, … `B10`, `B11`. Plus one reserved value, `NO-DEP`, for objects with no model consumer (a holding pen for human triage, not a schedulable wave).

Two further reserved forms exist, minted only by `migration-batching-generate` in `partition_mode: readiness_waves` (wire#199, the tenant carve-out readiness partition):

- **`B00`**: shipped history. Models this release has already delivered (`delivery_stage: merged` or `production_verified`). Not a schedulable wave; preserved across re-runs so history survives re-partitioning.
- **`PEN-<NAME>`**: a named holding pen, same principle as `NO-DEP`. `PEN-` followed by upper-case letters and hyphens, starting and ending with a letter. The two pens readiness mode mints are `PEN-UNRESOLVED` (no established carve mechanism) and `PEN-EXCLUSION-PENDING` (adjudicated `defer`/`split`, pending a rescope). Not schedulable waves.

A `batch_id` of `B00` or `PEN-*` in a `domain` or `build_ordered_waves` CSV is a token-form failure (`migration-batching-validate` Check 2b): only readiness mode mints them.

Nothing else is a valid `batch_id`. `b1`, `1`, `W01`, `wave-1`, `pen-unresolved` (lower-case in the file) are not.

Release types may extend this canonical set. Any extension must state its minting artifact here, extend the normalisation table below in the same change, and update the mirror test.

## Normalisation (what a consumer accepts as input)

A consultant types `--wave` by hand, so the flag is permissive where the file is strict. Normalise the supplied value, then match the normalised result against `batch_id` **case-insensitively and pad-insensitively**:

| Input | Normalises to |
|---|---|
| `2`, `02` | `B02` |
| `b2`, `B2`, `b02`, `B02` | `B02` |
| `w2`, `W2`, `W02` | `B02` (the `W` display form the status tooling shows consultants) |
| `0`, `00`, `b0`, `B00`, `w0` | `B00` (the shipped-history wave; only readiness mode mints it, so on any other release resolution finds no rows and aborts with the standard message) |
| `NO-DEP`, `no-dep` | `NO-DEP` |
| `pen-unresolved`, `PEN-UNRESOLVED` | `PEN-UNRESOLVED` (any well-formed `PEN-<NAME>` normalises to its upper-case form; pens are addressable by `--wave` exactly like `NO-DEP`) |
| `wave-2`, `B 02`, `2a`, `PEN-` (no name), anything else | Reject: `[wire] Unrecognised wave id "<input>". Expected a wave number (2), a padded id (B02), NO-DEP, or a holding-pen id (PEN-UNRESOLVED).` |

Matching is case- and pad-insensitive **on both sides**. A file carrying `b2` still resolves against `--wave B02`, and a file carrying `B02` still resolves against `--wave 2`. This is defence in depth, not permission for the producer to write a non-canonical file: `migration-batching-validate` still fails such a file, and the tolerant match exists so a release already holding one is not bricked mid-flight.

## Resolution (what a consumer does with the normalised id)

1. Load `migration/migration_batching.csv`. Absent: abort with `[wire] No migration_batching.csv found — run /wire:migration-batching-generate $ARGUMENTS first.`
2. Filter to rows whose `batch_id` matches the normalised id per the rule above.
3. **No rows at all** for that id: abort with `[wire] No rows found for wave <id> in migration_batching.csv.`
4. Filter further to the object types **this command** owns (`dbt_model`, `connector`, `reverse_etl_sync`, `metabase_card`, and so on). This step is the only part that legitimately differs per command, and each command states its own filter.
5. Rows matched the wave but **none** are this command's object type: print `[wire] Wave <id> has no <object-type> objects — nothing to <verb> for this command.` and stop **cleanly**. Not an error: a wave that contains connectors but no models is a normal wave, and a command that treats it as a failure teaches people to ignore its output.
6. Cross-reference each matched `object_id` against the relevant audit for the per-object detail, listing rather than silently dropping any `object_id` with no audit row.
7. Print the resolved-object preview before doing any work. Mandatory, in every `--wave` command.

## Why this is a contract

The rule was restated in prose in 18 spec files, and a produced `migration_batching.csv` drifted to `b1..b10` while every consumer expected `B0N` (wire#192). The specs agreed with each other; the artefact did not agree with the specs, and nothing checked the token form. A lane agent hit it, stopped rather than working around it, and the wave was blocked.

Restating a shared token rule per consumer means the drift is discovered once per consumer, at whatever time each is next run. One normative home plus a producer-side check means it is discovered once, at the gate that wrote it.

The duplication was close to unavoidable before v3.11.2: a `specs/utils/` doc did not ship in either package, so a reference would have pointed at a file that was not there. Since #179 item 1 the shared specs ship, and Tier 0's check 8 makes it impossible to reference one without shipping it.

Tests mirror the normalisation table (`wire/tests/platform_migration/validate_wave_resolution.py`).
