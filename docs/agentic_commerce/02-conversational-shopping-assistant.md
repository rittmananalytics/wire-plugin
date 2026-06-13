# Feature: Conversational Shopping Assistant

## Overview

A chat-based shopping interface where users describe what they need in natural language and receive curated product recommendations through a multi-turn conversation. The assistant asks clarifying questions, adapts to feedback, and supports add-to-cart and checkout — all within the chat window.

## Architecture

```
┌────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Chat Modal    │────▸│  Conversational API   │────▸│  Search Engine   │
│  (React)       │◂────│  (Edge Function)      │◂────│  (Retail / LLM)  │
└────────────────┘     └──────────────────────┘     └──────────────────┘
       │                        │
       ▼                        ▼
┌────────────────┐     ┌──────────────────────┐
│  Cart Store    │     │  Product API         │
│  (Zustand)     │     │  (Shopify / etc)     │
└────────────────┘     └──────────────────────┘
```

## Implementation Steps

### 1. Conversation Edge Function

Create a backend that manages conversational state with an AI model or conversational commerce API.

```typescript
// /functions/shopping-assistant
export async function handler(req) {
  const { message, conversationId, context } = await req.json();

  // Option A: Use a Conversational Commerce API (e.g. Google Retail)
  const response = await retailApi.conversationalSearch({
    query: message,
    conversationId,
    userLabels: context?.preferences || {},
  });

  // Option B: Use an LLM with tool calling
  const response = await llm.chat({
    messages: [...history, { role: "user", content: message }],
    tools: [{ name: "search_products", ... }],
  });

  return {
    reply: response.text,
    products: response.products || [],
    conversationId: response.conversationId,
    intent: response.intent, // e.g. "PRODUCT_SEARCH", "REFINEMENT", "CHECKOUT"
  };
}
```

### 2. Chat Modal Component

Build a full-featured chat UI with message bubbles, product cards, and action buttons.

```tsx
function ShoppingAssistant({ isOpen, onClose }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);

  const sendMessage = async (text: string) => {
    // Add user message to UI
    setMessages(prev => [...prev, { role: "user", content: text }]);

    // Call backend
    const { data } = await supabase.functions.invoke("shopping-assistant", {
      body: { message: text, conversationId },
    });

    // Add assistant response
    setMessages(prev => [...prev, {
      role: "assistant",
      content: data.reply,
      products: data.products,
    }]);

    setConversationId(data.conversationId);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <MessageList messages={messages} />
      <ChatInput value={input} onChange={setInput} onSend={sendMessage} />
    </Modal>
  );
}
```

### 3. Product Cards in Chat

Render interactive product cards inline within the conversation:

```tsx
function ChatProductCard({ product, onAddToCart, onTryOn }) {
  return (
    <div className="flex gap-3 p-3 border rounded-lg">
      <img src={product.imageUrl} className="w-20 h-20 object-cover rounded" />
      <div className="flex-1">
        <h4 className="font-medium">{product.title}</h4>
        <p className="text-sm text-muted-foreground">{product.price}</p>
        <div className="flex gap-2 mt-2">
          <button onClick={() => onAddToCart(product)}>Add to Cart</button>
          {onTryOn && <button onClick={() => onTryOn(product)}>Try On</button>}
        </div>
      </div>
    </div>
  );
}
```

### 4. Shortcut Pills

Add quick-action buttons that appear at conversation start to reduce typing:

```tsx
const SHORTCUTS = [
  { label: "🎁 Gift ideas", query: "Help me find a gift for a cyclist" },
  { label: "☀️ Summer gear", query: "What's good for hot weather rides?" },
  { label: "🔥 Best sellers", query: "Show me your most popular items" },
];
```

### 5. Intent-Aware UI Adaptation

Adapt the UI based on the assistant's detected intent:

```tsx
// When intent is PRODUCT_SEARCH → show product grid, minimal text
// When intent is REFINEMENT → show text + refined products
// When intent is CHECKOUT → show cart summary + checkout button
// When intent is GENERAL → show text only, no products
```

### 6. Inline Checkout

Allow users to complete purchase without leaving the chat:

```tsx
function InlineChatCheckout({ cartItems, onComplete }) {
  // Render a payment form (Stripe Elements, etc.) inside the modal
  // On success, show confirmation and call onComplete()
}
```

## Conversation Design Principles

1. **Greeting** — Start with a personalised hello if user data is available
2. **Qualify** — Ask 1-2 clarifying questions before searching
3. **Recommend** — Show 3-6 products with brief explanations
4. **Adapt** — Listen to feedback ("too formal", "cheaper") and refine
5. **Convert** — Offer add-to-cart and checkout when intent is clear

## Prompt for Claude Code

```
Build a conversational shopping assistant for this React ecommerce site:

1. Create an edge function at /functions/shopping-assistant that:
   - Accepts { message, conversationId } JSON body
   - Maintains conversation state across turns
   - Uses [LLM or Conversational API] to understand intent
   - Returns { reply, products[], conversationId, intent }
   - Supports intents: PRODUCT_SEARCH, REFINEMENT, GENERAL, CHECKOUT

2. Create a ShoppingAssistant modal component that:
   - Opens as a centered modal over the page
   - Shows a chat interface with message bubbles
   - Renders product cards inline when products are returned
   - Has shortcut pills for common queries
   - Includes add-to-cart buttons on product cards
   - Shows a checkout button when items are in cart
   - Adapts layout based on intent type

3. Add entry points:
   - A "Shopping Assistant" button in the hero section
   - Keyboard shortcut (Cmd+K) to open
   - Floating action button on mobile

4. Integrate with the existing cart store (Zustand).
```
