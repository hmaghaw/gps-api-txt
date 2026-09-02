"""
Stage 2: Language gate (BRD section 6.3.3 — Scope Boundary, Language Coverage).

Firm rule: only English content is moderated. Anything else is rejected on
language grounds without any content assessment (TXT-08).

Known limitation (TXT-10, documented in the BRD as residual risk, not a
defect): non-English content transliterated into Latin script, or slurs
mixed into an otherwise-English message, may be misclassified as English
and passed through to the moderation stage. This skeleton uses a placeholder
detector — swap `detect_language` for a real library/service
(e.g. `langdetect`, `fasttext`, or a cloud language-detection API) before
production use.
"""

from dataclasses import dataclass


@dataclass
class LanguageCheckResult:
    is_english: bool
    detected_language: str
    confidence: float


def detect_language(text: str) -> LanguageCheckResult:
    """
    Placeholder implementation.

    TODO: replace with a real detector. Suggested options:
      - `langdetect` / `lingua-py` for a fast local check
      - a cloud NLP API if you want higher accuracy on short strings
        (marketing messages are often short, which hurts local detectors)
    """
    stripped = text.strip()
    if not stripped:
        return LanguageCheckResult(is_english=False, detected_language="unknown", confidence=0.0)

    # Naive placeholder: flag if the text is dominated by non-ASCII letters.
    non_ascii = sum(1 for ch in stripped if ord(ch) > 127)
    ratio_non_ascii = non_ascii / max(len(stripped), 1)
    is_english = ratio_non_ascii < 0.2

    return LanguageCheckResult(
        is_english=is_english,
        detected_language="en" if is_english else "non-en",
        confidence=1.0 - ratio_non_ascii,
    )
