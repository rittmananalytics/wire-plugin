# Feature: Automated Demo Orchestration

## Overview

Create scripted, automated demo flows that showcase your AI commerce features without manual interaction. These demos run via URL parameters (e.g. `?demo=shopping-assistant`) and simulate a realistic user journey — typing queries, clicking buttons, and navigating the purchase flow — to demonstrate capabilities to stakeholders, investors, or at conferences.

## Architecture

```
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Demo Hook       │────▸│  Phase State Machine  │────▸│  UI Actions │
│  (URL trigger)   │     │  (useRef phases)      │     │  (DOM events│
└──────────────────┘     └──────────────────────┘     └─────────────┘
       │                          │
       ▼                          ▼
┌──────────────────┐     ┌──────────────────────┐
│  Demo Persona    │     │  Timer Management    │
│  (localStorage)  │     │  (addTimer, clear)   │
└──────────────────┘     └──────────────────────┘
```

## Implementation Steps

### 1. Phase State Machine

Define the demo as a sequence of phases:

```typescript
type Phase =
  | "idle"
  | "waiting_page"        // Show page briefly before starting
  | "waiting_modal"       // Open the assistant modal
  | "waiting_greeting"    // Wait for AI greeting
  | "typing_query"        // Auto-type a search query
  | "waiting_results"     // Wait for product results
  | "typing_refinement"   // Type a follow-up refinement
  | "waiting_refined"     // Wait for refined results
  | "clicking_action"     // Click try-on or add-to-cart
  | "waiting_checkout"    // Show checkout flow
  | "done";               // Show closing overlay
```

### 2. Demo Hook

Create a custom hook that drives the demo:

```typescript
function useAutoDemo({ openModal, resetCart }) {
  const enabled = new URLSearchParams(location.search).has("demo");
  const [started, setStarted] = useState(false);
  const phaseRef = useRef<Phase>("idle");
  const timersRef = useRef<number[]>([]);

  // Timer management with phase guards
  const addPhaseTimer = (expectedPhase: Phase, fn: () => void, ms: number) => {
    const id = setTimeout(() => {
      if (phaseRef.current !== expectedPhase) return; // Phase changed, skip
      fn();
    }, ms);
    timersRef.current.push(id);
  };

  // Simulated typing
  const typeAndSend = (text, inputRef, setInput, sendFn) => {
    phaseRef.current = "typing_query";
    let i = 0;
    const typeNext = () => {
      if (i < text.length) {
        setInput(text.slice(0, ++i));
        setTimeout(typeNext, 40 + Math.random() * 35);
      } else {
        setTimeout(() => sendFn(text), 700);
      }
    };
    typeNext();
  };

  // Click a button when it becomes available
  const clickWhenReady = (selector, onSuccess, maxAttempts = 15) => {
    let attempt = 0;
    const tryClick = () => {
      const btn = document.querySelector(selector);
      if (btn && !btn.disabled) {
        btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        onSuccess();
      } else if (attempt++ < maxAttempts) {
        setTimeout(tryClick, 400);
      }
    };
    tryClick();
  };

  return { enabled, started, startDemo, /* notify callbacks */ };
}
```

### 3. Phase Flow

Wire up the phase transitions:

```typescript
// Phase: idle → waiting_page → waiting_modal
useEffect(() => {
  if (!started) return;
  phaseRef.current = "waiting_page";
  addPhaseTimer("waiting_page", () => {
    phaseRef.current = "waiting_modal";
    openModal();
  }, 2000);
}, [started]);

// Phase: waiting_greeting → typing_query (triggered by notify callback)
const notifyGreetingReady = () => {
  if (phaseRef.current !== "waiting_greeting") return;
  addPhaseTimer("waiting_greeting", () => {
    typeAndSend("Show me summer cycling jerseys", inputRef, setInput, sendFn);
  }, 1500);
};

// Phase: waiting_results → typing_refinement (triggered by notify callback)
const notifyProducts = (hasProducts) => {
  if (phaseRef.current !== "waiting_results" || !hasProducts) return;
  addPhaseTimer("waiting_results", () => {
    typeAndSend("Something more lightweight and breathable", ...);
  }, 3000);
};
```

