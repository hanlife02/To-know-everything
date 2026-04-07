from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
ALLOWED_HOSTS = {"127.0.0.1", "0.0.0.0"}


def load_local_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()

        key, separator, value = line.partition("=")
        if not separator:
            continue

        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def parse_env_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def get_host(env_name: str, default: str = "127.0.0.1") -> str:
    candidate = os.getenv(env_name, default).strip() or default
    if candidate not in ALLOWED_HOSTS:
        return default
    return candidate


def get_port(env_name: str, default: int) -> int:
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return default

    try:
        port = int(raw_value)
    except ValueError:
        return default

    if not 1 <= port <= 65535:
        return default
    return port
