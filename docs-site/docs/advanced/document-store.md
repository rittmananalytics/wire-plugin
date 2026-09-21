---
sidebar_position: 7
title: Document Store
---

# Document Store Integration

Once Wire has drafted a requirements document or a data model, the people who most need to read and comment on it are usually at the client, and they are unlikely to have Claude Code open or to want to read Markdown out of a Git repository. Wire can therefore replicate generated artifacts to Confluence or Notion for client review. Configured at engagement setup, every generate command publishes the artifact to the document store after writing it locally, and review commands surface the comments and edits made in the document store as additional review context, so that what the client says in Confluence or Notion comes back into Wire's own review rather than sitting in a separate channel.

In this page we will look at how you configure a document store for either tool, how replication works after each generate command, what the review command reads back, how you share the store with your client and how you export the full artifact set at the end of the engagement.

## Configuring a document store

The document store is configured when you run `/wire:new`, and at Step 9.5 Wire asks:

```
Would you like to replicate artifacts to a document store for client review?
  [1] Confluence
  [2] Notion
  [3] Skip - manage client review outside Wire
```

You can also configure it after setup, using:

```
/wire:utils-docstore-setup <release-folder>
```

### Confluence

To publish to Confluence, the Atlassian MCP server must be configured (see Issue Tracking), and Wire needs a Confluence space key together with an optional parent page:

```
Confluence space key: DP
Parent page title (optional): Barton Peveril Engagement
```

Wire creates one Confluence page per artifact, nested under the parent page, and each page is tagged with the Wire artifact ID and engagement ID so that Wire can find and update it on subsequent runs.

### Notion

For Notion, the Notion MCP server must be configured:

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

Wire then needs a Notion database ID to write to:

```
Notion database ID: abc123...
```

and each artifact becomes a Notion page in that database.

## How replication works

So what happens once a generate command completes? Wire:

1. Writes the artifact locally as normal
2. Checks whether the artifact already exists in the document store
3. If yes: updates the existing page/document, preserving any client comments
4. If no: creates a new page/document
5. Adds a document store link to the execution log

The document format is Markdown rendered to the target format, and Mermaid diagrams are rendered as images before publishing, because Confluence and Notion both require image format.

## Review command with document store

When a document store is configured, the review command supplements the local review with context drawn from the document store, so that running, for example:

```
/wire:problem-definition-review <release-folder>
```

causes Wire to read:
1. The latest artifact content (local)
2. Any reviewer comments added to the Confluence/Notion page since the last review
3. Any edits made directly to the document in the document store
4. Fathom meeting transcripts (as usual)

All of this is presented to you as review context before you approve or request changes.

## Sharing with clients

How does the client get to the documents? The document store link for any artifact is visible in `/wire:status` output and in the execution log, and you share the Confluence space or Notion database directly with your client, who can then comment, edit and review without needing Claude Code access.

When a client edits a document directly in Confluence or Notion, Wire detects the edit on the next review run and flags it for your attention, and you can choose either to incorporate the edit into the local artifact or to override it with the locally generated version.

## Exporting the full artifact set

At the end of an engagement, export all artifacts from the document store with:

```
/wire:archive <release-folder>
```

This creates a `.wire/releases/<release>/archive/` directory with all artifacts as static Markdown files, independent of the document store, and the archive is suitable for handing over to a client who does not use Confluence or Notion.
