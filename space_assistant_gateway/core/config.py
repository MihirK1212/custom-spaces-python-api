from __future__ import annotations

import functools
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import dotenv

dotenv.load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SPACE_ASSISTANT_",
        case_sensitive=False,
    )

    api_prefix: str = "/api"
    default_agent_name: str = "claude_todo_list"
    anthropic_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    claude_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("CLAUDE_MODEL")
    )


@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

