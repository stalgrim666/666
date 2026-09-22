# Options vs Futures / Perpetual：每 $1 Notional 的 Effective Take Rate

研究时点：2026-09-22。比较口径是**一笔撮合只计一次的标的名义成交额**（underlying notional）。Taker fee 不是 take rate。权利金成交额只在辅助小节使用。

数字分三类：

- **官方披露**：交易所公告、帮助中心、清算价目表、投资者关系稿、10-K / 业绩稿。
- **推导值**：用官方费率或官方收入、官方合约乘数，乘上标明日期的价格。
- **第三方**：经纪商转嫁的交易所费、行情供应商价格、二手成交份额。不把它写成交易所价目表原文。

---

## 1. 三个定义

**Taker fee** 是单边主动成交者的费率。下文只把它当作输入。

**Theoretical Gross Take Rate**（理论毛费率）按一笔撮合的 notional 只计一次：

\[
Gross\ Take\ Rate = \frac{Maker\ Fee + Taker\ Fee}{Matched\ Notional}
\]

Maker 为返佣时，分子是 taker 减去返佣，得到的是**净**毛费率。买卖双方都按每张合约收费时：

\[
Gross\ Take\ Rate = \frac{Buyer\ Fee + Seller\ Fee}{Contract\ Notional}
\]

\[
Contract\ Notional = Underlying\ Price \times Multiplier
\]

**Realized Take Rate** 只用同期、同范围的交易手续费收入除以 notional volume。市场数据、上币、托管、利息、订阅、稳定币浮存、清算以外的其他收入都不进分子。产品收入拆不开，就写「无法计算产品级 Realized Take Rate」，不估。

权利金上限（premium cap）会让便宜期权的 **fee / notional 低于标题费率**，同时把 **fee / premium 抬到上限**。上限不是把 take rate 越算越高的开关。

---

## 2. 表 1｜Crypto

理论毛费率的前提：标题费率对两边都生效，且权利金上限**没有**绑定。上限一旦绑定，期权的 notional take rate 会低于表中数字。Realized 一列除 Deribit 的全平台混合下限外，全部是无法计算。

| 平台 | 产品 | 标准 Maker | 标准 Taker | 理论 Gross Take Rate | Realized Take Rate | 每 $1B Volume 收入 | 数据可信度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Deribit | Options | 3.0 bps | 3.0 bps | **6.0 bps** | 无法计算产品级 | 理论 $600,000 | 官方图（2025-11-01 档）经 OCR。2026-08-01 新表是标题图，数字未能转写 |
| Deribit | Perp | −1.0 bps | 5.0 bps | **4.0 bps 净** | 同上，仅有全产品混合 | 理论 $400,000 | 同上。此行是「周度 + 永续」列，不是 2026-08-01 之后的统一期货费率 |
| Deribit | 到期期货（不含周度） | 0 | 5.0 bps | **5.0 bps** | 同上 | 理论 $500,000 | 同上 |
| Bybit | Options | 0.020% | 0.030% | **5.0 bps** | 无法计算 | 理论 $500,000 | 官方帮助中心，更新于 2026-08-19。上限为权利金的 7% |
| Bybit | Perp | 0.020% | 0.055% | **7.5 bps** | 无法计算 | 理论 $750,000 | VIP0 来自 Bybit Kazakhstan 费率表，页面写明地区可能不同 |
| Binance | Options | 0.024% | 0.024% | **4.8 bps** | 无法计算 | 理论 $480,000 | 官方公告，2026-09-09 仍为现行促销（2025-08-04 起至另行通知） |
| Binance | USDⓈ-M Perp | 0.020% | 0.050% | **7.0 bps** | 无法计算 | 理论 $700,000 | 官方 FAQ 的 Regular User 示例。用 BNB 付费再打九折，两边都用 BNB 则约 6.3 bps |
| OKX | Options | 0.030% | 0.030% | **6.0 bps** | 无法计算 | 理论 $600,000 | 官方公告，2025-01-28 发布、2025-02-10 生效；页面 2026-08-11 仍可打开。上限为权利金的 7% |
| OKX | Perp / Futures | 0.0200% | 0.0500% | **7.0 bps** | 无法计算 | 理论 $700,000 | 官方 2026-09-09 调整说明：Regular 不变，只改 VIP 7/8 |

每 $1T 的理论收入是上表每 $1B 的 1,000 倍：期权大约 $480M–$600M，主流永续大约 $700M–$750M，Deribit 永续上一版净额约 $400M。

Deribit 全平台、2025 年 7 月，只有一个可以摆上桌的实现口径，而且**不是**期权单独 take rate：

