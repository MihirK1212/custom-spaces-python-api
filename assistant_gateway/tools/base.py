from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from assistant_gateway.schemas import ToolResult


class ToolMetadata(BaseModel):
    name: str
    description: str
    input_model: Optional[Type[BaseModel]] = None
    output_description: Optional[str] = None
    output_model: Optional[Type[BaseModel]] = None


class ToolContext(BaseModel):
    """
    Runtime context passed to tools.
    
    The context carries per request metadata such as input payload, timeout, and metadata.
    """

    input: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, description="Timeout in seconds for the tool execution")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def with_input(self, payload: Dict[str, Any]) -> "ToolContext":
        """
        Return a cloned context embedding the tool-specific input payload.

        This avoids mutating the shared context when multiple tools are called
        within the same agent turn.
        """

        data = deepcopy(self.model_dump())
        data["input"] = payload
        return ToolContext(**data)


class Tool(ABC):
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata

    @property
    def name(self) -> str:
        return self.metadata.name

    @abstractmethod
    async def run(self, context: ToolContext) -> ToolResult:
        raise NotImplementedError("The run method must be implemented by the subclass for a Tool")
