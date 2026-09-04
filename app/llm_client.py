"""
Shared OpenAI client.

Both pipeline/classify.py and pipeline/rewrite.py import get_client() from
here instead of building their own client, so there is exactly one place
that reads the API key/model/endpoint (all sourced from app/config.py,
which in turn loads them from .env). To switch providers or point at a
different OpenAI-compatible endpoint, only config.py / .env need to change.
"""

from functools import lru_cache

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_REQUEST_TIMEOUT


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env in the "
            "project root and fill in a real key, or set the OPENAI_API_KEY "
            "environment variable directly."
        )

    kwargs = {"api_key": OPENAI_API_KEY, "timeout": OPENAI_REQUEST_TIMEOUT}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL

    return OpenAI(**kwargs)
