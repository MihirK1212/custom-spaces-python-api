from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from space_assistant_gateway.core.schemas import ChatMetadata, StoredMessage


class ChatStore:
    """Abstraction for persisting chat metadata and messages."""

    async def create_chat(self, chat: ChatMetadata) -> ChatMetadata:
        raise NotImplementedError

    async def get_chat(self, chat_id: str) -> Optional[ChatMetadata]:
        raise NotImplementedError

    async def update_chat(self, chat: ChatMetadata) -> ChatMetadata:
        raise NotImplementedError

    async def append_message(self, chat_id: str, message: StoredMessage) -> None:
        raise NotImplementedError

    async def list_messages(self, chat_id: str) -> List[StoredMessage]:
        raise NotImplementedError


class InMemoryChatStore(ChatStore):
    """
    In-memory implementation that mirrors a document-style NoSQL layout.
    Replace with a real backend (e.g., MongoDB, DynamoDB) without changing the
    public interface.
    """

    def __init__(self) -> None:
        self._chats: Dict[str, ChatMetadata] = {}
        self._messages: Dict[str, List[StoredMessage]] = {}
        self._lock = asyncio.Lock()

    async def create_chat(self, chat: ChatMetadata) -> ChatMetadata:
        async with self._lock:
            self._chats[chat.chat_id] = chat
            self._messages.setdefault(chat.chat_id, [])
        return chat

    async def get_chat(self, chat_id: str) -> Optional[ChatMetadata]:
        async with self._lock:
            return self._chats.get(chat_id)

    async def update_chat(self, chat: ChatMetadata) -> ChatMetadata:
        async with self._lock:
            self._chats[chat.chat_id] = chat
        return chat

    async def append_message(self, chat_id: str, message: StoredMessage) -> None:
        async with self._lock:
            self._messages.setdefault(chat_id, []).append(message)

    async def list_messages(self, chat_id: str) -> List[StoredMessage]:
        async with self._lock:
            return list(self._messages.get(chat_id, []))

