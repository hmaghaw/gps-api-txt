"""
Stage 4: Decision logic — wires stages 1-3 together and produces the final
allow / rewrite / reject verdict. Each branch is annotated with the BRD test
case(s) it implements (v2.2, section 6.3.1).
"""

from dataclasses import dataclass

from app.config import (
    AGGRESSIVE_POLICY,
    AMBIGUOUS_POLICY,
    CONFIDENCE_THRESHOLD,
    HARD_REJECT_CATEGORIES,
    MAX_WORD_COUNT,
    REWRITABLE_CATEGORIES,
)
from app.pipeline.classify import classify_message
from app.pipeline.language import detect_language
from app.pipeline.rewrite import rewrite_message, word_count


@dataclass
class PipelineResult:
    decision: str
    final_message: str | None
    categories: list[str]
    confidence: float
    word_count: int
    guidance: str | None


def run_pipeline(message: str) -> PipelineResult:
    # --- Stage 1: input validation (TXT-09) ---
    if not message or not message.strip():
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["invalid_input"],
            confidence=1.0,
            word_count=0,
            guidance="Message is empty. Please provide marketing content.",
        )

    # --- Stage 2: language gate (TXT-08, TXT-10 residual risk) ---
    lang = detect_language(message)
    if not lang.is_english:
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["unsupported_language"],
            confidence=lang.confidence,
            word_count=word_count(message),
            guidance="Unsupported language — English only.",
        )

    # --- Stage 3: classification (TXT-01..TXT-06) ---
    result = classify_message(message)
    categories = set(result.categories)
    confidence = result.confidence

    # TXT-01: clean / compliant
    if not categories:
        wc = word_count(message)

        # Content is clean, and within the platform's word cap (BRD 6.1:
        # "~20 words, hard cap 30") — pass through unchanged.
        if wc <= MAX_WORD_COUNT:
            return PipelineResult(
                decision="allow",
                final_message=message.strip(),
                categories=[],
                confidence=confidence,
                word_count=wc,
                guidance=None,
            )

        # Content is clean but OVER the word cap. The cap applies to every
        # outgoing message, not just ones that tripped a moderation
        # category, so this still needs to go through rewrite — shortening
        # only, no content issue to flag. `["length"]` is a synthetic,
        # non-moderation category (see rewrite.py / schemas.py) so the
        # response doesn't misleadingly imply profanity/hate/etc.
        rewritten = rewrite_message(message, ["length"])
        rw_wc = word_count(rewritten)

        if rw_wc > MAX_WORD_COUNT:
            # Shouldn't normally happen — rewrite_message enforces the cap
            # itself — but kept as a backstop (mirrors the TXT-07 check
            # further down for the moderation-triggered rewrite path).
            return PipelineResult(
                decision="reject",
                final_message=None,
                categories=["length_exceeded"],
                confidence=confidence,
                word_count=rw_wc,
                guidance=f"Message exceeds the {MAX_WORD_COUNT}-word limit. Please shorten and resubmit.",
            )

        return PipelineResult(
            decision="rewrite",
            final_message=rewritten,
            categories=["length"],
            confidence=confidence,
            word_count=rw_wc,
            guidance=None,
        )

    # TXT-03 / TXT-04: hard-reject categories, never rewritten
    if categories & HARD_REJECT_CATEGORIES:
        triggered = sorted(categories & HARD_REJECT_CATEGORIES)
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=triggered,
            confidence=confidence,
            word_count=word_count(message),
            guidance=f"Message rejected due to: {', '.join(triggered)}. Please revise and resubmit.",
        )

    # TXT-06: low-confidence / ambiguous — routed per configured policy
    if confidence < CONFIDENCE_THRESHOLD:
        if AMBIGUOUS_POLICY == "reject":
            return PipelineResult(
                decision="reject",
                final_message=None,
                categories=["ambiguous"],
                confidence=confidence,
                word_count=word_count(message),
                guidance="Message confidence below threshold; manual review recommended.",
            )
        categories = categories | {"ambiguous"}  # fall through to rewrite path

    # TXT-05: aggressive/threatening — policy-driven (open decision, see config.py)
    if "aggressive" in categories and AGGRESSIVE_POLICY == "reject":
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["aggressive"],
            confidence=confidence,
            word_count=word_count(message),
            guidance="Message rejected due to aggressive/threatening tone. Please revise and resubmit.",
        )

    # TXT-02 (+ TXT-05 if AGGRESSIVE_POLICY == "rewrite"): rewrite-eligible
    rewritten = rewrite_message(message, sorted(categories))
    wc = word_count(rewritten)

    # TXT-07: rewrite still exceeds the hard cap
    if wc > MAX_WORD_COUNT:
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["length_exceeded"],
            confidence=confidence,
            word_count=wc,
            guidance=f"Rewritten message exceeds {MAX_WORD_COUNT}-word limit. Please shorten and resubmit.",
        )

    return PipelineResult(
        decision="rewrite",
        final_message=rewritten,
        categories=sorted(categories),
        confidence=confidence,
        word_count=wc,
        guidance=None,
    )
