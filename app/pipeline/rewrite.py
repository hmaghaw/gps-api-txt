"""
Stage 5: Rewrite (BRD section 6.1 — target ~20 words, hard cap 30).

Only called when decide.py routes to "rewrite". Calls OpenAI to produce a
sanitised, professional version of the message.

IMPORTANT: the word cap is enforced here in code, not just via the prompt.
Models don't reliably self-count words, so a first response that comes back
over MAX_WORD_COUNT triggers one shortening retry, and if that still isn't
enough, the text is hard-truncated to MAX_WORD_COUNT words. This guarantees
decide.py's downstream length check (TXT-07) never rejects a rewrite purely
because the model ran long.
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
    "- target about {target} words, and NEVER exceed {max_words} words — "
    "count your words before answering\n"
    "Respond with ONLY the rewritten message text, nothing else — no "
    "quotes, no preamble, no explanation."
)

RETRY_SUFFIX = (
    "\n\nYour previous attempt was {prev_count} words, which is over the "
    "{max_words}-word hard cap. Rewrite it again, shorter — {max_words} "
    "words or fewer, ideally close to {target}. Respond with ONLY the "
    "rewritten message text."
)


def word_count(text: str) -> int:
    return len(text.split())


def _truncate_to_word_limit(text: str, limit: int) -> str:
    """Last-resort hard cap: cut to `limit` words. Only reached if the
    model ignores both the prompt and the retry, so this exists purely as
    a guarantee, not the expected path."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(",;:") + "…"


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


def rewrite_message(text: str, categories: list[str]) -> str:
    """
    Calls OpenAI to rewrite `text` given the flagged `categories`, then
    enforces MAX_WORD_COUNT in code (see module docstring). On any API
    failure, falls back to the original text — decide.py's own
    MAX_WORD_COUNT check downstream still applies as a final backstop.
    """
    try:
        client = get_client()
        system = SYSTEM_PROMPT_TEMPLATE.format(
            categories=", ".join(categories) or "none",
            target=TARGET_WORD_COUNT,
            max_words=MAX_WORD_COUNT,
        )

        rewritten = _call_llm(client, system, text)
        if not rewritten:
            return text.strip()

        wc = word_count(rewritten)
        if wc > MAX_WORD_COUNT:
            # One shortening retry, explicitly telling it how far over it was.
            retry_system = system + RETRY_SUFFIX.format(
                prev_count=wc, max_words=MAX_WORD_COUNT, target=TARGET_WORD_COUNT
            )
            retried = _call_llm(client, retry_system, text)
            if retried:
                rewritten = retried

        if word_count(rewritten) > MAX_WORD_COUNT:
            # Model still ran long twice — guarantee the cap ourselves.
            rewritten = _truncate_to_word_limit(rewritten, MAX_WORD_COUNT)

        return rewritten
    except Exception:
        return text.strip()