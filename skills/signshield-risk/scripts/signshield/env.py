from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or _find_dotenv(Path.cwd())
    if env_path is None or not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def _find_dotenv(start: Path) -> Path | None:
    current = start.resolve()
    candidates = [current] if current.is_dir() else [current.parent]
    candidates.extend(candidates[0].parents)
    for directory in candidates:
        candidate = directory / ".env"
        if candidate.exists():
            return candidate
    return None


def _parse_env_line(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or text.startswith("#") or "=" not in text:
        return None
    key, value = text.split("=", 1)
    key = key.strip()
    if not key or not _valid_key(key):
        return None
    return key, _unquote(value.strip())


def _valid_key(key: str) -> bool:
    first = key[0]
    if not (first.isalpha() or first == "_"):
        return False
    return all(char.isalnum() or char == "_" for char in key)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
