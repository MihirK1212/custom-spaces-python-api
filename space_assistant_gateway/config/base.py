import os

from assistant_gateway.chat_orchestrator.chat.store import InMemoryChatStore
from assistant_gateway.chat_orchestrator.core.config import (
    AgentConfig,
    GatewayConfig,
    GatewayDefaultFallbackConfig,
)
from space_assistant_gateway.config.agents.todo_list import build_todo_agent
from space_assistant_gateway.config.agents.custom_space_widgets import (
    build_custom_space_widgets_agent,
)
from assistant_gateway.clauq_btm.instance import ClauqBTM


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
            ),
            "custom-space-widgets": AgentConfig(
                name="custom-space-widgets",
                builder=build_custom_space_widgets_agent,
            ),
        },
        default_fallback_config=default_fallback,
        chat_store=InMemoryChatStore(),
        clauq_btm=ClauqBTM(),
    )
