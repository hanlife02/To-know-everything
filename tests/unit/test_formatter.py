import unittest

from app.domain.models import ContentItem
from app.notifications.formatter import build_summary_body
from app.notifications.formatter import split_message


class FormatterTestCase(unittest.TestCase):
    def test_build_summary_body_only_contains_title_status_sku_and_time(self) -> None:
        body = build_summary_body(
            [
                ContentItem(
                    source_key="pku_reagent_orders",
                    source_name="试剂平台通知",
                    title="Order ready",
                    url="https://example.com/orders/1",
                    summary="这段内容不应该出现在推送里",
                    metadata={
                        "status": "平台配送中",
                        "sku": "HBZSX0952 / 40ml",
                        "order_time": "2026-04-14 15:08:09",
                    },
                )
            ]
        )

        self.assertEqual(
            body,
            "\n".join(
                [
                    "title: Order ready",
                    "status: 平台配送中",
                    "sku: HBZSX0952 / 40ml",
                    "time: 2026-04-14 15:08:09",
                ]
            ),
        )

    def test_split_message_respects_limit(self) -> None:
        body = "line-1\nline-2\nline-3\n"

        segments = split_message(body, max_length=10)

        self.assertEqual(segments, ["line-1", "line-2", "line-3"])


if __name__ == "__main__":
    unittest.main()
