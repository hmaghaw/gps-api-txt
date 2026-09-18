"""
Decision logic - wires the pipeline stages together and produces the final
allow / rewrite / reject verdict. Each branch is annotated with the BRD
test case(s) it originally implemented (v2.2, section 6.3.1); TXT-08/TXT-10
now generalize from "English-only" to "any SUPPORTED_LANGUAGES language".

Pipeline order (multi-language):
  1. Input validation (TXT-09)
  2. classify_message: ONE OpenAI call returns both the detected language
     and the moderation categories/confidence, evaluated in that language.
  3. Language gate: detected language must be in SUPPORTED_LANGUAGES at
     >= LANG_CONFIDENCE_THRESHOLD confidence, or reject (generalizes TXT-08).
  4. Everything downstream (word caps, confidence threshold, rewrite
     eligibility) uses that language's own settings from languages.json,
     not a single global value.
"""

from dataclasses import dataclass

from app.config import AGGRESSIVE_POLICY, AMBIGUOUS_POLICY, HARD_REJECT_CATEGORIES
from languages import get_language_settings
from app.pipeline.classify import classify_message
from app.pipeline.language import check_language
from app.pipeline.rewrite import rewrite_message, word_count


@dataclass
class PipelineResult:
    decision: str
    final_message: str | None
    categories: list[str]
    confidence: float
    word_count: int
    guidance: str | None
    detected_language: str
    language_confidence: float


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
            detected_language="unknown",
            language_confidence=0.0,
        )

    # --- Stage 2: language detection + moderation classification (one call) ---
    result = classify_message(message)
    categories = set(result.categories)
    confidence = result.confidence
    language = result.language
    language_confidence = result.language_confidence

    # --- Stage 3: language gate (generalizes TXT-08 / TXT-10) ---
    gate = check_language(language, language_confidence)
    if not gate.passed:
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["unsupported_language"],
            confidence=language_confidence,
            word_count=word_count(message),
            guidance=(
                f"Unsupported or unrecognized language (detected: '{language}', "
                f"confidence: {language_confidence:.2f})."
            ),
            detected_language=language,
            language_confidence=language_confidence,
        )

    settings = get_language_settings(language)
    max_words = settings["max_words"]
    rewrite_enabled = settings["rewrite_enabled"]
    lang_confidence_threshold = settings["moderation_confidence_threshold"]

    # TXT-01: clean / compliant
    if not categories:
        wc = word_count(message)

        # Content is clean, and within this language's word cap - pass
        # through unchanged.
        if wc <= max_words:
            return PipelineResult(
                decision="allow",
                final_message=message.strip(),
                categories=[],
                confidence=confidence,
                word_count=wc,
                guidance=None,
                detected_language=language,
                language_confidence=language_confidence,
            )

        # Content is clean but OVER the word cap. The cap applies to every
        # outgoing message, not just ones that tripped a moderation
        # category. `["length"]` is a synthetic, non-moderation category
        # so the response doesn't misleadingly imply profanity/hate/etc.
        if not rewrite_enabled:
            return PipelineResult(
                decision="reject",
                final_message=None,
                categories=["length_exceeded"],
                confidence=confidence,
                word_count=wc,
                guidance=(
                    f"Message exceeds the {max_words}-word limit for "
                    f"{settings['name']}, and rewrite is not enabled for this "
                    "language. Please shorten and resubmit."
                ),
                detected_language=language,
                language_confidence=language_confidence,
            )

        rewritten = rewrite_message(message, ["length"], language)
        rw_wc = word_count(rewritten)

        if rw_wc > max_words:
            # Shouldn't normally happen - rewrite_message enforces the cap
            # itself - but kept as a backstop.
            return PipelineResult(
                decision="reject",
                final_message=None,
                categories=["length_exceeded"],
                confidence=confidence,
                word_count=rw_wc,
                guidance=f"Message exceeds the {max_words}-word limit. Please shorten and resubmit.",
                detected_language=language,
                language_confidence=language_confidence,
            )

        return PipelineResult(
            decision="rewrite",
            final_message=rewritten,
            categories=["length"],
            confidence=confidence,
            word_count=rw_wc,
            guidance=None,
            detected_language=language,
            language_confidence=language_confidence,
        )

    # TXT-03 / TXT-04: hard-reject categories, never rewritten - language-agnostic
    if categories & HARD_REJECT_CATEGORIES:
        triggered = sorted(categories & HARD_REJECT_CATEGORIES)
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=triggered,
            confidence=confidence,
            word_count=word_count(message),
            guidance=f"Message rejected due to: {', '.join(triggered)}. Please revise and resubmit.",
            detected_language=language,
            language_confidence=language_confidence,
        )

    # TXT-06: low-confidence / ambiguous - per-language threshold
    if confidence < lang_confidence_threshold:
        if AMBIGUOUS_POLICY == "reject":
            return PipelineResult(
                decision="reject",
                final_message=None,
                categories=["ambiguous"],
                confidence=confidence,
                word_count=word_count(message),
                guidance="Message confidence below threshold; manual review recommended.",
                detected_language=language,
                language_confidence=language_confidence,
            )
        categories = categories | {"ambiguous"}  # fall through to rewrite path

    # TXT-05: aggressive/threatening - policy-driven (open decision, see config.py)
    if "aggressive" in categories and AGGRESSIVE_POLICY == "reject":
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["aggressive"],
            confidence=confidence,
            word_count=word_count(message),
            guidance="Message rejected due to aggressive/threatening tone. Please revise and resubmit.",
            detected_language=language,
            language_confidence=language_confidence,
        )

    # Rewrite-eligible category triggered, but this language has rewrite disabled
    if not rewrite_enabled:
        triggered = sorted(categories)
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=triggered,
            confidence=confidence,
            word_count=word_count(message),
            guidance=(
                f"Message rejected due to: {', '.join(triggered)}. Rewrite is not "
                f"enabled for {settings['name']}; please revise and resubmit."
            ),
            detected_language=language,
            language_confidence=language_confidence,
        )

    # TXT-02 (+ TXT-05 if AGGRESSIVE_POLICY == "rewrite"): rewrite-eligible
    rewritten = rewrite_message(message, sorted(categories), language)
    wc = word_count(rewritten)

    # TXT-07: rewrite still exceeds this language's hard cap
    if wc > max_words:
        return PipelineResult(
            decision="reject",
            final_message=None,
            categories=["length_exceeded"],
            confidence=confidence,
            word_count=wc,
            guidance=f"Rewritten message exceeds {max_words}-word limit. Please shorten and resubmit.",
            detected_language=language,
            language_confidence=language_confidence,
        )

    return PipelineResult(
        decision="rewrite",
        final_message=rewritten,
        categories=sorted(categories),
        confidence=confidence,
        word_count=wc,
        guidance=None,
        detected_language=language,
        language_confidence=language_confidence,
    )
