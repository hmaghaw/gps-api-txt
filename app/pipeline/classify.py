"""
Stage 3: Moderation classification (BRD section 6.1, TXT-02..TXT-06).

Returns which categories are triggered and an overall confidence score.
This skeleton stubs the actual model call — plug in whichever moderation/LLM
provider you choose (e.g. an LLM prompt with a structured-output schema, or
a dedicated moderation API) inside `classify_message`.
"""

from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    categories: list[str] = field(default_factory=list)  # subset of: profanity, hate, sexual, aggressive
    confidence: float = 1.0  # confidence in the classification itself


def classify_message(text: str) -> ClassificationResult:
    """
    TODO: replace with a real call, e.g.:

        response = llm_client.moderate(
            text=text,
            categories=["profanity", "hate", "sexual", "aggressive"],
        )
        return ClassificationResult(categories=response.categories, confidence=response.confidence)

    Keep the contract stable: categories is a list drawn from
    {"profanity", "hate", "sexual", "aggressive"} (empty list = clean),
    confidence is 0.0-1.0.
    """
    # Placeholder: always "clean" so the pipeline is runnable end-to-end
    # before a real classifier is wired in.
    return ClassificationResult(categories=[], confidence=1.0)
