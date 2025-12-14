from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from space_assistant_gateway.core.schemas import Message, Role, AssistantResponse, UserContext


class ChatRequest(BaseModel):
	messages: List[Message] = Field(description="Conversation so far, including system/user/assistant messages")
	agent_name: Optional[str] = Field(default=None, description="Override which agent to use")
	user_context: Optional[UserContext] = None


class ChatResponse(BaseModel):
	response: AssistantResponse


