"""
step5/agent.py — Full Agentic Loop: Observe → Think → Act → Repeat

What is NEW compared to Step 4:
  + A `while` loop replaces the two hardcoded cycles.
  + `Environment` now tracks `step` and `max_steps` to prevent infinite loops.
  + `Environment.is_done()` is the single exit condition for the loop.
  + The "finish" action lets the LLM explicitly signal it is satisfied.
  + A multi-file project (main.py + helper.py) shows the agent fixing
    failures across multiple files over multiple steps.

This is the COMPLETE agent — all previous steps built up to this.
"""

import json
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ---------------------------------------------------------------------------
# Environment — the agent's memory and loop controller
# ---------------------------------------------------------------------------

class Environment:
    """
    Central state object for the entire debugging session.

    Tracks:
      - Execution results (stdout, stderr, returncode, failed_file)
      - Loop progress (step counter)
      - Termination conditions (done flag, max_steps guard)
    """

    def __init__(self, entry_file="main.py", max_steps=6):
        self.entry_file = entry_file
        self.max_steps = max_steps       # Hard limit — prevents infinite loops
        self.step = 0
        self.done = False
        self.stdout = ""
        self.stderr = ""
        self.returncode = None
        self.failed_file = None

    def update(self, observation: dict):
        """
        Absorb the result of a tool call into the environment.

        The `done` field in the observation lets the agent signal "I'm finished".
        The step counter advances, and we force-stop if max_steps is reached.
        """
        self.stdout = observation.get("stdout", self.stdout)
        self.stderr = observation.get("stderr", self.stderr)
        self.returncode = observation.get("returncode", self.returncode)
        self.failed_file = observation.get("failed_file", self.failed_file)
        self.done = observation.get("done", False)
        self.step += 1

        # Safety net: stop even if the LLM never says "finish"
        if self.step >= self.max_steps:
            self.done = True

    def snapshot(self) -> str:
        """Serialize state to JSON so the LLM can read it."""
        return json.dumps({
            "entry_file": self.entry_file,
            "step": self.step,
            "max_steps": self.max_steps,
            "returncode": self.returncode,
            "failed_file": self.failed_file,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }, indent=2)

    def is_done(self) -> bool:
        """Return True when the loop should stop."""
        return self.done


# ---------------------------------------------------------------------------
# Tools — every action the agent can take
# ---------------------------------------------------------------------------

class Tools:
    """
    Three tools available to the agent:

      run    — execute the entry file and observe the result
      fix    — rewrite a broken file using the LLM
      finish — mark the task as done and stop the loop
    """

    def __init__(self, env: Environment):
        self.env = env
        self.client = OpenAI()
        self.project_dir = Path("./step5-agent-loop").resolve()

    def dispatch(self, action: dict) -> dict:
        """Route an action dict to the correct method."""
        tool = action.get("tool")

        if tool == "run":
            return self.run_program()
        if tool == "fix":
            return self.fix_file(action.get("file"))
        if tool == "finish":
            return {"done": True, "stdout": "Agent finished successfully."}

        return {"done": True, "stderr": f"Unknown tool: {tool}"}

    def run_program(self) -> dict:
        """
        Execute the entry Python file as a subprocess.

        Returns an observation dict with stdout, stderr, returncode,
        failed_file (parsed from the traceback), and done=True on success.
        """
        result = subprocess.run(
            ["python", self.env.entry_file],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )

        # Walk the traceback to find the deepest user file that crashed
        failed_file = None
        matches = re.findall(r'File "([^"]+\.py)"', result.stderr)
        if matches:
            failed_file = Path(matches[-1]).name

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "failed_file": failed_file,
            "done": result.returncode == 0,  # success → stop the loop
        }

    def fix_file(self, file_name: str) -> dict:
        """
        Ask the LLM to repair a broken Python file and overwrite it on disk.

        The LLM gets the file content + recent error output so it has full context.
        After writing the fix, done=False so the loop will re-run the program
        to verify the fix actually worked.
        """
        if not file_name:
            return {"done": True, "stderr": "No file specified"}

        path = self.project_dir / file_name
        if not path.exists():
            return {"done": True, "stderr": f"File not found: {file_name}"}

        broken_code = path.read_text()

        prompt = f"""
You are a Python debugging assistant.

Fix the file below so the whole program runs without errors.

Rules:
- Fix ONLY this file: {file_name}
- Return ONLY the corrected file content, no markdown fences
- Keep changes minimal

File content:
{broken_code}

Latest stderr:
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
            "returncode": None,  # Reset — we don't know if it works until we run again
            "done": False,       # Keep looping — next step should re-run the program
        }


# ---------------------------------------------------------------------------
# LLM — the decision-maker
# ---------------------------------------------------------------------------

class LLM:
    """
    Wraps the OpenAI API call for action selection.

    The system_prompt defines the agent's overall mission.
    The state snapshot gives it the current situation.
    It must return a JSON action object — nothing else.
    """

    def __init__(self, system_prompt: str):
        self.client = OpenAI()
        self.system_prompt = system_prompt

    def decide(self, state_snapshot: str) -> dict:
        """
        Given the current environment state, decide the next action.

        Returns a dict like:
          {"tool": "run"}
          {"tool": "fix", "file": "helper.py"}
          {"tool": "finish"}
        """
        prompt = f"""
{self.system_prompt}

Current state:
{state_snapshot}

Available actions (return ONE as JSON, nothing else):
1. {{"tool": "run"}}
2. {{"tool": "fix", "file": "<failed_file>"}}
3. {{"tool": "finish"}}

Decision rules:
- If returncode is null → run the program first.
- If returncode is non-zero and failed_file exists → fix that file.
- If returncode is 0 → finish.
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        return json.loads(text)


# ---------------------------------------------------------------------------
# Entry point — wire everything up and run the agentic loop
# ---------------------------------------------------------------------------

env = Environment(entry_file="main.py", max_steps=8)
tools = Tools(env)
llm = LLM("You are an agent that autonomously debugs Python programs using tools.")

print("=== Agent Started ===\n")

# ── The Agentic Loop ──────────────────────────────────────────────────────
#
#   Each iteration is one full Observe → Think → Act → Update cycle.
#   The loop continues until:
#     (a) A tool sets done=True  (program ran successfully, or "finish" called)
#     (b) max_steps is reached   (safety net against infinite loops)
#
while not env.is_done():
    print(f"─── Step {env.step + 1} / {env.max_steps} ───")

    # 1. OBSERVE: what is the current state?
    print("STATE:", env.snapshot())

    # 2. THINK: ask the LLM to pick the next action
    action = llm.decide(env.snapshot())
    print("ACTION:", json.dumps(action))

    # 3. ACT: execute the tool
    observation = tools.dispatch(action)
    print("OBSERVATION:", json.dumps(observation, indent=2))

    # 4. UPDATE: merge the result into the environment
    env.update(observation)
    print()

print("=== Agent Finished ===")
print(env.snapshot())
