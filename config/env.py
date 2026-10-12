"""Load environment variables from the project .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_LOADED = False


def load_project_env() -> None:
    """Load variables from the project-root .env file once."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(PROJECT_ROOT / ".env")
    _ENV_LOADED = True


def get_openai_api_key() -> str:
    """Return OPENAI_API_KEY or raise a clear configuration error."""
    load_project_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.strip() in {"", "sk-xxxxxxxxxxxxxxxxxxxxxxxx"}:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Define it in the .env file at the project root:\n"
            "  OPENAI_API_KEY=sk-...\n"
            "Copy .env.example to .env if needed."
        )
    return api_key
