from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config.settings import AppSettings
from app.domain.enums import ContentPriority, DeliveryMode, NotificationChannel
from app.domain.models import ContentItem, DeliveryReceipt, NotificationMessage, PipelineResult, SourceFetchResult
from app.services.notification_service import NotificationService
from app.sources.registry import SourceRegistry
from app.storage.cache_store import CacheStore
from app.storage.state_store import StateStore


class StubDispatcher:
    def __init__(self, result: PipelineResult) -> None:
        self._result = result

    def run(self, mode: DeliveryMode) -> PipelineResult:
        return self._result


class AssertingRouter:
    def __init__(self, root: Path) -> None:
        self._cache_file = root / "cache" / "pku_reagent_orders.json"
        self._pipeline_file = root / "state" / "latest_pipeline.json"

    def deliver(self, messages: list[NotificationMessage]) -> list[DeliveryReceipt]:
        if not self._cache_file.exists():
            raise AssertionError("source cache must be written before delivery")
        if not self._pipeline_file.exists():
            raise AssertionError("latest pipeline snapshot must be written before delivery")
        if len(messages) != 1:
            raise AssertionError("expected a single message to deliver")
        return [
            DeliveryReceipt(
                channel=NotificationChannel.TELEGRAM,
                delivered=True,
                detail="delivered in test",
            )
        ]


class DummyReportGenerator:
    def generate(self, items: list[ContentItem]) -> str:
        return "\n".join(item.title for item in items)


class NotificationServiceTestCase(unittest.TestCase):
    def test_run_persists_pipeline_snapshot_before_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_store = CacheStore(root / "cache")
            state_store = StateStore(root / "state")
            item = ContentItem(
                source_key="pku_reagent_orders",
                title="Order ready",
                summary="filtered item",
                url="https://example.com/orders/1",
                source_name="试剂平台通知",
                priority=ContentPriority.HIGH,
                metadata={"status": "平台配送中"},
            )
            message = NotificationMessage(
                title="信息摘要",
                body="Order ready",
                mode=DeliveryMode.SUMMARY,
                targets=(NotificationChannel.TELEGRAM,),
            )
            pipeline_result = PipelineResult(
                mode=DeliveryMode.SUMMARY,
                items=[item],
                messages=[message],
                source_results=[SourceFetchResult(source_key="pku_reagent_orders", source_name="试剂平台通知", items=[item])],
            )
            service = NotificationService(
                settings=AppSettings(),
                registry=SourceRegistry(),
                cache_store=cache_store,
                state_store=state_store,
                router=AssertingRouter(root),
                report_generator=DummyReportGenerator(),
            )
            service._dispatcher = StubDispatcher(pipeline_result)

            result = service.run(DeliveryMode.SUMMARY)

            latest_pipeline = state_store.get_latest_pipeline()
            self.assertEqual(result.item_count, 1)
            self.assertEqual(result.message_count, 1)
            self.assertEqual(latest_pipeline["mode"], DeliveryMode.SUMMARY.value)
            self.assertEqual(len(latest_pipeline["items"]), 1)
            self.assertEqual(len(latest_pipeline["messages"]), 1)
            self.assertEqual(len(latest_pipeline["source_results"]), 1)


if __name__ == "__main__":
    unittest.main()
