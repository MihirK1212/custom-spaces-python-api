from __future__ import annotations

from assistant_gateway.agents.base import Agent
from assistant_gateway.agents.claude import ClaudeBaseAgent
from assistant_gateway.config import get_settings


def get_agent(name: str) -> Agent:
	settings = get_settings()
	key = name.lower()
	if key == "claude":
		return ClaudeBaseAgent(api_key=settings.anthropic_api_key)
	# Default
	return None


