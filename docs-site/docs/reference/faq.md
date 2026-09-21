---
sidebar_position: 4
title: FAQ
---

# Frequently Asked Questions

The questions below are the ones that come up most often, grouped by topic, and where a fuller answer lives elsewhere on this site the answer points you to it.

## Installation and setup

**Q: Do I need both Claude Code and the Wire plugin, or just one?**

Both. Wire is a plugin that runs inside Claude Code, so you need Claude Code installed first and then install the Wire plugin on top of it. Claude Code without Wire is a general-purpose AI coding assistant, and Wire without Claude Code does not run at all.

**Q: Can I use Wire with Gemini CLI instead of Claude Code?**

Yes. Wire has a separate Gemini CLI extension, which you install with `gemini extensions install <repo-url>`, and all `/wire:*` commands work identically on both runtimes. Some integrations (Fathom MCP, Atlassian MCP) require MCP server configuration, which differs slightly between the two runtimes, so see the runtime-specific installation notes for those. Note, however, that directing the work rather than typing commands is Claude Code only; see the question on Gemini CLI further down this page.

**Q: How do I upgrade Wire to a new version?**

```
/plugin update wire@rittman-analytics
/reload-plugins
```

You do not need to restart Claude Code, as the `/reload-plugins` command is sufficient.

**Q: Why does `/reload-plugins` work but Wire commands still fail?**

Run `/plugin list` first and confirm that `wire@rittman-analytics` is showing as installed and active. If it is installed but commands still fail, run `/plugin reinstall wire@rittman-analytics` and then `/reload-plugins` again; the [Troubleshooting](./troubleshooting) page has the fuller sequence.

---

## Engagements and releases

**Q: What's the difference between an engagement and a release?**

An engagement is the top-level client project, and a release is a unit of delivery within it. Most engagements have one release, but large ones can have several, for example a requirements release followed by three delivery releases in parallel, and each release maps to its own folder under `.wire/releases/`.

**Q: Can I run multiple releases for the same client simultaneously?**

Yes. Each release has its own folder and its own execution log, and since Wire commands take the release folder as an argument they always operate on a specific release. Run `/wire:status` with no arguments to see all the active releases at once.

**Q: How do I restart a release from scratch?**

Archive the existing release (`/wire:archive <release-folder>`) and create a new one with `/wire:new`. Do not delete the old folder, as the execution log and approved artifacts may be useful reference later.

---

## Directing the work (v4.0.0)

**Q: Do I still have to know which command to run?**

No, not on Claude Code. Say what you want done ("run what's next", "approve it and carry on", "start an engagement from this SOW") and Wire works out which command that is from the release-type definition, runs it, names it in the closing line of its report and stops where a decision is yours. See [The Release Director Model](../advanced/release-director).

**Q: Does it tell me what it is going to run before it runs it?**

Yes. Every reply that starts work ends with a `Running:` line naming the command in full. When a directive would run two or more commands before the next decision, or anything that queries a warehouse, Wire first sets the run out as a plan (one row per command, with what it may touch and where the run stops) and waits for you to say go, adjust or cancel. A single command with no warehouse query gets the `Running:` line only. `/wire:work` and `/wire:delegate` do the same at their own entry points.

**Q: Is it doing something different from what my typed command would do?**

No. It runs the same command file, so the precondition gate, auto-validate, `status.md`, the execution log, the artifacts on disk and telemetry are all identical whichever way the command was started. The only difference is the `Session` column in the log and the `invoked_by` telemetry property, which say what invoked the run.

**Q: Will it approve things on my behalf?**

Never. A review edge is never treated as runnable, and at every review gate Wire asks you for one of three answers: approve now, request changes or park for client sign-off. Parked decisions are listed in `status.md` and are the first line of every session until you answer them. (`/wire:autopilot` is the exception, and it is a separate, explicitly-invoked command that answers its own review gates.)

**Q: How do I turn it off?**

There are three ways, depending on how far you want it turned off. Say **"you drive"** and it stops dispatching for the rest of the session. Set `orchestration.mode: manual` in `.wire/engagement/context.md` to restore pre-4.0 behaviour for a whole engagement, including `/wire:start` printing the next action rather than offering to run it. Or simply type commands: typing one always works, and Wire picks up from the resulting state.

