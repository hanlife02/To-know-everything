from __future__ import annotations

from pathlib import Path

from app.storage.json_store import JsonStore


class SettingsStore:
    def __init__(self, root: Path) -> None:
        self._path = root / "runtime_settings.json"
        self._store = JsonStore(self._path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict[str, object]:
        payload = self._store.load(default={})
        if isinstance(payload, dict):
            return payload
        return {}

    def save(self, payload: dict[str, object]) -> None:
        self._store.save(payload)

    def fingerprint(self) -> int | None:
        if not self._path.exists():
            return None
        return self._path.stat().st_mtime_ns
