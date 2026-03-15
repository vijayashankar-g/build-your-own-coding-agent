# Step 2 · `step2-chat-memory` — System Prompt + Conversation History

## What Changed from `step1-hello-llm`?

| | `step1-hello-llm` | `step2-chat-memory` |
|---|---|---|
| Turns | 1 (one question) | Many (back-and-forth loop) |
| Memory | ❌ None | ✅ `messages` list grows each turn |
| System prompt | ❌ None | ✅ Sets the bot's role |
| Structure | Bare script | `ChatBot` class |

## The Key Idea: The `messages` List

The OpenAI API is **stateless** — it remembers nothing between calls.  
To give it memory, you manually send the **entire conversation history** every time.

```
Turn 1:  [system, user]                    → reply 1
Turn 2:  [system, user, assistant, user]   → reply 2
Turn 3:  [system, user, assistant, user, assistant, user] → reply 3
```

Each role explained:

| Role | Who wrote it | Purpose |
|---|---|---|
| `system` | You (developer) | Set personality, rules, context |
| `user` | Human typing | The question or instruction |
| `assistant` | The LLM | Its previous replies |

## How to Run

```bash
python agent.py
```

## Example Session

```
=== Python Tutor Chat ===
Type 'quit' to exit.

You: What is a list comprehension?

Bot: A list comprehension is a compact way to create a list...
     squares = [x**2 for x in range(5)]  # [0, 1, 4, 9, 16]

You: Can you show me a filter example?

Bot: Sure! Here's how you filter even numbers...   ← remembers context!
```

## What's Missing (added in the next step)

- ❌ The LLM can only *talk* — it can't *do* anything
- ❌ No way to run code, read files, or take real actions

👉 **Next: `step3-tool-use`** — Add a **Tools layer** so the LLM can execute real actions.
