"""
Multi-language configuration.

Two moving parts, deliberately kept separate:

- `.env` (SUPPORTED_LANGUAGES) — the on/off switch. Which languages this
  deployment currently accepts. Easy to change per-environment without a
  code push (e.g. staging tests 2 languages, prod enables 6).
- `languages.json` (project root, alongside this file's grandparent) — how
  each language behaves once it's on: word-count caps, whether rewrite is
  offered at all for that language, and a per-language moderation
  confidence threshold (a threshold tuned on English data is not
  guaranteed to transfer cleanly to lower-resource languages).

Every code listed in SUPPORTED_LANGUAGES must have a matching entry in
languages.json — this module fails loudly at import time if not, rather
than falling back to silent defaults at request time.
"""

import json
from pathlib import Path

from app.config import DEFAULT_LANGUAGE, LANG_CONFIDENCE_THRESHOLD, SUPPORTED_LANGUAGES

_SCHEMA_PATH = Path(__file__).resolve().parent / "languages.json"

_REQUIRED_KEYS = {"name", "max_words", "target_words", "rewrite_enabled", "moderation_confidence_threshold"}


def _load_schema() -> dict:
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"languages.json not found at {_SCHEMA_PATH}. Every language listed in "
            "SUPPORTED_LANGUAGES (.env) needs a matching entry there."
        ) from exc

    missing_entries = [code for code in SUPPORTED_LANGUAGES if code not in raw]
    if missing_entries:
        raise RuntimeError(
            f"SUPPORTED_LANGUAGES (.env) lists {missing_entries}, but languages.json has no "
            "entry for them. Add a schema entry for each before starting the service."
        )

    for code in SUPPORTED_LANGUAGES:
        missing_keys = _REQUIRED_KEYS - raw[code].keys()
        if missing_keys:
            raise RuntimeError(f"languages.json entry '{code}' is missing required keys: {missing_keys}")

    if DEFAULT_LANGUAGE not in SUPPORTED_LANGUAGES:
        raise RuntimeError(
            f"DEFAULT_LANGUAGE ('{DEFAULT_LANGUAGE}') must be included in SUPPORTED_LANGUAGES "
            f"({sorted(SUPPORTED_LANGUAGES)})."
        )

    # Only keep schema entries this deployment actually has enabled.
    return {code: raw[code] for code in SUPPORTED_LANGUAGES}


LANGUAGE_SCHEMA = _load_schema()


def is_supported(language_code: str, confidence: float) -> bool:
    """Gate used by the pipeline: language must both be in the enabled set
    AND be detected with enough confidence to trust the moderation/rewrite
    calls that follow (see LANG_CONFIDENCE_THRESHOLD in .env)."""
    return language_code in LANGUAGE_SCHEMA and confidence >= LANG_CONFIDENCE_THRESHOLD


def get_language_settings(language_code: str) -> dict:
    """Per-language behavior. Callers should only reach this after
    is_supported() has already returned True."""
    return LANGUAGE_SCHEMA[language_code]


def supported_language_names() -> dict:
    """code -> display name, for docs/UI/error messages."""
    return {code: cfg["name"] for code, cfg in LANGUAGE_SCHEMA.items()}
