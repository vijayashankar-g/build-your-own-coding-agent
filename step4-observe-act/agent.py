"""
step4/agent.py — One-Shot Agent: Environment + State Tracking

What is NEW compared to Step 3:
  + An `Environment` class that holds all execution state in one place.
  + The agent runs ONE complete decide → act → observe cycle (not hardcoded if/else).
  + The LLM receives a structured JSON state snapshot instead of a plain sentence.
  + Observations from tools flow back into the Environment automatically.

What is still MISSING:
  - Still only ONE pass: run → fix → stop.
  - If the fix introduced a new bug, we won't catch it.
  - No loop yet — that comes in Step 5.
"""

import json
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ---------------------------------------------------------------------------
# Environment — the agent's shared state / memory
# ---------------------------------------------------------------------------

class Environment:
    """
    Holds everything the agent knows about the current debugging session.

    Think of it as the agent's "notebook": it records what happened after
    each action so the LLM always has up-to-date context.
    """

    def __init__(self, entry_file="main.py"):
        self.entry_file = entry_file
        self.stdout = ""        # Output from the last program run
        self.stderr = ""        # Error output from the last program run
        self.returncode = None  # Exit code (0 = success, non-zero = failure)
        self.failed_file = None # Which file the traceback points to

    def update(self, observation: dict):
        """Merge a tool's result into the current state."""
        self.stdout = observation.get("stdout", self.stdout)
        self.stderr = observation.get("stderr", self.stderr)
        self.returncode = observation.get("returncode", self.returncode)
        self.failed_file = observation.get("failed_file", self.failed_file)

    def snapshot(self) -> str:
        """
        Return the current state as a JSON string.

        This is what gets sent to the LLM so it can reason about
        what happened and decide the next action.
        """
        return json.dumps({
            "entry_file": self.entry_file,
            "returncode": self.returncode,
            "failed_file": self.failed_file,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }, indent=2)


# ---------------------------------------------------------------------------
# Tools — real-world actions
# ---------------------------------------------------------------------------

class Tools:
    """
    Executes actions and returns observations that update the Environment.

    The key difference from Step 3: every method now returns a standardized
    observation dict that feeds directly into Environment.update().
    """

    def __init__(self, env: Environment):
        self.env = env
        self.client = OpenAI()
        self.project_dir = Path("./step4-observe-act").resolve()

    def dispatch(self, action: dict) -> dict:
        """Route an action dict to the correct tool method."""
        tool = action.get("tool")

        if tool == "run":
            return self.run_program()
        if tool == "fix":
            return self.fix_file(action.get("file"))

        return {"stderr": f"Unknown tool: {tool}", "returncode": -1}

    def run_program(self) -> dict:
        """Execute the entry file and return an observation dict."""
        result = subprocess.run(
            ["python", self.env.entry_file],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )

        failed_file = None
        matches = re.findall(r'File "([^"]+\.py)"', result.stderr)
        if matches:
            failed_file = Path(matches[-1]).name

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "failed_file": failed_file,
        }

    def fix_file(self, file_name: str) -> dict:
        """Ask the LLM to rewrite a broken file, then save it."""
        if not file_name:
            return {"stderr": "No file specified", "returncode": -1}

        path = self.project_dir / file_name
        if not path.exists():
            return {"stderr": f"File not found: {file_name}", "returncode": -1}

        broken_code = path.read_text()

        prompt = f"""
You are a Python debugging assistant.

Fix the file so it runs without errors.

Rules:
- Fix ONLY this file: {file_name}
- Return ONLY the corrected file content, no markdown fences
- Keep changes minimal

File content:
{broken_code}

Error output:
{self.env.stderr}
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        fixed = response.choices[0].message.content.strip()
        fixed = re.sub(r"^```python\n", "", fixed)
        fixed = re.sub(r"\n```$", "", fixed)

        path.write_text(fixed)

        return {
            "stdout": f"Fixed {file_name}",
            "stderr": "",
            "returncode": 0,    # Assume the fix is applied; re-run to confirm
            "failed_file": None,
        }


# ---------------------------------------------------------------------------
# LLM — decides what action to take given the current Environment snapshot
# ---------------------------------------------------------------------------

class LLM:
    """
    The decision-maker.  It reads the Environment snapshot and returns an action.

    The LLM now receives a rich JSON state (not just a plain sentence), which
    makes its decisions more reliable and auditable.
    """

    def __init__(self):
        self.client = OpenAI()

    def decide(self, state_snapshot: str) -> dict:
        """
        Given the current Environment snapshot, return the next action as JSON.
        """
        prompt = f"""
You are a Python debugging agent.

Current state:
{state_snapshot}

Choose ONE action and return it as JSON — nothing else.

Available actions:
- {{"tool": "run"}}                         ← run the entry file
- {{"tool": "fix", "file": "<filename>"}}   ← fix the file that caused the error

Rules:
- If returncode is null, run the program first.
- If returncode is non-zero and failed_file exists, fix that file.
- If returncode is 0, the program succeeded — do nothing (return null).
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content.strip()
        if text.lower() == "null":
            return None

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        return json.loads(text)


# ---------------------------------------------------------------------------
# Main — one full Observe → Think → Act → Observe cycle
# ---------------------------------------------------------------------------

env = Environment(entry_file="main.py")
tools = Tools(env)
llm = LLM()

print("=== Step 4: One-Shot Agent ===\n")

# ── Cycle 1: Observe ──────────────────────────────────────────────
print("── Cycle 1 ──")
print("STATE:", env.snapshot())

# ── Think ────────────────────────────────────────────────────────
action = llm.decide(env.snapshot())
print("ACTION:", action)

# ── Act ──────────────────────────────────────────────────────────
observation = tools.dispatch(action)
print("OBSERVATION:", json.dumps(observation, indent=2))

# ── Update state ─────────────────────────────────────────────────
env.update(observation)

# ── Cycle 2 (only if the first run failed) ────────────────────────
if env.returncode != 0:
    print("\n── Cycle 2 ──")
    print("STATE:", env.snapshot())

    action = llm.decide(env.snapshot())
    print("ACTION:", action)

    if action:
        observation = tools.dispatch(action)
        print("OBSERVATION:", json.dumps(observation, indent=2))
        env.update(observation)

print("\n=== Final State ===")
print(env.snapshot())
