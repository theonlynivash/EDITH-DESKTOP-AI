"""Run this standalone to diagnose the GPT connection."""
import json, os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import socket

# --- 1. internet check ---
try:
    socket.create_connection(("8.8.8.8", 53), timeout=2)
    print("[OK] Internet reachable")
except OSError:
    print("[FAIL] No internet")

# --- 2. key check ---
config = Path(__file__).parent / "config.txt"
key = os.getenv("OPENAI_API_KEY", "").strip()
if not key and config.exists():
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key = line
            break

if key:
    print(f"[OK] Key found: {key[:12]}...{key[-4:]}")
else:
    print("[FAIL] No API key found — check config.txt")
    exit()

# --- 3. actual API call ---
payload = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "say hello in one word"}],
    "max_tokens": 10,
}
req = Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0",
    },
    method="POST",
)
try:
    with urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
        reply = data["choices"][0]["message"]["content"].strip()
        print(f"[OK] GPT replied: {reply}")
except HTTPError as e:
    body = e.read().decode()
    print(f"[FAIL] HTTP {e.code}: {body}")
except URLError as e:
    print(f"[FAIL] Network error: {e.reason}")
except Exception as e:
    print(f"[FAIL] Unexpected: {e}")