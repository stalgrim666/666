# 核验说明

采集脚本：`outputs/06/analyze.py`。运行日 2026-10-24，窗口终点 `2026-10-24T06:49:39Z`（北京时间 14:49）。只使用未登录的 HTTP 读接口，没有下单，没有读取 API key。

## RFQ 报价：两条公开途径

1. 官方文档。Deribit `public/get_block_rfq_trades` 是已成交的 Block RFQ；`private/get_block_rfq_quotes` 需要授权。Derive 文档写明全部 RFQ 方法为 `private/*`，`private/poll_quotes` 需要会话。
2. 未登录调用。Deribit 报价接口返回 `unauthorized` / `invalid_token`。Derive `private/poll_quotes` 返回缺少钱包头，`public/poll_quotes` 为 404。公开 Block RFQ 与 Derive 成交历史都返回 200，内容是成交。

因此不存在两边相同条件下的 RFQ 报价。订单簿最优价没有拿来充当 RFQ。

## 成交与分页

Derive `public/get_trade_history`，`instrument_type=option`，`page_size=1000`。声明 `count=77594`、`num_pages=78`。取回 78 页、77,594 行。去重键是 `trade_id + liquidity_role + subaccount_id`，去重后仍为 77,594，窗口外和非期权行都是 0。最早一笔 `2026-09-24T06:50:34Z`，最晚一笔 `2026-10-24T06:45:55Z`。终点早于请求上限约 4 分钟，页数和行数与接口声明一致。

名义和笔数只使用 `liquidity_role=taker`，避免 maker 行把同一笔计两次。RFQ 指 taker 行的 `rfq_id` 非空。地址只按公开 `wallet` 计数。Top 5 / Top 10 是 taker 名义份额。跨日指至少两个 UTC 日期；该名义占比由原始 gzip 按地址汇总，不在 `results.json` 的主表里。至少两笔的地址比例过宽，因为一条多腿 RFQ 就会产生多行，正文没有用它做稳定性结论。

Deribit 24 小时逐笔用 `public/get_last_trades_by_currency_and_time`，`count=1000`，按 `trade_id` 去重。BTC 8 页、7,070 笔，`has_more=false`。ETH 5 页、4,125 笔，同样结束。Block RFQ 用 `count=50` 翻页，BTC、ETH 都翻到了窗口起点之前。

## 单位核对

- Derive BTC 的 24 小时 taker 名义与 ticker `stats.v` 都是 36,932,413 美元。BTC 权利金与 `stats.pr` 都是 462,101 美元。ETH 逐笔名义比 ticker 高约 0.8%。
- Deribit BTC 逐笔名义 14.27 亿美元，订单簿 `volume × underlying_price` 为 14.19 亿美元。逐笔权利金 1,680 万美元，与全合约 `volume_usd` 合计一致。`volume_usd` 因此按权利金使用，不按名义使用。
- Deribit BTC Block RFQ 在成交接口和逐笔里都是 153 条期权腿、名义都是 2.265 亿美元。ETH 都是 17 条腿、名义 1,068 万美元。占比用逐笔名义做分母。非 RFQ 大宗是有 `block_trade_id`、没有 `block_rfq_id` 的打印。

同合约键是币种、到期日、行权价、Call/Put。Deribit 名称如 `BTC-30OCT26-84000-C`，Derive 如 `BTC-20261030-84000-C`。本次 BTC、ETH 期权的报价币都是 BTC 或 ETH。

执行价配对只保留 Derive 的 CLOB taker，以及 Deribit 上没有 `block_rfq_id`、`block_trade_id`、`combo_id` 的打印。5 分钟内就近、每笔 Deribit 只用一次。规模过滤是币数之比在 0.5 到 2。配对 14 笔、同方向 9 笔，不形成执行成本结论。

## 激励

OPTIONS-MAJ 的 `rewards.DRV` 来自 `public/get_maker_programs`。最近三个已结束周期都是 200,000 DRV、OP 为 0。`public/get_maker_program_scores` 的行字段是分数和 `volume`，没有 reward、DRV、USDC 发放字段。`total_volume` 与 DefiLlama 名义同数量级但大约高出三成，单位未在响应里说明。

账内返佣 = 期权 `dailyFees − dailyRevenue`。V2 适配器 `derive-options`，V3 适配器 `derive-v3-options`。同一天两边都为正才记为冲突；第 23–25 期没有这种日期，也没有缺日。10 月 6 日的名义只在 V2，费用和收入只在 V3。

机构奖励页在采集时仍写每 28 天最多 500,000 USDC 和 1,000,000 DRV。这是上限。30 日 maker 行的 `expected_rebate` 合计 33,170 美元，taker 行该字段全为 0。预期返佣未改写成已支付。

CoinGecko `derive` 现价 0.383398 美元只说明分配额的市价尺度。正文没有把 20 万 DRV 乘进单位成本。
