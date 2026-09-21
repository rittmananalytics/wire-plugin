---
sidebar_position: 3
title: Installation and Setup
---

# Installation and Setup

Before Wire can set up an engagement it needs two things from you: a git repository to hold the record of the work and one of the two AI coding agents it runs inside. Everything else that Wire needs travels with the plugin or extension itself, since each command carries its own full workflow specification, so there are no framework files to copy into the repository and nothing to keep in step by hand. In this page we will look first at what needs to be in place before you start, then at the two steps of installing and verifying, and finally at how upgrades reach you once you are up and running.

## Prerequisites

So what do you need before you start? The list is short, and the one choice you have to make is which AI coding agent you will use, since Wire runs on either Claude Code or Gemini CLI but you only need one of them. The cloud platform items vary with the stack the project uses, and the two groupings below cover the common cases.

**Required:**
- Git repository initialised (`git init` or cloned)
- **One of** the following AI coding agents:
  - **Claude Code**, installed and authenticated (`claude` CLI). Requires a Claude Pro, Max, Team or Enterprise subscription.
  - **Gemini CLI**, installed and authenticated (`gemini` CLI). Requires a Gemini Code Assist subscription or a Google Cloud project with Gemini API access.
- Python 3.8+ (for dbt and pipeline development)

**Recommended:**
- GitHub Desktop (for non-technical team members)
- dbt Cloud account (or dbt Core installed locally)

**Cloud platform access** (varies by project stack):
- Google Cloud: BigQuery access, Looker access, dbt Cloud connected to BigQuery, GCP service account credentials
- Other platforms: Snowflake/Databricks/Redshift credentials, BI platform access, dbt Cloud or dbt Core configured

At a high level, the two steps that follow are:

1. Install the plugin (Claude Code) or the extension (Gemini CLI).
2. Verify the install by opening your AI coding agent in the repository and running the start command.

Let's now take a look at these steps in more detail.

## Step 1: Install the plugin or extension

Which of the two you install depends on the AI coding agent you chose above, and in both cases the whole set of commands arrives with it.

**Claude Code users:**

In any Claude Code session, register the marketplace, install the plugin and then activate it:

```
/plugin marketplace add rittmananalytics/wire-plugin
/plugin install wire@rittman-analytics
/reload-plugins
```

When prompted for scope, select **"Install for you (user scope)"** so that Wire is available across all of your repositories.

The `/reload-plugins` step picks up the install in the current session, so there is no need to restart Claude Code, and all commands are then available as `/wire:*`.

**Gemini CLI users:**
```bash
gemini extensions install https://github.com/rittmananalytics/wire-extension
```

All commands are available immediately as `/dp *`, with no further setup required.

In either case, each command has its full workflow specification embedded inline, which is why no framework files need to exist in the repository.

## Step 2: Verify

Now that the plugin or extension is installed, how do you know that it is working? Open your AI coding agent in the repository root:

```bash
claude     # Claude Code
gemini     # Gemini CLI
```

Then run `/wire:start` (Claude Code) or `/dp start` (Gemini CLI) to confirm that everything works. On first run, `/wire:start` checks whether the plugin is installed and up to date, detects whether this is a new or an existing engagement and either walks you through onboarding or surfaces the right next action for the current project state, so the same command serves both as your check that the install worked and as the way into your first engagement.

## Upgrading

Plugin and extension users get updates automatically when a new version is published, so there is nothing to reinstall. Project data in `.wire/` is never touched by an upgrade: workflow specs are defensively compatible with existing project state.
