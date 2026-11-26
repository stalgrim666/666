# 卖家层：谁在以大幅折价出售推理额度

订阅额度与 API 刊例的价差见 `subscription_spread.md`（2026-11-26 晚间续篇）。那一篇从官方套餐算成本，不把订阅机制安到某一条匿名 offer 上。Mistral 单独的供给、促销时间和缓存对账见 `mistral_supply.md`。

快照时间：北京时间 2026-11-26 19:45（Surplus 成交窗）与 19:46（InferHub `/api/market`）。汇率只在把百炼人民币刊例换成美元时使用，取当日 CFETS 中间价 6.7096 元/美元，不是阿里云账单上的美元。

本地目录 `/Users/jiangxinrui/Documents/ChatGPT/Agent Economy/` 没有挂到这台机器上。本账号既往云端研究记录里也没有名为 V1–V8 的卖家报告。本轮没有重做平台级经营统计，结果只写在 `seller_research/`。

## 结论

公开接口能把「模型、上游通道、报价档、最近 20 笔成交」对齐，不能把这些报价归到一个自然人、公司或钱包。带直接经营披露、又能称为卖家的，只有 KR1 plc 这一家。Hermes 插件和 Aeon 技能说明了两种降价机制，作者没有公布自己的账单。InferHub 上的 Claude Code Opus 5.5 是一类匿名发布者，不是一个点名的人。

因此下面四张表把「卖家」「上游 Provider」「模型」分开。通道上的折价不能写成某个卖家的利润。

## 数据边界

| 接口 | 公开内容 | 没有的内容 |
|---|---|---|
| `GET https://api.surplusintelligence.ai/api/markets` | 502 个模型的通道汇总：`provider`、`trusted`、最优价、`distinct_seller_count` | 卖家姓名、钱包、offer id |
| `GET https://api.surplusintelligence.ai/api/markets/{model}` | 该模型全部 offer：`id`、`seller_base_url`、`cost_multiplier`、`trades_24h`、`volume_24h`，以及最多 20 条 `recent_fills` | `seller_id`、钱包、买家、缓存 token 拆分。`/api/sellers`、`/api/orderbook`、`/api/offers` 返回 404 |
| `GET /v1/seller/earnings` | 文档写明需 `si_seller_` 密钥；`direct_cost_usd` 与盘口成交同名字段，单位是 micro-USD | 本轮未持有任何卖家密钥，没有卖家账单 |
| `GET https://inferhub.dev/api/market` | `slug`、`family`、`minAskIn/Out`、`maxAskIn/Out`、`lastRate` | 发布者 id、姓名、订阅收据 |
| `GET https://inferhub.dev/api/pricing/config` | `maxAskPctOfOfficial=0.5`，`platformFeePct=0.2`，`publisherSharePct=80` | 单个发布者的收入 |
| X 全文检索 | 本轮调用返回 402，额度用尽 | 没有用浏览器登录或私人账号补抓 |

`seller_base_url` 是上游地址。`deepseek-v4.1-flash-1017` 上 477 条 Mistral 报价共用 `https://api.mistral.ai/v1`，37 条 DashScope 报价共用 `https://dashscope.aliyuncs.com/compatible-mode/v1`。同一地址不能用来把两条 offer 收成同一个卖家。名册上的 `distinct_seller_count` 是通道计数：该模型 Mistral 通道 10 个，DashScope 中国通道 4 个。计数没有对应的公开 id。

成交里的 `cost_usd` 与 `direct_cost_usd` 都是整数字符串。文档只把 `direct_cost_usd` 写成 micro-USD。同一条记录里两者之比就是 Surplus 自己的折扣，3 笔 Mistral 为 14.07–14.38，14 笔 DashScope 为 20.29–21.35，与对应档位的 `1 / cost_multiplier` 一致。这两个字符串并不等于「token 数 × 未缓存牌价」。例如 98,956 输入加 171 输出，按 OpenRouter $0.15 / $0.70 是 0.015 美元量级，而该笔 `direct_cost_usd` 只有 690。因此上游倍数一律用两边的牌价和同一笔 token 结构来算，不用这个字符串去除牌价。`direct_cost_usd` 是折扣的分母，不是 Mistral 或百炼的发票。

## 表一：公开身份与经营证据

完整行在 `table1_named_evidence.csv`。

