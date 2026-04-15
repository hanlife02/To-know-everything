from __future__ import annotations

from app.domain.models import ContentItem


class ReportGenerator:
    def generate(self, items: list[ContentItem]) -> str:
        if not items:
            return "今日观察\n暂无新增内容。\n\n重点内容\n暂无。\n\n推送建议\n继续等待下一轮采集。"
        titles = "\n".join(f"- {item.title}" for item in items[:5])
        return (
            "今日观察\n"
            f"本轮共整理 {len(items)} 条候选内容。\n\n"
            "重点内容\n"
            f"{titles}\n\n"
            "推送建议\n"
            "优先确认第一批正式接入的信息源与触发条件，再补具体抓取实现。"
        )

