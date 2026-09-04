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
    locale_hint: Optional[str] = Field(None, description="Optional hint, does not bypass the language gate")


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
    metadata: ResponseMetadata