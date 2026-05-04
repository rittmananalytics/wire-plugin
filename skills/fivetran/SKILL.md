---
name: fivetran
description: Skill for managing Fivetran data pipelines via the Fivetran MCP Server. Activates when the user wants to list, create, modify, sync, or monitor Fivetran connections, destinations, transformations, webhooks, or groups. Covers all 78 tools exposed by the MCP server.
---

# Fivetran MCP Skill

## When This Skill Activates

Activate when the user asks about:
- Listing, creating, modifying, pausing, or deleting Fivetran connections
- Checking sync status or triggering syncs
- Managing destinations (data warehouses)
- Managing transformation projects or dbt transformations
- Working with groups, users, webhooks, or hybrid deployment agents
- Schema / column / table configuration
- Any phrase containing: "Fivetran", "connector", "sync", "pipeline", "destination", "data warehouse"

---

## Authentication

The Fivetran MCP Server authenticates per-request using two headers:
- `X-Fivetran-API-Key` — your Fivetran API key
- `X-Fivetran-API-Secret` — your Fivetran API secret

Get credentials from: **Fivetran dashboard → Account → Settings → API Config**

When using Claude Code with this MCP server configured, credentials are passed via the MCP client setup — you do not need to include them in tool calls.

---

## Key Concepts

**connection_id**: Fivetran's internal ID for a connector (e.g. `unaffected_school`). Use `list_connections` to find IDs.

**group_id**: The destination group ID. Use `list_groups` to find IDs. Connections are associated with groups.

**service**: The connector type slug (e.g. `salesforce`, `postgres`, `calendly`, `hubspot`). Use `list_metadata_connectors` or `get_metadata_connector_config` to discover the correct service slug and its required config fields.

**Auth vs Config for connectors**: Some connectors (e.g. Calendly, Google Analytics) use an `auth` object with `access_token` for OAuth-based authentication, while others use a `config` object with API keys. Always call `get_metadata_connector_config` first when creating a new connector type to check which fields are required and whether they go in `config` or `auth`.

**Write operations**: Tools marked ⚠️ mutate data. The server has a `FIVETRAN_ALLOW_WRITES` env var — if set to `false`, all write operations are blocked. By default, writes are allowed.

---

## Common Use Cases

### 1. List all connections

```
"Show me all my Fivetran connections"
"List connections grouped by destination"
```

Tool: `list_connections` (no arguments required — auto-paginates)

Follow-up: use `list_connections_in_group` with a `group_id` to filter by destination.

---

### 2. Check connection status

```
"What's the status of my Salesforce connection?"
"Are any connections failing?"
"When did my HubSpot connector last sync?"
```

Tools:
- `list_connections` — scan `status.setup_state` and `succeeded_at` / `failed_at` fields
- `get_connection_details` — for a single connection's full status and config
- `get_connection_state` — for granular sync state

---

### 3. Trigger a sync

```
"Sync my Salesforce connection now"
"Force a full historical re-sync of my Stripe connection"
"Re-sync just the orders table in my Postgres connection"
```

Tools:
- `sync_connection` — immediate incremental sync. Pass `{"force": true}` in `request_body` to force.
- `resync_connection` — full historical re-sync (expensive — use sparingly)
- `resync_tables` — re-sync specific tables only

---

### 4. Pause and resume connections

```
"Pause all my connections during maintenance"
"Resume the postgres_production connection"
```

Tool: `modify_connection` with `request_body: {"paused": true}` or `{"paused": false}`

---

### 5. Create a new connection

```
"Create a new Calendly connection syncing to the ra-development destination"
"Set up a HubSpot connector in the marketing group"
```

Workflow:
1. `get_metadata_connector_config` with the service slug — check which fields go in `config` vs `auth`
2. `list_groups` — find the destination `group_id`
3. `create_connection` with:
   - `service`: connector type slug
   - `schema`: destination schema name (permanent, cannot be changed)
   - `group_id`: destination group ID
   - `config`: service-specific config fields (schema is merged in automatically)
   - `auth` (if required): OAuth tokens (use `modify_connection` after creation to set auth)
4. `run_connection_setup_tests` — verify connectivity after creation

**Note on OAuth connectors** (Calendly, Google Analytics, etc.): Create the connection first with `create_connection`, then call `modify_connection` with `{"auth": {"access_token": "..."}}` to add the token. The setup test will fail until auth is provided.

---

### 6. Modify connection settings

```
"Change Salesforce to sync every hour"
"Update the sync frequency of my Stripe connection to 6 hours"
```

Tool: `modify_connection` with `request_body: {"sync_frequency": 60}` (value in minutes)

