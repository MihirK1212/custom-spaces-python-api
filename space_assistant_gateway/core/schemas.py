from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from assistant_gateway.schemas import AssistantResponse, Message


class ChatStatus(str, Enum):
    active = "active"
    archived = "archived"


class StoredMessage(Message):
    id: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMetadata(BaseModel):
    chat_id: str
    user_id: str
    agent_name: str
    status: ChatStatus = ChatStatus.active
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Fixed metadata persisted for the chat lifetime",
    )
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chat-specific metadata that can vary per conversation",
    )
    last_task_id: Optional[str] = None


class Chat(BaseModel):
    chat: ChatMetadata
    messages: List[StoredMessage] = Field(default_factory=list)


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class BackgroundTask(BaseModel):
    id: str
    queue_id: str
    chat_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[AssistantResponse] = None
    error: Optional[str] = None

