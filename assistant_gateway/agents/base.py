from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from assistant_gateway.schemas import AssistantResponse, Message, UserContext
from assistant_gateway.tools.base import ToolContext


class Agent(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def run(
        self,
        messages: List[Message]
    ) -> AssistantResponse:
        raise NotImplementedError("Subclasses must implement this method")
