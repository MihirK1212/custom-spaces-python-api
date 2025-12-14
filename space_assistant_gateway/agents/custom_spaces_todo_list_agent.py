import sys
import os

from assistant_gateway.agents.claude import ClaudeBaseAgent
from assistant_gateway.tools.rest_tool import RESTTool
from pydantic import BaseModel
from assistant_gateway.tools.registry import ToolRegistry
from assistant_gateway.tools.base import ToolContext
from claude_agent_sdk import ClaudeAgentOptions
from pydantic import Field

import dotenv
dotenv.load_dotenv()


class GetTodoListQueryParamsModel(BaseModel):
    widgetId: str


class AddTodoItemDataPayloadModel(BaseModel):
    content: str = Field(description="The content of the todo item")


class GetTodoListRESTTool(RESTTool):
    def __init__(self):
        super().__init__(
            name="get_todo_list",
            description="""Get the todo list for a given widgetId from the Space API 
            The API endpoint is GET /api/widgets/todo/{widgetId}
            """,
            query_params_model=GetTodoListQueryParamsModel,
        )


class AddTodoItemRESTTool(RESTTool):
    def __init__(self):
        super().__init__(
            name="add_todo_item",
            description="""Add a new todo item to the todo list for a given widgetId from the Space API 
            The API endpoint is POST /api/widgets/todo/{widgetId}
            """,
            data_payload_model=AddTodoItemDataPayloadModel,
        )


TODO_API_REST_TOOLS = [
    GetTodoListRESTTool(),
    AddTodoItemRESTTool(),
]


class CustomSpacesTodoListClaudeAgent(ClaudeBaseAgent):
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_backend_url: str,
        jwt_bearer_token: str,
    ) -> None:
        super().__init__(api_key)

        predefined_tool_context = ToolContext(
            metadata={
                "base_url": base_backend_url,
                "default_headers": {
                    "Authorization": f"Bearer {jwt_bearer_token}",
                },
            },
        )

        space_todo_list_mcp_server, space_todo_list_tool_functions = (
            self.get_mcp_server_config(
                name="space-todo-list-agent",
                version="0.1.0",
                tool_registry=self.tool_registry,
                predefined_tool_context=predefined_tool_context,
            )
        )

        # Use with Claude
        self._mcp_server_options = ClaudeAgentOptions(
            model=model,
            mcp_servers={"space-todo-list": space_todo_list_mcp_server},
            system_prompt="You are a helpful space todo list assistant. Use the available tools to add and get todo items for a given widgetId from the Space API.",
            allowed_tools=[
                "mcp__space-todo-list__get_todo_list",
                "mcp__space-todo-list__add_todo_item",
            ],
        )

    def get_mcp_server_options(self) -> ClaudeAgentOptions:
        return self._mcp_server_options

    @property
    def tool_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        for tool in TODO_API_REST_TOOLS:
            registry.register(tool)
        return registry
