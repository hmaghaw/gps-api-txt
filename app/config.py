"""
Central configuration and policy thresholds for API-TXT.

IMPORTANT — two values below implement decisions the BRD (v2.2, section 6.3.1)
explicitly left open (see TXT-05 and TXT-06 notes). Sensible defaults are set
so the service is testable end-to-end now, but these should be confirmed with
GPS Special and updated here once agreed — nothing else in the codebase should
need to change.
"""

# --- TXT-06: confidence threshold for ambiguous / borderline content ---
# Below this, content is treated as low-confidence and routed per
# AMBIGUOUS_POLICY. At/above this, the classifier's flagged category applies
# normally.
CONFIDENCE_THRESHOLD = 0.7

# --- TXT-06: what happens at/under the threshold ---
# "reject" = safest default (fail closed). Flip to "rewrite" if the customer
# prefers to attempt a rewrite for borderline content instead.
AMBIGUOUS_POLICY = "reject"

# --- TXT-05: aggressive / threatening tone policy ---
# "reject" = hard reject, no rewrite attempted (same treatment as hate/sexual).
# "rewrite" = attempt to soften tone while preserving intent, like profanity.
# Default is the more conservative "reject" until the customer decides.
AGGRESSIVE_POLICY = "reject"

# --- Message length rules (BRD section 6.1) ---
TARGET_WORD_COUNT = 20
MAX_WORD_COUNT = 30

# Categories that are always a hard reject regardless of confidence —
# no rewrite is ever attempted for these (BRD: TXT-03, TXT-04).
HARD_REJECT_CATEGORIES = {"hate", "sexual"}

# Category that is eligible for rewrite (BRD: TXT-02).
REWRITABLE_CATEGORIES = {"profanity"}

MODEL_VERSION = "txt-moderation-v0.1-skeleton"