| 项目 | 数值 | 标签 |
| --- | --- | --- |
| 口径 | Options + Futures blended（Coinbase 写的是平台 trading volume 与 transaction revenue；当时现货零费，但仍含期货与永续） | 官方披露的范围，不是期权拆分 |
| 成交 | 超过 $185B | 官方，2025-08-14 |
| 交易收入 | 超过 $30M | 官方，2025-08-14 |
| 下限除下限 | \(30 / 185 = 1.62\) bps | 推导值。两边都是「超过」，比率本身可高可低 |
| 对应每 $1B | 约 $162,000 | 同一推导，只表示数量级 |

Coinbase 写明 Q3 只并表 8 月 14 日至 9 月 30 日，并提醒不要外推。Q3 那 47 天的 Deribit 收入若没有同期成交，本备忘录不计算比率。

---

## 3. Crypto 费率怎么来的

### 3.1 Deribit

2025-09-24 的官方说明《New Volume Discounts On Trading Fees》给出 2025-11-01 起的费率图。图本身不是 HTML 表。两套 OCR 对**标准档**读数一致：

- 到期期货（不含周度）：maker 0 / taker 5 bps
- 周度与永续：maker −1 / taker 5 bps
- 期权：maker 3 / taker 3 bps

因此标准用户、上限未绑定时：

- 期权 gross = 3 + 3 = **6.0 bps**
- 永续 gross = −1 + 5 = **4.0 bps 净**
- 非周度期货 gross = 0 + 5 = **5.0 bps**

同一张图的 VIP 档（OCR，VIP 行的个别字符不如标准行干净）：期权从 VIP1 的 2.5/2.5 bps 降到 VIP5–VIP6 的 1/1 bps；期货 taker 从 5 bps 降到大约 2.25–2.35 bps，maker 维持 −1 bp 返佣。标准档两边都付 3 bps，VIP 深处两边合计可以落到 **2 bps**。这是价目表，不是成交加权平均。

权利金上限来自 Deribit 帮助中心文本的公开转载：费用 = \(\min(0.0003 \times 标的, 0.125 \times 权利金)\)，maker 与 taker 同一公式，交割费同样受 12.5% 限制。本次没能打开现行知识库页面（SPA，无表），也没能转写 2026-08-01 新图。12.5% 按**历史官方规则**使用，不把它写成 2026-09-22 已逐字复核的现页。

上限绑定条件（单边 3 bps、上限 12.5%）：

\[
\frac{Premium}{Notional} < \frac{0.0003}{0.125} = 0.24\%
\]

权利金高于标的的 0.24% 时，收费停在 3 bps notional。更便宜的合约，fee / notional 低于 3 bps，fee / premium 升到 12.5%（单边）。

2026-06-29 公告、2026-08-01 生效的变化，正文写明了，数字表没有：

- 永续和期货的 taker 降低、maker 返佣也降低，**净费用与此前接近**
- 日度 / 周度期货不再单列，所有到期共用一套期货费
- 期货价差的 maker 返佣改为 0
- 强平费统一为 1%
- 新增 VIP7：区块交易费再打九折，期权结算费全免
- 现货费率最高档 2 / 5 bps，最低档 0 / 2 bps；在接入 Coinbase 现货流动性之前现货费减免

所以表 1 的 Deribit 期货行是 **2025-11-01 标准档**，不是 2026-08-01 之后的精确单元格。公告自己的判断是期货净费用变化不大。期权标题费率没有出现在这次正文的变更清单里，但是新表未能转写，**不能签字保证 2026-09-22 仍是 3/3**。

区块列在图上是单一 bps（标准档期货约 2.5、期权约 3），没有拆成 maker + taker。这里不把它再加一次，以免把区块费重复计算成 gross take rate。

交割费（历史规则约 0.015% of underlying，同样有 12.5% 上限）发生在行权，不是成交 notional 的手续费。不进 gross take rate。

### 3.2 Bybit

帮助中心《Options Trading: Fees Explained》，更新于 2026-08-19，非 VIP：

- Maker 0.02%，taker 0.03%，计费基数是指数价格（标的名义）
- 单张交易费不超过权利金的 **7%**
- 公式：\(\min(费率 \times Index,\ 7\% \times 权利金) \times 数量\)

Taker 上限绑定于权利金 / 标的 < \(0.03\% / 7\% = 0.429\%\)。Maker 绑定于 < \(0.02\% / 7\% = 0.286\%\)。

交割费另计：BTC/ETH 0.015%，SOL/MNT/XRP/DOGE 0.02%，上限为内在价值的 12.5%；日期权无交割费。强平 0.2%。Pro 用户的权利金上限从 7% 降到 4%。这些都不进表 1 的交易 gross take rate。

标准 gross = 0.02% + 0.03% = **5.0 bps**。

永续 VIP0：Bybit Kazakhstan《Trading Fee Structure》为 maker 0.0200%、taker 0.0550%，gross **7.5 bps**。该页写明实际费率可能因地区而异。Supreme VIP 在同一张表上是永续 maker 0 / taker 0.030%，期权 maker 0.005% / taker 0.015%。这是价目表顶端，不是市场平均。

