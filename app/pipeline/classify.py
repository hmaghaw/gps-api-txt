"""
Stage 3: Classification (BRD TXT-01..TXT-06).

Calls OpenAI to flag moderation categories and a confidence score for a
message. Replaces the earlier always-clean stub.
"""

import json
from dataclasses import dataclass, field

from app.config import OPENAI_MODEL
from app.llm_client import get_client

ALLOWED_CATEGORIES = {"profanity", "hate", "sexual", "aggressive"}

SYSTEM_PROMPT = (
    "You are a content moderation classifier for SMS/MMS marketing messages "
    "sent by small businesses to nearby customers on a geo-targeted offers "
    "platform. Given a message, decide which of these categories apply: "
    "profanity, hate, sexual, aggressive.\n"
    "- profanity: swearing / foul language\n"
    "- hate: racist or discriminatory wording\n"
    "- sexual: sexual or suggestive content\n"
    "- aggressive: aggressive or threatening phrasing\n"
    "A clean, professional marketing message has no categories flagged.\n"
    "Respond with ONLY a JSON object, no other text, in this exact shape:\n"
    '{"categories": ["<subset of the four above>"], "confidence": <0.0-1.0>}\n'
    "confidence is your confidence in this classification overall, not per-category."
)


@dataclass
class ClassificationResult:
    categories: list[str] = field(default_factory=list)  # subset of: profanity, hate, sexual, aggressive
    confidence: float = 1.0  # confidence in the classification itself


def classify_message(text: str) -> ClassificationResult:
    """
    Calls the OpenAI chat completions API with a JSON-mode system prompt and
    parses the structured result. On any failure (missing key, network
    error, malformed response), fails closed rather than silently allowing
    unmoderated content through — see the except branch below.
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

        categories = [c for c in data.get("categories", []) if c in ALLOWED_CATEGORIES]
        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return ClassificationResult(categories=categories, confidence=confidence)
    except Exception:
        # Fail closed: an empty categories list would route straight to
        # "allow" in decide.py regardless of confidence, so on error we
        # return a non-empty, non-hard-reject category with confidence 0.0.
        # That routes through decide.py's TXT-06 ambiguous-content branch
        # (AMBIGUOUS_POLICY) instead of silently allowing the message
        # through — flip AMBIGUOUS_POLICY in config.py if "rewrite" is the
        # preferred failure mode instead of "reject".
        return ClassificationResult(categories=["aggressive"], confidence=0.0)