**Q: Two of us are working the same engagement. What happens?**

Different releases on different branches is the normal case, and nothing changes. On the *same* release, the second session reads the release claim in `status.md` and offers to join as a reviewer, to take over (only if the holder has not written for 30 minutes) or to move to another release, and it will not dispatch work into a release someone else is driving. A person typing a single command gets a warning naming the holder, not a refusal.

**Q: Does this work in Gemini CLI?**

No. Gemini CLI has no skills or agents, so it stays command-driven and resolves to manual mode regardless of any setting. Gemini users still get the active-release resolution, the log columns and the profile question, however, since those arrive through the command changes themselves.

---

## Commands and artifacts

**Q: What happens if I run a generate command twice on the same artifact?**

Wire checks the execution log first. If the artifact already exists and is in Approved state, Wire asks for confirmation before overwriting it, and if it is in any other state (Generated, Validation failures, Awaiting review) Wire re-generates without prompting, using the same inputs plus any feedback recorded in the log.

**Q: Can I edit a generated artifact manually?**

Yes, but be aware that the next generate run will overwrite your edits unless you record them as design decisions in the execution log first. The safe habit, therefore, is to record manual edits as decisions (or to request a review with the changes incorporated as feedback) so that the generate command knows to preserve them.

:::note
Manual edits that are not recorded as decisions in the execution log are overwritten by the next generate run. Record them first.
:::

**Q: The validate command says PASS but the actual dbt run fails. Why?**

The validate command runs `dbt compile` (not `dbt run`) for structural validation, together with `dbt test` for test validation, so it follows that a model can compile cleanly and still fail at run time. If `dbt compile` passes but `dbt run` fails in production, the issue is typically an environment difference: a missing BigQuery permission, a source table that does not exist in the target environment or a variable that is defined in dev but not in prod. Check your `profiles.yml` and `dbt_project.yml` target settings.

**Q: Can I skip the validate step?**

You can, but the review command will flag that validation was skipped and ask you to confirm that you want to proceed to review without it, and the skip itself is recorded in the execution log.

---

## Integrations

**Q: Fathom isn't finding transcripts from recent meetings. Why?**

Fathom MCP has a short ingestion delay, and transcripts typically appear 15–30 minutes after a call ends, so if the call happened within the last hour, wait and retry. If it still does not appear, check that the Fathom MCP server URL in `.claude/settings.json` is correct and that your Fathom API token has the required read scopes.

**Q: Wire is creating Jira issues in the wrong project. How do I fix it?**

The Jira project key is set during `/wire:new`, and to change it after setup you edit `.wire/releases/<release-folder>/config.yaml` and update `jira_project_key`. Then run `/wire:status` to reconcile; Wire will detect the mismatch and offer to move the issues to the correct project.

**Q: Can I use Wire without any MCP integrations?**

Yes. All MCP integrations are optional, and Wire will skip Fathom context, Jira/Linear syncing and document store replication if the corresponding servers are not configured. The core functionality (artifact generation, validation and review) works entirely from local files, and the [MCP Servers](./mcp-servers) page describes what each integration adds when you do configure it.

---

## Common errors

**Q: I'm getting "No project context found" when running Wire commands.**

Wire reads the project context from `CLAUDE.md` at the repository root and from `.wire/releases/<release-folder>/config.yaml`, so this message means that one of those is missing or out of reach. Check that:
1. A `CLAUDE.md` exists at the project root with the client and project details
2. The release folder exists and contains a `config.yaml`
3. You are running the command from within the git repository (not from a subdirectory that does not contain the root `CLAUDE.md`)

**Q: Wire generates incomplete artifacts, with some sections missing.**

This usually means that Wire could not find the upstream inputs the spec requires. Check the spec file for the artifact (`wire/specs/<type>/<artifact>.md`) to see what inputs it reads, and verify that those files exist and are in Approved state. Running the preceding artifact's review command to completion before generating the next artifact prevents most of these.

**Q: Validation is marking everything as FAIL even though the output looks correct.**

Run the validate command with `--verbose` to see the individual check results. The most common cause is a structural check failing, for example because the artifact document is missing a required section heading that the validate spec expects to find, so check the exact section titles in the generated artifact against the spec.