### 3.3 Binance

期权：公告《Binance Launches Dual Options Promotions》，发布 2025-07-31，更新 2026-09-09。2025-08-04 起新上市合约、至另行通知，全 VIP 促销费率 maker = taker = **0.024%**（在 0.030% 上打八折）。Gross = **4.8 bps**。

Enhanced Program（2025-08-05 起）：

| 档 | Maker | Taker |
| --- | --- | --- |
| Regular | 0.0240% | 0.0240% |
| Tier 1 | −0.0120% | 0.0210% |
| Tier 2 | −0.0150% | 0.0150% |

Tier 2 对 Tier 2 的净毛费率 = −1.5 + 1.5 = **0 bp**。做市份额高的时候，标题 4.8 bps 不是交易所拿到的钱。

该公告没有重申权利金上限。更早的 FAQ 转述把交易费封在成交金额的 10%、行权费约 0.015%。本次**不把 10% 上限写成已复核的现行单元格**。

USDⓈ-M：官方 FAQ 的 Regular User 示例为 maker **0.02%**、taker **0.05%**，费用 = 持仓名义 × 费率。Gross = **7.0 bps**。BNB 支付有 10% 折扣；两边都用 BNB 时为 1.8 + 4.5 = **6.3 bps**。这是可选项，不替代 7.0 bps 的主行。

Binance、Bybit、OKX 都没有可与产品成交匹配的交易收入披露。产品级 Realized Take Rate：**无法计算**。

### 3.4 OKX

期权公告 2025-01-28，2025-02-10 生效。Regular / Lvl 1：maker 0.030%、taker 0.030%。Gross = **6.0 bps**。VIP 8：maker −0.010%、taker 0.013%，净毛费率 **0.3 bps**。资格门槛后来可能被全球费率框架改过；本表用的是这张期权专用费率，不是用期货 VIP 表去套期权。

现行《Trading Fee Rules》给出的公式是：

\[
\min(费率,\ 7\% \times 权利金) \times 乘数 \times 面值 \times 张数
\]

行权费 = \(\min(0.02\%,\ 用户 taker,\ 7\% \times 结算价值)\)。日期权无行权费。RFQ 组合最高约 50% 折扣，且费记在名义更高的那一腿。组合折扣会把多腿策略的 notional take rate 再压低，但没有成交结构，就不做加权。

期货：2026-09-09 的调整说明列出 Standard 组 Regular 为 maker **0.0200%**、taker **0.0500%**，并写明 VIP 7/8 以外的档位不变。Gross = **7.0 bps**。VIP 9 为 maker −0.0050%、taker 0.0150%，净毛费率 **1.0 bp**。

FAQ 里「Trader A：maker 0.02%、taker 0.03%」是举例用的费率，低于 Regular 期权的 0.03%/0.03%，不拿来覆盖公告。

### 3.5 未进入主表的平台

Coinbase Derivatives、Hyperliquid、Paradex、Derive、Aevo：这次没有拿到与上表同一口径、可复核的期权 maker/taker 原文，也没有产品收入。主表留空，不补第三方博客费率。

---

## 4. Crypto 行业：没有收入加总，只有理论费率加权

四家平台没有可加总的期权交易收入，也没有可加总的永续交易收入。因此：

\[
Industry\ Options\ Take\ Rate = \frac{\sum Options\ Transaction\ Revenue}{\sum Options\ Notional}
\]

**无法计算。** 期货 / 永续同样无法计算。

下面是费率表推导的 **Headline Fee Yield**，明确不是实现收入率。份额用的是第 4 章已引用的 2026 年上半年代理数据（CoinGlass，经 ChainCatcher），只覆盖这四家在加密期权成交里的相对权重，并重新归一。份额是第三方，费率是上面的官方标题档。

| 平台 | 归一化期权成交权重 | 标准期权 Gross | 贡献 |
| --- | --- | --- | --- |
| Deribit | 49.3 / 98.4 = 50.1% | 6.0 bps | 3.01 bps |
| Bybit | 22.8% | 5.0 bps | 1.14 bps |
| Binance | 13.6% | 4.8 bps | 0.65 bps |
| OKX | 13.5% | 6.0 bps | 0.81 bps |
| 合计 | 100% |  | **5.61 bps** |

每 $1B 期权 notional 的理论毛收入约 **$561,000**；每 $1T 约 **$561M**。权重里 Deribit 用的是 2025-11-01 的 6.0 bps。若 2026-08-01 之后期权标题费率变了，这个加权要重算。

三种情形，不要混用：

