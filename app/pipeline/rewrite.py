"""
Stage 5: Rewrite (BRD section 6.1 — target ~20 words, hard cap 30).

Only called when decide.py routes to "rewrite". Produces a sanitized,
professional version of the message. This skeleton stubs the actual model
call — plug in an LLM prompt that removes/neutralises the flagged category
while preserving the marketing intent.
"""


def rewrite_message(text: str, categories: list[str]) -> str:
    """
    TODO: replace with a real LLM call, e.g. a prompt instructing the model to:
      - remove/neutralise profanity or soften aggressive tone (per `categories`)
      - keep it professional, inclusive, and compelling
      - target ~20 words, never exceed 30

        rewritten = llm_client.complete(
            system=REWRITE_SYSTEM_PROMPT,
            user=text,
        )
        return rewritten.strip()
    """
    # Placeholder passthrough — replace before production use.
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split())
