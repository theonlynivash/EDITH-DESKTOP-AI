"""
OpenAI API integration — uses stdlib urllib only.
No 'openai' pip package needed.

Easiest setup: create a file called  config.txt  next to main.py
and put your key on the first line:
    sk-proj-...

Alternatively set the environment variable OPENAI_API_KEY.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils import has_internet

OPENAI_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

# config.txt lives next to this file
_CONFIG_FILE = Path(__file__).parent / "config.txt"


def _get_api_key() -> Optional[str]:
    # 1. Environment variable (set OPENAI_API_KEY=sk-...)
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key

    # 2. config.txt next to main.py  ← EASIEST option
    try:
        text = _CONFIG_FILE.read_text(encoding="utf-8").strip()
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line          # first non-comment line is the key
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[Edith] Could not read config.txt: {e}")

    return None


def ask_openai(prompt: str) -> Optional[str]:
    """Call the OpenAI chat API and return the reply, or None on any failure."""
    if not has_internet():
        return None

    api_key = _get_api_key()
    if not api_key:
        print("[Edith] OPENAI_API_KEY not set — GPT unavailable.")
        return None

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Edith, a friendly AI desktop assistant. "
                    "Keep answers concise — 1 to 3 sentences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 150,
    }

    req = Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip()
    except HTTPError as e:
        print(f"[Edith] OpenAI HTTP {e.code}: {e.read().decode()[:200]}")
    except URLError as e:
        print(f"[Edith] Network error: {e.reason}")
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[Edith] Bad API response: {e}")
    return None