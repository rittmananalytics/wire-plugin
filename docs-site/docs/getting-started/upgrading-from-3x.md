---
sidebar_position: 4
title: Upgrading from Wire 3.x
---

# Upgrading from Wire 3.x

**Applies to**: v4.0.0 and later. If you have engagements running on Wire 3.x, you will want to know three things before you move: what will look different the first time you open one of them under 4.x, whether anything in the repository has to change first and how you would step back to 3.x if you needed to. This page covers what changes when you move from any Wire 3.x version to 4.x, how the upgrade works and how to reverse it.

## What you get

So what does 4.x actually change? The short answer is that it turns the delivery process itself into data. Every release type has a machine-readable definition (`release-types/<type>.yaml`) giving its phases, its artifacts and the dependencies between them, and several mechanisms read that definition, which is where most of what you notice day to day comes from.

| Feature | What you see |
|---|---|
| **Directing rather than typing** | On Claude Code, say what you want done and Wire works out which command that is, names it, runs it and stops where a decision is yours. Every step runs the real command, so the record is identical. Typing commands still works. One setting turns it off per engagement. See [The Release Director Model](../advanced/release-director.md). |
| **Precondition gate** | Every generate, validate and review command checks its prerequisites before doing anything. If a required upstream artifact is not approved, the command blocks and tells you why. |
| **Recorded overrides** | You can proceed past a block, but only by giving your name and a reason. Both are written into `status.md` (`precondition_overrides`) and the execution log. Skipping a step becomes a visible, attributable decision. |
| **Automatic validation** | Generate runs its own validate step when it finishes and folds the PASS or FAIL into its output. Six expensive validates (real dbt builds, live warehouse or BI queries) stay manual, and generate says so plainly when that applies. Review still requires a passing validate either way. |
| **Autopilot rewrite** | Autopilot resolves execution order from the same release-type definition the gate reads, so it can no longer drift from the real process. It runs the real commands, supports self-review (recorded as `Wire Autopilot (self-review)`) and pauses for a human on any gate block. |
| **Fathom call sync** | `new` asks for the client's email domain. Given one, new call transcripts arrive in `.wire/engagement/calls/` automatically at session start, each with a findings write-up. It refuses to enable itself for internal RA engagements. `utils-fathom-sync` covers backfills and Gemini CLI. |
| **Data model registry** (RA staff, optional) | `data_model-generate` can propose a canonical industry data model as a starting baseline. The content lives in a private repo, never bundled in the public plugin; access is by your own GitHub credentials via `utils-data-model-registry-setup`. Without access, everything skips silently. |
| **Execution tracing** (opt-in) | Set `WIRE_TRACE=true` and every command writes a step-by-step local trace to `trace.jsonl` in the release folder. Off by default, never sent anywhere. See [Detailed Execution Tracing](../advanced/tracing.md). |
| **Parked decisions and the release claim** | Decisions waiting on you are a list in `status.md`, reported at the start of every session, replacing the single `paused_at` value. A release records who is driving it, so a second session offers to join as reviewer rather than dispatching into it. |
| **Attribution in the log** | Execution-log rows gain `By` (the git user) and `Session` (`typed`, `orchestrator`, a lane label or `autopilot`). Existing four-column rows stay valid and are never rewritten. |
| **The full 3.11.x line** | 4.x is a superset of the final 3.x release: status-sync, reference legibility, the migration and carve-out features, the Plain Language output style and the rest. |

## What changes in your day-to-day workflow

Several of these mechanisms show up as a change in what you do at the keyboard, and it helps to know them in advance so that an automatic validate or a gate block is expected rather than a surprise. In practice the changes come down to the following.

- **Stop running validate manually.** Generate does it and reports the result. The exceptions name themselves in generate's output.
- **Treat a gate block as information.** A block means a prerequisite is not approved. The normal response is to complete the prerequisite; the exceptional response is an override, with a reason you are content to see in the record.
- **`new` asks one more question** (the client email domain, for call sync).
- **Autopilot runs need a human within reach**, because Autopilot pauses on gate blocks rather than pushing through.
- **You can stop looking up command names.** Say what you want; Wire tells you what it did in plain words and names the command in the last line of each report, so you learn them as you go rather than up front. If you would rather keep typing, nothing stops you.
- **Answer the parked decisions.** The first line of each session is the count of decisions waiting on you. A parked review is not a stalled release, since other work continues around it, but nothing downstream of it moves until you rule.
- **One driver per release.** Two people on one release means one drives and one reviews. Two releases, two branches, two terminals is the shape that works.
- **Process changes go through the registry.** Release-type definitions and command specs are a pinned mirror of the private, branch-protected `wire-process-registry` repo. If the process itself is wrong, that is a registry pull request, not a local edit. See [Process and Data Model Registries](../advanced/registries.md).

## What you can no longer do

