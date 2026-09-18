"""
Language gate.

Detection itself now happens inside pipeline/classify.py's single OpenAI
call (one round-trip covers both language ID and moderation, evaluated in
the detected language). This module just answers the gate question: given
what classify_message reported, is this message eligible to proceed?

Firm rule, same shape as the original English-only rule, generalized:
only languages listed in SUPPORTED_LANGUAGES (.env) are accepted, and only
when detected with at least LANG_CONFIDENCE_THRESHOLD confidence. Anything
else is rejected on language grounds without any further content
assessment — the moderation categories from that same call are not used
for unsupported/low-confidence languages.

Known limitation, same class of risk as the original English-only design:
detection is not perfect and can be evaded (e.g. one supported language's
slurs/hate speech transliterated to look like another, or text rendered as
an image rather than plain text — the latter is out of scope for API-TXT).
Vendor cannot guarantee detection in these edge cases.
"""

from dataclasses import dataclass

from languages import is_supported


@dataclass
class LanguageGateResult:
    passed: bool
    language: str
    confidence: float


def check_language(language: str, confidence: float) -> LanguageGateResult:
    return LanguageGateResult(
        passed=is_supported(language, confidence),
        language=language,
        confidence=confidence,
    )
