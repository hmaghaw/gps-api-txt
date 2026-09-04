"""
Stage 5: Rewrite (BRD section 6.1 — target ~20 words, hard cap 30).

Only called when decide.py routes to "rewrite". Calls OpenAI to produce a
sanitised, professional version of the message. Replaces the earlier
passthrough stub.
"""

from app.config import MAX_WORD_COUNT, OPENAI_MODEL, TARGET_WORD_COUNT
from app.llm_client import get_client

SYSTEM_PROMPT_TEMPLATE = (
    "You rewrite SMS/MMS marketing messages for a geo-targeted local-offers "
    "platform so they are safe to broadcast. The original message was "
    "flagged for: {categories}.\n"
    "Rewrite it to:\n"
    "- remove or neutralise the flagged issue(s) while preserving the "
    "business's actual offer/intent\n"
    "- keep a professional, inclusive, and compelling marketing tone\n"
    "- target about {target} words, and NEVER exceed {max_words} words\n"
    "Respond with ONLY the rewritten message text, nothing else — no "
    "quotes, no preamble, no explanation."
)


def rewrite_message(text: str, categories: list[str]) -> str:
    """
    Calls OpenAI to rewrite `text` given the flagged `categories`. On any
    failure, falls back to the original text — decide.py's MAX_WORD_COUNT
    check downstream still applies, and this path is only reached for
    rewrite-eligible categories (never the hard-reject ones), so failing
    back to the original is the same conservative behaviour as before this
    was wired to a real model.
    """
    try:
        client = get_client()
        system = SYSTEM_PROMPT_TEMPLATE.format(
            categories=", ".join(categories) or "none",
            target=TARGET_WORD_COUNT,
            max_words=MAX_WORD_COUNT,
        )
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
        )
        rewritten = (response.choices[0].message.content or "").strip()
        return rewritten or text.strip()
    except Exception:
        return text.strip()


def word_count(text: str) -> int:
    return len(text.split())