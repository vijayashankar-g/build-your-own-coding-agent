# Step 1 · `step1-hello-llm` — Skeleton: The Bare Minimum

## What Is This?

The very first building block of any AI agent: **one question in, one answer out**.

No loop. No memory. No tools. Just a direct call to the OpenAI API.

```
[You] ──question──▶ [OpenAI LLM] ──answer──▶ [Print]
```

## What You Learn

| Concept | Where |
|---|---|
| Loading API keys safely with `.env` | `load_dotenv()` |
| Creating an `OpenAI` client | `client = OpenAI()` |
| Reading a CLI argument **or** prompting interactively | `sys.argv` + `input()` |
| Sending a chat message | `client.chat.completions.create(...)` |
| Reading the reply | `response.choices[0].message.content` |

## How to Run

1. Create a `.env` file in this folder (or the project root):
   ```
   OPENAI_API_KEY=sk-...
   ```

2. Install dependencies (only needed once):
   ```bash
   pip install openai python-dotenv
   ```

3. Run it — two ways:

   **Pass the question as a CLI argument:**
   ```bash
   python agent.py "What is the speed of light?"
   ```

   **Let it prompt you interactively:**
   ```bash
   python agent.py
   # Ask anything: What is the speed of light?
   ```

## Expected Output

```
Question: What is the speed of light?
Answer:   The speed of light in a vacuum is approximately 299,792 km/s.
```

## What's Missing (added in the next step)

- ❌ Multi-turn conversation (chat history / memory)
- ❌ A system prompt to set the assistant's behaviour
- ❌ Any kind of loop

👉 **Next: `step2-chat-memory`** — Add a proper chat wrapper with a system prompt and conversation history.
