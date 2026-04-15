import unittest
from datetime import date, timedelta
from pathlib import Path

from app.config.settings import PkuReagentSettings
from app.domain.models import SourceFetchResult
from app.sources.pku_reagent.models import PkuReagentOrderQuery
from app.sources.pku_reagent.models import PkuReagentSession
from app.sources.pku_reagent.service import PkuReagentOrderSource


class StubClient:
    def fetch_order_rows(self, session: PkuReagentSession, query: PkuReagentOrderQuery) -> list[dict[str, object]]:
        return [
            {
                "订单号": "19834213017288",
                "商品信息": '<a href="http://reagent.pku.edu.cn/#/product/detail?id=1">刚玉坩埚<br>GLASS</a>',
                "货号/规格": "HBZSX0952<br>40ml",
                "课题组": "1006178307-邹如强<br>杨晗",
                "订单信息": "19834213017288<br>2026-04-14 15:08:09<br>",
                "订单状态": "供货商配送中<br>8410104626<br>",
                "支付信息": "",
                "价格信息": "52.00*4<br>208.00",
                "操作": "退货",
            }
        ]


class StubAuthenticator:
    def authenticate(self, *, force_refresh: bool = False) -> PkuReagentSession | None:
        return PkuReagentSession(username="CG17288", token="session-token", cookie_header="JWTUser=abc")


class PkuReagentSourceTestCase(unittest.TestCase):
    def test_from_settings_defaults_to_recent_year_window(self) -> None:
        source = PkuReagentOrderSource.from_settings(
            PkuReagentSettings(
                enabled=True,
                username="CG17288",
                password="secret",
            ),
            session_cache_path=Path("/tmp/pku_reagent_session_test.json"),
        )

        self.assertEqual(source.query.end_date, date.today().isoformat())
        self.assertEqual(source.query.start_date, (date.today() - timedelta(days=365)).isoformat())

    def test_source_fetch_wraps_rows_as_content_items(self) -> None:
        source = PkuReagentOrderSource(
            key="pku_reagent_orders",
            name="PKU Reagent Orders",
            enabled=True,
            authenticator=StubAuthenticator(),
            client=StubClient(),
            query=PkuReagentOrderQuery(),
            base_url="https://reagent.pku.edu.cn",
        )

        result = source.fetch()

        self.assertIsInstance(result, SourceFetchResult)
        self.assertEqual(result.source_key, "pku_reagent_orders")
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].metadata["status"], "供货商配送中")


if __name__ == "__main__":
    unittest.main()