### 4. Demo Persona

Set up a fake user profile for the demo:

```typescript
function startDemo() {
  // Clear previous state
  resetCart();

  // Set demo persona
  localStorage.setItem("session_id", "demo-session");
  localStorage.setItem("user_profile_id", DEMO_PROFILE_ID);
  localStorage.setItem("user_photo_url", DEMO_PHOTO_URL);

  setStarted(true);
}
```

### 5. Start Overlay

Show a "Start Demo" button before the demo begins:

```tsx
{isDemo && !started && (
  <div className="fixed inset-0 z-50 bg-background/90 flex items-center justify-center">
    <button onClick={startDemo} className="flex flex-col items-center gap-4">
      <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center">
        <PlayIcon className="w-8 h-8" />
      </div>
      <span>Start Demo</span>
    </button>
  </div>
)}
```

### 6. Closing Overlay

Show a branded closing screen when the demo completes:

```tsx
{closingOverlay && (
  <div className="fixed inset-0 z-50 bg-background flex items-center justify-center">
    <div className="text-center">
      <h1 className="text-4xl font-bold">Personalised shopping, powered by AI.</h1>
      <p className="text-xl text-muted-foreground mt-4">
        From discovery to checkout — one seamless conversation.
      </p>
    </div>
  </div>
)}
```

### 7. Notify Pattern

The demo hook doesn't control the assistant directly — instead, it receives notifications when things happen and decides what to do next:

```typescript
// In the assistant component:
useEffect(() => {
  if (latestMessage && demo) {
    demo.notifyAssistantMessage(
      hasProducts,
      hasTryOnPrompt,
      hasTryOnImage
    );
  }
}, [latestMessage]);
```

## Design Principles

1. **Phase guards** — Every timer checks the current phase before executing. This prevents stale timers from firing after the demo has moved on.
2. **No hardcoded timeouts for API responses** — Use notify callbacks instead. The demo waits for the real response, then adds a viewing delay.
3. **Graceful degradation** — If a step fails (e.g. try-on times out), skip to the next phase.
4. **Clean teardown** — Clear all timers on unmount.
5. **Data attributes** — Use `data-demo-*` attributes on buttons so the demo can find them reliably.

## Multiple Demo Modes

Support different demo scenarios via URL parameters:

```typescript
const demoMode = new URLSearchParams(location.search).get("demo");

switch (demoMode) {
  case "shopping":    return <ShoppingAssistantDemo />;
  case "search":      return <SearchComparisonDemo />;
  case "tryon":       return <VirtualTryOnDemo />;
  case "full":        return <FullJourneyDemo />;
}
```

## Prompt for Claude Code

```
Add automated demo orchestration to this React ecommerce site:

1. Create a useAutoDemo hook that:
   - Activates when ?demo=true is in the URL
   - Uses a phase state machine (useRef) to track progress
   - Manages timers with phase guards to prevent stale execution
   - Provides notify callbacks for the assistant component
   - Implements simulated typing with random delays
   - Has a clickWhenReady utility for DOM interaction
   - Cleans up all timers on unmount

2. Define a demo flow:
   - Show a "Start Demo" overlay
   - Open the shopping assistant modal
   - Wait for greeting, then auto-type a query
   - Wait for results, then auto-type a refinement
   - Click "Try On" on a specific product
   - Wait for try-on result (with 45s timeout fallback)
   - Click "Add to Cart"
   - Show inline checkout
   - Display closing overlay

3. Add a demo persona with preset profile data.

4. Use data-demo-* attributes on interactive elements
   for reliable DOM targeting.
```
