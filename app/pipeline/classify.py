"""
Stage 2+3 (combined): Language detection + moderation classification.

A single OpenAI call now does both jobs that used to be two pipeline
stages: detect the message's language (ISO 639-1 code + confidence), and
flag moderation categories (profanity, hate, sexual, aggressive) + an
overall confidence — evaluated IN the detected language, not assumed to be
English. One round-trip instead of two, and the categories are defined
abstractly (not via English example word lists) so the same prompt applies
regardless of which language the message turns out to be in.

decide.py is responsible for checking the detected language against
SUPPORTED_LANGUAGES (app/languages.py) before trusting the moderation
categories — this module only reports what it found.
"""

import json
from dataclasses import dataclass, field

from app.config import OPENAI_MODEL
from app.llm_client import get_client

ALLOWED_CATEGORIES = {"profanity", "hate", "sexual", "aggressive"}

SYSTEM_PROMPT = (
    "You are a content moderation classifier for SMS/MMS marketing messages "
    "sent by small businesses to nearby customers on a geo-targeted offers "
    "platform. The platform supports multiple languages, so first identify "
    "the message's language, then evaluate it for moderation issues IN "
    "THAT LANGUAGE — do not assume English, and do not require translation "
    "to English before evaluating.\n\n"
    "Step 1 - language: identify the message's primary language as an "
    "ISO 639-1 two-letter code (e.g. 'en', 'es', 'fr', 'ar'). If you cannot "
    "confidently identify a real language (e.g. gibberish, a single emoji, "
    "mixed nonsense), use 'unknown' with low confidence.\n\n"
    "Step 2 - moderation: decide which of these categories apply, "
    "evaluated in the message's own language and cultural context:\n"
    "- profanity: swearing / foul language\n"
    "- hate: racist or discriminatory wording\n"
    "- sexual: sexual or suggestive content\n"
    "- aggressive: aggressive or threatening phrasing\n"
    "A clean, professional marketing message has no categories flagged.\n\n"
    "Respond with ONLY a JSON object, no other text, in this exact shape:\n"
    '{"language": "<ISO 639-1 code or unknown>", "language_confidence": <0.0-1.0>, '
    '"categories": ["<subset of the four above>"], "confidence": <0.0-1.0>}\n'
    "confidence is your confidence in the moderation classification overall, "
    "not per-category. language_confidence is separate and reflects only "
    "how sure you are of the detected language."
)


@dataclass
class ClassificationResult:
    language: str = "unknown"  # ISO 639-1 code, or "unknown"
    language_confidence: float = 0.0
    categories: list[str] = field(default_factory=list)  # subset of: profanity, hate, sexual, aggressive
    confidence: float = 1.0  # confidence in the moderation classification itself


def classify_message(text: str) -> ClassificationResult:
    """
    Calls the OpenAI chat completions API with a JSON-mode system prompt and
    parses the structured result (language + moderation categories in one
    round-trip). On any failure (missing key, network error, malformed
    response), fails closed rather than silently allowing unmoderated or
    unlanguage-checked content through — see the except branch below.
    """
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        language = str(data.get("language", "unknown")).strip().lower() or "unknown"
        language_confidence = max(0.0, min(1.0, float(data.get("language_confidence", 0.0))))

        categories = [c for c in data.get("categories", []) if c in ALLOWED_CATEGORIES]
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))

        return ClassificationResult(
            language=language,
            language_confidence=language_confidence,
            categories=categories,
            confidence=confidence,
        )
    except Exception:
        # Fail closed on BOTH axes: unknown language (so the language gate
        # in decide.py rejects it rather than guessing) and a non-empty,
        # non-hard-reject moderation category with confidence 0.0 (so even
        # if the language gate were somehow bypassed, decide.py's
        # ambiguous-content branch still catches it instead of silently
        # allowing the message through).
        return ClassificationResult(
            language="unknown",
            language_confidence=0.0,
            categories=["aggressive"],
            confidence=0.0,
        )
