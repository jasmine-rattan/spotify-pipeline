import hashlib
import json
import math
import re
from decimal import Decimal, ROUND_HALF_UP

FIELDS = ("review_id", "review_text", "review_rating", "review_likes", "app_version", "review_timestamp")
LABEL_CONFIG = "jev-1.14.0+classify-v1"
TOPICS = ("access", "usability", "playback", "downloads", "catalog", "billing", "support", "other")
INTENTS = ("cancellation", "complaint", "request", "praise", "unclear")
LABEL_FIELDS = ("topic", "intent", "sentiment", "severity", "entities", "evidence_quote", "needs_review", "label_config")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def row_sha(row: dict) -> str:
    """Exact match to check_submission.py. NO normalization of any field."""
    return hashlib.sha256(canonical([row[k] for k in FIELDS]).encode("utf-8")).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_key(text: str, label_config: str) -> str:
    """Cache key MUST include label_config to prevent invalid reuse across versions."""
    return hashlib.sha256(f"{text}\x00{label_config}".encode("utf-8")).hexdigest()


def mean_string(severity_sum: int, complaint_count: int) -> str:
    """Decimal half-up to 6 places. NEVER use float division or SQL AVG()."""
    return str(
        (Decimal(severity_sum) / Decimal(complaint_count)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    )


def extract_quote(review_text: str) -> str:
    """Always an exact substring. Never normalize. Never use sentence splitter."""
    if len(review_text) <= 300:
        return review_text
    cut = review_text.rfind(' ', 0, 250)
    return review_text[:cut if cut > 0 else 250]


TOPIC_KEYWORDS = {
    "access":    ["login", "sign in", "sign up", "password", "account", "logout", "authentication"],
    "usability": ["ad", "ads", "advertisement", "shuffle", "queue", "playlist", "navigation",
                  "interface", "layout", "skip", "scroll", "button"],
    "playback":  ["play", "crash", "playback", "audio", "lag", "buffer", "connect", "stream",
                  "freeze", "stuck", "pause"],
    "downloads": ["download", "offline", "saved", "cache", "storage"],
    "catalog":   ["lyric", "search", "discover", "recommendation", "missing", "artist", "song"],
    "billing":   ["premium", "subscription", "payment", "charge", "price", "cost", "upgrade"],
    "support":   ["support", "customer service", "help", "response", "contact", "ticket"],
    "other":     [],
}


def extract_entities(review_text: str, topic: str) -> list:
    """Keyword-based entity extraction. Returns deduplicated list (may be empty)."""
    text_lower = review_text.lower()
    seen, entities = set(), []
    for kw in TOPIC_KEYWORDS.get(topic, []):
        if kw in text_lower and kw not in seen:
            seen.add(kw)
            entities.append(kw)
    return entities