Common `sync_frequency` values: 5, 15, 30, 60, 180, 360, 720, 1440

---

### 7. Delete a connection

```
"Delete the old Stripe test connection"
```

Tool: `delete_connection` — **DESTRUCTIVE, cannot be undone**. Always confirm with the user before calling.

---

### 8. Manage schema / table / column sync config

```
"Which tables are being synced from my Postgres connection?"
"Disable the internal_logs table from syncing"
"Hash the email column in the users table"
```

Tools:
- `get_connection_schema_config` — view all schemas, tables, columns and their enabled status
- `modify_connection_table_config` — enable/disable a table
- `modify_connection_column_config` — enable/disable or hash a column (`hashed: true` anonymises values)
- `reload_connection_schema_config` — discover new tables added at source since last reload
- `modify_connection_schema_config` — bulk update multiple schemas/tables at once

---

### 9. List and manage destinations

```
"What destinations do I have?"
"Show me the config for my BigQuery destination"
```

Tools:
- `list_destinations` — all destinations
- `get_destination_details` — single destination config
- `run_destination_setup_tests` — verify destination connectivity

---

### 10. Work with groups

```
"List all my destination groups"
"Who's in the ra-development group?"
"Add user@company.com to the marketing group"
```

Tools:
- `list_groups` — all groups with their IDs
- `get_group_details` — single group
- `list_users_in_group` — users with access to a group
- `add_user_to_group` / `delete_user_from_group` — manage group membership
- `list_connections_in_group` — all connections in a specific destination

---

### 11. Manage dbt transformations

```
"List my transformation projects"
"Run the nightly dbt transformation"
"Cancel the transformation that's been running too long"
```

Tools:
- `list_transformation_projects` — all projects
- `list_transformations` — all transformations
- `get_transformation_details` — single transformation
- `run_transformation` — trigger a run
- `cancel_transformation` — cancel a running transformation
- `upgrade_transformation_package` — upgrade dbt package version

---

### 12. Manage webhooks

```
"List my webhooks"
"Create a webhook for sync completion events"
"Test the webhook at https://my-endpoint.com"
```

Tools:
- `list_webhooks` — all webhooks
- `create_account_webhook` — account-level webhook
- `create_group_webhook` — group-level webhook
- `test_webhook` — send a test event
- `delete_webhook` — remove a webhook

---

### 13. Discover connector types

```
"What connectors does Fivetran support?"
"What config fields does the Calendly connector need?"
"What scopes does the HubSpot connector require?"
```

Tools:
- `list_metadata_connectors` — all connector types with metadata
- `get_metadata_connector_config` — detailed config schema for a specific connector (shows required `config` and `auth` fields)
- `list_public_connectors` — public connector list (no auth required)

---

### 14. Get a connection's dashboard URL

```
"Give me the link to the Salesforce connection in Fivetran"
```

Tool: `get_connection_url` with `connection_id`

---

### 15. Account information

```
"What's my Fivetran account info?"
"What plan am I on?"
```

Tool: `get_account_info` (no arguments)

---

## Full Tool Reference

### Account
| Tool | Type | Description |
|------|------|-------------|
| `get_account_info` | Read | Account info for current credentials |

### Connections
| Tool | Type | Description |
|------|------|-------------|
| `list_connections` | Read | All connections (auto-paginated) |
| `create_connection` | Write | Create a new connection |
| `get_connection_details` | Read | Full details for one connection |
| `modify_connection` | Write | Update connection settings |
| `delete_connection` | Destructive | Permanently delete a connection |
| `get_connection_state` | Read | Detailed sync state |
| `modify_connection_state` | Write | Update sync state |
| `sync_connection` | Write | Trigger immediate sync |
| `resync_connection` | Write | Full historical re-sync |
| `resync_tables` | Write | Re-sync specific tables |
| `run_connection_setup_tests` | Write | Verify connection config |
| `create_connect_card` | Write | Embed Fivetran setup UI token |
| `get_connection_url` | Read | Dashboard URL for a connection |

### Schema / Table / Column Config
| Tool | Type | Description |
|------|------|-------------|
| `get_connection_schema_config` | Read | Which tables/columns are enabled |
| `reload_connection_schema_config` | Write | Discover new tables from source |
| `modify_connection_schema_config` | Write | Bulk enable/disable schemas and tables |
| `modify_connection_database_schema_config` | Write | Update a specific database schema |
| `get_connection_column_config` | Read | Column-level config for a table |
| `modify_connection_table_config` | Write | Enable/disable a table |
| `modify_connection_column_config` | Write | Enable/disable/hash a column |
| `delete_connection_column_config` | Destructive | Remove a blocked column config |
| `delete_multiple_columns_connection_config` | Destructive | Remove multiple blocked columns |