| 情形 | 期权 | 永续 / 期货 | 性质 |
| --- | --- | --- | --- |
| 标准用户，上限未绑定 | 四家加权 **5.6 bps**；单家 4.8–6.0 bps | Binance / OKX **7.0 bps**，Bybit VIP0 **7.5 bps**，Deribit 上一版永续净 **4.0 bps** | 价目表。假设两边都付标准费 |
| 大型做市 / 高 VIP | 可以落到约 **0–2 bps**（Binance Tier2 对 Tier2 为 0；Deribit VIP5+ 期权为 2 bps；OKX 期权高 VIP 约 0.3 bp） | 高 VIP 常见 maker 返佣，净毛费率约 **1–2.5 bps** | 价目表顶端，不是成交加权 |
| 可观察的实现区间 | 产品级：**无法计算**。唯一锚是 Deribit 2025-07 全产品下限除下限 **1.6 bps** | 同左，不能拆出永续 | 数量级：明显低于 6 bps 标题，和 VIP、上限、区块、返佣之后的净额同一量级 |

合理的实际区间因此不是一个点。标题档把期权放在 5–6 bps、把主流永续放在 7–7.5 bps；成交一旦偏向 VIP、区块和便宜期权，交易所留在账上的钱会靠近 2 bps 甚至更低。1.6 bps 只证明「全产品混合可以低到这个数量级」，不能证明期权单独就是 1.6 bps。

---

## 5. 表 2｜TradFi

全部是 **Headline / Theoretical**。CME 公开的是按资产类别的 rate per contract（美元 / 张），没有按产品公布「交易费收入 / 标的 notional」。资产类别 RPC 混有期货和期权、会员和非会员、标准合约和微型合约，**不能**除以某一个合约的 notional 冒充该品种的 Realized Take Rate。表内不出现 Realized 字样。

价格是 Yahoo Finance 的最近一根日线，用于把「美元 / 张」换成 bps，不是交易所结算价，也不是成交加权均价。

| 合约 | 行情 | 时点 (UTC) | 乘数 | Contract notional |
| --- | --- | --- | --- | --- |
| E-mini S&P 500 (ES) | 7,837.75 | 2026-09-22 04:00 | $50 | $391,887.50 |
| WTI (CL) | $93.53 | 2026-09-22 04:00 | 1,000 桶 | $93,530 |
| COMEX Gold (GC) | $4,357.80 | 2026-09-22 04:00 | 100 盎司 | $435,780 |
| US 10Y Note (ZN) | 105.96875 | 2026-09-22 04:00 | 面值 $100,000 | $105,968.75 |
| CME Bitcoin | $85,495 | 2026-09-22 00:00 | 5 BTC | $427,475 |
| EURO STOXX 50 指数，用作 FESX / OESX 近似 | 6,318.2 | 2026-09-21 07:00 | €10 | €63,182 |

ZN 名义 = \(105.96875 / 100 \times 100{,}000\)。EURO STOXX 用的是指数现货，期货基差没有调整。

CME / CBOT / NYMEX / COMEX 的美元费率来自 Interactive Brokers 的交易所费转嫁表。IBKR 写明这些数字**大体反映**非会员 Globex 费用，个别情况下可以高于或低于交易所实收。下表把它们标成**经纪商转嫁，近似价目**，不是 CME 价目表 PDF 的逐格抄录。NFA 监管费约 $0.01 / 边，是监管收费，不进交易所 take rate。Eurex 来自清算价目表和 2026 年费率通函，单位是每张、每边。

Gross =（买方每张 + 卖方每张）/ notional。下表假设一笔撮合的两边属于同一类参与者。

| 市场 | 参与者 | Options Take Rate | Futures Take Rate | O/F | 口径 |
| --- | --- | --- | --- | --- | --- |
| WTI | 非会员 | **0.321 bps** | **0.321 bps** | **1.00** | Headline。CL 期货与期权非会员都是 $1.50 / 边 |
| WTI | 会员（IBKR Tier 3） | 0.150 bps | 0.160 bps | 0.93 | Headline。期权 $0.70 / 边，期货 $0.75 / 边 |
| Gold | 非会员 | **0.0757 bps** | **0.0757 bps** | **1.00** | Headline。期货与期权都是 $1.65 / 边 |
| Gold | 会员 | 0.0367 bps | 0.0344 bps | 1.07 | Headline。期权 $0.80 / 边，期货 $0.75 / 边 |
| US 10Y | 非会员 | **0.160 bps** | **0.151 bps** | **1.06** | Headline。期权 $0.85 / 边，期货 $0.80 / 边 |
| US 10Y | 股权类会员公司（IBKR Tier II） | 0.0264 bps | 0.0264 bps | 1.00 | Headline。两边都是 $0.14 / 边 |
| E-mini S&P | 非会员 | **0.0281 bps** | **0.0704 bps** | **0.40** | Headline。期权 $0.55 / 边，期货 $1.38 / 边。会员美元费率本次没有从同一页抄到，留空 |
| EURO STOXX 50 | A 账户，订单簿标准档 | **0.114 bps** | **0.133 bps** | **0.86** | Headline。OESX €0.36 / 边，FESX €0.42 / 边。FESX 单元格来自 2026-08-17 价目表的文本抽取，列有错位，精确到欧分的置信度中等 |
| EURO STOXX 50 | P/M 账户，订单簿标准档 | 0.101 bps | 0.104 bps | 0.97 | Headline。OESX €0.32 / 边，FESX €0.33 / 边 |
| CME BTC | 非会员 | **0.234 bps** | **0.351 bps** | **0.67** | Headline。期权 $5.00 / 边，期货 $7.50 / 边。会员档本次未列出 |

