# Derive 架构核对（仅事实）

采集窗口：2026-10-21 09:58:03Z–10:01:28Z（北京时间 17:58–18:01）。下文只记录官方页面、治理帖摘录和公开 API 读到的内容。文章中的成交额、用户数和护城河判断不在本文件下结论。

## 官方源可获取性（12 项）

| # | 源 | 本次状态 | 能核对的内容 | 不能核对的内容 |
| --- | --- | --- | --- | --- |
| 1 | [Derive V3 介绍](https://docs.derive.xyz/getting-started/introduction.md)，抓取于 2026-10-21 | 全文可读 | 链下撮合；保证金、结算、权限编译为 RISC-V，用 SP1 Hypercube 在链下证明；批次用 PLONK 在 Ethereum L1 验证；主网 API `https://api.derive.xyz/v3` | 证明生成延迟、实际 gas、匹配引擎是否在电路内 |
| 2 | [DIP: Launch Derive V3](https://forums.derive.xyz/t/dip-launch-derive-v3/322)，2026-09-14 05:36 UTC，本次为检索摘录而非整页存档 | 关键段落可读 | 提案中的角色、逃生舱、约 40–50 万 gas、Celestia DA、迁移不重新入金 | 提案是否按原文执行、链上 vkey、二进制是否已公开 |
| 3 | [Portfolio Margin](https://docs.derive.xyz/portfolio-margin.md) 与 [Parameters](https://docs.derive.xyz/portfolio-margin-parameters.md)，抓取于 2026-10-21 | 全文可读 | 23 个常规情景、尾部、skew、forward；币种之间不互抵 | 某一账户的实际初始保证金数值 |
| 4 | [Managers & Risk Universes](https://docs.derive.xyz/trading/managers-and-risk-universes.md) 加 `public/get_risk_universes`，2026-10-21 09:58Z | 文档与实盘列表都读到 | 实盘宇宙名称、可交易合约族、抵押品 | 各宇宙的未平仓和坏账 |
| 5 | [Oracles](https://docs.derive.xyz/oracles.md)，抓取于 2026-10-21 | 全文可读 | 标记输入来自 Block Scholes；SVI；置信度只加初始保证金 | Block Scholes 是否拟合 Deribit |
| 6 | [Trading Fees](https://docs.derive.xyz/integrators/trading/trading-fees.md)、[Institutional Rewards](https://docs.derive.xyz/integrators/programs/institutional-trading-rewards.md)、[Builder Fees](https://docs.derive.xyz/integrators/programs/builder-fees)、[RFQ](https://docs.derive.xyz/trading/rfq.md)，抓取于 2026-10-21 | 全文可读 | 订单簿和 RFQ 价目、做市商奖励规则、builder `extra_fee`、RFQ 为私有接口 | 奖励是否已停发、builder 实际分成、公开 RFQ 报价 |
| 7 | Derive 公开 API：`public/get_tickers`、`public/get_vaults`、`public/get_all_currencies`，2026-10-21 09:58Z | 调用成功 | 指定到期日的买卖价和顶档数量、金库列表、永续行情 | 订单簿更深层、全所期权未平仓、交易者人数 |
| 8 | [Deribit Portfolio Margin](https://support.deribit.com/hc/en-us/articles/25944756247837-Portfolio-Margin)（页内写 Updated 2026-10-12 的是相邻的 margin types 文）、[Fees](https://support.deribit.com/hc/en-us/articles/25944746248989-Fees)，以及 `public/get_order_book`，2026-10-21 09:58:47Z | 可读且订单簿成功 | 情景保证金、标准期权费率、可比合约的盘口 | Deribit 完整扩展表的每个币种参数 |
| 9 | [Paradex Dated Options](https://docs.paradex.trade/trading/dated-options/overview.md)、[Trading Fees](https://docs.paradex.trade/trading/trading-fees.md)，以及 `v1/markets/summary`、`v1/orderbook`，2026-10-21 10:01Z | 文档可读；两个行情接口都返回 | 欧式日期期权已上市、零售与 Pro 费率；summary 有价，orderbook 在抽样行权价上没有双边 | summary 价格是否可成交 |
| 10 | [Hyperliquid HIP-4](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-4-outcome-markets) 与 `https://api.hyperliquid.xyz/info` `outcomeMeta`，2026-10-21 09:59Z | 文档与 API 都读到 | 已上线的是全额抵押的 outcome，不是 call/put 链 | 香草期权上线日（文档没有给出） |
| 11 | [Lighter binary options](https://apidocs.lighter.xyz/docs/binary-options)，页面写 Updated about 23 hours ago（相对本次抓取，约 2026-10-20） | 全文可读 | Up/Down 二元期权、全额抵押、无杠杆无清算 | Lighter 永续的 ZK 撮合电路；本次没有打开那部分文档 |
| 12 | [DefiLlama options overview](https://api.llama.fi/overview/options)（2026-10-21 09:59:47Z）与 [derive-v3 adapter](https://github.com/DefiLlama/dimension-adapters/blob/master/options/derive-v3.ts) | API 与适配器源码可读 | 适配器同时定义名义和权利金；overview 的 `total24h` 字段本身没有标注用的是哪一个 | 文章中的 142 亿美元、74.9%、88.1% |

Variational 不在这 12 项里。补看了 [Omni 介绍](https://docs.variational.io/omni/about-omni.md) 和 [路线图](https://docs.variational.io/getting-started/roadmap.md)：文档索引里没有 “option”。Omni 写的是永续、资金费和 OLP。路线图未列期权。因此不把 Variational 算作已上线的期权场所。

## 已上线的结算形态

V3 介绍写明：撮合是亚毫秒、链下的。保证金、结算和权限写在协议里，编译成 RISC-V，由 SP1 Hypercube zkVM 在链下执行并生成证明；批次提交 Ethereum L1，用 PLONK SNARK 验证。提款在批次验证后付出，并受提款速率限制。

2026-10-07，Nick Forster 的 [V3 is live](https://insights.derive.xyz/v3/) 写：匹配保持在链下；排序之后再为每个批次生成证明；状态变更发到 Celestia；逃生舱规则下，若 Derive 超过超时仍不处理提款，另一名操作者可以继续结算。同一篇写明，V3 是分阶段底座，不是一次性放完所有市场和集成。DefiLlama `derive-v3.ts` 把切换日记为 `2026-10-06`。本次没有核对链上停机区块。

DIP 提案（2026-09-14）写的验证成本是固定约 400,000–500,000 gas。这是提案数字，本次没有链上收据。

主网在采集时响应。`public/get_tickers` 返回了 BTC、ETH 的 2026-10-30 期权。V2 链下撮合加专链结算是这篇 DIP 所描述的被迁移对象：提案要求把 V2 余额和仓位种进 V3 genesis，并关闭 Derive Chain。用户不必重新入金，是提案原文，不是本次对每个账户的核对。

## ZK 覆盖什么、不覆盖什么

覆盖，按 V3 介绍和 DIP 的措辞：排序之后的状态转换，包括保证金、定价和结算，在 zkVM 中执行，再由 L1 验证证明。

不覆盖，按同一批官方文字：

- 撮合本身留在链下。文档要的是亚毫秒匹配，没有声称价格优先或时间优先在电路里证明。
- 预言机数值是外部输入。Oracles 页写明 spot、forward、perp、隐含波动率和利率由 Block Scholes 提供。证明的是协议按这些输入计算，不是这些输入等于 Deribit。
- 排序由 sequencer 完成。DIP 列出的 Owner 可以更新 state root、设置 verifying key、升级代理合约，并解除提款暂停。Guardian 可以刷新提款节流，并且有一个单向开关用来阻止提款。因此，在 Owner 可更换验证密钥和状态根的前提下，证明并不约束运营方。
- 逃生舱：提案写 sequencer 必须按顺序处理 L1 动作队列；初始处理期限为 2 周，逾期后任何人可以接管并提出新批次。提案同时写“上线后不久会公开交易所二进制”。本次没有验证二进制是否已经公开，也没有验证 L2Beat Stage 1。提案只把 Stage 1 写成目标。

这和“撮合公平性本身被 ZK 证明”不是同一句话。本次没有阅读 Lighter 永续撮合电路，不能用 Derive 的文档去描述 Lighter。

## Portfolio Margin、宇宙、预言机、清算

PM 文档写：组合保证金把期权、永续和风险对冲抵押品放进情景里重估，取最差结果，再加上情景没有覆盖的应急保证金。

V3 的跨币种是持仓意义上的，不是盈亏互抵。原文：一个 PM 子账户可以持有其风险宇宙列出的每一种币；Prime 可持有 BTC 和 ETH。净额停在宇宙边界。每个币种的情景网格单独计算，再把各币种的最差损失相加。一种币的亏损不会被另一种币的盈利抵消。

BTC 常规网格是 −14% 到 +14%，步长 3.5%，共 23 个情景；最外侧 ±14% 只有波动率上升。ETH 常规网格是 ±16%，不是 ±14%。尾部情景 8 行，波动率方向为上升，并带阻尼。V3 的 skew 是四条轨（线性顺/逆时针，以及对称翼上/下），按到期日取最差，只把负的结果加总。Forward 损失是 `maxLoss` 的四个候选之一，不是额外再加一层。

每个 PM2 子账户最多 100 个资产（期权、现金、基础资产、永续），文档写明是计算量限制。

实盘 `get_risk_universes`（2026-10-21 09:58Z）：

| id | 名称 | PM2 合约族 |
| --- | --- | --- |
| 0 | FALLBACK | 无交易 |
| 1 | PRIME | BTC、ETH 的期权和永续 |
| 2 | MIDCAP | 只有 HYPE 期权和永续 |
| 3 | ALT | ADA、CC、LIT、PUMP、SOL、VVV、XRP、ZEC 的期权和永续。标准保证金管理器另外列出 BNB、DOGE、LINK 永续，PM2 列表里没有这三项，也没有 DOGE 期权 |
| 4 | RWA | XAUT 期权和永续 |

文档写：不同宇宙之间的成交、RFQ 和清算会被拒绝；资不抵债只在该宇宙的 Security Module 内消化，必要时只向同一宇宙的有偿付能力账户分摊。

预言机：Block Scholes 的 SVI。置信度阈值 0.55。置信度下降只增加初始保证金，不增加维持保证金，因此单靠变差的预言机不能把账户推进清算。负利率在两个保证金引擎里都先夹到 0。

清算数字在两份当前文档里不一致，本次不合并：

- Parameters：`LIQUIDATION_PENALTY` 为 500 bps。
- Trading Fees：清算费为被清算组合盯市价值的 10%。

维持保证金系数 `mm_factor` 文档写为 0.80。

## 订单簿、RFQ、费率、奖励

订单簿期权：

- Taker：`$0.50 + min(0.03% × 名义, 12.5% × 权利金)`
- Maker：`min(0.01% × 名义, 12.5% × 权利金)`

RFQ 对双方收 taker 名义费率，taker 另有基础费。多腿按多头 call、多头 put、空头 call、空头 put、永续分组：最贵的一组全额，最便宜的一组免单，第二和第三便宜的一组 50%。两腿价差的第二条腿因此可以是 0。盒式价差另收 `名义 × 0.5% × 年化剩余期限`，买卖双方都收，taker 再加 $0.50。

RFQ 全部是 `private/*`。公开接口不能看到别人的 RFQ 报价。成交是整包原子的。默认可报价窗口文档写 30 分钟，并注明部署之间可能不同。

机构奖励页仍写着每个 28 天周期最多 $500,000 USDC 和 1,000,000 DRV。期权 maker 最高档写的是 −0.005%，条件是做市分数份额、28 天成交或份额，以及 stDRV，并且注明数字可以改。义务栏写：15 分钟窗口随机快照；最低报价数量 500（页面没有写单位）；delta 大于 1 且小于 98；28 天名义成交大于 $50M；份额大于 2%。

RFQ 计分：只有成交了的 RFQ 才计分。赢单的做市商 1.2 倍，其余报过价的 0.5 倍。首次报价 ≤5 分钟时间分 2，≤15 分钟为 1，更慢为 0.5。未成交的 RFQ 不加分。

Builder fee：订单和 RFQ 可带 `referral_code` 与 `extra_fee`（0.000001–1,000 USDC），每四周打到 builder 钱包，加在交易所费之上。

## 已上线与仍是文档/提案

已观察到上线：V3 主网期权和永续行情、上述五个风险宇宙、订单簿公开最优价、RFQ 私有接口、builder fee 字段、金库接口。

`public/get_vaults` 在 2026-10-21 09:58Z 返回 1 个金库，不是多页。名称 “XRP Weekly Put/Call Income”。NAV 10,836.66 美元。总份额与 curator 份额都是 8,000.180124496536。`whitelist_only` 为 false，`closed` 为 false。管理费 100 bps，业绩费 0，协议分成 1,000 bps。按份额数字，外部持有人份额为 0。

本次 API 和金库列表里没有 Dream、LEVR，也没有 builder 成交额。

Parameters 写：日期期货在 V3 启动时没有上市，所以期货应急保证金为 0。

旧文档 [Overview](https://docs.derive.xyz/docs/overview-2) 在检索摘要里写保证金在链上计算，并提到 Sigma Prime。该页描述的是另一套链上 manager 架构。本次没有打开完整审计 PDF，也不把这句话当作 V3 zkVM 的审计结论。
