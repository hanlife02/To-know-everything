from __future__ import annotations

from datetime import datetime

from app.domain.models import JobRunResult
from app.storage.json_store import JsonStore


class StateStore:
    def __init__(self, root) -> None:
        self._run_history = JsonStore(root / "run_history.json")

    def append_run(self, result: JobRunResult) -> None:
        history = self._run_history.load(default=[])
        history.append({"timestamp": datetime.utcnow().isoformat(), **result.as_dict()})
        self._run_history.save(history)

    def get_run_history(self) -> list[dict[str, object]]:
        return self._run_history.load(default=[])

