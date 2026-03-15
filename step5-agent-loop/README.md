# Step 5 · `step5-agent-loop` — Full Agentic Loop: Observe → Think → Act → Repeat

## What Changed from `step4-observe-act`?

| | `step4-observe-act` | `step5-agent-loop` |
|---|---|---|
| Cycles | 2 hardcoded `if` blocks | `while` loop — runs until done |
| Safety net | ❌ None | ✅ `max_steps` guard |
| Stop condition | End of script | `env.is_done()` |
| "I'm done" signal | ❌ Always stops after 2 | ✅ LLM calls `{"tool": "finish"}` |
| Test project | Single file | Two files (`main.py` + `helper.py`) |

## This Is the Complete Agent

All previous steps were building blocks. Step 5 combines them all:

```
step1-hello-llm    → bare API call
step2-chat-memory  + conversation history & system prompt
step3-tool-use     + Tools layer (run / fix)
step4-observe-act  + Environment (structured state)
step5-agent-loop   + while loop + max_steps + finish action  ✅
```

## The Full Loop

```
┌─────────────────────────────────────────────────────────┐
│                while not env.is_done()                   │
│                                                         │
│  1. OBSERVE   env.snapshot()  ──────────────────────┐   │
│                                                     ▼   │
│  2. THINK     llm.decide(snapshot)  →  action JSON  │   │
│                                                     ▼   │
│  3. ACT       tools.dispatch(action)  →  observation│   │
│                                                     ▼   │
│  4. UPDATE    env.update(observation)               │   │
│               ├─ done=True?  ──────────── exit loop │   │
│               └─ step >= max_steps? ───── exit loop │   │
└─────────────────────────────────────────────────────────┘
```

## Included Files

| File | Purpose |
|---|---|
| `agent.py` | The complete agentic loop |
| `main.py` | Entry point — calls `helper.multiply()` |
| `helper.py` | **Broken** — returns a string instead of a number |

## Expected Step Trace

```
Step 1  → ACTION: run         → RESULT: TypeError (wrong type from helper.py)
Step 2  → ACTION: fix helper.py → RESULT: helper.py rewritten
Step 3  → ACTION: run         → RESULT: returncode=0 ✅ → done=True, loop exits
```

## How to Run

```bash
python agent.py
```

## Key Concepts Summary

| Concept | Where it lives |
|---|---|
| API call | `LLM.decide()` |
| Conversation memory | `messages` list (Step 2) |
| Structured actions | JSON `{"tool": ...}` |
| Real-world execution | `Tools.run_program()` |
| Error detection | traceback regex in `run_program()` |
| Automatic repair | `Tools.fix_file()` |
| Shared state | `Environment` class |
| Loop control | `env.is_done()` + `env.max_steps` |
