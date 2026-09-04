"""
Central configuration and policy thresholds for API-TXT.

IMPORTANT — two values below implement decisions the BRD (v2.2, section 6.3.1)
explicitly left open (see TXT-05 and TXT-06 notes). Sensible defaults are set
so the service is testable end-to-end now, but these should be confirmed with
GPS Special and updated here once agreed — nothing else in the codebase should
need to change.

LLM configuration (OPENAI_*) is loaded from a .env file (or real environment
variables) rather than hardcoded, so the key/model can be changed without
touching code. Copy .env.example to .env and fill it in.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Loads /.env (project root, one level up from app/) if present. Real
# environment variables (e.g. set by docker-compose's env_file, or by the
# host shell) always win — override=False means load_dotenv will not
# clobber a variable that's already set in the environment.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

# --- LLM / OpenAI configuration ---
# Used by app/llm_client.py, and from there by pipeline/classify.py and
# pipeline/rewrite.py. Nothing else in the codebase should need to change
# to swap keys, models, or point at an OpenAI-compatible endpoint.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_REQUEST_TIMEOUT = float(os.getenv("OPENAI_REQUEST_TIMEOUT", "20"))

# --- TXT-06: confidence threshold for ambiguous / borderline content ---
# Below this, content is treated as low-confidence and routed per
# AMBIGUOUS_POLICY. At/above this, the classifier's flagged category applies
# normally.
CONFIDENCE_THRESHOLD = 0.7

# --- TXT-06: what happens at/under the threshold ---
# "reject" = safest default (fail closed). Flip to "rewrite" if the customer
# prefers to attempt a rewrite for borderline content instead.
AMBIGUOUS_POLICY = "reject"

# --- TXT-05: aggressive / threatening tone policy ---
# "reject" = hard reject, no rewrite attempted (same treatment as hate/sexual).
# "rewrite" = attempt to soften tone while preserving intent, like profanity.
# Default is the more conservative "reject" until the customer decides.
AGGRESSIVE_POLICY = "reject"

# --- Message length rules (BRD section 6.1) ---
TARGET_WORD_COUNT = 20
MAX_WORD_COUNT = 30

# Categories that are always a hard reject regardless of confidence —
# no rewrite is ever attempted for these (BRD: TXT-03, TXT-04).
HARD_REJECT_CATEGORIES = {"hate", "sexual"}

# Category that is eligible for rewrite (BRD: TXT-02).
REWRITABLE_CATEGORIES = {"profanity"}

# Reflects that classify/rewrite are now backed by a real OpenAI model
# rather than the earlier stub. Shown in the API response metadata.
MODEL_VERSION = f"txt-moderation-v0.2-openai:{OPENAI_MODEL}"
