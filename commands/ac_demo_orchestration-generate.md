---
description: Add automated demo flows with phase state machine
argument-hint: <release-folder>
---

# Add automated demo flows with phase state machine

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.14\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_demo_orchestration-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.14\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Implement automated demo orchestration with phase state machine and multiple demo modes
argument-hint: <project-folder>
---

# Agentic Commerce — Demo Orchestration Generate Command

## Purpose

Build scripted, automated demo flows that showcase all AI commerce features without manual interaction. Demos activate via URL parameters (`?demo=shopping`, `?demo=tryon`, `?demo=full`) and simulate a realistic user journey — typing queries, clicking buttons, waiting for AI responses — using a phase state machine (useRef), phase-guarded timers, simulated typing with random delays, and a demo persona with preset localStorage data.

## Usage

```bash
/wire:ac_demo_orchestration-generate YYYYMMDD_project_name
```

## Prerequisites

- `storefront.review: approved` in status.md
- All features to be demoed must have `generate: complete` in status.md
- GitHub repo cloned locally
- Local dev server available for testing

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Confirm `storefront.review == approved`
3. Check which features are `generate: complete` — the demo will only include
   complete features. Note which modes to implement:
   - `?demo=shopping` — requires conversational_assistant
   - `?demo=search` — requires semantic_search
   - `?demo=tryon` — requires virtual_tryon and conversational_assistant
   - `?demo=full` — requires all of the above

### Step 2: Read Project Structure

1. Read `src/components/ShoppingAssistant.tsx` to understand the component API
   (what props and callbacks it exposes)
2. Read `src/components/SemanticSearch.tsx` if it exists
3. Read `src/stores/` to understand the Zustand cart store (for resetCart)
4. Read `src/lib/personalisation.ts` to understand the localStorage keys used
5. Read `src/lib/analytics.ts` for the `getVisitorId` function

### Step 3: Define the Demo Persona and Constants

Provide the following Claude Code prompt:

```
Create src/lib/demoConstants.ts with demo configuration:

// Demo persona — pre-built profile for a consistent demo experience
export const DEMO_PROFILE = {
  first_name: "Alex",
  style_preferences: ["performance", "technical"],
  shirt_collar_size: "M",
  waist_size: "32",
};

// A pre-uploaded demo photo URL (or a placeholder stock photo)
// This should be a real URL accessible during the demo
export const DEMO_PHOTO_URL = "[set to a real stock photo or pre-uploaded image URL]";

// A pre-seeded profile ID in the database (optional — can be null)
export const DEMO_PROFILE_ID = null; // set after seeding if using database profiles

// Demo query sequences by mode
export const DEMO_QUERIES = {
  shopping: {
    initial: "Show me summer cycling jerseys",
    refinement: "Something more lightweight and breathable",
    cart: null, // will click "Add to Cart" on first product
  },
  tryon: {
    initial: "Show me jerseys that would look good on me",
    refinement: "Something a bit more technical",
    tryon: true, // will trigger try-on after refinement
  },
  search: {
    query: "breathable jersey for hot summer rides",
  },
};

// Phase timing (ms)
export const DEMO_TIMINGS = {
  pageWait: 2000,       // pause before opening modal
  greetingWait: 1500,   // wait after greeting before typing
  resultsWait: 3000,    // pause to view results before refinement
  refinedWait: 4000,    // pause to view refined results
  tryonWait: 2000,      // pause after try-on button appears
  cartWait: 2000,       // pause after add to cart
  closingWait: 3000,    // pause before closing overlay
};

// Typing simulation
export const TYPING_MIN_DELAY = 40;  // ms per character minimum
export const TYPING_MAX_DELAY = 75;  // ms per character maximum
```

### Step 4: Generate the useAutoDemo Hook

Create `src/hooks/useAutoDemo.ts`.

Provide the following Claude Code prompt:

```
Create a custom React hook at src/hooks/useAutoDemo.ts implementing the demo
phase state machine. This hook drives the demo without controlling components
directly — it uses a notify/callback pattern.

1. Hook signature:
   function useAutoDemo({
     openModal: () => void,
     resetCart: () => void,
     inputRef: React.RefObject<HTMLInputElement>,
     setInput: (value: string) => void,
     sendMessage: (text: string) => void,
   })

2. URL parameter detection:
   const demoMode = new URLSearchParams(window.location.search).get("demo");
   const isDemo = demoMode !== null;
   Export isDemo so the parent can show the start overlay.

3. Phase state machine using useRef (NOT useState — no re-renders on phase change):
   type Phase =
     | "idle"
     | "waiting_page"
     | "waiting_modal"
     | "waiting_greeting"
     | "typing_initial"
     | "waiting_results"
     | "typing_refinement"
     | "waiting_refined"
     | "clicking_tryon"
     | "waiting_tryon"
     | "clicking_cart"
     | "waiting_cart"
     | "done";

   const phaseRef = useRef<Phase>("idle");

4. Timer management:
   const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

   const addPhaseTimer = (expectedPhase: Phase, fn: () => void, ms: number) => {
     const id = setTimeout(() => {
       if (phaseRef.current !== expectedPhase) return; // phase guard
       fn();
     }, ms);
     timersRef.current.push(id);
   };

   // Cleanup all timers on unmount
   useEffect(() => () => timersRef.current.forEach(clearTimeout), []);

5. Simulated typing:
   const typeAndSend = (text: string) => {
     let i = 0;
     const typeNext = () => {
       if (i < text.length) {
         setInput(text.slice(0, ++i));
         const delay = TYPING_MIN_DELAY + Math.random() * (TYPING_MAX_DELAY - TYPING_MIN_DELAY);
         setTimeout(typeNext, delay);
       } else {
         setTimeout(() => sendMessage(text), 700);
       }
     };
     typeNext();
   };

6. clickWhenReady utility:
   const clickWhenReady = (
     selector: string,
     onSuccess: () => void,
     maxAttempts = 15
   ) => {
     let attempt = 0;
     const tryClick = () => {
       const el = document.querySelector(selector) as HTMLButtonElement | null;
       if (el && !el.disabled) {
         el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
         onSuccess();
       } else if (attempt++ < maxAttempts) {
         setTimeout(tryClick, 400);
       }
     };
     tryClick();
   };

7. startDemo function:
   const startDemo = () => {
     // 1. Reset state
     resetCart();

     // 2. Set demo persona in localStorage
     localStorage.setItem("visitor_id", "demo-visitor");
     localStorage.setItem("user_first_name", DEMO_PROFILE.first_name);
     localStorage.setItem("user_profile", JSON.stringify(DEMO_PROFILE));
     localStorage.setItem("user_photo_url", DEMO_PHOTO_URL);

     // 3. Start the phase sequence
     setStarted(true);
   };

8. Phase flow (connect phases using useEffect and addPhaseTimer):

   When started: idle → waiting_page
   addPhaseTimer("waiting_page", () => {
     phaseRef.current = "waiting_modal";
     openModal();
   }, DEMO_TIMINGS.pageWait);

   notifyGreetingReady (called by ShoppingAssistant when greeting appears):
   addPhaseTimer("waiting_greeting", () => {
     phaseRef.current = "typing_initial";
     typeAndSend(DEMO_QUERIES[demoMode].initial ?? DEMO_QUERIES.shopping.initial);
   }, DEMO_TIMINGS.greetingWait);

   notifyProducts(hasProducts: boolean):
   If phaseRef.current === "waiting_results" && hasProducts:
   addPhaseTimer("waiting_results", () => {
     phaseRef.current = "typing_refinement";
     typeAndSend(DEMO_QUERIES[demoMode].refinement ?? "Something more breathable");
   }, DEMO_TIMINGS.resultsWait);

   notifyRefinedProducts(hasProducts: boolean):
   If phaseRef.current === "waiting_refined" && hasProducts:
   - If demoMode includes tryon:
     addPhaseTimer("waiting_refined", () => {
       phaseRef.current = "clicking_tryon";
       clickWhenReady("[data-demo-tryon]", () => {
         phaseRef.current = "waiting_tryon";
       });
     }, DEMO_TIMINGS.refinedWait);
   - Otherwise, go straight to cart:
     addPhaseTimer("waiting_refined", () => {
       phaseRef.current = "clicking_cart";
       clickWhenReady("[data-demo-add-to-cart]", () => {
         phaseRef.current = "done";
         setClosingOverlay(true);
       });
     }, DEMO_TIMINGS.refinedWait);

   notifyTryOnComplete():
   If phaseRef.current === "waiting_tryon":
   addPhaseTimer("waiting_tryon", () => {
     phaseRef.current = "clicking_cart";
     clickWhenReady("[data-demo-add-to-cart]", () => {
       phaseRef.current = "done";
       setClosingOverlay(true);
     });
   }, DEMO_TIMINGS.tryonWait);

9. Returns:
   {
     isDemo,
     started,
     startDemo,
     closingOverlay,
     notifyGreetingReady,
     notifyProducts,
     notifyRefinedProducts,
     notifyTryOnComplete,
   }
```

### Step 5: Add Start and Closing Overlays

Provide the following Claude Code prompt:

