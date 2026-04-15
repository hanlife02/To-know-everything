from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PkuReagentOrderQuery:
    query: str = "vueshop我的订单list"
    qtype: str = "sqlstr"
    current_page: int = 1
    page_size: int = 20
    start_date: str | None = None
    end_date: str | None = None
    keyword: str = ""
    group_code: str = ""

    def to_payload(self, *, username: str, token: str) -> dict[str, object]:
        return {
            "username": username,
            "token": token,
            "system": "",
            "from": "PC",
            "query": self.query,
            "qtype": self.qtype,
            "current-page": self.current_page,
            "page-size": self.page_size,
            "商品名称": self.keyword,
            "开始日期": self.start_date or "",
            "结束日期": self.end_date or "",
            "课题组编号": self.group_code,
        }


@dataclass(frozen=True, slots=True)
class PkuReagentSession:
    username: str
    token: str
    cookie_header: str
    acquired_at: datetime | None = None
    source: str = "unknown"

    def as_dict(self) -> dict[str, str]:
        payload = {
            "username": self.username,
            "token": self.token,
            "cookie_header": self.cookie_header,
            "source": self.source,
        }
        if self.acquired_at is not None:
            payload["acquired_at"] = self.acquired_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "PkuReagentSession":
        acquired_at = payload.get("acquired_at")
        return cls(
            username=payload.get("username", ""),
            token=payload.get("token", ""),
            cookie_header=payload.get("cookie_header", ""),
            acquired_at=datetime.fromisoformat(acquired_at) if acquired_at else None,
            source=payload.get("source", "unknown"),
        )


@dataclass(frozen=True, slots=True)
class PkuReagentOrderStatus:
    label: str
    reference: str = ""


@dataclass(frozen=True, slots=True)
class PkuReagentOrder:
    order_no: str
    product_title: str
    supplier: str
    sku: str
    group_name: str
    order_time: str
    status: PkuReagentOrderStatus
    payment_info: str
    detail_url: str
    price_info: str = ""
    action_label: str = ""
    raw: dict[str, object] = field(default_factory=dict)
