"""Offline command handlers — stdlib only, no pip packages."""

from __future__ import annotations
import os
import subprocess
import webbrowser
from datetime import datetime
from typing import Tuple
from urllib.parse import quote_plus

from utils import find_file_in_common_directories, find_folder_in_common_directories
from intent_classifier import classify_intent, extract_payload


# ── helpers ──────────────────────────────────────────────────────────────────

def _open_path(path: str) -> None:
    try:
        os.startfile(path)          # type: ignore[attr-defined]
    except OSError as e:
        print(f"[Edith] Cannot open {path}: {e}")


def _open_app(name: str) -> str:
    try:
        subprocess.Popen(["start", name], shell=True)
        return f"Opening {name}…"
    except Exception as e:
        return f"Failed to open {name}: {e}"


def _open_settings() -> str:
    try:
        os.startfile("ms-settings:")   # type: ignore[attr-defined]
        return "Opening Settings…"
    except OSError as e:
        return f"Could not open Settings: {e}"


def _lock_screen() -> str:
    try:
        subprocess.run(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            check=True, shell=False,
        )
        return "Screen locked."
    except subprocess.SubprocessError as e:
        return f"Could not lock screen: {e}"


def _play_song(name: str) -> str:
    """Play song on YouTube using Opera GX - tries to open first video"""
    if not name.strip():
        return "What song would you like to play?"

    query = quote_plus(name.strip())

    # Try to find Opera GX executable
    opera_path = None
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera GX\opera.exe"),
        r"C:\Program Files\Opera GX\opera.exe",
        r"C:\Users\Nivash\AppData\Local\Programs\Opera GX\opera.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            opera_path = path
            break

    # Register Opera GX with webbrowser module
    if opera_path:
        try:
            webbrowser.register(
                'operagx',
                None,
                webbrowser.BackgroundBrowser(opera_path),
                preferred=True
            )
            controller = webbrowser.get('operagx')
        except:
            controller = webbrowser.get()
    else:
        controller = webbrowser.get()

    # YouTube search filtered to videos only (best simple method)
    url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAQ%3D%3D"

    try:
        controller.open(url, new=2)  # new=2 opens in new tab
        return f"🎵 Opening '{name}' in Opera GX...\nClick the first video to play it."
    except Exception:
        # Fallback to default browser
        webbrowser.open(url)
        return f"🎵 Searching YouTube for '{name}'..."


# ── dispatch ──────────────────────────────────────────────────────────────────

def _dispatch(handler: str, raw: str) -> str:
    if handler == "time":
        return f"The current time is {datetime.now().strftime('%I:%M %p')}."

    if handler == "date":
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

    if handler == "lock_screen":
        return _lock_screen()

    if handler == "shutdown":
        subprocess.run(["shutdown", "/s", "/t", "60"], shell=False)
        return "Shutting down in 60 seconds. Say 'abort shutdown' to cancel."

    if handler == "restart":
        subprocess.run(["shutdown", "/r", "/t", "60"], shell=False)
        return "Restarting in 60 seconds. Say 'abort shutdown' to cancel."

    if handler == "abort_shutdown":
        subprocess.run(["shutdown", "/a"], shell=False)
        return "Shutdown cancelled."

    if handler == "play":
        return _play_song(extract_payload(raw, "play"))

    if handler == "camera":
        try:
            subprocess.Popen("start microsoft.windows.camera:", shell=True)
            return "Opening Camera…"
        except Exception:
            return "Could not open the camera app."

    if handler == "settings":
        return _open_settings()

    if handler == "bluetooth_on":
        return "Bluetooth ON (use Windows Settings for full control)."

    if handler == "bluetooth_off":
        return "Bluetooth OFF (use Windows Settings for full control)."

    if handler == "open":
        target = extract_payload(raw, "open")
        if not target:
            return "What would you like me to open?"
        fp = find_file_in_common_directories(target)
        if fp:
            _open_path(str(fp))
            return f"Opening file: {fp}"
        dp = find_folder_in_common_directories(target)
        if dp:
            _open_path(str(dp))
            return f"Opening folder: {dp}"
        return _open_app(target)

    return "I didn't understand that."


# ── public entry point ────────────────────────────────────────────────────────

def handle_offline_command(command: str) -> Tuple[bool, str]:
    command = command.strip()
    if not command:
        return False, ""
    handler = classify_intent(command)
    if handler is None:
        return False, ""
    return True, _dispatch(handler, command)
