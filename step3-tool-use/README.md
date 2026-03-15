# Step 3 · `step3-tool-use` — Tools Layer: The LLM Can Now DO Things

## What Changed from `step2-chat-memory`?

| | `step2-chat-memory` | `step3-tool-use` |
|---|---|---|
| LLM output | Plain text reply | JSON **action** object |
| Real actions | ❌ None | ✅ Run code, fix files |
| Structure | `ChatBot` class | `Tools` + `LLM` classes |
| Turns | Many (human loop) | 2 max (run → maybe fix) |

## The Big Idea: Actions as JSON

Instead of returning a human-readable answer, the LLM now returns structured JSON:

```json
{"tool": "run", "file": "main.py"}
```

or

```json
{"tool": "fix", "file": "main.py"}
```

We **parse** that JSON and **dispatch** it to the right Python function.

```
LLM decides  ──JSON action──▶  Tools.dispatch()  ──calls──▶  run_program() / fix_file()
```

## Architecture

```
┌─────────┐    situation     ┌─────────┐    action JSON    ┌─────────┐
│  You    │ ───────────────▶ │   LLM   │ ────────────────▶ │  Tools  │
│ (main)  │                  │ decides │                   │ executes│
└─────────┘                  └─────────┘                   └─────────┘
```

## Included Files

| File | Purpose |
|---|---|
| `agent.py` | The agent code |
| `main.py` | Intentionally broken Python file (missing `:` on `def`) |

## How to Run

```bash
python agent.py
```

Watch it:
1. Ask the LLM what to do → LLM says "run it"
2. Run `main.py` → crashes with `SyntaxError`
3. Ask the LLM again → LLM says "fix main.py"
4. Fix is applied → done (one round)

## What's Missing (added in the next step)

- ❌ After fixing, we never verify the fix actually worked
- ❌ Only 2 hardcoded steps — not a real loop

👉 **Next: `step4-observe-act`** — Make it a **real single-pass agent** with an Environment state object.
