import unittest

from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import ContentItem
from app.pipeline.report import build_report_messages


class DummyReportGenerator:
    def generate(self, items: list[ContentItem]) -> str:
        return "\n".join(item.title for item in items)


class ReportTestCase(unittest.TestCase):
    def test_build_report_messages_groups_items_by_source(self) -> None:
        items = [
            ContentItem(
                source_key="x_posts",
                source_name="X 关注",
                title="@sama",
                summary="new post",
                url="https://x.com/sama/status/1",
                metadata={
                    "content": "new post",
                    "time": "2026-04-18 10:30:00 UTC",
                    "include_url": "true",
                },
            ),
            ContentItem(
                source_key="mse_notices",
                source_name="材料学院通知",
                title="关于答辩安排的通知",
                summary="",
                url="https://www.mse.pku.edu.cn/info/1013/1.htm",
                metadata={
                    "time": "2026年04月18日",
                    "include_url": "true",
                },
            ),
            ContentItem(
                source_key="x_posts",
                source_name="X 关注",
                title="@OpenAI",
                summary="launch update",
                url="https://x.com/OpenAI/status/2",
                metadata={
                    "content": "launch update",
                    "time": "2026-04-18 11:00:00 UTC",
                    "include_url": "true",
                },
            ),
        ]

        messages = build_report_messages(
            items=items,
            report_generator=DummyReportGenerator(),
            targets=(NotificationChannel.TELEGRAM,),
            disable_web_page_preview=True,
        )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].title, "To know everything | X 关注")
        self.assertEqual(messages[0].mode, DeliveryMode.REPORT)
        self.assertEqual(
            messages[0].body,
            "@sama | 2026-04-18 10:30:00 UTC | https://x.com/sama/status/1\n"
            "@OpenAI | 2026-04-18 11:00:00 UTC | https://x.com/OpenAI/status/2",
        )
        self.assertEqual(messages[1].title, "To know everything | 材料学院通知")
        self.assertEqual(
            messages[1].body,
            "关于答辩安排的通知 | 2026年04月18日 | https://www.mse.pku.edu.cn/info/1013/1.htm",
        )


if __name__ == "__main__":
    unittest.main()
