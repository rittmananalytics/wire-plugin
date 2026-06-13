# Feature: LLM Chat with Tool Calling

## Overview

Build a conversational shopping interface where an LLM (like Gemini or GPT) can autonomously decide when to search for products using tool/function calling. Unlike a simple chatbot, this pattern gives the LLM a "toolbox" — it can have a normal conversation, and when the user's intent requires product data, it calls the search tool and weaves the results into a natural response.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Chat UI     │────▸│  Coordinator     │────▸│  LLM (Gemini/GPT)   │
│  (React)     │◂────│  Edge Function   │◂────│  with tool_calls     │
└──────────────┘     └──────────────────┘     └─────────────────────┘
                              │                         │
                              │   ┌─────────────────────┘
                              ▼   ▼
                     ┌──────────────────┐
                     │  Search Function │
                     │  /semantic-search│
                     └──────────────────┘
```

## Implementation Steps

### 1. Define Tools for the LLM

Tell the LLM what tools it has access to using the OpenAI-compatible function calling format:

```typescript
const TOOLS = [
  {
    type: "function",
    function: {
      name: "search_products",
      description: "Search the product catalog using semantic search. Use when the user wants to find, browse, or buy products.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "A descriptive search query. Convert conversational intent into product-focused terms.",
          },
        },
        required: ["query"],
      },
    },
  },
];
```

### 2. Coordinator Edge Function

This is the orchestrator — it calls the LLM, handles tool calls, and returns the final response.

```typescript
// /functions/chat-coordinator
export async function handler(req) {
  const { messages } = await req.json();

  const SYSTEM_PROMPT = `You are a friendly shopping assistant for [STORE_NAME].
  You can search for products using the search_products tool.
  Only search when the user expresses intent to find or buy products.
  For greetings or general chat, respond naturally without searching.`;

  // Step 1: First LLM call (may include tool_calls)
  const completion = await llm.chat({
    model: "gemini-2.5-flash",
    messages: [{ role: "system", content: SYSTEM_PROMPT }, ...messages],
    tools: TOOLS,
    tool_choice: "auto",
  });

  const choice = completion.choices[0];

  // Step 2: If no tool calls, return text directly
  if (!choice.message.tool_calls?.length) {
    return { type: "text", content: choice.message.content };
  }

  // Step 3: Execute tool calls
  const toolCall = choice.message.tool_calls[0];
  const { query } = JSON.parse(toolCall.function.arguments);
  const searchResults = await searchProducts(query);

  // Step 4: Second LLM call with tool results
  const followUp = await llm.chat({
    model: "gemini-2.5-flash",
    messages: [
      ...previousMessages,
      choice.message,           // assistant message with tool_call
      {
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(searchResults),
      },
    ],
  });

  return {
    type: "products",
    content: followUp.choices[0].message.content,
    products: searchResults,
    search_query: query,
  };
}
```

### 3. The Two-Call Pattern

This is the key architectural pattern:

```
User: "I need something for cold weather rides"
                    │
                    ▼
        ┌───────────────────────┐
        │   1st LLM Call        │
        │   → Decides to call   │
        │     search_products   │
        │     query: "thermal   │
        │     cycling gear"     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Execute Tool        │
        │   → Call semantic     │
        │     search endpoint   │
        │   → Get 6 products    │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   2nd LLM Call        │
        │   → Given products,   │
        │     write a natural   │
        │     response about    │
        │     WHY each fits     │
        └───────────────────────┘
```

### 4. React Chat Interface

```tsx
function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);

  const sendMessage = async (text: string) => {
    const userMsg = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);

    const { data } = await supabase.functions.invoke("chat-coordinator", {
      body: { messages: [...messages, userMsg] },
    });

    setMessages(prev => [...prev, {
      role: "assistant",
      content: data.content,
      products: data.products || [],
    }]);
  };

  return (
    <div>
      {messages.map(msg => (
        <div key={msg.id}>
          <p>{msg.content}</p>
          {msg.products?.map(p => <ProductCard key={p.id} product={p} />)}
        </div>
      ))}
      <ChatInput onSend={sendMessage} />
    </div>
  );
}
```

## Why Tool Calling > Prompt Engineering

| Approach | Pros | Cons |
|----------|------|------|
| **Tool calling** | LLM decides when to search; structured output; composable | Slightly more complex |
| **Always search** | Simple | Wastes API calls on greetings, irrelevant queries |
| **Keyword detection** | Fast | Brittle; misses nuanced intent |
| **Prompt-only JSON** | No extra API | Unreliable parsing; hallucinated products |

## Extending with More Tools

```typescript
const EXTENDED_TOOLS = [
  searchProductsTool,
  {
    type: "function",
    function: {
      name: "check_stock",
      description: "Check stock availability for a specific product variant",
      parameters: { ... },
    },
  },
  {
    type: "function",
    function: {
      name: "apply_discount",
      description: "Apply a discount code to the current cart",
      parameters: { ... },
    },
  },
];
```

## Prompt for Claude Code

```
Build an LLM-powered chat with tool calling for this ecommerce site:

1. Create a coordinator edge function at /functions/chat that:
   - Accepts { messages[] } as conversation history
   - Defines a search_products tool for the LLM
   - Makes a first LLM call with tools enabled
   - If tool_calls are returned, executes them against the search endpoint
   - Makes a second LLM call with tool results for a natural response
   - Returns { type, content, products[], search_query }
   - Handles both text-only and product responses

2. Create a ChatInterface React component that:
   - Shows message bubbles for user and assistant
   - Renders product cards inline when products are returned
   - Maintains conversation history across turns
   - Has a text input with send button

3. Use [MODEL] via the AI gateway. Set system prompt to be
   a knowledgeable assistant for [STORE_TYPE].
```
