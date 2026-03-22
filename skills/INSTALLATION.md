# Installation Guide for Claude Skills

This guide provides step-by-step instructions for uploading and configuring your custom Claude skills.

## Table of Contents

- [Quick Start](#quick-start)
- [Detailed Installation Steps](#detailed-installation-steps)
- [Tool Integration Setup](#tool-integration-setup)
- [Verification and Testing](#verification-and-testing)
- [Troubleshooting](#troubleshooting)

## Quick Start

**Time required**: 15-30 minutes (depending on number of tool integrations needed)

1. Extract this ZIP file to a local folder
2. Log into claude.ai
3. Go to Settings > Skills
4. Upload each skill folder (one at a time)
5. Connect required tools in Settings > Integrations
6. Test each skill with example commands

## Detailed Installation Steps

### Step 1: Prepare Your Files

1. **Download and Extract**
   - If you downloaded a ZIP file, extract it to a convenient location
   - You should see 8 folders, each representing one skill:
     - `business-performance-looker/`
     - `daily-briefing/`
     - `dbt-development/`
     - `google-doc-proposal-generator/`
     - `harvest-project-creator/`
     - `jira-cycle-time-analysis/`
     - `xero-aged-debtors-analysis/`
     - `xero-bookkeeping/`

2. **Verify Folder Structure**
   - Each folder should contain at minimum a `SKILL.md` file
   - Some folders have additional resources (examples, references, scripts)
   - All files are necessary for the skill to function properly

### Step 2: Access Claude.ai Skills Management

1. **Navigate to Claude.ai**
   - Open your web browser
   - Go to https://claude.ai
   - Log in with your credentials

2. **Open Settings**
   - Click your profile icon or name in the top-right corner
   - Select "Settings" from the dropdown menu

3. **Navigate to Skills**
   - In the left sidebar of Settings, find "Skills"
   - Click on "Skills" to open the skills management page

### Step 3: Upload Skills (One at a Time)

For each of the 8 skills, follow this process:

1. **Click "Create New Skill" or "Upload Skill"**
   - You'll see a button to create/upload a new skill
   - Click this button to start the upload process

2. **Select Skill Folder**
   - A file/folder picker will appear
   - Navigate to where you extracted the ZIP file
   - Select the folder for ONE skill (e.g., `daily-briefing/`)
   - Click "Open" or "Select Folder"

3. **Verify Upload**
   - Claude will process the folder and read the `SKILL.md` file
   - You should see a preview of the skill name and description
   - Verify the information looks correct

4. **Confirm Upload**
   - Click "Create" or "Confirm" to finalize the upload
   - The skill should now appear in your skills list

5. **Repeat for All 8 Skills**
   - Go back to step 1 and repeat for each remaining skill folder
   - This ensures each skill is properly uploaded with all its files

**Recommended Upload Order**:
1. `daily-briefing` (most commonly used)
2. `xero-aged-debtors-analysis` (frequently used)
3. `xero-bookkeeping`
4. `harvest-project-creator`
5. `business-performance-looker`
6. `google-doc-proposal-generator`
7. `jira-cycle-time-analysis`
8. `dbt-development`

### Step 4: Connect Tool Integrations

After uploading skills, you need to connect the external tools they use.

1. **Navigate to Integrations**
   - In Settings, find "Integrations" or "Connected Tools"
   - Click to see available integrations

2. **Connect Required Tools**

   The skills require these tool connections:

   | Tool | Required For | Priority |
   |------|--------------|----------|
   | Xero | xero-aged-debtors-analysis, xero-bookkeeping | HIGH |
   | Google Calendar | daily-briefing | HIGH |
   | Slack | daily-briefing | HIGH |
   | Gmail | daily-briefing | HIGH |
   | Looker | business-performance-looker, jira-cycle-time-analysis | MEDIUM |
   | HubSpot | harvest-project-creator | MEDIUM |
   | Harvest | harvest-project-creator | MEDIUM |
   | Fathom | daily-briefing, google-doc-proposal-generator | MEDIUM |
   | Google Drive | daily-briefing, google-doc-proposal-generator | MEDIUM |
   | Atlassian/Jira | jira-cycle-time-analysis (optional) | LOW |

3. **For Each Tool**:
   - Find the tool in the integrations list
   - Click "Connect" or "Authorize"
   - Follow the OAuth flow to grant Claude access
   - Ensure you grant all requested permissions
   - Verify the connection shows as "Connected"

### Step 5: Configure Tool-Specific Settings

Some tools may require additional configuration:

#### Xero Configuration
- Ensure the connected Xero organization is your primary one
- Verify you have accounting permissions in Xero
- Check that the organization has active data

#### Looker Configuration
- Confirm you're connected to the correct Looker instance
- Verify you have access to:
  - Analytics model
  - Business Operations explore
  - Finance explore (for P&L)
  - Web Analytics explore
  - Website Leads explore

#### Slack Configuration
- Ensure the integration can:
  - Send direct messages
  - Search public and private channels you're in
  - Read message history

#### Google Calendar Configuration
- Verify access to all calendars you want to include in briefings
- Check that the primary calendar is correctly identified

## Tool Integration Setup

### Detailed Integration Steps by Tool

#### Xero Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "Xero"
   - Click "Connect"

2. **In Xero OAuth Flow**:
   - Select your organization
   - Review permissions (read/write to invoices, contacts, accounts)
   - Click "Authorize"

3. **Verify**:
   - Return to Claude.ai
   - Check that Xero shows as "Connected"
   - Organization name should be displayed

#### Slack Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "Slack"
   - Click "Connect"

2. **In Slack OAuth Flow**:
   - Select your workspace
   - Review permissions (channels, messages, users)
   - Click "Allow"

3. **Verify**:
   - Return to Claude.ai
   - Workspace name should be displayed
   - Test by asking Claude "What's my Slack user ID?"

#### Google Workspace (Calendar, Gmail, Drive)

1. **In Claude.ai**:
   - Settings > Integrations > Find "Google"
   - Click "Connect Google Account"

2. **In Google OAuth Flow**:
   - Select your Google account
   - Review permissions for Calendar, Gmail, Drive
   - Click "Allow"

3. **Verify**:
   - Return to Claude.ai
   - Your Google email should be displayed
   - All three services (Calendar, Gmail, Drive) should show as connected

#### Looker Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "Looker"
   - Click "Connect"

2. **Configuration**:
   - Enter your Looker instance URL
   - Authenticate with your Looker credentials

3. **Verify**:
   - Check that you can access your explores
   - Test with: "Show me my Looker explores"

#### HubSpot Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "HubSpot"
   - Click "Connect"

2. **In HubSpot OAuth Flow**:
   - Select your HubSpot account/portal
   - Review permissions (deals, contacts, companies)
   - Click "Grant access"

3. **Verify**:
   - Portal name should be displayed
   - Test with: "Show me recent HubSpot deals"

#### Harvest Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "Harvest"
   - Click "Connect"

2. **In Harvest OAuth Flow**:
   - Select your Harvest account
   - Review permissions (projects, time entries, clients)
   - Click "Authorize"

3. **Verify**:
   - Account name should be displayed
   - Test with: "List my Harvest projects"

#### Fathom Integration

1. **In Claude.ai**:
   - Settings > Integrations > Find "Fathom"
   - Click "Connect"

2. **In Fathom OAuth Flow**:
   - Log in to Fathom if needed
   - Review permissions (meetings, transcripts)
   - Click "Allow"

3. **Verify**:
   - Connection should show as active
   - Test with: "Show me recent Fathom meetings"

## Verification and Testing

### Step 1: Test Each Skill

After installation and integration, test each skill:

#### Daily Briefing
```
Test command: "Give me a brief summary of tomorrow's calendar"
Expected: Claude should list your calendar events for tomorrow
```

#### Xero Aged Debtors Analysis
```
Test command: "Show me our outstanding invoices"
Expected: Claude should retrieve and analyze Xero invoices
```

#### Xero Bookkeeping
```
Test command: "What are the daily reconciliation steps?"
Expected: Claude should provide structured bookkeeping workflow
```

#### Harvest Project Creator
```
Test command: "Show me recent HubSpot deals"
Expected: Claude should list recent deals from HubSpot
```

#### Business Performance Looker
```
Test command: "What explores are available in Looker?"
Expected: Claude should list available Looker explores
```

#### Google Doc Proposal Generator
```
Test command: "List my Google Doc templates"
Expected: Claude should search for template documents
```

#### Jira Cycle Time Analysis
```
Test command: "Show me Jira projects"
Expected: Claude should list available projects (if Jira connected)
```

#### dbt Development
```
Test command: "Review this dbt model: [paste simple model]"
Expected: Claude should analyze the model against conventions
```

### Step 2: Verify Tool Access

Check that skills can access tools:

1. **Start a new conversation with Claude**
2. **Ask**: "What tools do you have access to?"
3. **Verify**: Claude should list all connected tools
4. **Test**: Ask Claude to use a specific tool (e.g., "Search my Slack messages")

### Step 3: Check Skill Activation

Verify skills activate automatically:

1. **Use a trigger phrase** (e.g., "What did I do today?")
2. **Observe**: Claude should automatically use the daily-briefing skill
3. **Confirm**: The response should include data from multiple sources

## Troubleshooting

### Skills Not Appearing

**Problem**: Uploaded skill doesn't show in skills list

**Solutions**:
1. Verify the folder contains a `SKILL.md` file
2. Check that the SKILL.md file has proper YAML front matter:
   ```yaml
   ---
   name: skill-name
   description: Description here
   ---
   ```
3. Re-upload the skill folder
4. Refresh the Claude.ai page

### Tool Connection Failed

**Problem**: Tool integration fails or shows as disconnected

**Solutions**:
1. **Check Permissions**: Ensure you have admin/appropriate permissions in the tool
2. **Try Reconnecting**: 
   - Disconnect the tool
   - Wait 30 seconds
   - Reconnect
3. **Clear Browser Cache**: Sometimes helps with OAuth flows
4. **Try Different Browser**: Some OAuth flows work better in certain browsers
5. **Check Tool Status**: Verify the external tool's service is operational

### Skill Not Activating

**Problem**: Skill doesn't trigger when expected

**Solutions**:
1. **Use Clear Trigger Phrases**: Try the example commands from the README
2. **Check Tool Connections**: Ensure all required tools are connected
3. **Verify Skill is Enabled**: Check that the skill is turned on in Settings
4. **Start New Conversation**: Sometimes helps reset context
5. **Be Explicit**: Say "Use the [skill-name] skill to..."

### Tool Returns No Data

**Problem**: Skill activates but returns empty results

**Solutions**:
1. **Check Data Exists**: Verify you have data in the source tool (e.g., calendar events)
2. **Verify Permissions**: Ensure the integration has read access
3. **Check Date Ranges**: Some queries may be looking at wrong date ranges
4. **Test Tool Directly**: Try accessing the tool directly to confirm data is there

### Skill Returns Error

**Problem**: Skill encounters an error during execution

**Solutions**:
1. **Check Error Message**: Often indicates specific issue (e.g., "Invoice not found")
2. **Verify Input Format**: Ensure you're providing data in expected format
3. **Check Tool Limits**: Some tools have rate limits or data limits
4. **Try Simpler Query**: Start with basic command and build up
5. **Report Issue**: Note exact error and steps to reproduce

### General Debugging Steps

1. **Start Fresh**:
   - Open new conversation
   - Clear browser cache
   - Log out and back in

2. **Verify Basics**:
   - Skills uploaded correctly
   - All tools connected
   - Proper permissions granted

3. **Test Incrementally**:
   - Test tool access first
   - Then test skill with simple command
   - Build up to complex queries

4. **Check Logs**:
   - Look for any error messages in browser console (F12)
   - Note exact error text for troubleshooting

## Getting Help

If you continue to experience issues:

1. **Document the Problem**:
   - What skill you're using
   - What command you gave
   - What tools are connected
   - What error occurred

2. **Check Tool Documentation**:
   - Each skill has detailed documentation in its folder
   - Review the SKILL.md for specific requirements

3. **Contact Support**:
   - For Rittman Analytics team members: Contact internal IT support
   - For Claude.ai issues: Use the help/feedback option in Claude.ai

## Next Steps

Once installation is complete and verified:

1. **Bookmark Key Trigger Phrases**: Keep a note of commonly used commands
2. **Create Workflows**: Combine skills for powerful automation
3. **Share Best Practices**: Document what works well for your use cases
4. **Customize as Needed**: Modify skills to fit your specific workflows

---

**Installation Support**: For internal support, contact the Rittman Analytics team
**Last Updated**: November 2025
