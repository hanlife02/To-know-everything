from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STATE_PATH = Path(__file__).resolve().parent / "data" / "delivery_state.json"


def normalize_state(payload: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    source = payload or {}
    return {
        "summary": {
            "xhs": str(source.get("summary", {}).get("xhs", "")).strip(),
        },
        "report": {
            "xhs": str(source.get("report", {}).get("xhs", "")).strip(),
        },
    }


def load_delivery_state(path: Path = STATE_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        return normalize_state()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_state(payload)


def save_delivery_state(
    state: dict[str, dict[str, str]],
    path: Path = STATE_PATH,
) -> Path:
    normalized = normalize_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def get_delivery_signature(
    mode: str,
    platform: str,
    path: Path = STATE_PATH,
) -> str:
    state = load_delivery_state(path)
    return str(state.get(mode, {}).get(platform, "")).strip()


def set_delivery_signature(
    mode: str,
    platform: str,
    signature: str,
    path: Path = STATE_PATH,
) -> Path:
    state = load_delivery_state(path)
    if mode not in state:
        state[mode] = {}
    state[mode][platform] = str(signature or "").strip()
    return save_delivery_state(state, path)


def build_xhs_signature(notes: list[dict[str, Any]], limit: int = 20) -> str:
    payload = [
        {
            "title": str(note.get("title", "")).strip(),
            "url": str(note.get("url", "")).strip(),
            "author_name": str(note.get("author_name", "")).strip(),
            "note_type": str(note.get("note_type", "")).strip(),
        }
        for note in notes[:limit]
    ]
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else ""
