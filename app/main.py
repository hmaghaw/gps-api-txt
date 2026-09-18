import os
import sys
import time

# Allow `python app/main.py` to work directly: when run as a script, Python
# only puts this file's own directory (app/) on sys.path, not the project
# root, so the `app.` package imports below would otherwise fail. This has
# no effect when the app is started normally (uvicorn CLI, -m, container).
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI

from app.config import MODEL_VERSION
from languages import supported_language_names
from app.pipeline.decide import run_pipeline
from app.schemas import ModerateTextRequest, ModerateTextResponse, ResponseMetadata

app = FastAPI(
    title="GPS Special - API-TXT",
    description="Text Moderation & Rewrite Service (BRD v2.2, section 6.1 / 6.3.1)",
    version="0.2.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/languages")
def list_languages():
    """Languages currently enabled on this deployment (SUPPORTED_LANGUAGES
    in .env, cross-checked against languages.json at startup)."""
    return {"supported_languages": supported_language_names()}


@app.post("/v1/moderate/text", response_model=ModerateTextResponse)
def moderate_text(payload: ModerateTextRequest) -> ModerateTextResponse:
    start = time.perf_counter()
    result = run_pipeline(payload.message)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return ModerateTextResponse(
        decision=result.decision,
        original_message=payload.message,
        final_message=result.final_message,
        categories=result.categories,
        confidence=result.confidence,
        word_count=result.word_count,
        guidance=result.guidance,
        detected_language=result.detected_language,
        language_confidence=result.language_confidence,
        metadata=ResponseMetadata(processing_ms=elapsed_ms, model_version=MODEL_VERSION),
    )


if __name__ == "__main__":
    # Lets you run `python app/main.py` directly for local testing —
    # no container, no separate `uvicorn` CLI invocation needed.
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)