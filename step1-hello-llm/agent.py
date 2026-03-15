"""
step1/agent.py — Skeleton: The Bare Minimum

What you learn here:
  - How to call the OpenAI API with a single message.
  - The simplest possible "agent": one question, one answer, done.
  - How to accept a question from the CLI (sys.argv or interactive input).

There is no loop, no tools, no memory.
Just: send a message → get a reply → print it.

Usage:
  python agent.py                              # prompts you to type a question
  python agent.py "What is the speed of light?"  # question passed as argument
"""

import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load OPENAI_API_KEY from the .env file in this folder (or the project root)
load_dotenv()

# Create a single reusable OpenAI client
client = OpenAI()

# ---------------------------------------------------------------------------
# Get the question — from CLI argument, or ask the user to type one
# ---------------------------------------------------------------------------

if len(sys.argv) > 1:
    # Question passed directly:  python agent.py "your question here"
    question = " ".join(sys.argv[1:])
else:
    # No argument given — ask interactively
    question = input("Ask anything: ").strip()
    if not question:
        print("No question provided. Exiting.")
        sys.exit(1)

print(f"\nQuestion: {question}")

# ---------------------------------------------------------------------------
# Send the question to the LLM and print the answer
# ---------------------------------------------------------------------------

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": question}
    ]
)

answer = response.choices[0].message.content
print(f"Answer:   {answer}")