| 对象 | 层级 | 能确认的事 |
|---|---|---|
| KR1 plc | 卖家，上市公司 | 持有 557 枚 DIEM，在 Surplus 上自选模型、自定价格，Venice 用它的额度履约，它收 USDC；同时向 Diem Relay 供币 |
| Diem Relay | 额度池，不是一条 Surplus offer | 抽成 20%，供给方分 80%。除 KR1 自述供币外，没有供给方名单 |
| ProlowN 的 Hermes 插件 | 卖家工具 | 把当日未用完的 DIEM 在 00:00 UTC 前卖掉；最后一小时提到参考价七五折。仓库没有收入数字 |
| Aeon `compute-resell` | 卖家工具 | 把 Bankr、Bedrock、Vertex 的低价或免费额度挂到 Surplus，按可成交盘口的 0.99 倍报价。作者写明自己没有运行记录 |
| InferHub 发布者 | 匿名群体 | 条款写明服务由个人运营，发布者接入自己的订阅（含 Claude、Codex 的 OAuth）。没有发布者姓名 |
| Surplus 上的 Mistral / DashScope 通道 | 上游，不是卖家 | 成交路由写成 “Mistral AI direct” 或 “Alibaba DashScope — China”，指的是密钥所打的 API |

KR1，伦敦证券交易所 RNS 7704D，2026-11-19 07:00（伦敦时间）：

> On Surplus Intelligence, KR1 chooses which AI models to offer and sets its prices. When the marketplace matches a customer request to one of those offers, Venice runs the model using KR1’s credits and KR1 earns USDC.

同文：截至 2026-11-16 的 90 天内，约 192 万次第三方请求、1015 亿 token；10 月这笔 DIEM 的公允价值年化收益率估计为 5.45%。原文没有模型名单、成交单价、美元收入和利润。

