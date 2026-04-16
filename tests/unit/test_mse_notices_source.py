import unittest

from app.domain.models import SourceFetchResult
from app.sources.mse_notices.service import MSE_NOTICES_SOURCE_KEY, MSE_NOTICES_SOURCE_NAME, MseNoticesSource


class StubClient:
    def fetch_page(self, url: str) -> str:
        return """
        <ul>
           <li><a href="info/1013/5784.htm">通知标题一</a><i>[2026年04月16日]</i></li>
           <li><a href="info/1013/5774.htm">通知标题二</a><i>[2026年04月15日]</i></li>
        </ul>
        """


class MseNoticesSourceTestCase(unittest.TestCase):
    def test_fetch_wraps_notice_rows_as_content_items(self) -> None:
        source = MseNoticesSource(client=StubClient())

        result = source.fetch()

        self.assertIsInstance(result, SourceFetchResult)
        self.assertEqual(result.source_key, MSE_NOTICES_SOURCE_KEY)
        self.assertEqual(result.source_name, MSE_NOTICES_SOURCE_NAME)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].source_name, MSE_NOTICES_SOURCE_NAME)
        self.assertEqual(result.items[0].metadata["time"], "2026年04月16日")


if __name__ == "__main__":
    unittest.main()
