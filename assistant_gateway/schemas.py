from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class Message(BaseModel):
    role: Role
    content: str
    tool_result: Optional[ToolResult] = None


class ToolCall(BaseModel):
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    thought: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    final_response: Optional[str] = None


class ToolResult(BaseModel):
    tool_name: str
    output: Any
    raw_response: Any = None
    tool_call_id: Optional[str] = None


class UserContext(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    messages: List[Message]
    steps: List[AgentStep] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    final_text: Optional[str] = None
