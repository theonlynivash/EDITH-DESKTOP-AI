"""
ML-style intent classifier — pure Python stdlib, zero pip dependencies.
Uses TF-IDF-like phrase + token scoring.
"""

from __future__ import annotations
import re
from typing import Optional


INTENTS: dict[str, dict] = {
    "get_time": {
        "keywords": ["time", "clock", "hour", "what time", "current time", "tell me the time"],
        "handler": "time",
    },
    "get_date": {
        "keywords": ["date", "today", "day", "what day", "current date", "what's the date"],
        "handler": "date",
    },
    "lock_screen": {
        "keywords": [
            "lock", "lock screen", "lock system", "lock computer", "lock pc",
            "lock the screen", "lock the system", "lock the computer",
            "lock my pc", "lock my computer", "secure screen", "screen lock",
        ],
        "handler": "lock_screen",
    },
    "shutdown": {
        "keywords": [
            "shutdown", "shut down", "turn off", "power off",
            "shut down computer", "turn off computer", "power down",
        ],
        "handler": "shutdown",
    },
    "restart": {
        "keywords": [
            "restart", "reboot", "restart computer",
            "restart pc", "restart system",
        ],
        "handler": "restart",
    },
    "abort_shutdown": {
        "keywords": [
            "abort", "cancel shutdown", "abort shutdown",
            "stop shutdown", "cancel restart",
        ],
        "handler": "abort_shutdown",
    },
    "play_song": {
        "keywords": ["play", "song", "music", "listen", "youtube"],
        "handler": "play",
    },
    "open_camera": {
        "keywords": ["camera", "webcam", "photo", "take a photo", "open camera", "selfie"],
        "handler": "camera",
    },
    "open_settings": {
        "keywords": [
            "settings", "preferences", "control panel",
            "open settings", "system settings",
        ],
        "handler": "settings",
    },
    "bluetooth_on": {
        "keywords": ["bluetooth on", "turn on bluetooth", "enable bluetooth"],
        "handler": "bluetooth_on",
    },
    "bluetooth_off": {
        "keywords": ["bluetooth off", "turn off bluetooth", "disable bluetooth"],
        "handler": "bluetooth_off",
    },
    "open_item": {
        "keywords": ["open", "launch", "start", "run"],
        "handler": "open",
    },
}


def _tokenize(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def _score(tokens: list[str], text_lower: str, keywords: list[str]) -> float:
    score = 0.0
    for kw in keywords:
        kw_l = kw.lower()
        if kw_l in text_lower:
            score += 3.0 + len(kw_l.split())
        else:
            kw_toks = kw_l.split()
            hits = sum(1 for t in kw_toks if t in tokens)
            if hits:
                score += hits / len(kw_toks)
    return score


def classify_intent(user_text: str, threshold: float = 2.0) -> Optional[str]:
    """Return the handler key for the best matching intent, or None."""
    text = user_text.strip()
    if not text:
        return None
    tokens = _tokenize(text)
    text_lower = text.lower()
    scores = {name: _score(tokens, text_lower, d["keywords"]) for name, d in INTENTS.items()}
    best = max(scores, key=lambda k: scores[k])
    return INTENTS[best]["handler"] if scores[best] >= threshold else None


def extract_payload(user_text: str, handler: str) -> str:
    """Strip the leading verb to get the target (song name, app name, etc.)."""
    lower = user_text.lower().strip()
    prefixes = {
        "play": ("play song ", "play music ", "play "),
        "open": ("open ", "launch ", "start ", "run "),
    }
    for prefix in prefixes.get(handler, ()):
        if lower.startswith(prefix):
            return user_text[len(prefix):].strip()
    return user_text.strip()
