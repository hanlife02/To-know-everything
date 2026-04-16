import unittest

from app.sources.pku_reagent.parser import parse_order_row, to_content_item
from app.sources.pku_reagent.service import PKU_REAGENT_SOURCE_NAME


class PkuReagentParserTestCase(unittest.TestCase):
    def test_parse_order_row_extracts_status_and_product_fields(self) -> None:
        row = {
            "订单号": "19836054017288",
            "商品信息": (
                '<a href="http://reagent.pku.edu.cn/#/product/detail?id=589144576">'
                "环己六酮八水合物, 99%<br>innochem（伊诺凯）<br><span>伊诺凯15501051890彭梦飞</span></a>"
            ),
            "货号/规格": "A02600<br>25g/瓶",
            "课题组": "1006178307-邹如强<br>杨晗",
            "订单信息": "19836054017288<br>2026-04-14 20:09:18<br>",
            "订单状态": "平台配送中<br>8410104626<br>",
            "支付信息": "",
            "价格信息": "318.40*1<br>318.40",
            "操作": "",
        }

        order = parse_order_row(row, base_url="https://reagent.pku.edu.cn")
        item = to_content_item(order, source_key="pku_reagent_orders", source_name=PKU_REAGENT_SOURCE_NAME)

        self.assertEqual(order.order_no, "19836054017288")
        self.assertEqual(order.product_title, "环己六酮八水合物, 99%")
        self.assertEqual(order.status.label, "平台配送中")
        self.assertEqual(order.status.reference, "8410104626")
        self.assertEqual(order.order_time, "2026-04-14 20:09:18")
        self.assertEqual(item.source_name, PKU_REAGENT_SOURCE_NAME)
        self.assertEqual(item.metadata["status"], "平台配送中")
        self.assertIn("订单编号: 19836054017288", item.summary)


if __name__ == "__main__":
    unittest.main()
