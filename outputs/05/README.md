# 05 期权三类判断：哪些数拿得到

抓取时间：2026-10-21 约 10:09 UTC。脚本把原始响应放在 `raw/`，整理结果在 `observations.csv`。可获取性结论在 `availability.csv`，15 行。不能识别的问题在 `unknowns.md`。

## 运行

```bash
cd outputs/05
python3 -m pip install -r requirements.txt
python3 fetch_data.py
```

依赖只有 `requests` 和 `pandas`。不需要 API key，不读取环境变量里的密钥。本环境实测版本是 Python 3.12、requests 2.34.2、pandas 3.0.6。

再次运行会覆盖 `raw/` 和 `observations.csv`。Derive 的成交缓存含公开钱包地址；`observations.csv` 只保留地址个数。

## 已测试

成功且无步骤失败：OCC 月内 CSV、CFTC TFF Combined 与 Futures Only、CFTC 公开目录、Deribit 期权与期货 book summary、Deribit trade volumes、Deribit Block RFQ、Deribit 最近 1000 笔期权成交、Coinbase International instruments、Derive 全部活期权 ticker、Derive 最近 24 小时期权成交、Derive OPTIONS-MAJ 激励计划合计、DefiLlama Derive V3 名义 / 权利金 / OI 和 V2 名义。

未拿到字段：`https://www.cmegroup.com/` 在 12 秒时超时，0 字节。CME 比特币期权和期货的成交、未平仓没有写入数字。

只核实字段、没有采用数值：Cboe Open-Close 的公开样例表头。样例文件是专有数据，没有放进 `raw/`。

## 这批数能支持的说法

精确值以 `observations.csv` 为准。下面只写口径已经在返回字段或官方字段说明里对上的部分。

OCC 2026-10-20 的成交是 63,368,285 张，其中 Equity 56,086,800 张，Index/Others 6,933,247 张，Futures 348,238 张。同一天 OI 合计 652,055,789 张，Equity 604,883,900 张。单位是合约张数。

CFTC 标准 CME Bitcoin（合约单位 5 BTC）在 2026-10-13 的 Combined 未平仓是 21,018 张，Futures Only 是 20,752 张。Combined 多头一侧的公布百分比是 Dealer 31.6、Asset Manager 24.2、Leveraged Funds 26.1、Other Reportables 0.8、Nonreportable 4.9；对应的 spreading 百分比是 2.2、1.3、8.7、0.3。空头一侧 Leveraged Funds 是 54.1，Dealer 22.7，Asset Manager 6.8，Nonreportable 4.0。微型合约 Nonreportable 多头是 18.8，和标准合约不是同一个结构。交易商人数在标准合约 Combined 报告里是 115。

Deribit 同一快照里，BTC 期权未平仓 383,821 个基础币，按各合约 `underlying_price` 相乘后约 322.4 亿美元。24 小时期权基础币成交 50,446，按同样方法约 42.1 亿美元。OI 加权 mark IV 是 45.0（这个接口的 mark IV 是百分数）。ETH 期权 OI 加权 mark IV 是 59.7。BTC 期货 `volume` 合计 16,464 基础币，`volume_usd` 13.59 亿美元；`BTC-PERPETUAL` 的 `open_interest` 是 849,259,380，文档把反向期货的该字段定义为美元。期权上的 `volume_usd` 不是基础币乘标的价格：成交最大的 `BTC-30OCT26-95000-C`，`volume_usd` 为 401,766.7，基础币乘标的价格约 1.010e9。

Derive 全部期权的名义 OI（`stats.oi` 乘指数 `I`）约 20.05 亿美元。DefiLlama 对 Derive V3 的单边名义 OI 最新点是 2,007,676,472 美元。Derive ticker 的 24 小时名义约 2.061 亿美元、权利金约 279 万美元；DefiLlama 的 UTC 日名义是 219,395,154 美元、权利金 2,974,774 美元。两个窗口不一样，数量级和权利金比率一致。taker 成交的 `trade_amount * trade_price` 除以 ticker `stats.pr`，全部期权是 1.009。名义加权 IV 是 BTC 0.411、ETH 0.620。

Derive 最近 24 小时的 taker 成交里，RFQ（`rfq_id` 非空）占全部期权成交笔数的 25.4%，占 taker 名义的 81.3%。BTC 是 24.6% 的笔数和 86.3% 的名义。这是执行通道的集中度：大名义更多走 RFQ，多数笔数仍在订单簿。

## 文件

| 文件 | 内容 |
| --- | --- |
| `availability.csv` | 15 行可获取性 |
| `observations.csv` | 269 行实测数值 |
| `fetch_data.py` | 可重复运行的抓取 |
| `raw/` | 原始响应 |
| `unknowns.md` | 标成 N/A 的问题 |