每 $1B notional 的理论交易所收入（非会员或 A 账户，两边同档）：

| 市场 | 期权 | 期货 |
| --- | --- | --- |
| WTI | $32,100 | $32,100 |
| Gold | $7,570 | $7,570 |
| US 10Y | $16,000 | $15,100 |
| E-mini S&P | $2,810 | $7,040 |
| EURO STOXX 50（A） | €11,400 | €13,300 |
| CME BTC | $23,400 | $35,100 |

每 $1T 是上表的 1,000 倍。E-mini 非会员期货大约 **$7.0M / $1T**；同一合约的非会员期权大约 **$2.8M / $1T**。WTI 两边都大约 **$32M / $1T**。

### 5.1 计算式

WTI 非会员，期货与期权相同：

\[
\frac{1.50 + 1.50}{93.53 \times 1{,}000} = \frac{3.00}{93{,}530} = 0.321\ \text{bps}
\]

Gold 非会员：

\[
\frac{1.65 + 1.65}{4{,}357.80 \times 100} = \frac{3.30}{435{,}780} = 0.0757\ \text{bps}
\]

Gold 会员期权：

\[
\frac{0.80 + 0.80}{435{,}780} = 0.0367\ \text{bps}
\]

US 10Y 非会员期货：

\[
\frac{0.80 + 0.80}{105.96875 / 100 \times 100{,}000} = \frac{1.60}{105{,}968.75} = 0.151\ \text{bps}
\]

US 10Y 非会员期权：

\[
\frac{0.85 + 0.85}{105{,}968.75} = 0.160\ \text{bps}
\]

E-mini 非会员期货：

\[
\frac{1.38 + 1.38}{7{,}837.75 \times 50} = \frac{2.76}{391{,}887.50} = 0.0704\ \text{bps}
\]

E-mini 非会员期权：

\[
\frac{0.55 + 0.55}{391{,}887.50} = 0.0281\ \text{bps},\quad O/F = 0.40
\]

CME Bitcoin 非会员：

\[
\frac{7.50 + 7.50}{85{,}495 \times 5} = 0.351\ \text{bps},\qquad
\frac{5.00 + 5.00}{427{,}475} = 0.234\ \text{bps}
\]

EURO STOXX 50，A 账户，订单簿，指数 6,318.2 近似：

\[
\frac{0.42 + 0.42}{6{,}318.2 \times 10} = 0.133\ \text{bps (FESX)},\qquad
\frac{0.36 + 0.36}{63{,}182} = 0.114\ \text{bps (OESX)}
\]

OESX 的 M 账户在超过 8,000 张的减费档是 €0.05 / 边，两边合计 €0.10，对应 **0.016 bps**。这是流动性提供者减费，不是全市场平均。

微型合约的 bps 会高一截，因为每张费用没有按名义等比例缩小。Micro Bitcoin 非会员 $1.15 / 边，名义 = \(0.1 \times 85{,}495 = 8{,}549.5\)：

\[
\frac{2.30}{8{,}549.5} = 2.69\ \text{bps}
\]

这是合约规格效应，不代表标准 CME Bitcoin 的市场。Micro E-mini 同理：费用约 $0.35 / 边，名义是 ES 的十分之一，非会员 gross 大约是 ES 期货的 2.5 倍 bps，仍然远低于加密永续的 7 bps。

### 5.2 CME 的实现 RPC 为什么不能填进表 2

2025 年 10-K 与 Q4 业绩稿（官方）：

- 清算与交易费收入 $5,281.1M，其中现金市场 BrokerTec + EBS 约 $283.7M，利率互换另有 $84.4M。上市期货与期权的清算交易费大约是资产类别合计 **$4,913.0M**（利率 1,719.6 + 股指 1,170.4 + 外汇 197.0 + 农产品 658.1 + 能源 813.2 + 金属 354.7）。
- 上市期货与期权 ADV **28.1M** 张。业绩稿定义：ADV 与 RPC 只含期货和期货期权，不含 event contracts。
- Q4 2025 平均 RPC **$0.707 / 张**。分项：利率 $0.486，股指 $0.611，外汇 $0.847，能源 $1.245，农产品 $1.427，金属 $1.295。

