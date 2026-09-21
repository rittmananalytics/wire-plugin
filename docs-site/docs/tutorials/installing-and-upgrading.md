---
sidebar_position: 15
title: "Tutorial: Installing and Upgrading"
---

# Tutorial: Installing and Upgrading

## What this tutorial covers

Before Wire can help with an engagement it has to be installed, activated and kept at a version you trust, and whether you are setting up a new machine or joining a team that already uses Wire, that mechanical work stands between you and your first release. This tutorial walks through installing Wire in Claude Code and Gemini CLI, configuring the MCP servers that extend what Wire can do, verifying that the installation works correctly and keeping the plugin current across engagements, which together cover all the mechanics you need before running your first `/wire:new`.

## Installing Wire in Claude Code

Installation takes three commands, and each must complete before you run the next. At a high level, the three steps are:

1. Register the Rittman Analytics marketplace with Claude Code.
2. Install the `wire` plugin from it.
3. Activate the plugin in your current session.

Let's now take a look at each of these in turn.

**Step 1: Register the marketplace**

```
/plugin marketplace add rittmananalytics/wire-plugin
-> Marketplace source added: rittmananalytics/wire-plugin
-> Registry updated. 1 new source available.
```

**Step 2: Install the plugin**

```
/plugin install wire@rittman-analytics
-> Downloading wire plugin from rittmananalytics/wire-plugin...
-> Installing... done.
-> Commands registered:
     /wire:new                       /wire:start
     /wire:status                    /wire:decisions
     /wire:requirements-generate     /wire:requirements-validate
     /wire:requirements-review       /wire:conceptual_model-generate
     /wire:conceptual_model-validate /wire:conceptual_model-review
     /wire:pipeline_design-generate  /wire:pipeline_design-validate
     /wire:pipeline_design-review    /wire:data_model-generate
     /wire:data_model-validate       /wire:data_model-review
     /wire:mockups-generate          /wire:mockups-review
     /wire:pipeline-generate         /wire:pipeline-validate
     /wire:pipeline-review           /wire:dbt-generate
     /wire:dbt-validate              /wire:dbt-review
     /wire:semantic_layer-generate   /wire:semantic_layer-validate
     /wire:semantic_layer-review     /wire:orchestration-generate
     /wire:orchestration-validate    /wire:orchestration-review
     /wire:dashboards-generate       /wire:dashboards-validate
     /wire:dashboards-review         /wire:data_quality-generate
     /wire:data_quality-validate     /wire:data_quality-review
     /wire:uat-generate              /wire:uat-review
     /wire:deployment-generate       /wire:deployment-validate
     /wire:deployment-review         /wire:training-generate
     /wire:training-validate         /wire:training-review
     /wire:documentation-generate    /wire:documentation-validate
     /wire:documentation-review      /wire:delegate
     /wire:autopilot                 /wire:playbook-generate
     /wire:session-plan              /wire:session-end
     /wire:upgrade                   /wire:archive
     ... (66 /wire:* commands total)
-> Installation complete. Run /reload-plugins to activate in this session.
```

**Step 3: Activate in the current session**

```
/reload-plugins
-> Plugins reloaded.
-> wire plugin active — 265 commands available as /wire:*
-> No Claude Code restart required.
```

When prompted during install for scope, select "Install for you (user scope)", which makes Wire available across every repository on the machine rather than just the current one.

## Verifying the installation

So how do you know it worked? Run `/wire:start` to confirm Wire is active, and on first run in a repository with no existing engagement you should see the following:

```
/wire:start
-> Wire Framework v3.9.4 — active.

   No engagement detected in this repository.

   Wire guides a full data platform engagement from requirements
   through to deployment and enablement. To begin:

     /wire:new

   Available release types:
     full_platform        — end-to-end: pipeline, dbt, semantic layer, dashboards
     dbt_development      — transformation layer only (data already in warehouse)
     dbt_migration        — migrate dbt models between warehouses or patterns
     dashboard_first      — start from dashboard mockups, derive the data model
     droughty             — schema-driven warehouse introspection and LookML generation

   Run /wire:new to create a release and set the engagement type.
```

