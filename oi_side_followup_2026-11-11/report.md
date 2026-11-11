# 未确认 OI 字段补证（2026-11-11）

本轮只补上一轮 `oi_side_audit_2026-11-11` 里尚未闭合的官方原始 OI 字段。DefiLlama 适配器取自 `DefiLlama/dimension-adapters` 的 `1204e61680a1a4583d3b2d43f7c2c94b254d3d28`。采样窗口约为 2026-11-11 07:50–08:05 UTC。机器可读结果在 `dashboard_config.v3.json`。

单侧的含义不变：每份未平仓合约的名义金额只计一次。官方字段已经是单侧时 factor 为 1；字段把双方镜像持仓都算进去时 factor 为 0.5。

## 结论表

| 项目 | 官方原始字段 | 原始单位 | 官方单/双侧 | factor | 关键验证证据 | 置信等级 | DefiLlama 是否正确 |
|---|---|---|---|---:|---|---|---|
| edgeX V2 | `getTicker.openInterest`；`getTicketSummary.tickerSummary.openInterest` | 逐市场为基础币；平台汇总为 USD | 未解 | 未设 | 157 个合约的 base×mark 之和与平台汇总比值为 1.0008。公开 K 线与文档都没有持仓侧 | unresolved | 不能判定。代码把汇总 /2，2026-11-11 00:00 UTC 公开值为 1.477 亿美元，约为当时官方标题值的一半 |
| Aster | `aster/ticker/pair.openInterest`；`apx/pair.openInterest`；`/fapi/v1/openInterest` | aster/apx 为 USD；FAPI 为基础币 | aster BAPI 约为 FAPI 美元值的 2 倍；apx 当前空仓 | 0.5（暂定，只用于 aster） | 7 个市场的 BAPI/FAPI 比值在 1.997–2.000。公告 588 与 53 个市场的零 OI、零成交一致 | B+ | aster 路由 /2 与 FAPI 对齐。apx 并入当前只加 0，应从活跃汇总移除并保留非零告警 |
| Hyperliquid | `metaAndAssetCtxs.openInterest` | 基础币 | 多头基础币 + 空头基础币 | 0.5（暂定） | 2026-11-10 Hydromancer 全仓位合计：BTC 多空各 20976.96，之和落在同一分钟官方区间内。本轮未重放 | B+ | /2 与该持仓合计一致，仍非官方公式 |
| Pacifica | `info/prices.open_interest` | 基础币。文档写成 USD | 未取得新的持仓公式 | 0.5（暂定） | BTC 原始值 509.01619，乘 mark 后为 3763 万美元 | B− | 乘 mark 正确；/2 维持暂定 |
| Extended | `marketStats.openInterest` | 抵押品 USD。`openInterestBase` 为基础币 | 未解侧数。订单簿与 RFQ 同一字段 | 0.5（暂定） | BTC 的 USD / (base×mark) = 0.9997。活跃订单簿 1.127 亿美元，活跃 RFQ 1751 万美元 | B− | /2 仍是暂定。Arc 与 RFQ 不要拆成两套系数 |
| GRVT | `ticker.open_interest`；`dailyOpenInterest` | 逐市场为基础币；日汇总为 USD | 未解 | 1.0（暂定） | 2026-11-10 日汇总 3.816 亿美元。多空拆分字段为空。未结束的 UTC 日返回 0 | B− | 直接使用日汇总，侧数仍未证实 |
| Nado | Archive `open_interests` | USDT0，x18 | 双侧。多头等于总量的一半 | 0.5（确认） | Archive BTC 报价与 `contracts.open_interest_usd` 比值为 1；long/open_interest = 0.5。快照键等于 83 个永续，不含 16 个现货 | A− | /2 一次，正确。没有重复折半，也没有现货混入 |

## 重点异常

### edgeX 是否存在错误折半

官方平台字段 `tickerSummary.openInterest` 在 07:50:54 UTC 为 294,117,220.21 美元。同一窗口 157 个可交易且可展示合约的 `openInterest × markPrice` 之和为 293,881,192.23 美元，比值 1.0008。BTCUSDC 的原始 OI 是 2259.757 BTC，乘 mark 73,847.78 为 166,878,042 美元。逐市场字段是基础币，平台字段是这些名义金额的加总。

DefiLlama `open-interest/edgex-v2.ts` 读取 `getTicketSummary`（路径拼写是 Ticket）后除以 2。`api.llama.fi/summary/open-interest/edgex` 在 2026-11-11 00:00 UTC 的点是 147,695,684 美元。

这次除以 2 的来源是 PR #9685（2026-09-25）。PR 正文为空。十天前的 PR #9365 把 edgeX 标成已经单侧、不做除法。CodeRabbit 在 #9685 写明改动没有证明字段是双侧。

因此可以复核的事实是：DefiLlama 把已经等于逐市场名义金额之和的官方标题值再除以 2，公开序列约为该标题值的一半。官方文档、Golang SDK 和 Python SDK 都只把字段叫做 Open Interest。`priceType=OPEN_INTEREST` 的 K 线返回空列表，没有成交增量可以反推计数侧。

这还不能写成“已经证实的错误折半”。如果每个市场的基础币 OI 本身就是多头加空头，除以 2 仍然正确。最小补证是同一时刻 BTC 的多头基础币合计：接近 2259.757 则 factor 为 1，接近 1129.9 则 factor 为 0.5。

Dashboard 在补证之前不要采用 0.5，也不要把 1.0 标成已确认。官方标题值单独展示。

### Aster 的两路 BAPI 是否继续合并

