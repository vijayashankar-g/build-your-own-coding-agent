"""
agent.py - A simple agentic loop that autonomously debugs Python programs.

The agent follows a Observe → Think → Act loop:
  1. Observe: Render the current environment state (stdout, stderr, return code, etc.)
  2. Think:   Ask an LLM to decide the next action based on the state.
  3. Act:     Execute the chosen tool (run the program or fix a file).

The loop continues until the program runs successfully or the max step limit is reached.
"""

import json
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from a .env file (e.g., OPENAI_API_KEY)
load_dotenv()


class Environment:
    """
    Tracks the current state of the debugging session.

    This acts as the agent's "memory" — it holds the program's last execution
    results (stdout, stderr, return code) and controls when the loop should stop.
    """

    def __init__(self, entry_file="main.py", max_steps=6):
        """
        Args:
            entry_file: The Python file to run and debug.
            max_steps:  Maximum number of agent steps before giving up.
        """
        self.entry_file = entry_file
        self.max_steps = max_steps
        self.step = 0           # Tracks how many steps have been taken
        self.done = False       # Flag to signal the loop should stop
        self.stdout = ""        # Captured standard output from the last run
        self.stderr = ""        # Captured standard error from the last run
        self.returncode = None  # Exit code from the last run (0 = success)
        self.failed_file = None # The Python file that caused the error, if any

    def render_state(self):
        """
        Serialize the current environment state to a JSON string.

        This snapshot is passed to the LLM so it can reason about what happened
        and decide the next action.
        """
        return json.dumps({
            "entry_file": self.entry_file,
            "step": self.step,
            "max_steps": self.max_steps,
            "returncode": self.returncode,
            "failed_file": self.failed_file,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }, indent=2)

    def update(self, observation):
        """
        Update the environment state after a tool has been executed.

        Args:
            observation: A dict returned by the tool containing keys like
                         stdout, stderr, returncode, failed_file, and done.
        """
        self.stdout = observation.get("stdout", self.stdout)
        self.stderr = observation.get("stderr", self.stderr)
        self.returncode = observation.get("returncode", self.returncode)
        self.failed_file = observation.get("failed_file", self.failed_file)
        self.done = observation.get("done", False)
        self.step += 1

        # Force stop if the agent has reached the maximum allowed steps
        if self.step >= self.max_steps:
            self.done = True

    def is_done(self):
        """Return True if the agent loop should terminate."""
        return self.done


