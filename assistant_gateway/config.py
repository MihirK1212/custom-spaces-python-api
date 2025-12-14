from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, AnyHttpUrl, Field


class Settings(BaseModel):
	env: str = Field(default=os.getenv("APP_ENV", "development"))
	api_prefix: str = "/assistant"
	# Base URL for the NestJS CRUD backend
	crud_base_url: AnyHttpUrl | str = Field(default=os.getenv("CRUD_BASE_URL", "http://localhost:5000"))
	# Optional API key or bearer token for CRUD backend
	crud_api_key: Optional[str] = Field(default=os.getenv("CRUD_API_KEY"))
	crud_bearer_token: Optional[str] = Field(default=os.getenv("CRUD_BEARER_TOKEN"))

	# Default agent to use
	default_agent: str = Field(default=os.getenv("DEFAULT_AGENT", "simple"))

	# Claude / LangGraph config placeholders
	anthropic_api_key: Optional[str] = Field(default=os.getenv("ANTHROPIC_API_KEY"))


@lru_cache()
def get_settings() -> Settings:
	return Settings()


