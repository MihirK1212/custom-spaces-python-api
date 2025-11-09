from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from space_assistant_gateway.api.router import router as assistant_router
from space_assistant_gateway.core.config import get_settings


def create_app() -> FastAPI:
	settings = get_settings()
	app = FastAPI(title="Space Assistant Gateway", version="0.1.0")
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	app.include_router(assistant_router, prefix=settings.api_prefix, tags=["assistant"])
	return app


app = create_app()