### Destinations
| Tool | Type | Description |
|------|------|-------------|
| `list_destinations` | Read | All destinations (auto-paginated) |
| `create_destination` | Write | Create a new destination |
| `get_destination_details` | Read | Config for one destination |
| `modify_destination` | Write | Update destination config |
| `delete_destination` | Destructive | Delete a destination |
| `run_destination_setup_tests` | Write | Verify destination connectivity |

### Groups
| Tool | Type | Description |
|------|------|-------------|
| `list_groups` | Read | All groups (auto-paginated) |
| `create_group` | Write | Create a new group |
| `get_group_details` | Read | Details for one group |
| `modify_group` | Write | Update a group |
| `delete_group` | Destructive | Delete a group |
| `list_connections_in_group` | Read | Connections in a group (auto-paginated) |
| `list_users_in_group` | Read | Users in a group (auto-paginated) |
| `add_user_to_group` | Write | Add a user to a group |
| `delete_user_from_group` | Destructive | Remove a user from a group |
| `get_group_ssh_public_key` | Read | SSH public key for a group |
| `get_group_service_account` | Read | Service account email for a group |

### Log Services
| Tool | Type | Description |
|------|------|-------------|
| `list_log_services` | Read | All external log services |
| `create_log_service` | Write | Create a new log service |
| `get_log_service_details` | Read | Details for one log service |
| `update_log_service` | Write | Update a log service |
| `delete_log_service` | Destructive | Delete a log service |
| `run_log_service_setup_tests` | Write | Test a log service |

### Hybrid Deployment Agents
| Tool | Type | Description |
|------|------|-------------|
| `list_hybrid_deployment_agents` | Read | All hybrid agents |
| `create_hybrid_deployment_agent` | Write | Create a new agent |
| `get_hybrid_deployment_agent` | Read | Details for one agent |
| `re_auth_hybrid_deployment_agent` | Write | Regenerate agent credentials |
| `reset_hybrid_deployment_agent_credentials` | Write | Reset agent credentials |
| `delete_hybrid_deployment_agent` | Destructive | Delete an agent |

### Connector Metadata
| Tool | Type | Description |
|------|------|-------------|
| `list_metadata_connectors` | Read | All connector types with metadata |
| `get_metadata_connector_config` | Read | Config schema for a connector type |
| `list_public_connectors` | Read | Public connector list (no auth) |

### Transformations
| Tool | Type | Description |
|------|------|-------------|
| `list_transformation_projects` | Read | All transformation projects |
| `create_transformation_project` | Write | Create a new project |
| `get_transformation_project_details` | Read | Details for one project |
| `modify_transformation_project` | Write | Update a project |
| `delete_transformation_project` | Destructive | Delete a project |
| `test_transformation_project` | Write | Run project tests |
| `list_transformations` | Read | All transformations |
| `create_transformation` | Write | Create a new transformation |
| `get_transformation_details` | Read | Details for one transformation |
| `update_transformation` | Write | Update a transformation |
| `delete_transformation` | Destructive | Delete a transformation |
| `run_transformation` | Write | Trigger a transformation run |
| `cancel_transformation` | Write | Cancel a running transformation |
| `upgrade_transformation_package` | Write | Upgrade dbt package version |
| `list_transformation_package_metadata` | Read | Quickstart package metadata |
| `get_transformation_package_metadata_details` | Read | Details for a quickstart package |

### Webhooks
| Tool | Type | Description |
|------|------|-------------|
| `list_webhooks` | Read | All webhooks |
| `create_account_webhook` | Write | Create account-level webhook |
| `create_group_webhook` | Write | Create group-level webhook |
| `get_webhook_details` | Read | Details for one webhook |
| `modify_webhook` | Write | Update a webhook |
| `delete_webhook` | Destructive | Delete a webhook |
| `test_webhook` | Write | Send a test event to a webhook |

---

## Safety Guidelines

- Always confirm with the user before calling **Destructive** tools (`delete_*`, `delete_multiple_columns_connection_config`)
- `resync_connection` triggers a full historical re-sync — this can be slow and costly for large datasets. Prefer `sync_connection` unless a full re-sync is specifically needed
- `modify_connection_column_config` with `hashed: true` anonymises data on the next sync — this is a one-way operation per sync cycle
- `schema` in `create_connection` is permanent and cannot be changed after creation — confirm the schema name before creating