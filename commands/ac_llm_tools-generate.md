---
description: Implement LLM with autonomous tool calling
argument-hint: <release-folder>
---

# Implement LLM with autonomous tool calling

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.16\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_llm_tools-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.16\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Implement LLM chat with autonomous tool calling for product search
argument-hint: <project-folder>
---

# Agentic Commerce — LLM Tools Generate Command

## Purpose

Build an LLM-powered chat interface where the model autonomously decides when to call product search tools using the function calling pattern. This is distinct from the conversational assistant: instead of a managed conversation API, the LLM is given a toolbox and decides when to use it — executing a two-call architecture (intent + tool call → enriched response) that produces natural language replies with embedded product recommendations.

## Usage

```bash
/wire:ac_llm_tools-generate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.review: approved` in status.md
- GitHub repo cloned locally (URL in status.md)
- LLM API credentials with function/tool calling support (Google Gemini 2.5 Flash, OpenAI GPT-4o, or Anthropic Claude)
- Semantic search edge function deployed (from `semantic_search` feature, if available)
- Supabase project configured

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Confirm `storefront.review == approved`
3. Ask the consultant which LLM to use:
   - **Google Gemini 2.5 Flash** (recommended — fast, native tool calling)
   - **OpenAI GPT-4o** (industry standard function calling format)
   - **Anthropic Claude** (tool_use pattern)
4. Confirm whether the `semantic-search` edge function is deployed from the semantic search feature.
   If not, the llm-chat function will call the Shopify Storefront API directly.

### Step 2: Read Project Structure

1. Read `supabase/functions/` to understand existing edge functions
2. If `semantic-search/index.ts` exists, note the function endpoint URL — the LLM tool will call it
3. Read `src/lib/shopify.ts` for the storefrontApiRequest helper (fallback if no semantic search)
4. Read `src/stores/` to understand the Zustand cart store

### Step 3: Define Tool Schema

Provide the following Claude Code prompt:

```
In supabase/functions/llm-chat/index.ts, define the tool schema for the LLM.

Use the OpenAI-compatible function calling format (Gemini and most models support this):

const TOOLS = [
  {
    type: "function",
    function: {
      name: "search_products",
      description: [
        "Search the product catalog for items matching a natural language query.",
        "Use this tool when the user expresses intent to find, browse, or purchase products.",
        "Do NOT use for greetings, general questions, or checkout-related requests.",
        "Convert conversational intent into product-focused search terms before calling."
      ].join(" "),
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "A product-focused search query derived from the user's intent. " +
              "E.g. 'lightweight summer cycling jersey' not 'I want something for summer'."
          },
          filters: {
            type: "object",
            description: "Optional filters to narrow results",
            properties: {
              maxPrice: { type: "number", description: "Maximum price in store currency" },
              productType: { type: "string", description: "Product category or type" }
            }
          }
        },
        required: ["query"]
      }
    }
  }
];
```

### Step 4: Generate LLM Chat Coordinator Edge Function

Create `supabase/functions/llm-chat/index.ts`.

Provide the following Claude Code prompt:

```
Create a Supabase edge function at supabase/functions/llm-chat/index.ts that
implements the two-call tool-calling pattern:

1. Accepts a JSON body with:
   { messages: Array<{ role: "user" | "assistant", content: string }> }
   (Full conversation history — the client sends all prior messages each time)

2. Defines a SYSTEM_PROMPT:
   "You are a knowledgeable and friendly shopping assistant for [STORE_NAME].
   You have access to a product search tool. Use it whenever the user wants
   to find, browse, or buy products. For general questions or greetings,
   respond naturally without calling any tools.
   When presenting products from search results, describe why each is a
   good match for the user's request. Keep your response under 150 words."

3. Implements the FIRST LLM CALL:
   - Send [SYSTEM_PROMPT + conversation history] to the LLM with TOOLS defined
   - Set tool_choice: "auto" (let the model decide whether to call a tool)
   - Parse the response: does it contain tool_calls?

4. If NO tool_calls in the first response:
   - Return immediately: { type: "text", content: firstResponse.content, products: [] }

5. If tool_calls are present (model decided to search):
   a. Extract the search_products call: parse { query, filters } from arguments
   b. Execute the tool call:
      - If semantic-search function is deployed: call it via fetch()
      - Otherwise: call Shopify Storefront API using storefrontApiRequest()
      - Apply filters.maxPrice and filters.productType if provided
      - Return top 6 results
   c. Implement the SECOND LLM CALL:
      - Resend the full conversation + the assistant's tool_call message
        + the tool result message (role: "tool", tool_call_id, content: JSON.stringify(products))
      - No tools in the second call (just ask for a natural language response)
   d. Parse the second response content

6. Return:
   {
     type: "products",
     content: secondResponse.content,  // natural language with product context
     products: searchResults,
     search_query: query
   }

7. Handle tool call failures gracefully:
   - If the search tool throws, return the first response content without products
   - Log the error but do not crash

8. All API keys must come from Deno.env.get() — OPENAI_API_KEY, GEMINI_API_KEY, etc.

Read the existing edge functions for the correct Deno/Supabase initialisation patterns.
```

