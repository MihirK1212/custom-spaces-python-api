from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, status

from assistant_gateway.schemas import AssistantResponse, Message, Role, UserContext
from space_assistant_gateway.agents import get_agent_builder, DEFAULT_AGENT_NAME
from space_assistant_gateway.core.config import get_settings
from space_assistant_gateway.core.schemas import (
    BackgroundTask,
    ChatMetadata,
    ChatStatus,
    StoredMessage,
    TaskStatus,
)
from space_assistant_gateway.orchestration.agent_session_manager import (
    AgentSessionManager,
)
from space_assistant_gateway.tasks_queue import (
    InMemoryTasksQueueManager,
    TasksQueueManager,
)
from space_assistant_gateway.storage import ChatStore, InMemoryChatStore


class ConversationOrchestrator:
    """
    Coordinates chat lifecycle, persistence, background processing, and agent
    session reuse.
    """

    def __init__(
        self,
        chat_store: Optional[ChatStore] = None,
        queue_manager: Optional[TasksQueueManager] = None,
        agent_session_manager: Optional[AgentSessionManager] = None,
    ) -> None:
        self.settings = get_settings()
        self.chat_store = chat_store or InMemoryChatStore()
        self.queue_manager = queue_manager or InMemoryTasksQueueManager()
        self.agent_session_manager = agent_session_manager or AgentSessionManager(
            agent_factory=self._build_agent
        )

    def _build_agent(self, agent_name: str, **kwargs: Any):
        builder = get_agent_builder(agent_name or DEFAULT_AGENT_NAME)
        return builder(
            **kwargs,
        )

    async def create_chat(
        self,
        user_id: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
        extra_metadata: Optional[Dict] = None,
    ) -> ChatMetadata:
        chat_id = str(uuid4())
        now = datetime.now(timezone.utc)
        chat = ChatMetadata(
            chat_id=chat_id,
            user_id=user_id,
            agent_name=agent_name
            or self.settings.default_agent_name
            or DEFAULT_AGENT_NAME,
            status=ChatStatus.active,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            extra_metadata=extra_metadata or {},
        )
        await self.chat_store.create_chat(chat)
        return chat

    async def get_chat(self, chat_id: str) -> ChatMetadata:
        chat = await self.chat_store.get_chat(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
        return chat

    async def list_messages(self, chat_id: str) -> List[StoredMessage]:
        await self._ensure_chat_exists(chat_id)
        return await self.chat_store.list_messages(chat_id)

    async def send_message(
        self,
        chat_id: str,
        content: str,
        run_in_background: bool,
        message_metadata: Optional[Dict] = None,
        user_context: Optional[UserContext] = None,
    ) -> Tuple[ChatMetadata, Optional[AssistantResponse], Optional[BackgroundTask]]:
        chat = await self.get_chat(chat_id)
        user_message = StoredMessage(
            id=str(uuid4()),
            role=Role.user,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=message_metadata or {},
        )
        await self.chat_store.append_message(chat_id, user_message)
        chat.updated_at = datetime.now(timezone.utc)
        await self.chat_store.update_chat(chat)

        if run_in_background:
            task = await self._enqueue_background_task(
                chat=chat, user_context=user_context
            )
            chat.last_task_id = task.id
            await self.chat_store.update_chat(chat)
            return chat, None, task

        else:
            assistant_response = await self._run_agent_for_chat(
                chat, user_context=user_context
            )
            chat.updated_at = datetime.now(timezone.utc)
            await self.chat_store.update_chat(chat)
            return chat, assistant_response, None

        return chat, None, None

    async def get_task(self, chat_id: str, task_id: str) -> BackgroundTask:
        task = await self.queue_manager.get(queue_id=chat_id, task_id=task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task

    async def _run_agent_for_chat(
        self,
        chat: ChatMetadata,
        user_context: Optional[UserContext],
    ) -> AssistantResponse:
        messages = await self.chat_store.list_messages(chat.chat_id)
        agent_messages = [
            Message(role=msg.role, content=msg.content, tool_result=msg.tool_result)
            for msg in messages
        ]
        agent = self.agent_session_manager.get_or_create(
            chat_id=chat.chat_id,
            agent_name=chat.agent_name,
            **{
                "api_key": self.settings.anthropic_api_key,
                "model": self.settings.claude_model,
            },
        )
        response = await agent.run(messages=agent_messages)
        await self._persist_assistant_response(chat_id=chat.chat_id, response=response)
        return response

    async def _persist_assistant_response(
        self, chat_id: str, response: AssistantResponse
    ) -> None:
        if response.messages:
            now = datetime.now(timezone.utc)
            tool_metadata = (
                {"tool_results": [tr.model_dump() for tr in response.tool_results]}
                if response.tool_results
                else {}
            )
            for msg in response.messages:
                stored = StoredMessage(
                    id=str(uuid4()),
                    role=msg.role,
                    content=msg.content,
                    created_at=now,
                    metadata=tool_metadata,
                )
                await self.chat_store.append_message(chat_id, stored)

    async def _enqueue_background_task(
        self,
        chat: ChatMetadata,
        user_context: Optional[UserContext],
    ) -> BackgroundTask:
        now = datetime.now(timezone.utc)
        task = BackgroundTask(
            id=str(uuid4()),
            queue_id=chat.chat_id,
            chat_id=chat.chat_id,
            status=TaskStatus.pending,
            created_at=now,
            updated_at=now,
            payload={
                "user_context": user_context.model_dump() if user_context else None
            },
        )
        await self.queue_manager.enqueue(chat.chat_id, task)
        asyncio.create_task(
            self._execute_task(chat=chat, task=task, user_context=user_context)
        )
        return task

    async def _execute_task(
        self,
        chat: ChatMetadata,
        task: BackgroundTask,
        user_context: Optional[UserContext],
    ) -> None:
        task.status = TaskStatus.in_progress
        task.updated_at = datetime.now(timezone.utc)
        await self.queue_manager.update(chat.chat_id, task)
        try:
            response = await self._run_agent_for_chat(chat, user_context=user_context)
            task.status = TaskStatus.completed
            task.result = response
        except Exception as exc:  # pragma: no cover - surfaced via task status
            task.status = TaskStatus.failed
            task.error = str(exc)
        task.updated_at = datetime.now(timezone.utc)
        await self.queue_manager.update(chat.chat_id, task)

    async def _ensure_chat_exists(self, chat_id: str) -> None:
        exists = await self.chat_store.get_chat(chat_id)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
