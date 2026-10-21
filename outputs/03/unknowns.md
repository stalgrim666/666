# 未能核实的项目与下一步

采集日：2026-10-21。下面每一项都是本次主动找过、但不能填进结论的缺口。

## 账户与归属

- **DAO 可支配奖励余额。** DefiLlama Ethereum-OwnTokens 的 487,645,145.71 DRV 等于 `0xee900961552df080712fbefaee7152d932b384bc` 与 `0x169a99b9958386a5d91e732ed08b344946a92391` 之和。二者是外部账户，不是 DIP 所写的 3/5 Safe，治理原文也没有点名。Coinranking 的 FOUNDATION 标签覆盖了另一个地址 `0x526a371f9b65835a5c54d6065a792b418da2ed88`，与 DefiLlama 集合不一致。下一步：向基金会要 BVI 3/5 与战略托管的地址清单，再对这两个地址做历史内部转账；在此之前余额不能当奖励预算。
- **主 USDC 地址。** 2026-10-21 跟踪余额为 4,860,638.99 USDC，外加 sUSDe 与 syrupUSDC。DIP-309 的 Zapper 包今日只还对得上 Optimism `0xD4C00FE7657791C2A43025dE483F05E49A5f76A6` 的 8,738.42 USDC。下一步：从 DefiLlama treasury 适配器源码导出地址（当前 `projects/treasury/lyra.js` 在默认分支已 404），再与 Safe 签名人名单对照。
- **HyperEVM 上「铸给 BVI Safe」的原始收款地址。** 提案只写了机制。五链 `totalSupply` 合计已接近 15 亿，但单笔铸造交易未在本次逐笔打开。下一步：在 HyperEVM 上查 `0x9628bba16db41ea7fe1fd84f9ce53bc27c63f59b` 的 Mint 事件。

## 私人协议与实际补贴

- **FalconX 或任何做市商的侧信、抵押映射、保证报价期限。** 不在公开治理文本里。负费率是否被某家用满，无法从费率表推出。
- **每 28 天实际发出的 DRV 与 USDC。** `stats-api.derive.xyz/fees` 需要 `DERIVE_API_KEY`，无密钥为 404。DefiLlama 只提供返佣代理。下一步：用官方只读密钥重拉 `makerRebates` 日行，并对照 epoch 付款交易。
- **「9 月末暂停 Trading Rewards」。** 论坛无暂停 DIP；docs 仍描述零售奖励在发放；2026-09-24 DIP 背景仍列每周 5 万 DRV。X 全文检索返回意外的账单错误，本次没有读到官方帖。下一步：重试 X 上 `@derivexyz` 2026-09-23 至 10-07 的帖子，并核对 `derive.xyz/rewards` 的 epoch 金额。这是产品页，不是链上证明。
- **June 30 的年份。** 机构文档写 1,000,000 DRV 自 June 30 00:00 UTC 的 epoch 起分配，页面没印年份。标的列表像 2026 年的市场集，但不能单独当作日期证据。

## 付费或本次没有的市场数据

- **周活跃交易者、累计独立交易者。** 公开 DefiLlama 汇总里没有。Dune 与 Token Terminal 一类接口通常要账号或付费。下一步：若有现成的公开 Dune 查询号，只复用其 SQL，不新建猜字段的脚本。
- **期权未平仓的日序列。** 协议页搜索摘要里出现过时点 OI，但 `summary/options` 本次没有可用的日度 OI。comparison.csv 留空。
- **同口径买卖价差。** `api.lyra.finance` 本次 503。即使恢复，也只有当前盘口，没有暂停前的历史快照。15 分钟随机快照是内部评分输入，公开文档没有结果序列。
- **V3 之后的 builder fee 明细。** DefiLlama V3 期权收入表把 builder fee 单独列出，累计到采集日只有数百美元量级的一行，不足以做「第三方流量占比」。未单列进比较表。

## 可以立刻做、且不依赖新权限的复核

1. 用 HyperEVM、以太坊浏览器打开上述两个 DRV 地址的首次入账，看对手方是不是公开的团队多签。
2. 等 X 检索恢复后，只核「trading rewards paused」是否出自 `@derivexyz`。
3. 若拿到 `DERIVE_API_KEY`，只拉已有文档写明的 `fees` 查询参数：`market=all`、`instrument=option|perp|spot`、`view=daily`，用 `makerRebates` 替换本次的费用减收入代理。
