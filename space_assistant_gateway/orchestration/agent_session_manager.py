from __future__ import annotations

from typing import Any, Callable, Dict

from assistant_gateway.agents.base import Agent


class AgentSessionManager:
    """
    Maintains long-lived agent instances per chat so the same MCP session
    (tools, auth, cached state) can be reused across API calls.
    """

    def __init__(self, agent_factory: Callable[[str, ...], Agent]) -> None:
        self._agent_factory = agent_factory
        self._sessions: Dict[str, Agent] = {}

    def get_or_create(self, chat_id: str, agent_name: str, **kwargs: Any) -> Agent:
        if chat_id not in self._sessions:
            self._sessions[chat_id] = self._agent_factory(agent_name, **kwargs)
        return self._sessions[chat_id]

    def drop(self, chat_id: str) -> None:
        if chat_id in self._sessions:
            del self._sessions[chat_id]

