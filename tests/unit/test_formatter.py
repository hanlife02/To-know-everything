import unittest

from app.domain.models import ContentItem
from app.notifications.formatter import build_summary_body
from app.notifications.formatter import split_message


class FormatterTestCase(unittest.TestCase):
    def test_build_summary_body_formats_each_item_on_one_line_without_field_labels(self) -> None:
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
            "Order ready | 平台配送中 | HBZSX0952 / 40ml | 2026-04-14 15:08:09",
        )

    def test_build_summary_body_includes_url_when_source_requests_it(self) -> None:
        body = build_summary_body(
            [
                ContentItem(
                    source_key="mse_notices",
                    source_name="材料学院通知",
                    title="关于调整研究生毕（结）业和学位授予批次的通知",
                    url="https://www.mse.pku.edu.cn/info/1013/5774.htm",
                    summary="",
                    metadata={
                        "time": "2026年04月16日",
                        "include_url": "true",
                    },
                )
            ]
        )

        self.assertEqual(
            body,
            "关于调整研究生毕（结）业和学位授予批次的通知 | 2026年04月16日 | https://www.mse.pku.edu.cn/info/1013/5774.htm",
        )

    def test_build_summary_body_formats_x_post_with_author_time_and_url(self) -> None:
        body = build_summary_body(
            [
                ContentItem(
                    source_key="x_posts",
                    source_name="X 关注",
                    title="@OpenAI",
                    url="https://x.com/OpenAI/status/123",
                    summary="",
                    metadata={
                        "content": "New launch details",
                        "time": "2026-04-18 10:30:00 UTC",
                        "include_url": "true",
                    },
                )
            ]
        )

        self.assertEqual(
            body,
            "@OpenAI | 2026-04-18 10:30:00 UTC | https://x.com/OpenAI/status/123",
        )

    def test_split_message_respects_limit(self) -> None:
        body = "line-1\nline-2\nline-3\n"

        segments = split_message(body, max_length=10)

        self.assertEqual(segments, ["line-1", "line-2", "line-3"])


if __name__ == "__main__":
    unittest.main()
