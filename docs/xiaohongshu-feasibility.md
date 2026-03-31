# 小红书抓取可行性说明

更新日期：2026-03-25

## 结论

截至 2026-03-25，我检索到的小红书官方开放平台资料主要覆盖：

- Ark / 开放平台接入
- 商品与库存接口
- 订单与包裹接口
- 物流与公共数据接口

没有在官方开放平台文档中找到面向“公开笔记内容、视频内容、评论内容”的通用官方 API。

这意味着当前项目的第一阶段存在一个明确前置结论：

- 如果坚持“官方 API 优先”，目前没有看到能直接满足“抓第三方公开账号笔记/视频/评论”的官方内容接口
- 如果继续推进真实抓取器，下一步必须进入“低风控 Cookie 会话 + 实测 PoC”路线验证
- 由于项目约束是不接受高风控方案，也不允许假抓取器占位，所以在抓取层真正开工前，必须先做可行性验证

## 官方资料观察

从官方开放平台资料能确认的内容：

1. 开放平台介绍明确提到 Ark 面向第三方合作伙伴，用于商品、库存和包裹管理
2. Quick Start 和鉴权文档围绕 `app-key`、`app-secret`、签名调用
3. Product & Item APIs 聚焦商品信息
4. Inventory APIs 聚焦库存
5. Order & Package APIs 聚焦订单和包裹

这些资料没有体现：

- 公开笔记列表接口
- 笔记详情接口
- 评论区接口
- 创作者公开内容抓取接口
- 第三方公开账号内容订阅接口

## 对当前项目的直接影响

### 1. 真实抓取器不能再假设“官方内容 API 很快能接”

如果继续按官方 API 路线写抓取器，大概率会先走进死路。

### 2. 下一步应转为“低风控 PoC 先行”

PoC 目标不是大规模抓取，而是先回答 3 个问题：

1. 使用受控 Cookie 会话时，是否能稳定访问公开内容页
2. 是否能在不高频、不并发的前提下拿到目标账号最近内容
3. 评论、高赞评论、图片资源、视频资源是否能通过同一条低风险链路取到

### 3. 项目当前更适合先把非抓取部分做稳

这也是为什么当前仓库先落了：

- 本地鉴权
- 配置管理
- API Key / Cookie 加密存储骨架
- Bark 配置
- 模型列表发现
- 手动同步预检
- 任务运行记录

这些部分无论后续抓取链路怎么定，都会保留。

## 推荐的下一阶段执行顺序

1. 做小红书抓取可行性 PoC
2. 验证是否存在可接受的低风控内容获取路径
3. 只有 PoC 通过后，再进入：
   - 账号内容列表抓取
   - 笔记详情抓取
   - 评论抓取
   - OCR / 转写 / 摘要联动

## 官方参考入口

- https://school.xiaohongshu.com/en/open/quick-start/introduction.html
- https://school.xiaohongshu.com/en/open/quick-start/how-to-get-app-key.html
- https://school.xiaohongshu.com/en/open/product/summary.html
- https://school.xiaohongshu.com/en/open/package/summary.html
- https://school.xiaohongshu.com/en/open/common/summary.html
