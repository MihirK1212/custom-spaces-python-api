from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from fastapi import HTTPException, status

from assistant_gateway.schemas import AssistantResponse, Message, Role
from assistant_gateway.chat_orchestrator.core.config import (
    GatewayConfig,
)
from assistant_gateway.chat_orchestrator.core.schemas import (
    BackgroundTask,
    BackendServerContext,
    ChatMetadata,
    ChatStatus,
    StoredMessage,
    TaskStatus,
    UserContext,
)
from assistant_gateway.chat_orchestrator.orchestration.agent_session_manager import (
    AgentSessionManager,
)


class ConversationOrchestrator:
    """
    Coordinates chat lifecycle, persistence, background processing, and agent
    session reuse.
    """

    def __init__(
        self,
        *,
        config: GatewayConfig,
    ) -> None:
        self._config = config
        self._chat_store = self._config.get_chat_store()
        self._queue_manager = self._config.get_queue_manager()

        agent_configs = self._config.get_agent_configs()
        if not agent_configs:
            raise ValueError("No agent configs provided")

        self._agent_session_manager = AgentSessionManager(
            agent_configs=agent_configs,
            default_fallback_config=self._config.default_fallback_config,
        )

    async def create_chat(
        self,
        user_id: str,
        agent_name: str,
        metadata: Optional[Dict] = None,
        extra_metadata: Optional[Dict] = None,
    ) -> ChatMetadata:
        chat_id = str(uuid4())
        now = datetime.now(timezone.utc)
        chat = ChatMetadata(
            chat_id=chat_id,
            user_id=user_id,
            agent_name=agent_name,
            status=ChatStatus.active,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            extra_metadata=extra_metadata or {},
        )
        await self._chat_store.create_chat(chat)
        return chat

    async def get_chat(self, chat_id: str) -> ChatMetadata:
        chat = await self._chat_store.get_chat(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
        return chat

    async def list_messages(self, chat_id: str) -> List[StoredMessage]:
        await self._ensure_chat_exists(chat_id)
        return await self._chat_store.list_messages(chat_id)

    async def send_message(
        self,
        chat_id: str,
        content: str,
        run_in_background: bool,
        message_metadata: Optional[Dict] = None,
        user_context: Optional[UserContext] = None,
        backend_server_context: Optional[BackendServerContext] = None,
    ) -> Tuple[ChatMetadata, Optional[AssistantResponse], Optional[BackgroundTask]]:
        chat = await self.get_chat(chat_id)
        user_message = StoredMessage(
            id=str(uuid4()),
            role=Role.user,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=message_metadata or {},
        )
        await self._chat_store.append_message(chat_id, user_message)
        chat.updated_at = datetime.now(timezone.utc)
        await self._chat_store.update_chat(chat)

        if run_in_background:
            task = await self._enqueue_background_task(
                chat=chat,
                user_context=user_context,
                backend_server_context=backend_server_context,
            )
            chat.last_task_id = task.id
            await self._chat_store.update_chat(chat)
            return chat, None, task

        else:
            assistant_response = await self._run_agent_for_chat(
                chat,
                user_context=user_context,
                backend_server_context=backend_server_context,
            )
            chat.updated_at = datetime.now(timezone.utc)
            await self._chat_store.update_chat(chat)
            return chat, assistant_response, None

    async def get_task(self, chat_id: str, task_id: str) -> BackgroundTask:
        task = await self._queue_manager.get(queue_id=chat_id, task_id=task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return task

    async def _run_agent_for_chat(
        self,
        chat: ChatMetadata,
        user_context: Optional[UserContext] = None,
        backend_server_context: Optional[BackendServerContext] = None,
    ) -> AssistantResponse:
        messages = await self._chat_store.list_messages(chat.chat_id)
        agent_messages = [
            Message(role=msg.role, content=msg.content, tool_result=msg.tool_result)
            for msg in messages
        ]
        agent = self._agent_session_manager.get_or_create(
            chat_id=chat.chat_id,
            agent_name=chat.agent_name,
            user_context=user_context,
            backend_server_context=backend_server_context,
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
                await self._chat_store.append_message(chat_id, stored)

    async def _enqueue_background_task(
        self,
        chat: ChatMetadata,
        user_context: Optional[UserContext] = None,
        backend_server_context: Optional[BackendServerContext] = None,
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
                "user_context": user_context.model_dump() if user_context else None,
                "backend_server_context": (
                    backend_server_context.model_dump()
                    if backend_server_context
                    else None
                ),
            },
        )
        await self._queue_manager.enqueue(chat.chat_id, task)
        asyncio.create_task(
            self._execute_task(
                chat=chat,
                task=task,
                user_context=user_context,
                backend_server_context=backend_server_context,
            )
        )
        return task

    async def _execute_task(
        self,
        chat: ChatMetadata,
        task: BackgroundTask,
        user_context: Optional[UserContext] = None,
        backend_server_context: Optional[BackendServerContext] = None,
    ) -> None:
        task.status = TaskStatus.in_progress
        task.updated_at = datetime.now(timezone.utc)
        await self._queue_manager.update(chat.chat_id, task)
        try:
            response = await self._run_agent_for_chat(
                chat,
                user_context=user_context,
                backend_server_context=backend_server_context,
            )
            task.status = TaskStatus.completed
            task.result = response
        except Exception as exc:  # pragma: no cover - surfaced via task status
            task.status = TaskStatus.failed
            task.error = str(exc)
        task.updated_at = datetime.now(timezone.utc)
        await self._queue_manager.update(chat.chat_id, task)

    async def _ensure_chat_exists(self, chat_id: str) -> None:
        exists = await self._chat_store.get_chat(chat_id)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
