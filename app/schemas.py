from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    allow = "allow"
    rewrite = "rewrite"
    reject = "reject"


class Category(str, Enum):
    profanity = "profanity"
    hate = "hate"
    sexual = "sexual"
    aggressive = "aggressive"
    ambiguous = "ambiguous"
    # Clean content that was shortened only because it exceeded the word
    # cap — distinct from length_exceeded, which means shortening wasn't
    # enough and the message was rejected.
    length = "length"
    length_exceeded = "length_exceeded"
    unsupported_language = "unsupported_language"
    invalid_input = "invalid_input"


class ModerateTextRequest(BaseModel):
    message: str = Field(..., description="Raw marketing message drafted by the business owner")
    business_id: Optional[str] = Field(None, description="Used for logging / owner notification")
    locale_hint: Optional[str] = Field(
        None,
        description=(
            "Optional ISO 639-1 hint (e.g. 'es'). Does not bypass the language "
            "gate or override detection — language is always auto-detected from "
            "the message itself; this is reserved for future use as a tie-breaker."
        ),
    )


class ResponseMetadata(BaseModel):
    processing_ms: int
    model_version: str


class ModerateTextResponse(BaseModel):
    decision: Decision
    original_message: str
    final_message: Optional[str] = None
    categories: list[Category] = []
    confidence: float = 0.0
    word_count: int = 0
    guidance: Optional[str] = None
    # Multi-language: the language the input was detected as (ISO 639-1
    # code, or "unknown"), and the detector's confidence in that call.
    # Always populated, even on allow/rewrite, not just on language-based
    # rejections.
    detected_language: str = "unknown"
    language_confidence: float = 0.0
    metadata: ResponseMetadata
