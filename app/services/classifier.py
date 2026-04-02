from __future__ import annotations

from app.utils import clean_text


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "technology": ("科技", "ai", "人工智能", "手机", "数码", "互联网", "软件", "硬件", "编程", "开源"),
    "entertainment": ("娱乐", "明星", "综艺", "电影", "电视剧", "古偶", "idol", "音乐", "演唱会"),
    "society": ("社会", "热点", "民生", "警方", "教育局", "约谈", "公益", "公共", "新闻"),
    "sports": ("体育", "足球", "篮球", "wtt", "乒乓", "比赛", "奥运", "马拉松"),
    "finance": ("财经", "股票", "基金", "商业", "企业", "融资", "投资", "经济"),
    "gaming": ("游戏", "电竞", "steam", "主机", "手游"),
    "lifestyle": ("生活", "日常", "情感", "vlog", "居家", "收纳"),
    "fashion": ("穿搭", "彩妆", "妆容", "护肤", "时尚", "美甲", "卷发"),
    "food": ("美食", "料理", "食谱", "减脂餐", "烘焙", "餐厅", "咖啡"),
    "travel": ("旅行", "旅游", "攻略", "酒店", "景点", "澳门"),
    "health": ("健身", "减脂", "瑜伽", "拉伸", "医护", "健康"),
    "military": ("军事", "战争", "中东", "伊朗", "国防"),
    "automotive": ("汽车", "华为汽车", "新能源", "驾驶"),
}


def infer_category(title: str, tags: list[str], source_category: str | None = None) -> str:
    haystack = " ".join([clean_text(title), clean_text(source_category), *[clean_text(tag) for tag in tags]]).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in haystack for keyword in keywords):
            return category
    return "general"

