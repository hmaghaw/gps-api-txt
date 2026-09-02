# API-TXT — Text Moderation & Rewrite Service

Skeleton implementation for GPS Special AI Filter Project, BRD v2.2, sections 6.1 / 6.3.1.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then `POST` to `http://localhost:8000/v1/moderate/text`:

```bash
curl -X POST http://localhost:8000/v1/moderate/text \
  -H "Content-Type: application/json" \
  -d '{"message": "Fresh pasta specials all week!"}'
```

## Run tests

```bash
pytest
```

`tests/test_txt_cases.py` has one test per BRD case (TXT-01 through TXT-10).

## What's stubbed vs. real

| Module | Status |
|---|---|
| `app/main.py`, `app/schemas.py`, `app/pipeline/decide.py` | Real — full decision logic implemented |
| `app/pipeline/language.py` | **Stub** — placeholder ASCII-ratio heuristic, needs a real language detector |
| `app/pipeline/classify.py` | **Stub** — always returns "clean", needs a real moderation/LLM call |
| `app/pipeline/rewrite.py` | **Stub** — passthrough, needs a real LLM rewrite call |

## Open decisions (blocking full TXT-05 / TXT-06 correctness)

These are called out as open questions in the BRD itself and are currently defaulted
in `app/config.py` so the service is runnable and testable end-to-end. Confirm with
GPS Special and update the config values — no other code changes needed:

- **TXT-05** — Is aggressive/threatening tone always a hard reject, or eligible for
  rewrite like profanity? Default: `AGGRESSIVE_POLICY = "reject"`.
- **TXT-06** — Confidence threshold for ambiguous/low-confidence content, and whether
  it should reject or attempt rewrite. Default: `CONFIDENCE_THRESHOLD = 0.7`,
  `AMBIGUOUS_POLICY = "reject"`.

## Next steps

1. Confirm TXT-05 / TXT-06 policy with customer, update `config.py`.
2. Wire a real language detector into `pipeline/language.py`.
3. Wire a real moderation/LLM call into `pipeline/classify.py`.
4. Wire a real LLM rewrite call into `pipeline/rewrite.py`.
5. Replace mocked tests in `test_txt_cases.py` with runs against the
   customer-supplied/vendor-agreed sample dataset (per BRD 6.3).
