from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import JobRunResult, PipelineResult
from app.storage.json_store import JsonStore


class StateStore:
    def __init__(self, root) -> None:
        self._latest_pipeline = JsonStore(root / "latest_pipeline.json")
        self._run_history = JsonStore(root / "run_history.json")

    def save_pipeline_snapshot(self, result: PipelineResult) -> None:
        self._latest_pipeline.save(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                **result.as_dict(),
            }
        )

    def get_latest_pipeline(self) -> dict[str, object]:
        return self._latest_pipeline.load(default={})

    def append_run(self, result: JobRunResult) -> None:
        history = self._run_history.load(default=[])
        history.append({"timestamp": datetime.now(UTC).isoformat(), **result.as_dict()})
        self._run_history.save(history)

    def get_run_history(self) -> list[dict[str, object]]:
        return self._run_history.load(default=[])
