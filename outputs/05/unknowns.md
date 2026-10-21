# 不能识别的部分

下面每一项都是 N/A。没有用金额、换手或产品名称去补。

## 独立持仓还是配套对冲

N/A。CFTC 的 spreading 列是跨月份或期货与期权之间的报告头寸，不是“这笔期权是否配了现货或永续”。Deribit 和 Derive 的公开成交没有对手方的其他场所仓位。客户在 Deribit 的期权成交，不能用来看见他在 Binance 的现货或永续仓位。Coinbase International 的公开合约列表里没有期权，也没有和 Deribit 账户相连的身份。

## 客户类型的成交占比，以及它和持仓占比的差别

N/A，除了已经付费才能拿到的 Cboe Open-Close。那份数据的字段已经从公开样例表头读到：Customer、Professional Customer、Broker-Dealer、Firm 有买/卖和开/平；Market Maker 只有买/卖。它统计的是成交张数。即便买到全量，开仓张数仍不等于独立持仓占比。

OCC 日文件没有客户类型，也没有开/平仓。

CFTC 给出的是持仓分类，不是成交分类。Nonreportable 在标准 CME Bitcoin Combined 报告里占多头 OI 的 4.9%、空头的 4.0%。这是低于报告门槛的交易商占该合约未平仓的比例。它不是零售成交占比，也不是期权客户占比。微型合约的 Nonreportable 多头是 18.8%，所以两个合约也不能合成一个“比特币零售占比”。

Deribit 没有公开的客户类型成交。Block RFQ 和 `block_trade_id` 都不是客户类型。

Derive 的钱包地址可见，客户类型不可见。最近 24 小时有 261 个不同的 taker 地址。这不是注册用户数，也不是专业用户数。

## 期权单独的 CFTC 持仓

N/A。公开目录没有 Options-only 视图。`opt_disagg_txt_2026.zip` 返回 404。Combined 未平仓 21,018 与 Futures Only 20,752 都是公布值，两者的差不是官方期权持仓。

## RFQ 或 Block 是否等于机构成交

N/A。Derive 上 RFQ 占 BTC taker 名义的 86.3%，只说明执行通道。一笔大额 RFQ 可以是任何能提交 RFQ 的账户。

Deribit 近 24 小时返回 44 个 BTC Block RFQ 包，`amount` 合计 1,320.2；ETH 是 4 个包，合计 1,300。最近 1,000 笔 BTC 期权成交里有 28 笔带 block 字段，时间只从 2026-10-21 08:13 UTC 到 10:09 UTC。这些计数没有除以盘口成交。包的 `amount` 不是各腿加总，非 RFQ 的大宗不在这个公开接口里。

## 用金额判断是不是专业交易者

N/A。Cboe 样例把客户再按张数分成三档，那是合约张数档，不是专业身份。Professional Customer 才是容量标签，而且只在付费文件里。

## CME 比特币期权相对期货

N/A。本环境没有从 `www.cmegroup.com` 读到任何成交或未平仓字段。

## Derive 的用户规模，以及激励前后的成交

用户规模：N/A。

激励前后：N/A。`OPTIONS-MAJ` 返回的 26 个 epoch 每一期都有 DRV 奖励，序列里没有激励开始前的 BTC/ETH 期权窗口。上一期的 `total_volume` 是计划内记分成交，不是全市场成交，也不能扣成自然成交。当期奖励是 200,000 DRV，这是分配额度，不是已经发生的手续费。

## 不能拿这一天去改研报里的半年比率

Deribit 这一天的期权基础币成交高于它自己的期货基础币成交。分母只是 Deribit。研报里 Crypto-native CEX 的 7.5% 用的是半年、多家交易所的名义成交。这两个比率不是同一次测量。DefiLlama 的 Derive 日名义也只覆盖 Derive，不能当成全部 DEX 期权。

## 字段本身还留下的口径差

- Deribit 期权 `volume_usd` 与期货 `volume_usd` 不是同一个经济量。
- Derive 其他币的合约张数很大，名义 OI 并不大。跨币比较用名义，不用张数。
- OCC 的张数不是名义金额。Equity 占当天张数的大部分，不能换成“Equity 占了大部分风险”。
- DefiLlama V2 名义序列的最后一点是 2026-10-07 的 0。V3 大约 15 个日点。中间的迁移不能当成连续增长。
