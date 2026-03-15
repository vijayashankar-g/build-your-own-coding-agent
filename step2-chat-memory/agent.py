"""
step2/agent.py — Chat Wrapper: System Prompt + Conversation History

What is NEW compared to Step 1:
  + A `system` message that sets the assistant's personality/role.
  + A `messages` list that grows with every turn (conversation memory).
  + A loop so the user can have a back-and-forth conversation.
  + A `ChatBot` class to keep things organized.

What is still MISSING:
  - The LLM cannot DO anything — it can only talk.
  - There are no tools (no code execution, no file writing, etc.)
"""

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ChatBot:
    """
    A simple multi-turn chatbot.

    Keeps a growing list of messages so the LLM remembers the conversation.
    The first message is always a 'system' message that defines the bot's role.
    """

    def __init__(self, system_prompt: str):
        self.client = OpenAI()

        # The conversation history starts with the system prompt.
        # Every new user/assistant turn gets appended here so the LLM has context.
        self.messages = [
            {"role": "system", "content": system_prompt}
        ]

    def chat(self, user_message: str) -> str:
        """
        Send a user message, get a reply, and save both to history.

        Args:
            user_message: The text the user typed.

        Returns:
            The assistant's reply as a plain string.
        """
        # 1. Add the user's message to history
        self.messages.append({"role": "user", "content": user_message})

        # 2. Send the FULL history to the LLM so it has context of prior turns
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages
        )

        # 3. Extract the reply
        reply = response.choices[0].message.content

        # 4. Save the assistant's reply to history for the next turn
        self.messages.append({"role": "assistant", "content": reply})

        return reply


# ---------------------------------------------------------------------------
# Run an interactive chat session in the terminal
# ---------------------------------------------------------------------------

bot = ChatBot(
    system_prompt=(
        "You are a helpful Python tutor. "
        "Explain concepts clearly with short code examples. "
        "You can remember the conversation history and refer back to it in the same sessions. "
        "Keep answers concise."
    )
)

print("=== Python Tutor Chat ===")
print("Type 'quit' to exit.\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() in ("quit", "exit", "q"):
        print("Goodbye!")
        break

    if not user_input:
        continue

    reply = bot.chat(user_input)
    print(f"\nBot: {reply}\n")
