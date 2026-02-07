import os

from typing import Dict, Optional

import dotenv
from claude_agent_sdk import ClaudeAgentOptions
from pydantic import BaseModel, Field


from assistant_gateway.agents.claude import ClaudeBaseAgent
from assistant_gateway.chat_orchestrator.core.config import (
    GatewayDefaultFallbackConfig,
)
from assistant_gateway.chat_orchestrator.core.schemas import (
    BackendServerContext,
    UserContext,
)
from assistant_gateway.tools.registry import ToolRegistry
from assistant_gateway.tools.rest_tool import RESTTool
from typing import Any

dotenv.load_dotenv()

# Default Claude model; override with CLAUDE_MODEL env var if desired.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")


class GetTodoListQueryParamsModel(BaseModel):
    widgetId: str = Field(description="The ID of the todo list widget")


class AddTodoItemDataPayloadModel(BaseModel):
    content: str = Field(description="The content of the todo item")


class UpdateTodoItemQueryParamsModel(BaseModel):
    widgetId: str = Field(description="The ID of the todo list widget")
    itemId: str = Field(description="The ID of the todo item to update")


class UpdateTodoItemDataPayloadModel(BaseModel):
    content: Optional[str] = Field(
        default=None, description="The updated content of the todo item"
    )
    completed: Optional[bool] = Field(
        default=None, description="Whether the todo item is completed"
    )


class DeleteTodoItemQueryParamsModel(BaseModel):
    widgetId: str = Field(description="The ID of the todo list widget")
    itemId: str = Field(description="The ID of the todo item to delete")


class GetTodoListRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="get_todo_list",
            description=(
                "Get the todo list for a given widgetId from the Space API. "
                "Endpoint: GET /api/widgets/todo/{widgetId}"
            ),
            query_params_model=GetTodoListQueryParamsModel,
        )


class AddTodoItemRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="add_todo_item",
            description=(
                "Add a new todo item to the todo list for a given widgetId from the "
                "Space API. Endpoint: POST /api/widgets/todo/{widgetId}"
            ),
            data_payload_model=AddTodoItemDataPayloadModel,
        )


class UpdateTodoItemRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="update_todo_item",
            description=(
                "Update an existing todo item in the todo list for a given widgetId and itemId. "
                "Can update the content and/or completed status. "
                "Endpoint: PATCH /api/widgets/todo/item/{widgetId}/{itemId}"
            ),
            query_params_model=UpdateTodoItemQueryParamsModel,
            json_payload_model=UpdateTodoItemDataPayloadModel,
        )


class DeleteTodoItemRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="delete_todo_item",
            description=(
                "Delete a todo item from the todo list for a given widgetId and itemId. "
                "Endpoint: DELETE /api/widgets/todo/item/{widgetId}/{itemId}"
            ),
            query_params_model=DeleteTodoItemQueryParamsModel,
        )


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GetTodoListRESTTool())
    registry.register(AddTodoItemRESTTool())
    registry.register(UpdateTodoItemRESTTool())
    registry.register(DeleteTodoItemRESTTool())
    return registry


class DynamicClaudeTodoListAgent(ClaudeBaseAgent):
    """
    Claude agent wired with the todo REST tools.

    The tool context (backend URL + headers) is injected at construction time so it
    can be derived from the chat_orchestrator GatewayConfig builder arguments.
    """

    def __init__(
        self,
        *,
        model: Optional[str],
        agent_level_input_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self._agent_level_input_overrides = agent_level_input_overrides
        self._model = model or DEFAULT_MODEL
        self._tool_registry = build_tool_registry()

        server, _ = self.get_mcp_server_config(
            name="space-todo-list-agent",
            version="0.1.0",
            tool_registry=self._tool_registry,
            agent_level_input_overrides=agent_level_input_overrides,
        )

        self._options = ClaudeAgentOptions(
            model=self._model,
            mcp_servers={"space-todo-list": server},
            system_prompt=(
                "You are a helpful space todo list assistant. Use the available tools "
                "to get, add, update, and delete todo items for a given widgetId from the Space API."
            ),
            allowed_tools=[
                "mcp__space-todo-list__get_todo_list",
                "mcp__space-todo-list__add_todo_item",
                "mcp__space-todo-list__update_todo_item",
                "mcp__space-todo-list__delete_todo_item",
            ],
        )

    def get_mcp_server_options(self) -> ClaudeAgentOptions:
        return self._options


def build_todo_agent(
    user_context: Optional[UserContext],
    backend_server_context: Optional[BackendServerContext],
    default_fallback_config: Optional[GatewayDefaultFallbackConfig],
) -> DynamicClaudeTodoListAgent:
    """
    Create a todo-list agent using dynamic inputs supplied by the orchestrator.
    """

    backend_url = (
        (backend_server_context.base_url if backend_server_context else None)
        or (
            default_fallback_config.fallback_backend_url
            if default_fallback_config
            else None
        )
        or os.environ.get("BACKEND_URL")
    )

    if not backend_url:
        raise ValueError(
            "Missing backend_url. Provide BackendServerContext.base_url or set "
            "BACKEND_URL/FALLBACK_BACKEND_URL."
        )

    token = (user_context.auth_token if user_context else None)
    headers: Dict[str, str] = {"Authorization": f"Bearer {token}"} if token else {}

    agent_level_input_overrides = {
        "backend_url": backend_url,
        "headers": headers,
    }
    print("agent_level_input_overrides inside build_todo_agent", agent_level_input_overrides)

    return DynamicClaudeTodoListAgent(
        model=os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL),
        agent_level_input_overrides=agent_level_input_overrides,
    )
