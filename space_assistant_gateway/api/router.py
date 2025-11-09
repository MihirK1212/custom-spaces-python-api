from __future__ import annotations

from fastapi import APIRouter, Depends

from space_assistant_gateway.api.schemas import ChatRequest, ChatResponse
from space_assistant_gateway.orchestration.orchestrator import ConversationOrchestrator


def get_orchestrator() -> ConversationOrchestrator:
	return ConversationOrchestrator()


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, orchestrator: ConversationOrchestrator = Depends(get_orchestrator)) -> ChatResponse:
	if body.agent_name:
		orchestrator.agent_name = body.agent_name
	response = await orchestrator.handle_messages(messages=body.messages, user_context=body.user_context)
	return ChatResponse(response=response)


