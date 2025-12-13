from __future__ import annotations

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(".")
sys.path.append("..")
sys.path.append("../..")


import asyncio
from typing import Optional

from space_assistant_gateway.orchestration.orchestrator import ConversationOrchestrator


async def main() -> None:
    """
    Interactive helper that mirrors the chat create/send endpoints.
    Creates a chat, sends one synchronous message, and prints results.
    """
    orchestrator = ConversationOrchestrator()

    print("=== Space Assistant Gateway CLI ===")
    user_id = input("User id (default: demo-user): ").strip() or "demo-user"
    agent_name_input = input("Agent name (leave blank for default): ").strip()
    agent_name: Optional[str] = agent_name_input or None
    message = input("Message to send: ").strip()

    print("\nCreating chat...")
    chat = await orchestrator.create_chat(
        user_id=user_id,
        agent_name=agent_name,
        metadata={},
        extra_metadata={},
    )
    print(f"Chat created with id: {chat.chat_id}")

    print("\nSending message (synchronous)...")
    chat, assistant_response, task = await orchestrator.send_message(
        chat_id=chat.chat_id,
        content=message,
        run_in_background=False,
        message_metadata=None,
        user_context=None,
    )

    if task:
        print("Background task was created unexpectedly; this runner uses sync mode only.")

    print("\nAssistant response:")
    if assistant_response and assistant_response.messages:
        for idx, msg in enumerate(assistant_response.messages, start=1):
            print(f"{idx}. [{msg.role}] {msg.content}")
    else:
        print("No assistant response returned.")

    print("\nStored messages:")
    stored = await orchestrator.list_messages(chat.chat_id)
    for idx, msg in enumerate(stored, start=1):
        print(f"{idx}. [{msg.role}] {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())