Since the same mechanisms now enforce what 3.x only stated in prose, there is also a short list of things you could do in 3.x and can no longer do in 4.x.

| In 3.x | In 4.x |
|---|---|
| Run a command out of sequence and rely on nobody noticing | The gate blocks; proceeding requires a recorded name and reason |
| Ship a generate and forget to validate until review | Validate runs automatically, or generate states explicitly that it is on you |
| Let Autopilot push through a questionable state | Autopilot pauses for a human on any gate block |
| Adjust a spec or the process order in your local plugin copy | Specs and release-type definitions are pinned mirrors of the governed registry |
| Have two sessions dispatch agent work into the same release at once | The release claim stops the second one, and offers join, take-over or move |
| Let a subagent write `status.md` while another is writing it | In orchestrated mode the orchestrating session is the single writer of `status.md` and the execution log |

Nothing about review changes: review always required a passing validate, and no agent approves an artifact on your behalf. As such, 4.x enforces mechanically what 3.x stated in prose.

### Existing engagements

What happens to a release that was already under way? `/wire:upgrade` adds the new `status.md` and `context.md` blocks with defaults (`parked_decisions`, the expanded `agents` block, `orchestration.mode`) and writes the profile field explicitly where a release type has one and the release has been running on the default implicitly. It deliberately does **not** write a `budget` block, because an absent block means no budget was set, and writing one would claim a decision nobody made. Nothing changes for the release until someone gives a directive.

## Do you need the latest 3.x first?

No. The 4.x `upgrade` command carries every schema backfill from the 3.11.x series (the tenant predicate registry backfill, the register linkage columns, the physical `bq_target` re-resolution), so a repo last touched on any 3.x version can move straight to 4.x.

## The upgrade itself

So what does the upgrade involve? Nothing in an engagement repo has to change before 4.x can work on it, because 4.x reads the same `status.md` and artifact files that 3.x writes, and there is therefore no separate upgrade script and no repo-wide migration. The mechanism is one command, run once per release:

```
/wire:upgrade <release-folder>
/wire:upgrade <release-folder> --dry-run
```

It diffs the release's `status.md` against the current template, adds any missing keys, runs the migration backfills where relevant and lists the commands that are new for that release type. Releases you never upgrade still work, since upgrade only adds keys, backfills and awareness of new commands.

The optional follow-ups per engagement are to give the client email domain for call sync (or run `utils-fathom-sync` for a backfill), to run `utils-data-model-registry-setup` if you have access and to set `WIRE_TRACE=true` when you want traces.

## Going back to 3.x

What if you need to go back? The repo side reverses cleanly in every case, because 4.x adds only new information and 3.x ignores what it does not know:

| 4.x leaves behind | Effect under 3.x |
|---|---|
| `precondition_overrides` entries in `status.md` (only if an override happened) | Ignored; remains as history |
| `trace.jsonl` files (only if tracing was on) | Inert local files |
| `fathom_sync` keys in the engagement context | Ignored |
| `reviewed_by: "Wire Autopilot (self-review)"` values | Read like any other reviewer name |

Nothing needs stripping, and every artifact produced under 4.x remains a valid 3.x artifact. The plugin side of a downgrade is covered below.

---

## The plugin side

4.x is the `wire` plugin, versioned 4.0.0, with commands under `/wire:*`, and consultants receive it through the normal marketplace update. Because the plugin auto-updates, consultants will usually be on 4.x before their engagement repos are, and that is fine, since 4.x reads 3.x repos as they stand. Run `upgrade` per release when convenient, migration releases first (they carry the backfills).

**Mixing becomes pinning.** With one namespace, a release is operated by whatever plugin version the workstation runs. It follows, therefore, that keeping an engagement on 3.x means pinning its workstations to the 3.x maintenance line and recording the pin in the engagement context. Move whole engagements rather than single releases, and prefer moving them.

**Downgrading needs a prepared path.** Once `wire-plugin`'s main is 4.x, installing 3.x requires a source to install from: the 3.x maintenance branch and tag cut at the final 3.x publish. A downgrade is then to remove the plugin, re-add the marketplace pinned to that branch and reinstall, with auto-update off for the pinned install. The repo side still needs nothing.

**Rollout checklist (maintainers):**

| # | Action | Why |
|---|---|---|
| 1 | Cut the final 3.x release, then branch and tag `wire-plugin` (`v3-maintenance`, `v3.11.x`) | The only clean downgrade path once main becomes 4.x |
| 2 | Publish an override-etiquette note with the announcement | The gate's value is the record; the record is only useful if reasons are real |
| 3 | Tell consultants the two visible changes up front: validate is automatic, and blocks are expected behaviour | The most common first reaction to a gate is to assume the tool is broken |
| 4 | Run `upgrade --dry-run` across active engagements before announcing | Finds surprises before they find you |
