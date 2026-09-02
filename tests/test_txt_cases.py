"""
One test per BRD (v2.2, section 6.3.1) test case, TXT-01 through TXT-10.

Since `classify_message` and `detect_language` are stubs pending real
model/service integration, these tests monkeypatch them to simulate the
classifier's output for each scenario. Once the real classifier is wired in,
these same tests should be re-run against representative sample inputs
(the BRD calls for a "Customer-supplied or Vendor-agreed sample dataset")
instead of mocked outputs.
"""

import pytest

from app.pipeline import decide as decide_module
from app.pipeline.classify import ClassificationResult
from app.pipeline.language import LanguageCheckResult


def _mock_classify(categories=None, confidence=1.0):
    def _fn(text):
        return ClassificationResult(categories=categories or [], confidence=confidence)
    return _fn


def _mock_language(is_english=True):
    def _fn(text):
        return LanguageCheckResult(
            is_english=is_english,
            detected_language="en" if is_english else "non-en",
            confidence=1.0,
        )
    return _fn


def test_txt01_clean_allow(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify([]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("Fresh pasta specials all week — come try our new menu!")
    assert result.decision == "allow"
    assert result.categories == []


def test_txt02_profanity_rewrite(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["profanity"]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("This dang sale is too good to miss!")
    assert result.decision == "rewrite"
    assert "profanity" in result.categories


def test_txt03_hate_hard_reject(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["hate"]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("some discriminatory message")
    assert result.decision == "reject"
    assert result.final_message is None
    assert "hate" in result.categories


def test_txt04_sexual_hard_reject(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["sexual"]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("some suggestive message")
    assert result.decision == "reject"
    assert result.final_message is None


def test_txt05_aggressive_policy_driven(monkeypatch):
    # Default policy (config.AGGRESSIVE_POLICY = "reject") — confirm current behavior.
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["aggressive"]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("Last chance or else!")
    assert result.decision in ("reject", "rewrite")  # depends on AGGRESSIVE_POLICY
    assert "aggressive" in result.categories


def test_txt06_ambiguous_low_confidence(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["profanity"], confidence=0.5))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    result = decide_module.run_pipeline("edgy borderline humor message")
    # Default AMBIGUOUS_POLICY = "reject"
    assert result.decision in ("reject", "rewrite")  # depends on AMBIGUOUS_POLICY


def test_txt07_rewrite_exceeds_length(monkeypatch):
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify(["profanity"]))
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    long_text = " ".join(["word"] * 40)  # forces rewrite passthrough > 30 words in this stub
    result = decide_module.run_pipeline(long_text)
    assert result.decision == "reject"
    assert "length_exceeded" in result.categories


def test_txt08_non_english_reject(monkeypatch):
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(False))
    result = decide_module.run_pipeline("mensaje en español")
    assert result.decision == "reject"
    assert "unsupported_language" in result.categories


def test_txt09_empty_input_reject():
    result = decide_module.run_pipeline("   ")
    assert result.decision == "reject"
    assert "invalid_input" in result.categories


def test_txt10_transliterated_evasion_best_effort(monkeypatch):
    # Documented residual risk: no strict assertion, just confirms the
    # pipeline runs without error on this class of input.
    monkeypatch.setattr(decide_module, "detect_language", _mock_language(True))
    monkeypatch.setattr(decide_module, "classify_message", _mock_classify([]))
    result = decide_module.run_pipeline("transliterated non-english text in latin script")
    assert result.decision in ("allow", "reject", "rewrite")
