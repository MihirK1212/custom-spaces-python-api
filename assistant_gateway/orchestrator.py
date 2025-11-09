from __future__ import annotations

from typing import List, Optional

from assistant_gateway.agents.base import Agent
from assistant_gateway.config import get_settings
from assistant_gateway.schemas import AssistantResponse, Message, UserContext
from assistant_gateway.tools.base import ToolContext


class ConversationOrchestrator:
    def __init__(
        self,
        agent: Agent,
    ) -> None:
        self._agent = agent

    def _build_predefined_tool_context(self, user_context: UserContext) -> ToolContext:
        settings = get_settings()
        headers = {}
        if settings.crud_api_key:
            headers["x-api-key"] = settings.crud_api_key
        if settings.crud_bearer_token:
            headers["authorization"] = f"Bearer {settings.crud_bearer_token}"
        metadata = {
            "user_context": user_context.model_dump(exclude_none=True),
            "base_url": str(settings.crud_base_url),
            "default_headers": headers,
        }
        return ToolContext(metadata=metadata)

    async def handle_messages(
        self, messages: List[Message], user_context: Optional[UserContext] = None
    ) -> AssistantResponse:
        user_context = user_context or UserContext()
        predefined_tool_context = self._build_predefined_tool_context(
            user_context
        )  # predefined tool context that can be used by all tools
        return await self._agent.run(
            messages=messages,
            predefined_tool_context=predefined_tool_context,
            user_context=user_context,
        )
