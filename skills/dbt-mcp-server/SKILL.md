---
name: dbt-mcp-server
description: Proactive skill for setting up and configuring the dbt MCP server for use with Claude Code and Claude Desktop. Auto-activates when a user asks about connecting Claude to dbt, setting up dbt MCP, or accessing dbt Semantic Layer or Discovery API from Claude. Covers local vs remote server modes, credential handling, and Wire project setup.
---

# dbt MCP Server Skill

## Purpose

The dbt MCP server connects Claude Code (and Claude Desktop) to dbt's CLI, Semantic Layer, Discovery API, and Admin API. Once configured, other dbt skills (`dbt-analytics-qa`, `dbt-semantic-layer`, `dbt-dag`) can use MCP tools like `list_metrics`, `get_lineage`, `get_mart_models`, and `dbt_build` directly rather than falling back to manifest parsing.

This skill guides users through choosing the right server type, generating the correct configuration, and verifying the connection.

## When This Skill Activates

### User-Triggered Activation

- "How do I connect Claude to my dbt project?"
- "Set up the dbt MCP server"
- "I want Claude to be able to run dbt commands"
- "How do I use the dbt Semantic Layer with Claude?"
- "Configure dbt MCP for Claude Code"

**Keywords**: "dbt MCP", "dbt-mcp", "dbt MCP server", "dbt semantic layer MCP", "dbt Discovery API", "dbt tools", "uvx dbt-mcp"

### Self-Triggered Activation

Activate when:
- Another dbt skill falls back to manifest parsing because MCP tools are unavailable
- The user asks why Claude can't see their dbt metrics or model lineage
- `.mcp.json` or `~/.claude.json` are being edited in a Wire project

---

## Step 1: Choose server type

Ask: "Do you want to use the **local** or **remote** dbt MCP server?"

| | Local server | Remote server |
|---|---|---|
| How it runs | On your machine via `uvx dbt-mcp` | HTTP endpoint at dbt Cloud |
| dbt CLI access | Yes (`dbt run`, `build`, `test`, `show`) | No |
| Semantic Layer | Yes (if dbt Cloud connected) | Yes |
| Discovery API | Yes (if dbt Cloud connected) | Yes |
| Requires dbt Cloud | No (CLI-only mode works without it) | Yes |
| Credits consumed | No | Yes (dbt Copilot credits) |
| **Best for** | Wire project development work | Consumption/analytics Q&A only |

**Recommendation for Wire projects**: Use **local server**. It gives Claude access to dbt CLI commands during development and connects to dbt Cloud for Semantic Layer / Discovery when needed.

---

## Step 2: Choose what to enable

Defaults are sensible for Wire projects:

| Category | Default | Disable with |
|---|---|---|
| dbt CLI (`run`, `build`, `test`, `compile`) | **Enabled** | `DISABLE_DBT_CLI=true` |
| Semantic Layer (metrics, dimensions) | **Enabled** | `DISABLE_SEMANTIC_LAYER=true` |
| Discovery API (models, lineage) | **Enabled** | `DISABLE_DISCOVERY=true` |
| Admin API (jobs, runs) | **Enabled** | `DISABLE_ADMIN_API=true` |
| SQL (`text_to_sql`, `execute_sql`) | Disabled | `DISABLE_SQL=false` to enable |
| Codegen (generate models/sources) | Disabled | `DISABLE_DBT_CODEGEN=false` to enable |

---

## Step 3: Prerequisites

Before generating the configuration, gather:

1. **`DBT_PROJECT_DIR`**: Absolute path to the folder containing `dbt_project.yml`
   ```bash
   # From inside your dbt project:
   pwd
   ```

2. **`DBT_PATH`**: Path to the dbt executable
   ```bash
   which dbt        # dbt Core in venv
   which dbtf       # dbt Fusion
   ```

3. **dbt Cloud credentials** (only needed for Semantic Layer, Discovery, Admin API):
   - `DBT_HOST`: your dbt Cloud host (e.g. `https://your-account.us1.dbt.com` or `cloud.getdbt.com`)
   - `DBT_TOKEN`: personal access token (Settings → API Access in dbt Cloud)
   - `DBT_ACCOUNT_ID`: from your dbt Cloud URL (`cloud.getdbt.com/accounts/XXXXX`)
   - `DBT_PROD_ENV_ID`: from Orchestration → Environments in dbt Cloud

---

## Configuration Templates

### Local server — CLI only (no dbt Cloud)