CME 的成交量按撮合张数计一次：买入 1 张 E-mini，volume +1，不是 +2。因此 RPC 已经是「这一张撮合带给交易所的收入」，接近两边费用之和的成交加权平均，而不是单边 taker fee。

股指 Q4 RPC $0.611，若错误地除以 ES 名义 $391,888，会得到 0.016 bps。这个除法无效：股指 ADV 里有大量 Micro E-mini，名义只有 ES 的 1/10，RPC 是张数加权，不是名义加权。能源 RPC $1.245 除以 CL 名义会得到约 0.13 bps，同样无效，因为能源里有天然气、迷你和期权。

在 CME 公布按资产的 notional volume 之前，**资产级 Realized Take Rate = N/A**。能说的只有：实现的美元 / 张远低于「非会员两边都付价目表」——股指 $0.611 对比 ES 非会员两边 $2.76。会员价、激励和产品结构吃掉了大部分标题费率。这正是不能用零售最高价代表市场的原因。

### 5.3 美国股票 / ETF 期权

Cboe / OCC 的股票与 ETF 期权、SPX、SPY、IBIT **不进入表 2**。交易所层同时存在 maker-taker、inverted pricing、ORF、清算费；经纪商层还有 PFOF。把其中任何一项除以 notional，再和 CME 期货的双边交易所费放在同一张精确表里，会把不同收费层加成一个数。

Robinhood 的期权净收入大约每张客户合约 $0.44（第 4 章已按公司披露核对）。那是分销和订单流的变现，不是交易所 take rate。SPY 一张的名义大约是股价 × 100；在 2026-09 的指数水平上，每张几十美元的经纪商收入对 notional 可以是几个 bps，和 CME 交易所那零点几个 bps 不是同一层生意。

---

## 6. 权利金分母

主比较始终用 notional。权利金只解释「费率看起来不高，但占客户实际支付对价的比例可以很高」。

Deribit 标准档、上限未绑定，单边 3 bps of notional：

| 权利金 / 标的 | 单边 fee / premium | 双边 fee / premium | 单边 fee / notional |
| --- | --- | --- | --- |
| 10% | 0.30% | 0.60% | 3.0 bps |
| 5% | 0.60% | 1.20% | 3.0 bps |
| 2% | 1.50% | 3.00% | 3.0 bps |
| 0.24%（刚好绑定） | 12.5% | 25% | 3.0 bps |
| 0.10% | 12.5% | 25% | **1.25 bps** |

绑定之后，交易所对 notional 的变现**变差**，对权利金的变现停在上限。Bybit / OKX 的 7% 上限更早绑定（Bybit taker 在权利金 / 标的低于 0.43% 时）。没有各所「权利金成交额 / 名义成交额」的官方序列，本备忘录**不估算**全市场 fee / premium volume。

TradFi 期权交易所费按张收取，和权利金无关。一张 ES 期权无论值 $50 还是 $5,000，非会员交易所费都是 $0.55 / 边。便宜期权上，fee / premium 可以很高；贵的期权上，fee / premium 很低。这也是不能用权利金费率去和期货 bps 比大小的原因。

---

## 7. 六个问题

**1. Crypto Options 每 $1 notional 能赚多少？**

标准用户、上限未绑定：四家标题毛费率 **4.8–6.0 bps**，按 2026 年上半年期权成交权重加权约 **5.6 bps**。即每 $1B 理论毛收入约 **$56 万**，每 $1T 约 **$5.6 亿**。大型做市档可以到 **0–2 bps**。产品级实现收入率：**无法计算**。Deribit 2025 年 7 月全产品混合的下限除下限是 **1.6 bps**（每 $1B 约 $16 万），这是 Options + Futures blended，而且分子分母都是「超过」。

**2. Crypto Perp / Futures 每 $1 notional 能赚多少？**

Binance、OKX 的标准用户 **7.0 bps**（每 $1B 约 $70 万）。Bybit VIP0 **7.5 bps**。Deribit 在 2025-11-01 价目上，永续净 **4.0 bps**、非周度期货 **5.0 bps**；2026-08-01 之后净额「接近此前」，精确单元格缺失。高 VIP 净毛费率大约 **1–2.5 bps**。产品级 Realized：**无法计算**。

**3. 期权的单位成交变现效率，高于还是低于永续？差多少？**

在标准用户、上限未绑定的标题费率上，**期权低于或接近永续，而不是高于**。主流三家：期权 4.8–6.0 bps，永续 7.0–7.5 bps，期权大约低 **1–2.5 bps**，相当于永续标题费率的七成到八成。Deribit 是例外的方向：期权 6.0 bps，上一版永续净 4.0 bps，期权高 2 bps，因为永续 maker 有 1 bp 返佣。权利金上限、VIP 返佣、区块和组合折扣都把期权的 notional 变现再往下压。实现层面的「差多少」没有产品收入，**证据不足**。

