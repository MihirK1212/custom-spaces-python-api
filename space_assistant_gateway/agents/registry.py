from __future__ import annotations

from typing import Any, Callable

from assistant_gateway.agents.base import Agent
from assistant_gateway.examples.todo_list_agent import ClaudeTodoListAgent


AgentBuilder = Callable[..., Agent]

DEFAULT_AGENT_NAME = "claude_todo_list"


def _build_claude_todo_list_agent(**kwargs: Any) -> Agent:
    print("Building Claude Todo List Agent")
    print(f"API Key: {kwargs.get('api_key')}")
    print(f"Model: {kwargs.get('model')}")
    return ClaudeTodoListAgent(**kwargs)


AGENT_BUILDERS = {
    DEFAULT_AGENT_NAME: _build_claude_todo_list_agent,
}


def get_agent_builder(agent_name: str) -> AgentBuilder:
    try:
        return AGENT_BUILDERS[agent_name]
    except KeyError as exc:
        available = ", ".join(sorted(AGENT_BUILDERS.keys()))
        raise ValueError(
            f"Unknown agent '{agent_name}'. Available: {available}"
        ) from exc
