from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

from app.domain.models import ContentItem
from app.sources.pku_reagent.models import PkuReagentOrder, PkuReagentOrderStatus

BR_TAG_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
ANCHOR_HREF_PATTERN = re.compile(r'href="([^"]+)"', re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_html(value: object) -> str:
    text = str(value or "")
    text = BR_TAG_PATTERN.sub("\n", text)
    text = TAG_PATTERN.sub("", text)
    text = unescape(text).replace("\xa0", " ")
    return "\n".join(part.strip() for part in text.splitlines() if part.strip())


def extract_href(value: object, *, base_url: str) -> str:
    text = str(value or "")
    match = ANCHOR_HREF_PATTERN.search(text)
    if not match:
        return f"{base_url.rstrip('/')}/#/personal/list?query=vueshop我的订单p"
    return urljoin(base_url.rstrip("/") + "/", match.group(1))


def parse_order_row(row: dict[str, object], *, base_url: str) -> PkuReagentOrder:
    product_lines = strip_html(row.get("商品信息")).splitlines()
    status_lines = strip_html(row.get("订单状态")).splitlines()
    return PkuReagentOrder(
        order_no=str(row.get("订单号") or "").strip(),
        product_title=product_lines[0] if product_lines else "",
        supplier=product_lines[1] if len(product_lines) > 1 else "",
        sku=strip_html(row.get("货号/规格")),
        group_name=strip_html(row.get("课题组")),
        order_time=_extract_order_time(row.get("订单信息")),
        status=PkuReagentOrderStatus(
            label=status_lines[0] if status_lines else "",
            reference=status_lines[1] if len(status_lines) > 1 else "",
        ),
        payment_info=strip_html(row.get("支付信息")),
        detail_url=extract_href(row.get("商品信息"), base_url=base_url),
        price_info=strip_html(row.get("价格信息")),
        action_label=strip_html(row.get("操作")),
        raw=row,
    )


def parse_orders(rows: list[dict[str, object]], *, base_url: str) -> list[PkuReagentOrder]:
    return [parse_order_row(row, base_url=base_url) for row in rows]


def to_content_item(order: PkuReagentOrder, *, source_key: str) -> ContentItem:
    summary_parts = [
        f"订单状态: {order.status.label}",
        f"订单编号: {order.order_no}",
    ]
    if order.status.reference:
        summary_parts.append(f"状态附加信息: {order.status.reference}")
    if order.group_name:
        summary_parts.append(f"课题组: {order.group_name.replace(chr(10), ' / ')}")
    if order.order_time:
        summary_parts.append(f"下单时间: {order.order_time}")
    if order.payment_info:
        summary_parts.append(f"支付信息: {order.payment_info.replace(chr(10), ' / ')}")
    return ContentItem(
        source_key=source_key,
        title=order.product_title or order.order_no,
        summary=" | ".join(summary_parts),
        url=order.detail_url,
        external_id=order.order_no,
        metadata={
            "supplier": order.supplier,
            "status": order.status.label,
            "status_reference": order.status.reference,
            "sku": order.sku.replace("\n", " / "),
            "group_name": order.group_name.replace("\n", " / "),
            "order_time": order.order_time,
            "payment_info": order.payment_info.replace("\n", " / "),
            "price_info": order.price_info.replace("\n", " / "),
            "action_label": order.action_label,
        },
    )


def _extract_order_time(value: object) -> str:
    lines = strip_html(value).splitlines()
    if len(lines) >= 2:
        return lines[1]
    if lines:
        return lines[0]
    return ""

