from __future__ import annotations

import sys
from functools import lru_cache

sys.path.append("..")
sys.path.append(".")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from space_assistant_gateway.api.router import (
    get_orchestrator,
    router as assistant_router,
)
from space_assistant_gateway.core.config import (
    GatewayConfig,
    get_settings,
)
from space_assistant_gateway.orchestration.orchestrator import ConversationOrchestrator


def create_app(*, config: GatewayConfig) -> FastAPI:
    """
    Create a FastAPI app with minimal configuration.

    Developers can either:
    - pass a pre-built ConversationOrchestrator instance, or
    - provide a GatewayConfig describing agent builders and storage/queue options.
    """

    settings = get_settings()
    gateway_config = config

    @lru_cache()
    def orchestrator_factory() -> ConversationOrchestrator:
        return ConversationOrchestrator(config=gateway_config)

    app = FastAPI(title="Space Assistant Gateway", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.dependency_overrides[get_orchestrator] = orchestrator_factory
    app.include_router(assistant_router, prefix=settings.api_prefix, tags=["assistant"])
    return app


def enrich_app_with_assistant_router(
    *, app: FastAPI, config: GatewayConfig, api_prefix: str
) -> FastAPI:
    """
    Enrich a FastAPI app with the assistant router.
    """

    gateway_config = config

    @lru_cache()
    def orchestrator_factory() -> ConversationOrchestrator:
        return ConversationOrchestrator(config=gateway_config)

    app.dependency_overrides[get_orchestrator] = orchestrator_factory
    app.include_router(assistant_router, prefix=api_prefix, tags=["assistant"])
    return app


app = create_app()
