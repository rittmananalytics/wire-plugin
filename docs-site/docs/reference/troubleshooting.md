---
sidebar_position: 5
title: Troubleshooting
---

# Troubleshooting

When something goes wrong with Wire it is usually one of a small number of things: the plugin has not loaded, a command cannot find its inputs, dbt will not compile, an integration is not answering or the execution log has been damaged. This page takes each of those in turn, giving the symptom you will see and the steps to work through, and it ends with where to go if none of them helps.

## Plugin not loading

**Symptom**: `/wire:new` returns "Command not found" after installation.

The steps below run from the most likely cause to the least, so work through them in order.

**Steps**:
1. Confirm Wire is installed with `/plugin list`, looking for `wire@rittman-analytics` in the output
2. If it is listed, run `/reload-plugins` and then retry the command
3. If it is not listed, reinstall it with `/plugin install wire@rittman-analytics`, then run `/reload-plugins`
4. If installation fails with a network error, check your internet connection and whether the marketplace endpoint is accessible
5. Check your Claude Code version, as Wire requires Claude Code 1.5 or later; run `claude --version` to confirm

---

## Commands run but produce empty or very short artifacts

**Symptom**: `/wire:problem-definition-generate` completes but the output is a few sentences or missing all the required sections.

**Cause**: Wire could not find its upstream inputs and fell back to minimal generation.

Since the cause is missing inputs, the fix is to establish which input is missing, starting with the two files every command reads and working forward to the artifacts that this one depends on.

**Fix**:
1. Check that `CLAUDE.md` exists at the repository root and contains project context (client name, source systems, scope)
2. Check that `.wire/releases/<release-folder>/config.yaml` exists and has a populated `project_name` field
3. For later-phase artifacts, check that the prerequisite artifacts are present and in Approved state; run `/wire:status` to see the full picture
4. If the inputs exist but Wire still misses them, add their paths explicitly to the prompt: `/wire:problem-definition-generate <release> --context path/to/additional-context.md`

---

## dbt validation failures

**Symptom**: `/wire:dbt-validate` reports failures but the SQL looks correct.

When the SQL itself looks right, the cause is usually one of the four listed below, all of which are about what dbt can find rather than what you wrote, and so the first step is to get the exact error from dbt itself.

**Steps**:
1. Run `dbt compile --select <model-name>` manually to confirm the exact error
2. Common causes:
   - **Source not defined**: the staging model references `{{ source('system', 'table') }}` but `sources.yml` does not declare it; add the source definition
   - **Ref before model exists**: a model references `{{ ref('upstream_model') }}` but that model failed compilation earlier in the run; fix the upstream model first
   - **Environment variable missing**: a `var()` call references a project variable that is not set in your `dbt_project.yml` for the current target
   - **BigQuery permission error**: the service account running dbt does not have access to the source dataset; check IAM permissions
3. Run `dbt debug` to check connectivity and profile configuration

---

## Fathom MCP not surfacing meeting context

**Symptom**: Review commands say "No meeting context found" even though relevant calls happened recently.

There are two kinds of reason here, the connection itself and the calls Fathom holds, and the steps cover both.

**Steps**:
1. Confirm the Fathom MCP server is configured in `.claude/settings.json` and the server URL is correct
2. Confirm the Fathom API token in the environment has `meetings:read` scope
3. Check that the call was recorded in Fathom (not all calls are auto-recorded, so confirm in the Fathom dashboard)
4. Fathom transcripts take 15–30 minutes to process after a call ends, so retry if the call has just finished
5. Try a direct Fathom search: in Claude Code, ask "search Fathom for meetings with [client name] in the last 30 days" to test the MCP connection

---

## Jira or Linear sync failures

**Symptom**: Commands complete successfully but Jira/Linear issues are not updating.

A sync failure never stops a command, as the first step notes, which is helpful in the moment but means the board can fall behind without an obvious error, so the log is the place to look first.

**Steps**:
1. Check the execution log (`/wire:status`) for sync error messages; Wire logs MCP sync failures but does not block commands on them
2. Run `/wire:status` to trigger a full reconciliation, which retries any failed syncs
3. Confirm the MCP server for Jira/Linear is reachable: run a test query like "list my Jira projects" in Claude Code
4. Check that the Jira project key in `.wire/releases/<release>/config.yaml` matches an actual project you have write access to
5. For Linear: confirm the API key has `issues:write` scope

---

## Execution log corruption

**Symptom**: Wire reports a parsing error when reading the execution log, or `/wire:status` shows unexpected state.

The log is a plain text file, so you can open it and repair it by hand, and that is the route to try before anything more drastic.

**Steps**:
1. The execution log is at `.wire/releases/<release>/execution_log.md`; open it and look for malformed entries (truncated lines, unexpected characters)
2. The log is append-only, and each entry is separated by `---` and has a timestamp header, so corrupt entries can usually be identified by missing headers or incomplete JSON blocks
3. Remove or fix the corrupt entries, then run `/wire:status` to rebuild the in-memory state from the corrected log
4. If the log is completely unreadable, delete it. Wire will regenerate a minimal log from the artifact files that exist on disk; you will lose historical timestamps and decision notes, but the current state can be reconstructed

:::note
Deleting the execution log loses every historical timestamp and decision note, and Wire can rebuild only the current state from the artifacts on disk. Repair the corrupt entries first if you can.
:::

---

## Getting help

If the steps above have not resolved the issue, there are three places to go next:
- Check for open issues: `https://github.com/rittmananalytics/wire-plugin/issues`
- File a new issue with the output of `/wire:status` and the error message from the execution log
- For urgent client-impacting issues, contact Rittman Analytics support directly