### Step 5: Generate ChatInterface React Component

Create `src/components/ChatInterface.tsx`.

Provide the following Claude Code prompt:

```
Create a ChatInterface React component at src/components/ChatInterface.tsx that:

1. Renders as a panel or modal with:
   - A message list (scrollable, auto-scrolls to latest)
   - User messages: right-aligned, primary colour bubble
   - Assistant messages: left-aligned, muted bubble
   - A text input with send button at the bottom
   - Placeholder: "Ask me anything about our products..."

2. Maintains the FULL conversation history in component state:
   const [messages, setMessages] = useState<Message[]>([]);
   
   Send the full history with each request:
   supabase.functions.invoke("llm-chat", { body: { messages: [...history, newMessage] } })

3. Handles both response types:
   - type: "text" — render content in a plain assistant bubble
   - type: "products" — render content in a bubble, then render ProductCard components below it

4. Shows product cards inline:
   - Uses the existing product card component or creates a minimal inline card
   - Each card: image, title, price, "Add to Cart" button
   - "Add to Cart" calls the Zustand cart store

5. Shows a reasoning indicator when a tool call is made:
   - Before the second LLM response arrives, show:
     "Searching for products..." in a muted italic bubble
   - Replace with the actual response when it arrives

6. Shows a typing indicator (three animated dots) while waiting for any response

7. Has a "Clear conversation" button that resets messages to []

8. Exports: ChatInterface (named export)

Add a route or page where this component can be accessed:
- Either /chat page via React Router
- Or as a panel in the main layout (sidebar on desktop, sheet on mobile)
```

### Step 6: Update Status

```yaml
llm_tools:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  llm_model: [Gemini 2.5 Flash / GPT-4o / Claude]
  uses_semantic_search: true   # or false
  files:
    - supabase/functions/llm-chat/index.ts
    - src/components/ChatInterface.tsx
```

### Step 7: Confirm and Suggest Next Steps

```
## LLM Tools Chat Generated

**Files created:**
- supabase/functions/llm-chat/index.ts (two-call tool-calling coordinator)
- src/components/ChatInterface.tsx

### Next Steps

1. Add LLM credentials as Supabase secrets:
   - GEMINI_API_KEY (for Gemini)
   - OPENAI_API_KEY (for GPT-4o)

2. Deploy the edge function:
   ```bash
   supabase functions deploy llm-chat
   ```

3. **Validate**: `/wire:ac_llm_tools-validate <project>`
```

## Edge Cases

### LLM Calls Tool Every Time (Over-triggering)

If the LLM calls `search_products` even for greetings, tighten the system prompt:
"Only call search_products when the user explicitly asks to find or buy something.
Do NOT call it for greetings ('hello'), general questions ('what are your hours?'),
or affirmations ('thanks', 'great')."

### Second LLM Call Hallucinates Products Not in Results

The second LLM call should be instructed not to invent products:
"Present only the products provided in the tool results. Do not invent or
describe products that are not in the search results."
Add this to the system prompt for the second call.

### Tool Arguments Cannot Be Parsed

If the LLM returns malformed JSON in `tool_calls[].function.arguments`, wrap the
parse in a try/catch and fall back to using the raw user message as the search query.

## Output

This command produces:
- `supabase/functions/llm-chat/index.ts`
- `src/components/ChatInterface.tsx`
- Updated `.wire/<project_id>/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
