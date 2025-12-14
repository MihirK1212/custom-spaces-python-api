from __future__ import annotations

from typing import Any, Callable

from assistant_gateway.agents.base import Agent
from space_assistant_gateway.agents.custom_spaces_todo_list_agent import CustomSpacesTodoListClaudeAgent


AgentBuilder = Callable[..., Agent]

CUSTOM_SPACES_TODO_LIST_AGENT_NAME = "custom_spaces_todo_list"


def _build_custom_spaces_todo_list_agent(**kwargs: Any) -> Agent:
    print("Building Custom Spaces Todo List Agent")
    print(f"API Key: {kwargs.get('api_key')}")
    print(f"Model: {kwargs.get('model')}")
    return CustomSpacesTodoListClaudeAgent(**kwargs)


AGENT_BUILDERS = {
    CUSTOM_SPACES_TODO_LIST_AGENT_NAME: _build_custom_spaces_todo_list_agent,
}


def get_agent_builder(agent_name: str) -> AgentBuilder:
    try:
        return AGENT_BUILDERS[agent_name]
    except KeyError as exc:
        available = ", ".join(sorted(AGENT_BUILDERS.keys()))
        raise ValueError(
            f"Unknown agent '{agent_name}'. Available: {available}"
        ) from exc
