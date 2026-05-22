# GEMINI.md

Project instructions for Gemini CLI when working with the Wire Framework.

## Tool Mapping

When workflow specifications reference Claude Code tool names, use these Gemini equivalents:

| Spec References | Your Tool |
|----------------|-----------|
| `Read` | `read_file` |
| `Write` | `write_file` |
| `Edit` | `replace` |
| `Glob` | `glob` |
| `Grep` | `search_file_content` |
| `Bash` | `run_shell_command` |
| `WebFetch` | `web_fetch` |
| `WebSearch` | `google_web_search` |

## User Interaction

When specs reference `AskUserQuestion` with structured options, present the options as a numbered list and ask the user to select by number or description. Example:

Instead of a JSON schema, ask:
"What type of data platform project is this?
1. Full platform — Complete implementation
2. Pipeline only — Data pipeline development
3. dbt development — dbt models and semantic layer
4. Dashboard extension — New dashboards on existing platform
5. Enablement — Training and documentation"

## Framework Paths

- Framework specs: See `.gemini/dp-config.sh` for `DP_FRAMEWORK_PATH`
- Project data: See `.gemini/dp-config.sh` for `DP_PROJECTS_PATH`

## MCP Servers

Optional integrations are configured in `.gemini/settings.json`. Authenticate via `gemini mcp` commands.