```json
{
  "mcpServers": {
    "dbt": {
      "command": "uvx",
      "args": ["dbt-mcp"],
      "env": {
        "DBT_PROJECT_DIR": "/path/to/your/dbt/project",
        "DBT_PATH": "/path/to/dbt"
      }
    }
  }
}
```

### Local server — CLI + dbt Cloud (token auth)

```json
{
  "mcpServers": {
    "dbt": {
      "command": "uvx",
      "args": ["dbt-mcp"],
      "env": {
        "DBT_HOST": "cloud.getdbt.com",
        "DBT_TOKEN": "${DBT_TOKEN}",
        "DBT_ACCOUNT_ID": "${DBT_ACCOUNT_ID}",
        "DBT_PROD_ENV_ID": "${DBT_PROD_ENV_ID}",
        "DBT_PROJECT_DIR": "/path/to/project",
        "DBT_PATH": "/path/to/dbt"
      }
    }
  }
}
```

### Local server — using a `.env` file (recommended for teams)

```json
{
  "mcpServers": {
    "dbt": {
      "command": "uvx",
      "args": ["--env-file", "/path/to/.env", "dbt-mcp"]
    }
  }
}
```

`.env` file:
```
DBT_HOST=cloud.getdbt.com
DBT_TOKEN=<set-via-env-or-secret-manager>
DBT_ACCOUNT_ID=<your-account-id>
DBT_PROD_ENV_ID=<your-prod-env-id>
DBT_PROJECT_DIR=/path/to/project
DBT_PATH=/path/to/dbt
```

Add `.env` to `.gitignore` — never commit literal tokens.

### Remote server (dbt Cloud only, no CLI)

```json
{
  "mcpServers": {
    "dbt": {
      "url": "https://cloud.getdbt.com/api/ai/v1/mcp/",
      "headers": {
        "Authorization": "Token ${DBT_TOKEN}",
        "x-dbt-prod-environment-id": "${DBT_PROD_ENV_ID}"
      }
    }
  }
}
```

---

## Where to put the configuration

### Claude Code (primary Wire tool)

**Option A — Project-specific** (recommended for Wire projects, shareable with team):
Add to `.mcp.json` at the repo root. Wire Studio already creates `.mcp.json` with Atlassian, Fathom, and Context7 servers — **merge** the dbt entry rather than replacing:

```json
{
  "mcpServers": {
    "atlassian": { ... },
    "fathom": { ... },
    "context7": { ... },
    "dbt": {
      "command": "uvx",
      "args": ["dbt-mcp"],
      "env": {
        "DBT_PROJECT_DIR": "/path/to/project",
        "DBT_PATH": "/path/to/dbt"
      }
    }
  }
}
```

If using token auth, use `${DBT_TOKEN}` references (not literal values) so `.mcp.json` is safe to commit.

**Option B — User-global** (your machine only):
```bash
claude mcp add dbt -s user -- uvx dbt-mcp
```

**Option C — Project-scoped via CLI**:
```bash
claude mcp add dbt -s project -- uvx dbt-mcp
```

### Claude Desktop

1. Open **Claude menu** (system menu bar, not in-app) → **Settings** → **Developer** → **Edit Config**
2. Add the JSON configuration
3. Save and restart Claude Desktop
4. Verify: look for the MCP server indicator in the input box bottom-right

Config location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Credential security

- **Always use env var references** (`${DBT_TOKEN}`) in config files that may be committed
- **Never log or display token values** in terminal output
- **Use `.env` files with `.gitignore`** for local development; use Secret Manager or env var injection in CI/CD
- **Minimum required permissions**: read-only for Discovery/Semantic Layer; write permissions only if Admin API or dbt CLI job triggering is needed

---

## Verification

Test the local server before configuring a client:
```bash
export DBT_PROJECT_DIR=/path/to/project
export DBT_PATH=/path/to/dbt
uvx dbt-mcp
# No errors = server starts successfully; Ctrl+C to stop
```

After setting up in Claude Code, ask Claude:
- "What dbt tools do you have access to?"
- "List my dbt models" (tests Discovery API)
- "List my dbt metrics" (tests Semantic Layer — requires dbt Cloud connection)

---

## Wire Project Notes

- Wire projects default to BigQuery. Set `DBT_PROJECT_DIR` to the repo root (where `dbt_project.yml` lives, typically the repo root for Wire projects)
- Wire's `.mcp.json` already exists — always **add** the dbt server entry rather than creating a new file
- If using Wire's Dagster orchestration, the dbt MCP server and Dagster skill complement each other: dbt MCP for model development, Dagster skill for orchestration setup
- For projects using dbt Cloud jobs (orchestration tool = `dbt_cloud`), the remote server gives Claude visibility into job status via the Admin API
