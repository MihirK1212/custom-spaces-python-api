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
        """
        Get the MCP server options for the Claude agent.
        These options will be used to instantiate the ClaudeSDKClient.
        You can make use of the get_mcp_server_config to get the MCP server config,
        and then combine multiple server configs into a single options object.
        """
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

    async def run(self, messages: List[Message]) -> AssistantResponse:
        mcp_server_options = self.get_mcp_server_options()

        # Convert messages to Claude SDK format
        claude_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
            if msg.role in (Role.user, Role.assistant)
        ]

        prompt = claude_messages[-1]["content"] if claude_messages else ""

        # Call Claude with the configured MCP server options using ClaudeSDKClient
        # Collect all messages from the stream for proper parsing
        all_messages: List[Any] = []
        async with ClaudeSDKClient(options=mcp_server_options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                all_messages.append(message)

        # Parse all messages into AgentSteps and ToolResults
        steps: List[AgentStep] = []
        tool_results: List[SchemaToolResult] = []
        assistant_messages: List[Message] = []
        text_parts: List[str] = []
        result_text: Optional[str] = None

        for message in all_messages:
            # Handle AssistantMessage - has content list with ContentBlocks
            if self._is_assistant_message(message):
                step_thought: Optional[str] = None
                step_tool_calls: List[ToolCall] = []
                step_text_parts: List[str] = []

                for content_block in message.content:
                    # TextBlock - has 'text' attribute
                    if self._is_text_block(content_block):
                        step_text_parts.append(content_block.text)
                        text_parts.append(content_block.text)

                    # ThinkingBlock - has 'thinking' and 'signature' attributes
                    elif self._is_thinking_block(content_block):
                        step_thought = content_block.thinking

                    # ToolUseBlock - has 'id', 'name', 'input' attributes
                    elif self._is_tool_use_block(content_block):
                        tool_call = ToolCall(
                            id=content_block.id,
                            name=content_block.name,
                            input=content_block.input,
                        )
                        step_tool_calls.append(tool_call)

                    # ToolResultBlock - has 'tool_use_id', 'content', 'is_error' attributes
                    elif self._is_tool_result_block(content_block):
                        tool_result = SchemaToolResult(
                            tool_name="",  # Name not available in ToolResultBlock
                            output=content_block.content,
                            tool_call_id=content_block.tool_use_id,
                        )
                        tool_results.append(tool_result)

                # Create an AgentStep if we have thought or tool calls
                if step_thought or step_tool_calls:
                    step = AgentStep(
                        thought=step_thought,
                        tool_calls=step_tool_calls,
                        final_response="\n".join(step_text_parts) if step_text_parts else None,
                    )
                    steps.append(step)

                # Create assistant message if we have text
                if step_text_parts:
                    assistant_messages.append(
                        Message(role=Role.assistant, content="\n".join(step_text_parts))
                    )

            # Handle ResultMessage - has 'result', 'is_error', 'total_cost_usd', etc.
            elif self._is_result_message(message):
                if hasattr(message, "result") and message.result:
                    result_text = message.result

            # Handle SystemMessage - has 'subtype' and 'data' attributes
            elif self._is_system_message(message):
                # System messages are metadata, not included in response messages
                pass

            # Handle UserMessage - has 'content' attribute (str or list)
            elif self._is_user_message(message):
                # User messages from the stream are typically echoes, skip them
                pass

        # Combine all text parts for final_text
        final_text = "\n".join(text_parts) if text_parts else None

        # If we have a result from ResultMessage, use that as final_text
        if result_text:
            final_text = result_text
            if not assistant_messages or assistant_messages[-1].content != result_text:
                assistant_messages.append(Message(role=Role.assistant, content=result_text))

        return AssistantResponse(
            messages=assistant_messages,
            steps=steps,
            tool_results=tool_results,
            final_text=final_text,
        )

    @staticmethod
    def _is_assistant_message(message: Any) -> bool:
        """Check if message is an AssistantMessage (has content list and model)."""
        return (
            hasattr(message, "content")
            and isinstance(message.content, list)
            and hasattr(message, "model")
        )

    @staticmethod
    def _is_result_message(message: Any) -> bool:
        """Check if message is a ResultMessage (has subtype, duration_ms, is_error, etc.)."""
        return (
            hasattr(message, "subtype")
            and hasattr(message, "duration_ms")
            and hasattr(message, "is_error")
            and hasattr(message, "num_turns")
        )

    @staticmethod
    def _is_system_message(message: Any) -> bool:
        """Check if message is a SystemMessage (has subtype and data, but not ResultMessage fields)."""
        return (
            hasattr(message, "subtype")
            and hasattr(message, "data")
            and not hasattr(message, "duration_ms")
        )

    @staticmethod
    def _is_user_message(message: Any) -> bool:
        """Check if message is a UserMessage (has content but not model or subtype)."""
        return (
            hasattr(message, "content")
            and not hasattr(message, "model")
            and not hasattr(message, "subtype")
        )

    @staticmethod
    def _is_text_block(block: Any) -> bool:
        """Check if content block is a TextBlock."""
        return hasattr(block, "text") and not hasattr(block, "thinking")

    @staticmethod
    def _is_thinking_block(block: Any) -> bool:
        """Check if content block is a ThinkingBlock."""
        return hasattr(block, "thinking") and hasattr(block, "signature")

    @staticmethod
    def _is_tool_use_block(block: Any) -> bool:
        """Check if content block is a ToolUseBlock."""
        return (
            hasattr(block, "id")
            and hasattr(block, "name")
            and hasattr(block, "input")
            and not hasattr(block, "tool_use_id")
        )

    @staticmethod
    def _is_tool_result_block(block: Any) -> bool:
        """Check if content block is a ToolResultBlock."""
        return hasattr(block, "tool_use_id")

    @classmethod
    def _wrap_tool_for_claude(cls, tool: Tool, predefined_tool_context: ToolContext):
        from claude_agent_sdk import tool as claude_tool_decorator

        tool_input_schema = cls._build_input_schema(tool)
        print(f"tool input schema: {tool_input_schema}")

        @claude_tool_decorator(tool.name, tool.config.description, tool_input_schema)
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
        model = tool.config.input_model
        if not model:
            return {"type": "object", "properties": {}}

        # Use Pydantic's built-in JSON schema generation
        json_schema = model.model_json_schema()

        # Filter out fields we don't want to expose to the tool input
        excluded_fields = {}
        if "properties" in json_schema:
            json_schema["properties"] = {
                k: v
                for k, v in json_schema["properties"].items()
                if k not in excluded_fields
            }
        if "required" in json_schema:
            json_schema["required"] = [
                r for r in json_schema["required"] if r not in excluded_fields
            ]

        # Resolve $defs references inline for simpler schema
        json_schema = cls._resolve_schema_refs(json_schema)

        # Remove $defs after resolving
        if "$defs" in json_schema:
            del json_schema["$defs"]

        return json_schema

    @classmethod
    def _resolve_schema_refs(
        cls, schema: Dict[str, Any], defs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recursively resolve $ref references in JSON Schema."""
        if defs is None:
            defs = schema.get("$defs", {})

        if isinstance(schema, dict):
            # Handle $ref
            if "$ref" in schema:
                ref_path = schema["$ref"]
                # Extract the definition name from "#/$defs/DefinitionName"
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path.split("/")[-1]
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
