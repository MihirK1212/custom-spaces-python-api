import os
from enum import Enum
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
from assistant_gateway.tools.rest_tool import (
    RESTTool,
    RestToolContext,
    RestToolContextInputOverrides,
)

dotenv.load_dotenv()

# Default Claude model; override with CLAUDE_MODEL env var if desired.
DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")


class WidgetType(str, Enum):
    CHAT = "chat"
    MONEY_SPLIT = "money_split"
    TODO_LIST = "todo_list"


# ==================== Add Widget ====================


class AddWidgetQueryParamsModel(BaseModel):
    spaceId: str = Field(description="The ID of the custom space to add the widget to")


class AddWidgetDataPayloadModel(BaseModel):
    widgetType: WidgetType = Field(description="The type of widget to create")
    displayName: Optional[str] = Field(
        default=None, description="The display name of the widget"
    )
    description: Optional[str] = Field(
        default=None, description="The description of the widget"
    )


class AddWidgetRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="add_widget_to_space",
            description=(
                "Add a new widget to a custom space. "
                "Supported widget types: chat, money_split, todo_list. "
                "Endpoint: POST /api/custom_space/{spaceId}/widget"
                """
                Example:
                curl -X 'POST' \
                'http://localhost:5000/api/custom_space/68f7838274710931d1c342b5/widget' \
                -H 'accept: application/json' \
                -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIzOGUyM2FiMS1kNzNlLTQ2NjYtOTExYi0yNWNkZmRlZGMwY2UiLCJ1c2VybmFtZSI6InVzZXIxIiwiYXV0aE1ldGhvZElkIjoiMzBjMzI3ZDQtOTkxMC00NjI5LTgyYTktZWZjNGNmN2NhZDgwIiwidG9rZW5QdXJwb3NlIjoidXNlci1hdXRoIiwiaWF0IjoxNzY3MDE2MDEzLCJleHAiOjE3NjcwMTk2MTN9.jhQGvM58GNRQUayGIm4jaOu5HkW2vD7cF5GSrUYjTNA' \
                -H 'Content-Type: application/json' \
                -d '{
                "widgetType": "todo_list",
                "displayName": "Test From FastAPI Swagger",
                "description": ""
                }'
                """
            ),
            query_params_model=AddWidgetQueryParamsModel,
            data_payload_model=AddWidgetDataPayloadModel,
        )


# ==================== Remove Widget ====================


class RemoveWidgetQueryParamsModel(BaseModel):
    widgetId: str = Field(description="The ID of the widget to remove")


class RemoveWidgetRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="remove_widget_from_space",
            description=(
                "Remove a widget from a custom space. "
                "Endpoint: DELETE /api/custom-spaces/widget/{widgetId}"
            ),
            query_params_model=RemoveWidgetQueryParamsModel,
        )


# ==================== Update Widget ====================


class UpdateWidgetQueryParamsModel(BaseModel):
    widgetId: str = Field(description="The ID of the widget to update")


class UpdateWidgetDataPayloadModel(BaseModel):
    displayName: Optional[str] = Field(
        default=None, description="The updated display name of the widget"
    )
    description: Optional[str] = Field(
        default=None, description="The updated description of the widget"
    )


class UpdateWidgetRESTTool(RESTTool):
    def __init__(self) -> None:
        super().__init__(
            name="update_widget",
            description=(
                "Update an existing widget's display name and/or description. "
                "Endpoint: PATCH /api/custom-spaces/widget/{widgetId}"
            ),
            query_params_model=UpdateWidgetQueryParamsModel,
            data_payload_model=UpdateWidgetDataPayloadModel,
        )


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(AddWidgetRESTTool())
    registry.register(RemoveWidgetRESTTool())
    registry.register(UpdateWidgetRESTTool())
    return registry


class DynamicClaudeCustomSpaceWidgetsAgent(ClaudeBaseAgent):
    """
    Claude agent wired with custom space widget REST tools.

    The tool context (backend URL + headers) is injected at construction time so it
    can be derived from the chat_orchestrator GatewayConfig builder arguments.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: Optional[str],
        predefined_tool_context: RestToolContext,
    ) -> None:
        super().__init__(api_key)
        self._predefined_tool_context = predefined_tool_context
        self._model = model or DEFAULT_MODEL
        self._tool_registry = build_tool_registry()

        server, _ = self.get_mcp_server_config(
            name="space-custom-widgets-agent",
            version="0.1.0",
            tool_registry=self._tool_registry,
            predefined_tool_context=self._predefined_tool_context,
        )

        self._options = ClaudeAgentOptions(
            model=self._model,
            mcp_servers={"space-custom-widgets": server},
            system_prompt=(
                "You are a helpful custom space widget assistant. Use the available tools "
                "to add, update, and remove widgets from custom spaces. "
                "Widget types include: chat, money_split, and todo_list."
            ),
            allowed_tools=[
                "mcp__space-custom-widgets__add_widget_to_space",
                "mcp__space-custom-widgets__remove_widget_from_space",
                "mcp__space-custom-widgets__update_widget",
            ],
        )

    def get_mcp_server_options(self) -> ClaudeAgentOptions:
        return self._options


def build_custom_space_widgets_agent(
    user_context: Optional[UserContext],
    backend_server_context: Optional[BackendServerContext],
    default_fallback_config: Optional[GatewayDefaultFallbackConfig],
) -> DynamicClaudeCustomSpaceWidgetsAgent:
    """
    Create a custom space widgets agent using dynamic inputs supplied by the orchestrator.
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

    token = (user_context.auth_token if user_context else None) or os.environ.get(
        "WIDGETS_AGENT_BEARER_TOKEN"
    )
    headers: Dict[str, str] = {"Authorization": f"Bearer {token}"} if token else {}

    predefined_tool_context = RestToolContext(
        input_overrides=RestToolContextInputOverrides(
            backend_url=backend_url,
            default_headers=headers,
        )
    )
    print(
        "predefined_tool_context inside build_custom_space_widgets_agent",
        predefined_tool_context,
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required to run the agent.")

    return DynamicClaudeCustomSpaceWidgetsAgent(
        api_key=api_key,
        model=os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL),
        predefined_tool_context=predefined_tool_context,
    )
