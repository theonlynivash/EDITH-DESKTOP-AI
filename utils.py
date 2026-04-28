"""Utility helpers — stdlib only."""

from __future__ import annotations
import socket
from pathlib import Path
from typing import Optional

COMMON_DIRECTORIES = (
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Pictures",
    Path.home() / "Music",
    Path.home() / "Videos",
)

_cache: dict[str, Optional[Path]] = {}


def has_internet(timeout: float = 2.0) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def find_file_in_common_directories(filename: str) -> Optional[Path]:
    key = f"f_{filename}"
    if key in _cache:
        return _cache[key]
    for base in COMMON_DIRECTORIES:
        if not base.exists():
            continue
        try:
            for p in base.rglob("*"):
                if p.is_file() and p.name.lower() == filename.lower():
                    _cache[key] = p
                    return p
        except PermissionError:
            continue
    _cache[key] = None
    return None


def find_folder_in_common_directories(folder_name: str) -> Optional[Path]:
    key = f"d_{folder_name}"
    if key in _cache:
        return _cache[key]
    for base in COMMON_DIRECTORIES:
        if not base.exists():
            continue
        try:
            for p in base.rglob("*"):
                if p.is_dir() and p.name.lower() == folder_name.lower():
                    _cache[key] = p
                    return p
        except PermissionError:
            continue
    _cache[key] = None
    return None


def clear_cache() -> None:
    _cache.clear()