```
In the main page component (src/pages/Index.tsx or wherever the ShoppingAssistant
is mounted), integrate the useAutoDemo hook and add two overlays:

1. START OVERLAY — shown when isDemo && !started:

<div className="fixed inset-0 z-50 bg-background/90 backdrop-blur-sm
                flex items-center justify-center">
  <div className="text-center space-y-6">
    <div className="w-24 h-24 rounded-full bg-primary mx-auto flex items-center justify-center
                    cursor-pointer hover:bg-primary/90 transition-colors"
         onClick={startDemo}
         data-demo-start>
      <Play className="w-10 h-10 text-primary-foreground" />
    </div>
    <div>
      <p className="text-xl font-medium">Agentic Commerce Demo</p>
      <p className="text-muted-foreground text-sm mt-1">
        Click to start the automated demo
      </p>
    </div>
  </div>
</div>

2. CLOSING OVERLAY — shown when closingOverlay is true:

<div className="fixed inset-0 z-50 bg-background flex items-center justify-center
                animate-in fade-in duration-700">
  <div className="text-center space-y-4 max-w-lg px-6">
    <h1 className="text-4xl font-bold tracking-tight">
      Personalised shopping, powered by AI.
    </h1>
    <p className="text-xl text-muted-foreground">
      From discovery to checkout — one seamless conversation.
    </p>
    <p className="text-sm text-muted-foreground mt-8">
      Built with Wire Framework · Rittman Analytics
    </p>
  </div>
</div>

3. Wire up notify callbacks in ShoppingAssistant:
   Pass the demo object to ShoppingAssistant:
   <ShoppingAssistant demo={demo} ... />

   In ShoppingAssistant, on first assistant message (greeting):
   useEffect(() => {
     if (messages.length === 1 && messages[0].role === "assistant" && demo) {
       demo.notifyGreetingReady();
     }
   }, [messages]);

   On each new assistant message with products:
   useEffect(() => {
     const latestMsg = messages[messages.length - 1];
     if (latestMsg?.role === "assistant" && demo) {
       const hasProducts = (latestMsg.products?.length ?? 0) > 0;
       if (phaseIsWaitingResults) demo.notifyProducts(hasProducts);
       if (phaseIsWaitingRefined) demo.notifyRefinedProducts(hasProducts);
     }
   }, [messages]);

4. Add data-demo-* attributes to key interactive elements:
   - On the "Add to Cart" button in product cards: data-demo-add-to-cart
   - On the "Try On" button in product cards: data-demo-tryon
```

### Step 6: Implement Multiple Demo Modes

Provide the following Claude Code prompt:

```
In src/pages/Index.tsx (or the routing configuration), implement mode detection:

const demoMode = new URLSearchParams(window.location.search).get("demo");

switch (demoMode) {
  case "shopping":
    // conversational_assistant demo only
    // Sequence: open modal → greeting → "Show me summer jerseys" → refinement → cart
    break;

  case "search":
    // semantic_search demo only
    // Sequence: auto-populate search bar with query → show results → highlight relevance badges
    break;

  case "tryon":
    // virtual_tryon demo
    // Sequence: open modal → jerseys query → refinement → try-on click → add to cart
    break;

  case "full":
    // All features in sequence
    // Sequence: search demo → assistant greeting → query → refinement → try-on → cart
    break;
}

For the "search" mode, implement a separate useDemoSearch hook that:
- Waits 2 seconds, then auto-populates the semantic search input
- Uses DEMO_QUERIES.search.query
- Waits for results, highlights the relevance_reason badges
- After 5 seconds, clears and shows the closing overlay
```

### Step 7: Update Status

```yaml
demo_orchestration:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: YYYY-MM-DD
  demo_modes: [shopping, search, tryon, full]   # modes implemented
  files:
    - src/lib/demoConstants.ts
    - src/hooks/useAutoDemo.ts
    - src/pages/Index.tsx (modified — overlays + hook integration)
```

### Step 8: Confirm and Suggest Next Steps

```
## Demo Orchestration Generated

### Test the demos locally:
- http://localhost:5173/?demo=shopping
- http://localhost:5173/?demo=search
- http://localhost:5173/?demo=tryon
- http://localhost:5173/?demo=full

### Next Steps

1. Test each demo mode end-to-end locally
2. **Validate**: `/wire:ac_demo_orchestration-validate <project>`
```

## Edge Cases

### Phase Guard Prevents Stale Timer Execution

Every `addPhaseTimer` call includes an `expectedPhase` check. If a timer fires
after the phase has advanced (e.g. AI responded faster than expected), the timer
function returns early without executing. This prevents double-actions and out-of-order
execution.

### AI Response Slower Than Expected

If the AI takes longer than anticipated, the demo simply waits at the current
phase until `notifyProducts` (or equivalent) is called. Never hardcode timeouts
for API responses — always use the notify pattern.

### Try-On Times Out During Demo

If the virtual try-on times out (45 seconds), the `notifyTryOnComplete` callback
should still be called with a `timedOut: true` flag. The demo should continue
to the cart step rather than getting stuck. Use `clickWhenReady("[data-demo-add-to-cart]")`
as normal — the fallback state still shows the Add to Cart button.

## Output

This command produces:
- `src/lib/demoConstants.ts`
- `src/hooks/useAutoDemo.ts`
- Modified `src/pages/Index.tsx` (overlays + hook integration)
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