This output confirms that the plugin loaded correctly and that Wire can see the repository. If `/wire:start` is not recognised as a command, the `/reload-plugins` step did not complete, so run it again.

## Installing for Gemini CLI

If your team works in Gemini CLI rather than Claude Code, Wire is also available as a Gemini CLI extension:

```bash
gemini extensions install https://github.com/rittmananalytics/wire-extension
```

The Gemini CLI uses a different command syntax, however. Where Claude Code uses `/wire:requirements-generate my_project`, Gemini CLI uses `wire requirements generate my_project`, a space-separated form with no slash prefix. All 265 commands are available under both runtimes, and the workflow specs are shared between them and produce identical artifacts.

## Configuring MCP servers

Wire works without MCP servers from the moment you install it, and all generate, validate and review commands function with local context alone. Why configure them, then? MCP servers extend what Wire can do automatically, and the gains are material, as we will see for each of the three below.

The three most useful servers are Fathom, Atlassian and Linear. Add them to `.claude/settings.json` in the project root:

```json
{
  "mcpServers": {
    "fathom": {
      "type": "sse",
      "url": "https://mcp.fathom.video/sse",
      "headers": {
        "Authorization": "Bearer YOUR_FATHOM_API_KEY"
      }
    },
    "atlassian": {
      "type": "sse",
      "url": "https://mcp.atlassian.com/v1/mcp"
    },
    "linear": {
      "type": "sse",
      "url": "https://mcp.linear.app/sse"
    }
  }
}
```

**Fathom** Every review command (`/wire:requirements-review`, `/wire:data_model-review` and so on) automatically searches Fathom transcripts for calls during the engagement period, surfacing relevant decisions, concerns and action items before you gather stakeholder feedback. As such, a requirements review that would otherwise miss a client caveat from the kick-off call will find it automatically if the call was recorded in Fathom.

**Atlassian** This server enables one-click Jira hierarchy creation when you run `/wire:new`: Wire creates one Epic for the engagement and Tasks for each artifact, with Sub-tasks for the generate, validate and review steps, and every subsequent command syncs its status back to Jira. `/wire:status` performs a full reconciliation across the Jira hierarchy and the local `status.md`.

**Linear** This is the same as Atlassian but mapped to Linear Projects and Issues. Use either Atlassian or Linear depending on which tracker your team uses, and both can run in parallel if your client uses one and your team uses the other. If neither is configured, Wire tracks everything locally in `status.md` and `decisions.md`.

All three servers are optional, and Wire carries on without them when they are absent, noting in command output that context from that source was unavailable.

## Upgrading to a new version

```
/plugin update wire
-> Checking for updates to wire@rittman-analytics...
-> Update available: v3.9.4 -> v3.9.5
-> Downloading... done.
-> Updated wire to v3.9.5.
-> Run /reload-plugins to activate the new version in this session.
```

Run `/reload-plugins` after any update; no Claude Code restart is needed. To check what version is currently installed and active:

```
/wire:utils-version
-> Wire Framework
-> Installed version:  v3.9.5
-> Active in session:  v3.9.5
-> Plugin source:      rittmananalytics/wire-plugin
```

:::note
If the installed version and the active version differ, `/reload-plugins` was not run after the last update. Run it before continuing.
:::

## Pinning a version

For an active engagement, consider pinning the Wire version to avoid mid-engagement behaviour changes, because a generate command that behaves slightly differently in a new release can produce an artifact that is inconsistent with earlier approved artifacts in the same project. Pin by specifying the version explicitly in the install command:

```
/plugin install wire@rittman-analytics==3.9.4
```

Wire will not auto-update while pinned, and you unpin by running `/plugin install wire@rittman-analytics` without a version specifier.

Pinning is a version control mechanism, in that it controls which plugin code runs, and it is distinct from `/wire:upgrade`, which is a schema migration command that updates the `status.md` file inside an existing release folder to match the current plugin's schema. Pinning first, then selectively upgrading when you are ready to adopt new schema fields, gives you full control over when a dormant engagement inherits new Wire features.
