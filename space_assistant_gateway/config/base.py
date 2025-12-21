import sys
import os

from assistant_gateway.chat_orchestrator.chat.store import InMemoryChatStore
from assistant_gateway.chat_orchestrator.core.config import (
    AgentConfig,
    GatewayConfig,
    GatewayDefaultFallbackConfig,
)
from assistant_gateway.chat_orchestrator.tasks_queue_manager import (
    InMemoryTasksQueueManager,
)
from space_assistant_gateway.config.agents.todo_list import build_todo_agent


def build_gateway_config() -> GatewayConfig:
    """
    Compose GatewayConfig with:
    - one todo-list AgentConfig that uses the dynamic builder above
    - in-memory chat store
    - in-memory queue manager
    """

    default_fallback = GatewayDefaultFallbackConfig(
        fallback_backend_url=os.environ.get("BACKEND_URL")
    )

    return GatewayConfig(
        agent_configs={
            "todo-list": AgentConfig(
                name="todo-list",
                builder=build_todo_agent,
            )
        },
        default_fallback_config=default_fallback,
        chat_store=InMemoryChatStore(),
        queue_manager=InMemoryTasksQueueManager(),
    )