[RNS 原文](https://www.londonstockexchange.com/en/news/article/KR1/launch-of-diem-infrastructure-operations/3f1d-67-6e-3c-83-4705a5)

Diem Relay 文档：

> USDC from each sale is distributed to suppliers, with a 20% platform fee retained by Diem Relay.

[文档](https://www.diem-relay.com/docs)

Hermes 插件，仓库 2026-10-26 创建：

> Unused credit does not roll over, so DIEM left at the reset earns nothing.

最后一小时仍未售出的额度，价格放到参考价的 75% 折让。

[仓库](https://github.com/ProlowN/surplus-intelligence-seller)

Aeon，2026-10-13：

> The economics are unusual because the inventory is free. Promo credits cost nothing, so there is no cost to defend and no way to sell at a loss.

[原文](https://www.aeon.fun/blog/compute-resell)

InferHub 条款，更新于 2026-10-02：

> The Service is a reverse proxy and marketplace that resells access to upstream LLM subscription entitlements, including subscriptions accessed via OAuth (such as Claude and Codex).

条款同时写明运营者是个人，发布者必须保证自己有权把订阅交给第三方流量，并自行承担上游条款下的责任。

[条款](https://inferhub.dev/terms)

`claude-opus-5.5` 的订单簿上有 3 条 Google 报价，base URL 含 GCP 项目 `itpc-gcp-product-all-claude`。公开代码里能检索到的是别的项目名（`itpc-gcp-hybrid-pe-eng-claude`、`itpc-gcp-ospo-eng-claude`），不是这一条。本轮不把该 URL 认成某个公司的卖家账户。

## 表二：成本、售价、收入、利润

完整行在 `table2_cost_reconciliation.csv`。金额是公开价或公开成交，不是卖家发票。

| 案例 | 额度从哪来 | 公开成本 | 卖价 | 收入与利润 |
|---|---|---|---|---|
| KR1 | 557 枚 DIEM，每枚质押后每天 $1 面值的 Venice 额度 | 代币买价未披露。满额面值是每天 $557 的额度，过期作废 | RNS 只说自行定价 | 90 天 192 万次请求、1015 亿 token。利润只给了 10 月公允价值年化 5.45%，没有美元利润 |
| Mistral 通道上的 DeepSeek V4.1 Flash 1017 | Mistral 公开价 $0.30 / 缓存 $0.007 / $1.20 每百万 token | 最近 3 笔的 Surplus 参考价 / 实收是 14.07–14.38 倍，对上 0.070 档。按该档牌价，未缓存刊例是这 3 笔 token 结构的 28.48–28.54 倍 | 输入 $0.0105、输出 $0.049 | 没有卖家收入。若输入全部按 $0.007 缓存价，同一 token 结构只剩 0.86–1.19 倍。成交不写缓存拆分 |
| DashScope 中国通道，同一模型 | 百炼华北 2 刊例：忙时输入 2 元、输出 8 元；闲时 1 元、4 元；缓存命中 0.04 元、0.02 元。忙时为北京时间 08:00–22:00 | 14 笔的 Surplus 参考价 / 实收是 20.29–21.35 倍，对上 0.0478 档。闲时未缓存牌价是该档的 18.7–20.8 倍；闲时且输入全部按缓存价则是 0.47–12.53 倍，14 笔里有 6 笔低于卖价 | 健康最低档 $0.007177 / $0.033495，24 小时 3,080,027 笔，量字段 2.742 亿 micro-USD | 这是一条 offer，名册说该通道有 4 个卖家，分不开这 308 万笔属于谁 |
| InferHub Claude Code Opus 5.5 | 发布者自己的 Claude Code 或其他 OAuth 订阅，不是按 token 的批发合同 | 订阅月费不公开。平台抽 20%，发布者留 80% | 地板价 $0.108 / $0.54，相对页面所印官方价 $4 / $20 为 97.3%。要价上限 $2 / $10 | 没有单个发布者的收入。页面 24 小时用量是路由合计：输入 42 亿（其中缓存 33 亿）、输出 3750 万 |

Mistral 刊例：[Pricing](https://docs.mistral.ai/inference/pricing)，模型页写明 `deepseek-v4-1-flash-1017` 由 Mistral 托管、不做改动，发布日期 2026-10-28。

百炼刊例：[deepseek-v4.1-flash](https://help.aliyun.com/zh/model-studio/deepseek-v4-1-flash)。2026-11-10 的公告标题是缓存命中价调整，公告列表没有给出新旧数字；本轮用的是同日仍挂在模型页上的 0.02 / 0.04 元。页面写明不含限时优惠。

DeepSeek 自己的 API 用同一套人民币单价，但高峰时段是工作日 9:00–12:00 与 14:00–18:00。Surplus 这 14 笔的路由是 DashScope 中国，对账用的是百炼时段，不是 DeepSeek 官网时段。

## 表三：同一模型在不同场所的价格

这是通道对通道，不是同一卖家的跨平台账户。完整行在 `table3_cross_platform.csv`。

| 模型 | 场所 | 输入 / 输出，美元每百万 token |
|---|---|---|
| Opus 5.5 | InferHub 页面所印官方价 | 4 / 20 |
| Opus 5.5 | InferHub，`cc/claude-opus-5-5` 地板，1 个可用位 | 0.108 / 0.54 |
| Opus 5.5 | InferHub 同一 slug 的要价上限 | 2 / 10 |
| Opus 5.5 | Surplus 的 InferHub 通道，健康最低档 | 0.2524 / 1.262 |
| Opus 5.5 | Surplus 的 Venice 通道 | 1.965 / 9.827 |
| Opus 5.5 | Surplus 的 Anthropic 通道 | 1.00 / 5.00 |
| DeepSeek V4.1 Flash 1017 | Mistral 刊例 | 0.30 / 1.20，缓存输入 0.007 |
| 同一模型 | Surplus 用来打折的 OpenRouter 参考价 | 0.15 / 0.70 |
| 同一模型 | Surplus Mistral 通道健康最低档 | 0.0105 / 0.049 |
| 同一模型 | InferHub 自动路由页面地板 | 0.0174 / 0.0696 |
| 同一模型 | InferHub 家族 `mv`（Mistral Vibe） | 0.0051 / 0.0204 |
| 同一模型 | Surplus 的 InferHub 通道 | 0.007177 / 0.033494 |
| 同一模型 | Surplus 的 DashScope 中国健康最低档 | 0.007177 / 0.033495 |
| 同一模型 | 百炼闲时未缓存，按 6.7096 折美元 | 0.149 / 0.596 |
| 同一模型 | 百炼闲时缓存命中，只计输入 | 0.0030 |

Opus 5.5 上，InferHub 自己的地板低于 Surplus 上挂着 InferHub 地址的报价：0.108 对 0.252。两边都没有卖家 id，不能写成同一个发布者在两个市场的价差。

DeepSeek 上要分开三条 InferHub 数字。自动路由页面地板是 0.0174，高于 Surplus 的 InferHub 通道 0.0072。Mistral Vibe 家族地板是 0.0051，低于 Surplus 的 Mistral 通道和 Surplus 的 InferHub 通道。三句话不能合成「InferHub 一定更便宜」。

Mistral 通道在这个模型上同时挂着多档，且都打向同一个 Mistral 地址。仍有成交或仍健康的档位见 `mistral_offer_tiers.csv`。成交最多的是 0.1344 档：24 小时 486,904 笔，输入卖价 $0.02016，相对 Mistral 输入刊例 14.88 倍。0.070 档有 32 条健康报价、105,057 笔。0.0400 档此刻不健康，24 小时仍有 3,153 笔，输出腿相对 Mistral 刊例 $1.20 是 42.86 倍。

`mistral-large-4-0` 是另一个模型。其 Mistral 通道健康报价的折扣深到 97%，参考价是该模型自己的直接价，不是 DeepSeek 的 $0.15。不要和 DeepSeek V4.1 Flash 1017 的 10 个卖家混成一家。

## 表四：已证实、未证实、待解

完整行在 `table4_mechanisms.csv`。

已证实，而且对应到实际供给，不是一份优惠清单：

1. DIEM 是按日作废的额度。KR1 用它在 Surplus 上履约并收取 USDC，Diem Relay 把同一类额度池化后抽 20%。卖家愿意折价，是因为留到 00:00 UTC 的额度收入为零。KR1 公布的 5.45% 是公允价值收益率，不是「相对官方 API 的毛利」。
2. InferHub 的供给是订阅资格。Opus 5.5 的 `cc/` 家族地板是官方参考价的 2.7%。要价被限制在官方价的 50% 以内，地板没有下限。订阅已经付过，多卖一个 token 的增量成本接近零，拍卖就把要价往下推。这解释得了 97.3% 的标价，解释不了某一个发布者的净利润。
3. Aeon 把免费或低价云额度挂上 Surplus，并故意只比可成交对手低 1%。这是一套会下单的程序。它没有公布任何一笔 USDC。

未证实，本轮不把它写成事实：

- 「Mistral 提供的 DeepSeek V4.1 Flash 1017，部分成交的上游公开成本是 Surplus 成交金额的 42.6 倍。」公开的 20 笔里，3 笔 Mistral 成交对 Surplus 参考价是 14.07–14.38 倍。把 Mistral 未缓存刊例套到这 3 笔的 token 结构和 0.070 档卖价上，是 28.48–28.54 倍，不是 42.6 倍。最接近的公开报价是仍有 3,153 笔成交、当前不健康的 0.0400 档：输出腿 42.86 倍，输入腿 50 倍。20 笔窗口恢复不出 42.6 这一条样本。
- 「即使计入缓存和闲时，百炼成本仍远高于成交。」未缓存时成立：这 14 笔的 token 结构对闲时刊例是卖价的 18.7–20.8 倍，对忙时刊例是 37.4–41.5 倍。把全部输入改按闲时缓存价 0.02 元之后，倍数变成 0.47–12.53，其中 6 笔低于卖价。单独一个缓存命中的输入 token 约 $0.0030，是卖价 $0.007177 的 0.42 倍。成交没有缓存拆分，所以「远高于」只在未缓存或输出占比高的结构上成立。
- 同一个卖家同时在 Surplus、InferHub、OpenRouter、Antseed、Orbio 经营。订单簿没有跨模型的卖家键。
- Opus 5.5 低价路由的保真度、推理、上下文和稳定性已被公开测试。本轮检索没有找到对照官方端点的评测。InferHub 页面上的 1M 上下文、128K 输出、80% 缓存和 24 小时 token 数是用量，不是质量测试。

待解，而且公开接口本身回答不了：

- 名册里那 10 个 Mistral 卖家、4 个 DashScope 卖家、Opus 上 11 个 InferHub 通道卖家分别是谁。
- KR1 的 557 枚 DIEM 落在哪几条 offer 上，卖的是哪些模型。
- InferHub `lastRate`（Opus 5.5 为 0.44298850574712645）的定义。配置接口没有这个字段的说明，本轮不用它当价格。
- 百炼 2026-11-10 缓存调价的旧价，以及卖家账户里是否还有控制台优惠。模型页写明刊例外的优惠要到控制台看。
- 卖家真实利润。需要卖家密钥下的 `GET /v1/seller/earnings`，或发布者自己公开的账单。这两样都没有出现在公开互联网上。

## 本轮没有凑出来的卖家

指令要求有直接证据再计入，不为数量编造。除 KR1 外，没有第二家同时满足「公开经营身份」和「公开收入或收益率」。ProlowN 与 Aeon 是工具作者，不是已披露账单的卖方。InferHub 条款里的个人运营者没有署名。Antseed 上此前核到的 GesundAI、Apex Ant、Venice.ai Proxy 属于另一套结算系统，本轮的 Surplus offer 没有钱包字段，不能把它们接过来。

20 笔成交的逐笔界限在 `fills_deepseek_v4_1_flash_1017.csv`。