**4. TradFi 的期权和期货是不是同样的关系？**

不是「期权 take rate 系统性地更高」。在同一参与者、同一标的名义下：

- WTI：非会员两边都是 0.32 bps，比值 1.00
- 黄金：非会员两边都是 0.076 bps，比值 1.00；会员期权略高，比值 1.07
- 美国 10 年：非会员期权 0.16 bps、期货 0.15 bps，比值 1.06
- E-mini：非会员期权 0.028 bps、期货 0.070 bps，比值 **0.40**
- EURO STOXX 50：A 账户 0.114 / 0.133，比值 0.86；P/M 接近 1
- CME Bitcoin：非会员 0.23 / 0.35，比值 0.67

股指期权的交易所收费按张更便宜，名义又大，所以 notional take rate 低于对应期货。能源和国债大体同级。没有一张表支持「成熟市场靠极高的期权 take rate 赚钱」。

**5. Crypto 期权和 TradFi 期权的单位 notional 变现差多少？原因是什么？**

标准档、上限未绑定：加密期权约 **5–6 bps**，TradFi 期权非会员大约 **0.03 bps（E-mini）到 0.32 bps（WTI）**。倍数大约是 **20 倍（相对原油）到 200 倍（相对 E-mini）**。会员档的 TradFi 更低，倍数更大。

原因是收费层和合约设计，不是「加密期权客户更愿意付高费率」这一句就能说完的：

- 加密平台的费率是经纪、撮合、清算捆在一起的零售化百分比，直接打在标的名义上。
- CME / Eurex 的交易所费是每张几美元或几角欧元。ES 一张名义接近 $40 万，两边 $2.76 只有 0.07 bps。FCM 佣金、清算会员价差不在这张交易所表里。
- 会员和流动性项目把实现 RPC 再压到标题非会员费率之下。加密这边对应的机制是 VIP 返佣和权利金上限，所以 6 bps 同样不是实现值。
- 微型合约（Micro Bitcoin 非会员约 2.7 bps）说明：名义越小，固定每张费用的 bps 越高。加密期权按百分比收费，没有这种「大合约稀释」。

**6. 期权生意的价值来自更高的 take rate，还是来自用户、持仓、波动率生态和交叉销售？**

在本备忘录能够核对的费率上，**价值不来自更高的 notional take rate**。标准加密期权费率低于标准永续；TradFi 期权费率与对应期货同级或更低。Deribit 对 Coinbase 的可核对贡献是平台成交、持仓和一笔没有拆分的交易收入，加上收购对价 $2.9B 所承认的特许权，而不是一张「期权 bps 远高于永续」的实现表。

持仓和周转已经在第 4 章分开：期权可以占 BTC 衍生品未平仓的很大一块，同时只占衍生品成交的大约 2%。Take rate 如果只是同一数量级，收入份额就会更接近成交份额，而不是被 take rate 补成接近持仓份额。交叉销售（组保、期货对冲、现货）在费率公告里能看到产品设计，看不到单独的收入行。

---

## 8. 三个假设

**假设 A：期权成交低于永续，但 take rate 更高，所以收入缺口小于成交缺口。**

**不支持。** 可核验的标准费率方向相反或只是接近：主流平台期权 4.8–6.0 bps，永续 7.0–7.5 bps。权利金上限把便宜期权的 notional 费率再降低。Deribit 期权标题费率高于它自己的永续净费率，但加权之后行业标题仍然是期权略低。产品级收入不存在，所以「收入缺口是否小于成交缺口」这一句本身**证据不足**；A 所依赖的机制（take rate 更高）没有成立。

**假设 B：期权 take rate 与永续接近，价值来自机构客户、深的持仓和生态粘性。**

**部分支持。** 两边的标题费率都在几个 bps，VIP 之后都在大约 0–2 bps，实现锚（Deribit 全产品）在 1.6 bps 这个数量级。这和「同一量级」相符，和「期权是另一门高费率生意」不符。机构客户、OI 和粘性是定性判断：Deribit 的持仓份额长期高于成交份额（第 4 章，第三方），Coinbase 收购叙事强调的是期权流动性和持仓，不是超高费率。用户结构没有 2026 年的官方拆分，所以「价值主要来自机构」仍有一部分是判断，不是收入证明。

**假设 C：成熟市场的期权也不是靠极高 take rate，而是靠规模、长期持仓和做市 / 清算生态。**

**支持。** 表 2 里六组可算的 O/F 比值落在 **0.40 到 1.07**。没有一组的期权 notional take rate 达到加密标题费率的量级。CME 2025 年上市衍生品清算交易费 $49 亿、ADV 2,810 万张，变现体现在张数和规模上；股指实现 RPC $0.61 / 张，远低于非会员 ES 两边 $2.76，说明会员和激励才是成交的主体价格。Eurex 对 OESX 的 M 账户还有明确的量阶减费。美国股票期权交易所收入因为收费层太多，没有被塞进这张表；即便如此，也不存在一张「交易所靠极高 bps 吃期权名义」的官方比率。

