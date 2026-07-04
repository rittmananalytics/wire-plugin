---
sidebar_position: 5
title: Troubleshooting
---

# Troubleshooting

## Plugin not loading

**Symptom**: `/wire:new` returns "Command not found" after installation.

**Steps**:
1. Confirm Wire is installed: `/plugin list` — look for `wire@rittman-analytics` in the output
2. If listed, try `/reload-plugins` then retry the command
3. If not listed, reinstall: `/plugin install wire@rittman-analytics`, then `/reload-plugins`
4. If installation fails with a network error, check your internet connection and whether the marketplace endpoint is accessible
5. Check Claude Code version: Wire requires Claude Code 1.5 or later. Run `claude --version` to confirm

---

## Commands run but produce empty or very short artifacts

**Symptom**: `/wire:problem-definition-generate` completes but the output is a few sentences or missing all the required sections.

**Cause**: Wire couldn't find its upstream inputs and fell back to minimal generation.

**Fix**:
1. Check that `CLAUDE.md` exists at the repository root and contains project context (client name, source systems, scope)
2. Check that `.wire/releases/<release-folder>/config.yaml` exists and has a populated `project_name` field
3. For later-phase artifacts, check that the prerequisite artifacts are present and in Approved state — run `/wire:status` to see the full picture
4. If inputs exist but Wire still misses them, add their paths explicitly to the prompt: `/wire:problem-definition-generate <release> --context path/to/additional-context.md`

---

## dbt validation failures

**Symptom**: `/wire:dbt-models-validate` reports failures but the SQL looks correct.

**Steps**:
1. Run `dbt compile --select <model-name>` manually to confirm the exact error
2. Common causes:
   - **Source not defined**: the staging model references `{{ source('system', 'table') }}` but `sources.yml` doesn't declare it — add the source definition
   - **Ref before model exists**: a model references `{{ ref('upstream_model') }}` but that model failed compilation earlier in the run — fix the upstream model first
   - **Environment variable missing**: a `var()` call references a project variable that isn't set in your `dbt_project.yml` for the current target
   - **BigQuery permission error**: the service account running dbt doesn't have access to the source dataset — check IAM permissions
3. Run `dbt debug` to check connectivity and profile configuration

---

## Fathom MCP not surfacing meeting context

**Symptom**: Review commands say "No meeting context found" even though relevant calls happened recently.

**Steps**:
1. Confirm the Fathom MCP server is configured in `.claude/settings.json` and the server URL is correct
2. Confirm the Fathom API token in the environment has `meetings:read` scope
3. Check that the call was recorded in Fathom (not all calls are auto-recorded — confirm in the Fathom dashboard)
4. Fathom transcripts take 15–30 minutes to process after a call ends — retry if the call just finished
5. Try a direct Fathom search: in Claude Code, ask "search Fathom for meetings with [client name] in the last 30 days" to test the MCP connection

---

## Jira or Linear sync failures

**Symptom**: Commands complete successfully but Jira/Linear issues aren't updating.

**Steps**:
1. Check the execution log (`/wire:status`) for sync error messages — Wire logs MCP sync failures but doesn't block commands on them
2. Run `/wire:status` to trigger a full reconciliation — this retries any failed syncs
3. Confirm the MCP server for Jira/Linear is reachable: run a test query like "list my Jira projects" in Claude Code
4. Check that the Jira project key in `.wire/releases/<release>/config.yaml` matches an actual project you have write access to
5. For Linear: confirm the API key has `issues:write` scope

---

## Execution log corruption

**Symptom**: Wire reports a parsing error when reading the execution log, or `/wire:status` shows unexpected state.

**Steps**:
1. The execution log is at `.wire/releases/<release>/execution_log.md` — open it and look for malformed entries (truncated lines, unexpected characters)
2. The log is append-only — each entry is separated by `---` and has a timestamp header. Corrupt entries can usually be identified by missing headers or incomplete JSON blocks
3. Remove or fix the corrupt entries, then run `/wire:status` to rebuild the in-memory state from the corrected log
4. If the log is completely unreadable, delete it. Wire will regenerate a minimal log from the artifact files that exist on disk — you'll lose historical timestamps and decision notes, but the current state can be reconstructed

---

## Getting help

If you can't resolve an issue with the steps above:
- Check for open issues: `https://github.com/rittmananalytics/wire-plugin/issues`
- File a new issue with the output of `/wire:status` and the error message from the execution log
- For urgent client-impacting issues, contact Rittman Analytics support directly
