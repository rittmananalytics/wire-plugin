---
sidebar_position: 4
title: FAQ
---

# Frequently Asked Questions

## Installation and setup

**Q: Do I need both Claude Code and the Wire plugin, or just one?**

Wire is a plugin that runs inside Claude Code. You need Claude Code installed first, then install the Wire plugin on top. Claude Code without Wire is a general-purpose AI coding assistant. Wire without Claude Code doesn't run.

**Q: Can I use Wire with Gemini CLI instead of Claude Code?**

Yes. Wire has a separate Gemini CLI extension. Install it with `gemini extensions install <repo-url>`. All `/wire:*` commands work identically on both runtimes. Some integrations (Fathom MCP, Atlassian MCP) require MCP server configuration, which differs slightly between the two runtimes — see the runtime-specific installation notes.

**Q: How do I upgrade Wire to a new version?**

```
/plugin update wire@rittman-analytics
/reload-plugins
```

You do not need to restart Claude Code. The `/reload-plugins` command is sufficient.

**Q: Why does `/reload-plugins` work but Wire commands still fail?**

Run `/plugin list` and confirm `wire@rittman-analytics` is showing as installed and active. If it's installed but commands still fail, run `/plugin reinstall wire@rittman-analytics` and then `/reload-plugins` again.

---

## Engagements and releases

**Q: What's the difference between an engagement and a release?**

An engagement is the top-level client project. A release is a unit of delivery within that engagement. Most engagements have one release, but large ones can have several — for example, a requirements release followed by three delivery releases in parallel. Releases map to folders under `.wire/releases/`.

**Q: Can I run multiple releases for the same client simultaneously?**

Yes. Each release has its own folder and its own execution log. Wire commands require the release folder as an argument, so they always operate on a specific release. Run `/wire:status` with no arguments to see all active releases.

**Q: How do I restart a release from scratch?**

Archive the existing release (`/wire:archive <release-folder>`) and create a new one with `/wire:new`. Do not delete the old folder — the execution log and approved artifacts may be useful reference.

---

## Commands and artifacts

**Q: What happens if I run a generate command twice on the same artifact?**

Wire checks the execution log. If the artifact already exists and is in Approved state, Wire asks for confirmation before overwriting it. If it's in any other state (Generated, Validation failures, Awaiting review), Wire re-generates without prompting, using the same inputs plus any feedback recorded in the log.

**Q: Can I edit a generated artifact manually?**

Yes, but be aware that the next generate run will overwrite your edits unless you record them as design decisions in the execution log first. Best practice: record manual edits as decisions (or request a review with the changes incorporated as feedback) so the generate command knows to preserve them.

**Q: The validate command says PASS but the actual dbt run fails. Why?**

The validate command runs `dbt compile` (not `dbt run`) for structural validation, and `dbt test` for test validation. If `dbt compile` passes but `dbt run` fails in production, the issue is typically an environment difference — a missing BigQuery permission, a source table that doesn't exist in the target environment, or a variable that's defined in dev but not prod. Check your `profiles.yml` and `dbt_project.yml` target settings.

**Q: Can I skip the validate step?**

You can, but the review command will flag that validation was skipped and ask you to confirm you want to proceed to review without it. Skipping validate is recorded in the execution log.

---

## Integrations

**Q: Fathom isn't finding transcripts from recent meetings. Why?**

Fathom MCP has a short ingestion delay — transcripts typically appear 15–30 minutes after a call ends. If a call happened within the last hour, wait and retry. If it still doesn't appear, check that the Fathom MCP server URL in `.claude/settings.json` is correct and that your Fathom API token has the required read scopes.

**Q: Wire is creating Jira issues in the wrong project. How do I fix it?**

The Jira project key is set during `/wire:new`. To change it after setup, edit `.wire/releases/<release-folder>/config.yaml` and update `jira_project_key`. Run `/wire:status` to reconcile — Wire will detect the mismatch and offer to move the issues to the correct project.

**Q: Can I use Wire without any MCP integrations?**

Yes. All MCP integrations are optional. Wire will skip Fathom context, Jira/Linear syncing, and document store replication if the corresponding servers aren't configured. Core functionality — artifact generation, validation, and review — works entirely from local files.

---

## Common errors

**Q: I'm getting "No project context found" when running Wire commands.**

Wire reads the project context from `CLAUDE.md` at the repository root and from `.wire/releases/<release-folder>/config.yaml`. Check that:
1. A `CLAUDE.md` exists at the project root with the client and project details
2. The release folder exists and contains a `config.yaml`
3. You're running the command from within the git repository (not a subdirectory that doesn't contain the root `CLAUDE.md`)

**Q: Wire generates incomplete artifacts — some sections are missing.**

This usually means Wire couldn't find the upstream inputs the spec requires. Check the spec file for the artifact (`wire/specs/<type>/<artifact>.md`) to see what inputs it reads, and verify those files exist and are in Approved state. Running the preceding artifact's review command to completion before generating the next artifact prevents most of these.

**Q: Validation is marking everything as FAIL even though the output looks correct.**

Run the validate command with `--verbose` to see the individual check results. The most common cause is a structural check failing — for example, the artifact document is missing a required section heading that the validate spec expects to find. Check the exact section titles in the generated artifact against the spec.
