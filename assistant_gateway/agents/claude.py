from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from claude_agent_sdk import McpSdkServerConfig
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk import ClaudeSDKClient

from assistant_gateway.agents.base import Agent
from assistant_gateway.tools.base import Tool, ToolContext
from assistant_gateway.tools.registry import ToolRegistry
from assistant_gateway.schemas import (
    Message,
    AssistantResponse,
    UserContext,
    Role,
    AgentStep,
    ToolCall,
    ToolResult as SchemaToolResult,
)


class ClaudeBaseAgent(Agent):
    """
    Adapter that prepares tools from ``ToolRegistry`` for the ClaudeAgent SDK.

    The actual conversation loop still needs to be implemented, but the
    infrastructure for translating registry entries into ``@tool``-decorated
    callables lives here.
    """

    def __init__(self, api_key: Optional[str]) -> None:
        super().__init__()
        self.api_key = api_key

    def get_mcp_server_options(self) -> ClaudeAgentOptions:
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    def get_mcp_server_config(
        cls,
        name: str,
        version: str,
        tool_registry: ToolRegistry,
        predefined_tool_context: ToolContext,
    ) -> Tuple[McpSdkServerConfig, List[Callable]]:
        """
        Translate the registry into Claude SDK ``@tool`` callables and register
        them against an MCP server instance.

        Args:
                tool_registry: The tool registry to use.
                predefined_tool_context: The global tool context to use.

        Returns:
                A tuple containing the MCP server and the tool functions.
        """
        from claude_agent_sdk import create_sdk_mcp_server

        tool_functions = [
            cls._wrap_tool_for_claude(tool, predefined_tool_context)
            for tool in tool_registry.all()
        ]
        server = create_sdk_mcp_server(
            name=name,
            version=version,
            tools=tool_functions,
        )
        return server, tool_functions

    async def run(
        self,
        messages: List[Message]
    ) -> AssistantResponse:
        mcp_server_options = self.get_mcp_server_options()

        # Convert messages to Claude SDK format
        claude_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
            if msg.role in (Role.user, Role.assistant)
        ]

        prompt = claude_messages[-1]["content"] if claude_messages else ""

        # Call Claude with the configured MCP server options using ClaudeSDKClient
        response = None
        async with ClaudeSDKClient(options=mcp_server_options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                response = message  # Keep the last message as the final response

        # Parse the response into AgentSteps and ToolResults
        steps: List[AgentStep] = []
        tool_results: List[SchemaToolResult] = []
        assistant_messages: List[Message] = []

        # Extract the final text response from Claude
        final_text = ""
        if hasattr(response, "content"):
            # Handle response content (could be text or tool use)
            for content_block in response.content:
                if hasattr(content_block, "text"):
                    final_text += content_block.text
                elif (
                    hasattr(content_block, "type") and content_block.type == "tool_use"
                ):
                    tool_call = ToolCall(
                        id=content_block.id,
                        name=content_block.name,
                        input=content_block.input,
                    )
                    steps.append(AgentStep(tool_calls=[tool_call]))
        elif hasattr(response, "text"):
            final_text = response.text
        elif isinstance(response, str):
            final_text = response
        elif isinstance(response, dict):
            final_text = response.get("text", response.get("content", str(response)))
        else:
            final_text = str(response)

        # Create the assistant message
        if final_text:
            assistant_messages.append(Message(role=Role.assistant, content=final_text))

        return AssistantResponse(
            messages=assistant_messages,
            steps=steps,
            tool_results=tool_results,
            final_text=final_text if final_text else None,
        )

    @classmethod
    def _wrap_tool_for_claude(cls, tool: Tool, predefined_tool_context: ToolContext):
        from claude_agent_sdk import tool as claude_tool_decorator

        tool_input_schema = cls._build_input_schema(tool)
        print(f"tool input schema: {tool_input_schema}")

        @claude_tool_decorator(tool.name, tool.metadata.description, tool_input_schema)
        async def _invoke(args: Dict[str, Any]):
            tool_context_with_input = predefined_tool_context.with_input(args)
            result = await tool.run(tool_context_with_input)
            output = result.output
            if isinstance(output, str):
                text = output
            else:
                try:
                    text = json.dumps(output, default=str)
                except TypeError:
                    text = str(output)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ]
            }

        return _invoke

    @classmethod
    def _build_input_schema(cls, tool: Tool) -> Dict[str, Any]:
        """Build a proper JSON Schema from the tool's input model."""
        model = tool.metadata.input_model
        if not model:
            return {"type": "object", "properties": {}}
        
        # Use Pydantic's built-in JSON schema generation
        json_schema = model.model_json_schema()
        
        # Filter out fields we don't want to expose to the tool input
        excluded_fields = {}
        if 'properties' in json_schema:
            json_schema['properties'] = {
                k: v for k, v in json_schema['properties'].items()
                if k not in excluded_fields
            }
        if 'required' in json_schema:
            json_schema['required'] = [
                r for r in json_schema['required']
                if r not in excluded_fields
            ]
        
        # Resolve $defs references inline for simpler schema
        json_schema = cls._resolve_schema_refs(json_schema)
        
        # Remove $defs after resolving
        if '$defs' in json_schema:
            del json_schema['$defs']
        
        return json_schema

    @classmethod
    def _resolve_schema_refs(cls, schema: Dict[str, Any], defs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Recursively resolve $ref references in JSON Schema."""
        if defs is None:
            defs = schema.get('$defs', {})
        
        if isinstance(schema, dict):
            # Handle $ref
            if '$ref' in schema:
                ref_path = schema['$ref']
                # Extract the definition name from "#/$defs/DefinitionName"
                if ref_path.startswith('#/$defs/'):
                    def_name = ref_path.split('/')[-1]
                    if def_name in defs:
                        # Return a copy of the resolved definition (recursively resolve it too)
                        return cls._resolve_schema_refs(defs[def_name].copy(), defs)
                return schema
            
            # Recursively resolve all dict values
            return {k: cls._resolve_schema_refs(v, defs) for k, v in schema.items()}
        elif isinstance(schema, list):
            return [cls._resolve_schema_refs(item, defs) for item in schema]
        else:
            return schema
