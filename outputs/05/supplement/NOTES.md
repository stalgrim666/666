# 补充计算说明

第一轮的 `raw/` 和 `observations.csv` 没有改。24 小时通道统计用的是冻结文件 `raw/derive_option_trades_24h.json`。7 天成交是新抓的，写在 `supplement/derive_option_trades_7d.json`。7 天窗口的结束时间等于冻结快照的结束时间 `2026-10-21T10:11:34Z`。

口径：

- 只计 `liquidity_role=taker`。同一 `trade_id` 还有一行 maker，不计入名义和权利金。
- RFQ 是 taker 行的 `rfq_id` 非空。冻结的 24 小时里，有 `rfq_id` 的 335 条腿同时有 `quote_id`；没有 `rfq_id` 的 983 条腿也没有 `quote_id`。CLOB 就是 `rfq_id` 为空。
- 名义 = `trade_amount * index_price`。权利金 = `trade_amount * trade_price`。第一轮里，这个权利金合计除以 ticker `stats.pr` 是 1.009。
- 成交腿是一条 taker 成交、一个合约。独立 RFQ 数是这些腿上不同的 `rfq_id`。24 小时 203 个 RFQ 里，84 个 1 条腿、110 个 2 条腿、5 个 3 条腿、4 个 4 条腿。
- 去重键是 `trade_id + liquidity_role + subaccount_id`。24 小时和 7 天的原始行数都等于去重行数。
- Top 5 / Top 10 是该通道内部 taker 名义的地址占比。地址没有身份标签。同一地址可以同时出现在 RFQ 和 CLOB，所以两侧钱包数相加大于全部钱包数。
- OPTIONS-MAJ 来自冻结的 `raw/derive_maker_programs.json`。`rewards.DRV` 是该期接口返回的分配额度，不是已发放金额，也不是文档里那组 100 万 DRV 做市池的合计。
- 30 天只做了 `page_size=1` 的计数，没有拉成交。