---

## 9. 来源

官方披露

- Deribit Insights，2025-09-24，《New Volume Discounts On Trading Fees》，费率图 `https://insights.deribit.com/wp-content/uploads/2025/09/2025-11-10-fees-table.png`（2025-11-01 生效）。标准档经两套 OCR。
- Deribit Insights，2026-06-29（文内修改时间 2026-07-27），《New Fee Schedule On Deribit》。正文可用；主图是标题画，不是可转写的费率格。`https://insights.deribit.com/exchange-updates/new-fee-schedule-on-deribit/`
- Deribit Insights，2020-08-12，期权费自 0.04% 降至 0.03%。`https://insights.deribit.com/exchange-updates/deribit-lowers-option-trading-fees-to-make-the-market-more-accessible-to-retail-traders/`
- Bybit 帮助中心，更新 2026-08-19，《Options Trading: Fees Explained》。`https://www.bybit.com/en/help-center/article/Bybit-Option-Fees-Explained/`
- Bybit Kazakhstan，《Trading Fee Structure》（地区费率，VIP0 永续 0.0200% / 0.0550%）。`https://www.bybit.kz/en-KAZ/help-center/article/Trading-Fee-Structure/`
- Binance 公告，2025-07-31 发布，2026-09-09 更新。`https://www.binance.info/en/support/announcement/detail/8f1cae716974444da593806e7425e4ff`
- Binance FAQ，《Futures Fee Structure》，Regular User 0.02% / 0.05%。`https://www.binance.info/en/support/faq/detail/360033544231`
- OKX，2025-01-28，《OKX to adjust options trading fees》。`https://www.okx.com/help/okx-to-adjust-options-trading-fees`
- OKX，《Trading Fee Rules》。`https://www.okx.com/help/trading-fee-rules-faq`
- OKX，2026-09-09 期货费率调整说明。`https://www.okx.com/en-us/help/advance-notice-spot-and-futures-trading-fee-adjustment`
- Coinbase IR / Business Wire，2025-08-14，Deribit 7 月成交超过 $185B、交易收入超过 $30M。`https://investor.coinbase.com/news/news-details/2025/Deribit-Joins-Coinbase-Unlocking-the-Future-of-Global-Crypto-Derivatives/`
- CME Group 2025 Form 10-K 与 2025 年四季报业绩稿。清算交易费分项、ADV 28.1M、Q4 RPC。`https://www.sec.gov/Archives/edgar/data/1156375/000115637526000009/cme-20251231.htm`；业绩稿 `http://investor.cmegroup.com/static-files/ac5c7e05-582e-4e53-be77-6b173a1bf745`
- CME 教育材料：1 张成交 volume +1。`https://www.cmegroup.com/education/courses/introduction-to-futures/what-is-volume`
- Eurex Clearing Circular 094/25 及附件，2026-01-01 / 2026-04-01 费率。`https://www.eurex.com/resource/blob/4800556/d5e8d771a75421dc4d21c631ff6750f3/data/ec_094_25_Attach1.pdf`
- Eurex Clearing 价目表，文件日期 2026-08-17。`https://www.eurex.com/resource/blob/46180/6631079e089d8832ab3bf9380ecc853d/data/2026_08_17_ecag_price_list_en.pdf`
- FESX / OESX 合约乘数 €10 / 点：Eurex 合约规格（EURO STOXX 50 Index Futures / Options）。本备忘录按该公开规格使用。

第三方，只用于换算或份额

- 价格：Yahoo Finance 日线，ES=F、CL=F、GC=F、ZN=F、BTC-USD、^STOXX50E，时间戳见第 5 节。
- CME 美元 / 张：Interactive Brokers 交易所费转嫁，CME / CBOT / NYMEX / COMEX 页面，抓取于 2026-09-22。IBKR 声明数字可以偏离交易所实收。`https://www.interactivebrokers.com/en/accounts/fees/CME.php` 及 NYMEX、CBOT、COMEX 对应页。
- 四家期权成交权重：第 4 章所引 2026 年上半年代理统计，不是交易所成交月报。
- Deribit 12.5% 上限：帮助中心公式的公开转载。现行知识库页面本次没有抽出原文。

明确不做的计算

- 不用 taker fee 代替 take rate。
- 不用非会员或 Regular 费率代表实现平均。
- 不把 maker 返佣当成收入。
- 不把权利金成交额和名义成交额混在同一列。
- 不用未平仓计算 take rate。
- 不用全公司收入除以单一产品成交。
- 收入和成交不在同一窗口、或覆盖范围对不上时，写 N/A。
