import unittest

from app.sources.mse_notices.parser import parse_notice_list, to_content_item
from app.sources.mse_notices.service import MSE_NOTICES_SOURCE_KEY, MSE_NOTICES_SOURCE_NAME


class MseNoticesParserTestCase(unittest.TestCase):
    def test_parse_notice_list_extracts_title_link_and_date(self) -> None:
        html = """
        <ul>
           <li><a href="info/1013/5784.htm">【毕业生】关于在校研究生申请2026年11月批次毕（结）业和学位授予的相关工作...</a><i>[2026年04月16日]</i></li>
           <li><a href="content.jsp?urltype=news.NewsContentUrl&amp;wbtreeid=1013&amp;wbnewsid=5734">【研究生】材料学院2026年“北京大学优秀毕业生”（夏季）和“北京市普通高等...</a><i>[2026年04月13日]</i></li>
        </ul>
        """

        notices = parse_notice_list(html, base_url="https://www.mse.pku.edu.cn/tzgg.htm")

        self.assertEqual(len(notices), 2)
        self.assertEqual(notices[0].published_on, "2026年04月16日")
        self.assertEqual(notices[0].url, "https://www.mse.pku.edu.cn/info/1013/5784.htm")
        self.assertIn("优秀毕业生", notices[1].title)
        self.assertIn("wbtreeid=1013", notices[1].url)

    def test_to_content_item_sets_display_time(self) -> None:
        notice = parse_notice_list(
            '<li><a href="info/1013/5784.htm">通知标题</a><i>[2026年04月16日]</i></li>',
            base_url="https://www.mse.pku.edu.cn/tzgg.htm",
        )[0]

        item = to_content_item(notice, source_key=MSE_NOTICES_SOURCE_KEY, source_name=MSE_NOTICES_SOURCE_NAME)

        self.assertEqual(item.source_name, MSE_NOTICES_SOURCE_NAME)
        self.assertEqual(item.metadata["time"], "2026年04月16日")


if __name__ == "__main__":
    unittest.main()
