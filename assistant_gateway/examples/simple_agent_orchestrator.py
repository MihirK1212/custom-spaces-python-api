import asyncio
import sys

sys.path.append(".")

from assistant_gateway.orchestrator import ConversationOrchestrator
from assistant_gateway.examples.simple_echo_agent import SimpleEchoAgent
from assistant_gateway.schemas import Message


async def main():
    agent = SimpleEchoAgent()
    orchestrator = ConversationOrchestrator(agent)

    messages = [
        Message(role="user", content='''tool: todo.delete {"path": "/todos/1", "method": "DELETE"}'''),
    ]

    response = await orchestrator.handle_messages(messages)
    print(response)

if __name__ == "__main__":
    asyncio.run(main()) 