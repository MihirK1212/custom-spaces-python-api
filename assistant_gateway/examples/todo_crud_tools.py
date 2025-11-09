from __future__ import annotations

from assistant_gateway.tools.registry import ToolRegistry
from assistant_gateway.tools.rest_tool import RESTTool


def register_basic_crud_tools(registry: ToolRegistry) -> None:
	"""
	Register simple, composable tools for a typical TODO CRUD API.
	This is optional since the generic 'crud.rest' tool exists,
	but named tools improve agent affordances.
	"""
	registry.register(RESTTool(name="todo.list", description="List todos. GET /todos"))
	registry.register(RESTTool(name="todo.get", description="Get a todo by id. GET /todos/{id}"))
	registry.register(RESTTool(name="todo.create", description="Create a todo. POST /todos"))
	registry.register(RESTTool(name="todo.update", description="Update a todo. PUT or PATCH /todos/{id}"))
	registry.register(RESTTool(name="todo.delete", description="Delete a todo. DELETE /todos/{id}"))


def register_default_crud_suite(registry: ToolRegistry) -> ToolRegistry:
	"""
	Register the generic CRUD REST tool plus the optional named affordances.
	"""

	if registry.get("crud.rest") is None:
		registry.register(
			RESTTool(
				name="crud.rest",
				description="Call the CRUD backend using arbitrary HTTP method/path.",
			)
		)
	register_basic_crud_tools(registry)
	return registry