class Tools:
    """
    Executes actions chosen by the LLM.

    Available tools:
      - "run":    Execute the entry Python file and capture its output.
      - "fix":    Ask an LLM to repair a specific Python file that has errors.
      - "finish": Signal that the task is complete.
    """

    def __init__(self, env):
        """
        Args:
            env: The shared Environment instance used to read current state.
        """
        self.env = env
        self.client = OpenAI()                    # Reuse a single OpenAI client instance
        self.project_dir = Path(".").resolve()    # Working directory for running files

    def run(self, action):
        """
        Dispatch the action chosen by the LLM to the appropriate tool method.

        Args:
            action: A dict with at least a "tool" key, e.g. {"tool": "fix", "file": "main.py"}.

        Returns:
            An observation dict with execution results.
        """
        tool = action.get("tool")

        if tool == "run":
            return self.run_program()

        if tool == "fix":
            return self.fix_file(action.get("file"))

        if tool == "finish":
            return {"done": True}

        # Fallback if the LLM returns an unrecognized tool name
        return {"done": True, "stderr": f"Unknown tool: {tool}"}

    def run_program(self):
        """
        Execute the entry Python file in a subprocess and capture its output.

        Parses stderr to identify which file caused the failure, so the agent
        can target the correct file in a subsequent "fix" action.

        Returns:
            Observation dict with stdout, stderr, returncode, failed_file, and done.
        """
        result = subprocess.run(
            ["python", self.env.entry_file],
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )

        # Extract the last Python filename mentioned in the traceback (most likely culprit)
        failed_file = None
        matches = re.findall(r'File "([^"]+\.py)"', result.stderr)
        if matches:
            failed_file = Path(matches[-1]).name

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "failed_file": failed_file,
            "done": result.returncode == 0,  # done=True only when the program succeeds
        }

    def fix_file(self, file_name):
        """
        Use an LLM to automatically repair a Python file that contains errors.

        Reads the current file content, sends it along with the latest stdout/stderr
        to the LLM, and writes the corrected code back to disk.

        Args:
            file_name: Name of the file to fix (relative to project_dir).

        Returns:
            Observation dict indicating the file was updated.
        """
        if not file_name:
            return {"done": True, "stderr": "No file provided to fix"}

        path = self.project_dir / file_name
        if not path.exists():
            return {"done": True, "stderr": f"File not found: {file_name}"}

        code = path.read_text()

        # Build a focused prompt: give the LLM the broken code + error context
        prompt = f"""
You are a Python debugging agent.

Fix the target file so the whole program runs successfully.

Rules:
- Fix ONLY this file: {file_name}
- Return ONLY the full corrected file content
- No markdown fences
- Keep changes minimal

Current file content:
{code}

Latest stdout:
{self.env.stdout}

Latest stderr:
{self.env.stderr}
"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        fixed_code = response.choices[0].message.content.strip()

        # Strip any accidental markdown code fences the LLM may have added
        fixed_code = re.sub(r"^```python\n", "", fixed_code)
        fixed_code = re.sub(r"\n```$", "", fixed_code)

        # Overwrite the file with the corrected code
        path.write_text(fixed_code)

        return {
            "stdout": f"Updated {file_name}",
            "stderr": "",
            "done": False,  # After fixing, the loop should run the program again to verify
        }


class LLM:
    """
    The agent's "brain" — decides what action to take next based on the current state.

    Wraps an OpenAI chat completion call and parses the JSON action from the response.
    """

    def __init__(self, system_prompt):
        """
        Args:
            system_prompt: A high-level description of the agent's role and goal.
        """
        self.client = OpenAI()
        self.system_prompt = system_prompt

    def run(self, state):
        """
        Ask the LLM to choose the next action given the current environment state.

        The LLM is instructed to return a JSON object with a "tool" key and any
        required arguments (e.g. the file to fix).

        Args:
            state: A JSON string representing the current environment state.

        Returns:
            A dict representing the chosen action, e.g. {"tool": "fix", "file": "main.py"}.
        """
        prompt = f"""
{self.system_prompt}

Current state:
{state}

Available actions:
1. {{"tool": "run"}}
2. {{"tool": "fix", "file": "<failed_file>"}}
3. {{"tool": "finish"}}

Rules:
- Start by running the program
- If the program fails and failed_file exists, choose fix with that failed_file
- If the program succeeds, finish
- Return JSON only
"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content.strip()

        # Extract the JSON object from the response in case the LLM wraps it in prose
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        return json.loads(text)


# ---------------------------------------------------------------------------
# Entry point — wire up the components and run the agentic loop
# ---------------------------------------------------------------------------

# Environment holds shared state across all steps
env = Environment()

# Tools execute real-world actions (run program, fix file)
tools = Tools(env)

# LLM decides which tool to invoke at each step
llm = LLM("You are an agent that debugs Python programs using tools in a loop.")

print("=== Agent Started ===")

# Agentic loop: Observe → Think → Act, until done or max steps reached
while not env.is_done():
    print(f"\n--- Step {env.step + 1} ---")

    # 1. Observe: render the current state for the LLM
    print("STATE:")
    print(env.render_state())

    # 2. Think: ask the LLM to pick the next action
    action = llm.run(env.render_state())
    print("ACTION:", action)

    # 3. Act: execute the chosen tool
    observation = tools.run(action)
    print("OBSERVATION:", json.dumps(observation, indent=2))

    # Update state with the result of the action
    env.update(observation)

print("\n=== Agent Finished ===")
print(env.render_state())