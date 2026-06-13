---
sidebar_position: 6
title: Document Store
---

# Document Store Integration

Wire can replicate generated artifacts to Confluence or Notion for client review. Configured at engagement setup, every generate command publishes the artifact to the document store after writing it locally. Review commands surface comments and edits made in the document store as additional review context.

## Configuring a document store

The document store is configured when you run `/wire:new`. At Step 9.5, Wire asks:

```
Would you like to replicate artifacts to a document store for client review?
  [1] Confluence
  [2] Notion
  [3] Skip — manage client review outside Wire
```

You can also configure it after setup:

```
/wire:utils-docstore-config <release-folder>
```

### Confluence

The Atlassian MCP server must be configured (see Issue Tracking). Wire needs a Confluence space key and an optional parent page:

```
Confluence space key: DP
Parent page title (optional): Barton Peveril Engagement
```

Wire creates one Confluence page per artifact, nested under the parent page. Each page is tagged with the Wire artifact ID and engagement ID so Wire can find and update it on subsequent runs.

### Notion

The Notion MCP server must be configured:

```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/mcp"],
      "env": {
        "NOTION_API_KEY": "your-notion-integration-secret"
      }
    }
  }
}
```

Wire needs a Notion database ID to write to:

```
Notion database ID: abc123...
```

Each artifact becomes a Notion page in that database.

## How replication works

After a generate command completes, Wire:

1. Writes the artifact locally as normal
2. Checks whether the artifact already exists in the document store
3. If yes: updates the existing page/document, preserving any client comments
4. If no: creates a new page/document
5. Adds a document store link to the execution log

The document format is Markdown rendered to the target format. Mermaid diagrams are rendered as images before publishing (Confluence and Notion both require image format).

## Review command with document store

When a document store is configured, the review command supplements the local review with document store context:

```
/wire:problem-definition-review <release-folder>
```

Wire reads:
1. The latest artifact content (local)
2. Any reviewer comments added to the Confluence/Notion page since the last review
3. Any edits made directly to the document in the document store
4. Fathom meeting transcripts (as usual)

All of this is presented to you as review context before you approve or request changes.

## Sharing with clients

The document store link for any artifact is visible in `/wire:status` output and in the execution log. Share the Confluence space or Notion database directly with your client — they can comment, edit, and review without needing Claude Code access.

When a client edits a document directly in Confluence or Notion, Wire detects the edit on the next review run and flags it for your attention. You can choose to incorporate the edit into the local artifact or override it with the locally-generated version.

## Exporting the full artifact set

At the end of an engagement, export all artifacts from the document store:

```
/wire:archive <release-folder>
```

This creates a `.wire/releases/<release>/archive/` directory with all artifacts as static Markdown files, independent of the document store. The archive is suitable for handing over to a client who doesn't use Confluence or Notion.
