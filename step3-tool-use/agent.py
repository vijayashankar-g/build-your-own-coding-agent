"""
step3/agent.py — Tools Layer: The LLM Can Now DO Things

What is NEW compared to Step 2:
  + A `Tools` class with real callable actions (run_program, fix_file).
  + The LLM returns a JSON "action" object instead of plain text.
  + We parse that JSON and call the matching tool function.
  + A broken `main.py` is included so you can see the fix tool in action.

What is still MISSING:
  - This runs only ONE action — there is no loop.
  - The agent acts once and stops, even if the fix didn't work.
"""

import json
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Tools — the real-world actions the agent can take
# ---------------------------------------------------------------------------

class Tools:
    """
    A collection of actions the agent can invoke.

    Each method does something real in the world:
      - run_program: executes a Python file and captures its output.
      - fix_file:    rewrites a broken Python file using the LLM.

    The LLM does NOT call these directly — it returns a JSON "action" object
    like {"tool": "fix", "file": "main.py"}, and we dispatch it here.
    """

    def __init__(self):
        self.client = OpenAI()
        self.project_dir = Path("./step3-tool-use").resolve()

        # Stored so fix_file can include recent error context in its prompt
        self.last_stdout = ""
        self.last_stderr = ""

    def dispatch(self, action: dict) -> dict:
        """
        Route an action dict to the correct tool method.

        Args:
            action: e.g. {"tool": "run"} or {"tool": "fix", "file": "main.py"}

        Returns:
            A result dict with keys: stdout, stderr, returncode, success.
        """
        tool = action.get("tool")

        if tool == "run":
            return self.run_program(action.get("file", "main.py"))

        if tool == "fix":
            return self.fix_file(action.get("file"))

        return {"success": False, "stderr": f"Unknown tool: {tool}"}

    def run_program(self, file_name: str) -> dict:
        """Run a Python file and capture stdout/stderr/returncode."""
        path = self.project_dir / file_name
        result = subprocess.run(
            ["python", str(path)],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )

        # Save output so fix_file can reference it later
        self.last_stdout = result.stdout
        self.last_stderr = result.stderr

        # Find the file responsible for the crash by reading the traceback
        failed_file = None
        matches = re.findall(r'File "([^"]+\.py)"', result.stderr)
        if matches:
            failed_file = Path(matches[-1]).name

        success = result.returncode == 0
        print(f"  [run] exit={result.returncode} | {'✅ OK' if success else '❌ FAILED'}")
        if result.stderr:
            print(f"  [run] stderr: {result.stderr.strip()[:200]}")

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "failed_file": failed_file,
            "success": success,
        }

    def fix_file(self, file_name: str) -> dict:
        """Ask the LLM to rewrite a broken Python file."""
        if not file_name:
            return {"success": False, "stderr": "No file specified"}

        path = self.project_dir / file_name
        if not path.exists():
            return {"success": False, "stderr": f"File not found: {file_name}"}

        broken_code = path.read_text()

        # Give the LLM the broken code + the error message so it knows what to fix
        prompt = f"""
You are a Python debugging assistant.

Fix the file below so it runs without errors.

Rules:
- Fix ONLY this file: {file_name}
- Return ONLY the corrected file content, no markdown fences
- Keep changes minimal

File content:
{broken_code}

Error output:
{self.last_stderr}
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        fixed = response.choices[0].message.content.strip()
        # Strip markdown fences if the LLM added them despite instructions
        fixed = re.sub(r"^```python\n", "", fixed)
        fixed = re.sub(r"\n```$", "", fixed)

        path.write_text(fixed)
        print(f"  [fix] Rewrote {file_name}")

        return {"stdout": f"Fixed {file_name}", "stderr": "", "success": True}


# ---------------------------------------------------------------------------
# LLM — asks the model to pick ONE action given the current situation
# ---------------------------------------------------------------------------

class LLM:
    """
    Asks the OpenAI model to decide which tool to call next.

    The model receives a description of the situation and must return a
    JSON object that names the tool and its arguments.
    """

    def __init__(self):
        self.client = OpenAI()

    def decide(self, situation: str) -> dict:
        """
        Given a plain-English description of the situation, return an action.

        Returns:
            A dict like {"tool": "run", "file": "main.py"} or
                        {"tool": "fix", "file": "main.py"}
        """
        prompt = f"""
You are a Python debugging assistant.

Situation:
{situation}

Choose ONE action from the list below and return it as JSON — nothing else.

Available actions:
- {{"tool": "run", "file": "main.py"}}      ← run the program
- {{"tool": "fix", "file": "<filename>"}}   ← fix a broken file
"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content.strip()
        # Extract JSON even if the model wrapped it in extra prose
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        return json.loads(text)


# ---------------------------------------------------------------------------
# Main — one decision, one action, done
# ---------------------------------------------------------------------------

tools = Tools()
llm = LLM()

print("=== Step 3: One-Shot Tool Use ===\n")

# Describe the situation to the LLM
situation = "We have a Python file called main.py that may have bugs. Please run it first."

print("Situation:", situation)

# LLM decides what to do
action = llm.decide(situation)
print("LLM chose action:", action)

# Execute the chosen tool
result = tools.dispatch(action)
print("Result:", json.dumps(result, indent=2))

# If the run failed, ask the LLM to fix it — ONE more action
if not result.get("success") and result.get("failed_file"):
    print("\nProgram failed. Asking LLM to fix it...\n")

    fix_situation = (
        f"Running main.py failed with this error:\n{result['stderr']}\n"
        f"The file that caused the error is: {result['failed_file']}"
    )
    fix_action = llm.decide(fix_situation)
    print("LLM chose action:", fix_action)

    fix_result = tools.dispatch(fix_action)
    print("Fix result:", json.dumps(fix_result, indent=2))
