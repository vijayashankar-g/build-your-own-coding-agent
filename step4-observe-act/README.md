# Step 4 · `step4-observe-act` — One-Shot Agent: Environment + State Tracking

## What Changed from `step3-tool-use`?

| | `step3-tool-use` | `step4-observe-act` |
|---|---|---|
| State storage | Scattered variables | `Environment` class |
| LLM input | Plain English sentence | **JSON state snapshot** |
| Control flow | Hardcoded `if/else` | LLM decides based on state |
| Cycles | 2 (hardcoded) | 2 (driven by state, not code) |

## The Key Insight: Structured State

The `Environment` class acts as the agent's **shared notebook**.  
Every tool writes its result to it. The LLM reads from it.  
Nothing is hardcoded — the LLM decides what to do based on the numbers.

```
env.returncode == None   →  LLM says: "run it"
env.returncode != 0      →  LLM says: "fix main.py"
env.returncode == 0      →  LLM says: "null (done)"
```

## The Observe → Think → Act Cycle

```
┌──────────────────────────────────────────────────┐
│                    Cycle N                        │
│                                                   │
│  1. OBSERVE   env.snapshot() → JSON string        │
│       ↓                                           │
│  2. THINK     llm.decide(snapshot) → action dict  │
│       ↓                                           │
│  3. ACT       tools.dispatch(action) → observation│
│       ↓                                           │
│  4. UPDATE    env.update(observation)             │
└──────────────────────────────────────────────────┘
```

## How to Run

```bash
python agent.py
```

## What's Missing (added in the next step)

- ❌ Still only 2 cycles — hardcoded in the script
- ❌ If the fix produces a new bug, we stop anyway
- ❌ No max-step safety net

👉 **Next: `step5-agent-loop`** — Replace the hardcoded cycles with a **real loop** and add `max_steps` protection.
