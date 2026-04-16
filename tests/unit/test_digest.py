import unittest

from app.domain.enums import DeliveryMode, NotificationChannel
from app.domain.models import ContentItem
from app.pipeline.digest import build_digest_messages


class DigestTestCase(unittest.TestCase):
    def test_build_digest_messages_groups_items_by_source(self) -> None:
        items = [
            ContentItem(
                source_key="pku_reagent_orders",
                source_name="试剂平台通知",
                title="环己六酮八水合物, 99%",
                summary="",
                url="https://example.com/reagent/1",
                metadata={"status": "买方已收货", "sku": "A02600 / 25g/瓶", "order_time": "2026-04-14 20:09:18"},
            ),
            ContentItem(
                source_key="mse_notices",
                source_name="材料学院通知",
                title="关于调整研究生毕（结）业和学位授予批次的通知",
                summary="",
                url="https://www.mse.pku.edu.cn/info/1013/5774.htm",
                metadata={"time": "2026年04月16日", "include_url": "true"},
            ),
        ]

        messages = build_digest_messages(
            items=items,
            targets=(NotificationChannel.TELEGRAM,),
            disable_web_page_preview=True,
        )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].title, "试剂平台通知")
        self.assertEqual(messages[0].mode, DeliveryMode.SUMMARY)
        self.assertIn("环己六酮八水合物, 99% | 买方已收货 | A02600 / 25g/瓶 | 2026-04-14 20:09:18", messages[0].body)
        self.assertEqual(messages[1].title, "材料学院通知")
        self.assertIn(
            "关于调整研究生毕（结）业和学位授予批次的通知 | 2026年04月16日 | https://www.mse.pku.edu.cn/info/1013/5774.htm",
            messages[1].body,
        )


if __name__ == "__main__":
    unittest.main()
