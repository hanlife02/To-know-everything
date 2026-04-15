from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StoragePaths:
    root: Path
    cache: Path
    state: Path
    settings: Path
    logs: Path

    @classmethod
    def ensure(cls, root: Path) -> "StoragePaths":
        cache = root / "cache"
        state = root / "state"
        settings = root / "settings"
        logs = root / "logs"
        for path in (root, cache, state, settings, logs):
            path.mkdir(parents=True, exist_ok=True)
        return cls(root=root, cache=cache, state=state, settings=settings, logs=logs)