`aster/ticker/pair` 在 `asterdex.com` 与 `apollox.finance` 上都返回 594 个市场，OI 合计 2,661,525,213.42 美元。`apx/pair?excludeCake=true` 在两个主机上都返回 53 个 `productType=Perpetual` 的 `*USD` 市场，openInterest、baseVol、qutoVol 全部为 0，lastPrice 仍在更新。

公告 id 588《ApolloX Sunset Update》发布于 2026-11-03 08:00 UTC，正文写明 ApolloX（apollox.finance，含网页和 API）清退，旧 APX 合约自 2026-11-03 10:00 UTC 起清退，预计 48 小时完成。采样时已过该窗口。零 OI 与零成交一起出现，并且与公告指向同一旧产品，所以 apx 可以从当前活跃产品汇总中剔除。路由本身仍应保留非零 OI 或非零成交告警，一次零响应不能单独当成永久停用。

现行 aster 路由与 FAPI 是同一产品的两个水位。FAPI `openInterest` 是基础币。七个市场的 aster BAPI 美元值除以 FAPI 基础币×mark：

| 市场 | 比值 |
|---|---:|
| BTCUSDT | 2.00023 |
| ETHUSDT | 1.99968 |
| SOLUSDT | 2.00044 |
| TSLAUSDT | 1.99931 |
| XAUUSDT | 1.99973 |
| SUSHIUSDT | 1.99722 |
| ASTERUSDT | 1.99690 |

DefiLlama 把两路相加再除以 2。apx 现为 0，所以结果等于 aster BAPI 的一半，与 FAPI 美元化 OI 对齐。合并可以停止；aster 路由的 0.5 可以暂定使用。Aster 官方文档里没有找到 DefiLlama 注释所引的 “calculated both ways” 原句，因此系数保持 provisional，不升到 confirmed。

### Hyperliquid、Pacifica、Extended、GRVT 哪些可以正式确认

四家都没有升到 confirmed。

Hyperliquid 可以从“只靠 CoinGecko 约 2 倍”推进到 B+。2026-11-10 Hydromancer 用 `perpSnapshots` 合计 BTC 40,967 个仓位：多头与空头各 20,976.96 BTC，之和 41,953.93，落在同一分钟官方 `openInterest` 的 41,952.56–41,957.28。ETH 与 HYPE 同样成立。这是按仓位方向加总后与官方字段对照，本轮没有重放，也没有枚举账户。官方文档和公开节点代码仍没有求和公式。`provisional_factor` 维持 0.5。DefiLlama 的 /2 与该合计一致。

Pacifica 的单位可以确认，侧数不能。文档写 USD，BTC 原始值 509.01619，乘 mark 73,934 后为 37,633,603 美元。响应没有多空字段。`provisional_factor` 维持 0.5。DefiLlama 先乘 mark 再除以 2，单位换算成立，折半仍暂定。

Extended 的 USD 与 base 换算不能当侧数证明。BTC-USD 的 `openInterest / (openInterestBase × markPrice)` 为 0.9997。`isRfq=false` 的活跃订单簿 OI 为 112,682,680 美元，`isRfq=true` 的活跃 RFQ OI 为 17,514,716 美元，stats 字段相同。已下架、预上架和 reduce-only 残余合计约 9,731 美元。现货为 0。2026-10-22 之后 DefiLlama 的 Starknet 路径已停止，Arc 读取同一 URL。`provisional_factor` 维持 0.5，订单簿与 RFQ 共用。

GRVT 维持 B− 与 `provisional_factor` 1.0。已结束的 2026-11-10 UTC 日，`dailyOpenInterest` 为 381,644,023.17 美元，`dailyLongOpenInterest` 与 `dailyShortOpenInterest` 为空字符串。进行中的 2026-11-11 日桶返回 0。BTC ticker 为 2,498.89332092 BTC，乘 mark 为 184,735,773 美元。`long_short_ratio` 是账户数之比。没有独立持仓合计，不升级。

### Nado Archive 映射是否闭环

闭环，针对 DefiLlama 实际读取的 Archive 字段。

`GET /v2/contracts` 把 `long_open_interest` 与 `short_open_interest` 定义并返回为 `open_interest` 的一半。BTC、ETH、SOL 和全平台美元合计的比值都是 0.5。同一次脚本中，Archive `open_interests["2"] / 1e18` 为 22,963,383.650025 USDT0，`contracts["BTC-PERP_USDT0"].open_interest_usd` 为同一个数。

不带 `product_ids` 的快照有 83 个键，与 gateway 的 83 个 perp id 相同。16 个现货 id（含 product 0 的 USDT0）都不在快照里。7 个永续的 OI 为 0，加进去不改变合计。快照滞后约 1 秒。

DefiLlama `open-interest/nado.ts` 对全部 `open_interests` 做 `/ 1e18 / 2`。这一次折半对应文档中的双侧报价名义金额。没有第二次折半，也没有现货混入。`confirmed_factor` 为 0.5。

另一次亚秒读数里，gateway `state.open_interest` 为 307.7135 BTC，contracts 基础币为 310.6739，比值 0.9905。这是同一侧上的约 1% 差额，不是另一个 0.5。它不阻挡 Archive 与 contracts 美元字段的闭合。Dashboard 仍建议按 perp id 过滤，防止以后的快照把现货放进来；USDT0 继续按 1 美元计，并单独做脱锚告警。

## 本轮没有做的事

没有重跑 13 家全量审计，没有用 CoinGecko 的统一口径完成循环证明，没有把 DefiLlama 注释当成官方定义，没有枚举账户，也没有覆盖此前的 Volume 与 OI 审计文件。
