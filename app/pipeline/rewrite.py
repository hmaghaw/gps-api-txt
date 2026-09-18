"""
Stage 5: Rewrite.

Called from decide.py in two situations:
  1. A moderation category was flagged (e.g. profanity) - sanitise + shorten.
  2. The message is otherwise clean but over its language's word cap -
     shorten only, via the synthetic ["length"] category (no moderation
     issue exists).

Multi-language: the model is explicitly told which language to rewrite IN
(never translates to English), and the word-count target/cap come from
that language's entry in languages.json rather than a single global value
- some languages read naturally longer or shorter than English at the same
information density.

IMPORTANT: the word cap is enforced here in code, not just via the prompt.
Models don't reliably self-count words (and "words" is itself a fuzzier
concept for some scripts), so a first response that comes back over the
cap triggers one shortening retry, then a hard truncation as a last
resort. This guarantees the cap holds regardless of language or which path
called it.
"""

from app.config import OPENAI_MODEL
from languages import get_language_settings
from app.llm_client import get_client

MODERATION_PROMPT_TEMPLATE = (
    "You rewrite SMS/MMS marketing messages for a geo-targeted local-offers "
    "platform so they are safe to broadcast. The message is in {language_name} "
    "({language_code}) - write your rewrite in {language_name} as well. Do NOT "
    "translate it to another language.\n"
    "The original message was flagged for: {categories}.\n"
    "Rewrite it to:\n"
    "- remove or neutralise the flagged issue(s) while preserving the "
    "business's actual offer/intent\n"
    "- keep a professional, inclusive, and compelling marketing tone, "
    "natural for a {language_name}-speaking audience\n"
    "- target about {target} words, and NEVER exceed {max_words} words - "
    "count your words before answering\n"
    "Respond with ONLY the rewritten message text, nothing else - no "
    "quotes, no preamble, no explanation."
)

# Used when the message has NO moderation issue and only needs shortening
# (decide.py's clean-but-over-the-cap branch). Deliberately does not mention
# profanity/hate/etc. - there is nothing to sanitise, only to trim.
LENGTH_ONLY_PROMPT_TEMPLATE = (
    "You shorten SMS/MMS marketing messages for a geo-targeted local-offers "
    "platform. The message is in {language_name} ({language_code}) - write "
    "your shortened version in {language_name} as well. Do NOT translate it "
    "to another language.\n"
    "The message below is already compliant and professional - it simply "
    "exceeds the platform's word limit for {language_name}.\n"
    "Rewrite it to:\n"
    "- preserve the business's offer/intent and professional tone exactly\n"
    "- NOT remove or soften any content for moderation reasons - there is none\n"
    "- target about {target} words, and NEVER exceed {max_words} words - "
    "count your words before answering\n"
    "Respond with ONLY the rewritten message text, nothing else - no "
    "quotes, no preamble, no explanation."
)

RETRY_SUFFIX = (
    "\n\nYour previous attempt was {prev_count} words, which is over the "
    "{max_words}-word hard cap for {language_name}. Rewrite it again, "
    "shorter - {max_words} words or fewer, ideally close to {target}, "
    "still in {language_name}. Respond with ONLY the rewritten message text."
)


def word_count(text: str) -> int:
    return len(text.split())


def _truncate_to_word_limit(text: str, limit: int) -> str:
    """Last-resort hard cap: cut to `limit` words. Only reached if the
    model ignores both the prompt and the retry, so this exists purely as
    a guarantee, not the expected path. Note: word-splitting on whitespace
    is a reasonable approximation for space-delimited languages, but is
    cruder for others (e.g. some CJK text) - the retry step above is the
    primary mechanism; this is only a final backstop."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(",;:") + "…"


def _build_system_prompt(categories: list[str], language: str) -> str:
    settings = get_language_settings(language)
    language_name = settings["name"]
    target = settings["target_words"]
    max_words = settings["max_words"]

    if categories == ["length"]:
        return LENGTH_ONLY_PROMPT_TEMPLATE.format(
            language_name=language_name, language_code=language, target=target, max_words=max_words
        )
    return MODERATION_PROMPT_TEMPLATE.format(
        language_name=language_name,
        language_code=language,
        categories=", ".join(categories) or "none",
        target=target,
        max_words=max_words,
    )


def _call_llm(client, system: str, user_text: str) -> str:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
    )
    return (response.choices[0].message.content or "").strip()


def rewrite_message(text: str, categories: list[str], language: str) -> str:
    """
    Calls OpenAI to rewrite `text` (in `language`) given `categories`
    (either real moderation categories, or the synthetic ["length"] marker
    for a shorten-only pass), then enforces that language's max_words cap
    in code - see module docstring. On any API failure, falls back to the
    original text; decide.py's own length check downstream still applies
    as a final backstop.
    """
    settings = get_language_settings(language)
    max_words = settings["max_words"]
    target = settings["target_words"]
    language_name = settings["name"]

    try:
        client = get_client()
        system = _build_system_prompt(categories, language)

        rewritten = _call_llm(client, system, text)
        if not rewritten:
            return text.strip()

        wc = word_count(rewritten)
        if wc > max_words:
            # One shortening retry, explicitly telling it how far over it was.
            retry_system = system + RETRY_SUFFIX.format(
                prev_count=wc, max_words=max_words, target=target, language_name=language_name
            )
            retried = _call_llm(client, retry_system, text)
            if retried:
                rewritten = retried

        if word_count(rewritten) > max_words:
            # Model still ran long twice - guarantee the cap ourselves.
            rewritten = _truncate_to_word_limit(rewritten, max_words)

        return rewritten
    except Exception:
        return text.strip()


