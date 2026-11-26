# 低价货源专项核验

北京时间 2026-11-26 23:08 抓取 InferHub 公开 OpenAPI。Surplus 数字来自同日 21:15 的公开订单簿。本地没有挂载 V1–V8。X 全文检索本轮没有取到帖文原文。优惠机制存在，不写成某个匿名报价已经用了它。

## 任务一：InferHub 官方写明的货源

条款更新日期 2026-10-02。[inferhub.dev/terms](https://inferhub.dev/terms) 把服务定义成「转售上游订阅权益的反向代理」。条款正文点名的只有三类：

- OAuth 订阅，例子是 Claude 和 Codex。
- API key 套餐，例子是 Command Code。
- 第三方编码套餐，例子是 z.ai GLM Coding Plan 和 OpenCode Go。

发布者必须声明自己拥有或被授权使用该订阅，并自己承担上游条款。首页另外写了一句：可以接入「带有未用完月度额度的 Anthropic 或 OpenAI API key」，卖自己用不到的余量。[inferhub.dev](https://inferhub.dev/)，同日抓取。

公开 OpenAPI `POST /publisher/providers` 把接入方式写得更细。这是产品接口说明，不是某个人的经营自述。

| 上游 | 官方接入物 | 额度形态 |
|---|---|---|
| Claude Code | OAuth。另有开关：座位打满时自动兑换 Anthropic 的免费限额重置，包括每周的 5 小时重置和促销赠送 | 订阅座位，不是按 token 采购 |
| Codex | OAuth JSON。自动重置会花掉 ChatGPT 的 reset credits | 订阅座位 |
| Anthropic API `ant/` | Console key：`sk-ant-api`、`sk-ant-usr`、服务账号 key。Claude Code 的 `sk-ant-oat` 会被拒绝并指到另一条上游 | 套餐附带的月度 API credits。额度用尽后账号保存但停在 exhausted |
| OpenAI Platform `oai/` | `sk-proj`、`sk-svcacct` 或 `sk-`。Codex token 会被拒绝 | 同上 |
| CodeBuddy / CodeBuddy CN | API key、access token 或 refresh token，自动判断。每账号并发被平台固定为 50 | 编码产品积分。接口会去读额度 |
| Qwencloud / Qwencloud CN | 按 API key 接入。并发同样固定为 50。和下面的 Token Plan 是两条上游 | 文档没有写这是哪一种百炼 key |
| Alibaba Token Plan | 单独上游 `qwencloud-alibaba-tokenplan`。并发可调。接口写明阿里建议 Lite 1–2、Pro 6–8 | 订阅 Credits，不是按量 key |
| Mistral Vibe | 按 API key 接入，并由路由去读额度 | 订阅额度。接口没有写欧元数 |
| Grok CLI | xAI OAuth refresh token。只收付费档：SuperGrok、SuperGrok Heavy、X Premium 等。免费档拒绝 | 付费订阅 |
| Kiro | IDE 登录的 refresh token。长说明写「所有套餐都收」，短字段说明写成「仅付费」。两句不一致，以哪句为准未裁定 | IDE 登录额度 |
| Antigravity | refresh token，再挂到 Cloud Code Assist 项目 | Google 账号 |
| Gemini API | 付费项目的 AI Studio key。免费档拒绝 | 按量 key |
| xAI API、Azure AI Foundry、OrcaRouter | 各自的 API key。Azure 一条里可以是 GPT、Claude 或 DeepSeek 部署。额度用尽则停在 exhausted | 云上按量或预付 credits |
| z.ai、Codex、Claude Code | 有官方额度端点，轮询结果标成 live | 5 小时和每周窗口，首页写明只对这三家做这种轮询 |

定价页同日还列出 DeepSeek、Fireworks、MiniMax、Moonshot、ClinePass、Meta AI、Xiaomi MiMo、MiMo Token Plan。OpenAPI 的批量接入说明没有逐条定义它们的账户类型。FAQ 还提到 Qoder。不能把「定价页有这个按钮」写成「官方已说明它是某种订阅」。

条款第 6 条允许消费者把已经买到的付费模型再转卖给自己的用户。免费池模型禁止再转卖。这是平台允许二跳，不是一份中转站账单。

公开检索没有找到一家有名字的中转站，同时公布了「从 Claude、CodeBuddy、Mistral 或百炼买入的成本」和「在 InferHub 或 Surplus 卖出的收入」。KR1 和 Gondola 的公开收入是 Venice DIEM，不是这几条上游。

## 任务二：Mistral 极低价

官方文档，[Subscriptions](https://docs.mistral.ai/admin/billing-usage/subscriptions)：每个套餐有两笔月度金额，Vibe & Studio 和 API。非 Mistral 产品，包括第三方编码工具，只计入 API 那一笔。DeepSeek V4.1 Flash 1017 是 Mistral 托管的第三方开源模型，按量价 $0.30 / 缓存 $0.007 / $1.20，发布于 2026-10-28。[模型页](https://docs.mistral.ai/models/deepseek-v4-flash-1017)。所以订阅里的 API 额度可以花在这个模型上，但是按这个刊例扣，而且扣的是较小的那一笔，不是 Vibe 那一笔。

额度金额：

| 时点 | 官方或旁证 | 金额 |
|---|---|---|
| 2026-10 | UsagePricing 记录的定价页 | Pro 的 API credits 从 $30 降到 $25.50 |
| 2026-11-02 | 同站对定价页的抓取 | Pro 仍印 “$25.5 /mo in API credits”；学生版印 “$15 /mo” |
| 2026-11-12 | subvalue 对 Education 账户页的阅读，不是定价页 | €127.50 Vibe + €12.75 API，每月 1 日重置 |
| 2026-11-23 | 欧洲免费一个月的活动帖，媒体引述 | 帖子没有写欧元数 |
| 2026-11-24 | 定价页抓取 | Pro 和学生版的 API credits 行都没了。月费仍是 $14.99 / $5.99 |
| Free | 官方文档 | 只有 Vibe / Studio 试用预算，没有 API。开 API 要先开通账单和预付 credits |

这几行不能加成一个数。定价页当前不公布金额。账户页旁证和教育版、Pro 是否相同，官方没有写。

企业价：定价页是 Contact Sales。商业条款 2026-09-25 允许在「经授权的合作伙伴基础设施」上使用，并禁止买卖 API key 和账户，禁止未经书面授权把 Vibe 接到卖给第三方的产品上。[Commercial Terms](https://legal.mistral.ai/terms/commercial-terms-of-service/)。没有公开的企业单价。

没有公开账单显示有人用 Mistral 额度在 InferHub 或 Surplus 上转售，也没有中转站公布「买入 Mistral 额度、卖出临期余额、补货后仍盈利」。InferHub 只是把 `mistral-vibe` 列成可接入、可读额度的上游。

按量刊例下，Surplus 上 Mistral 通道 2026-11-26 21:15 的健康最低档是 DeepSeek $0.0105 / $0.049、GLM 5.3 $0.166 / $0.599。$0.0105 低于缓存价 $0.007 的结论只在输入腿不成立：输入卖价高于缓存价，输出卖价远低于 $1.20。全缓存、输入很少的请求可以打平中间档；地板档和输出很重的请求，按量采购解释不了。

## 任务三：阿里云预购和清仓

官方说明：[节省计划与资源包](https://help.aliyun.com/zh/model-studio/savings-plan-and-resource-package)。价格：[模型价格](https://help.aliyun.com/zh/model-studio/model-pricing)。汇率只用 2026-11-26 中间价 6.7096，标成「刊例人民币 / 6.7096」。

华北 2（北京）刊例：

| 模型 | 输入 / 输出，每百万 token | 免费额度 | Surplus dashscope-cn 健康最低档，21:15 |
|---|---|---|---|
| qwen3.8-max-0902 | ¥12 / ¥36。同名不带日期的 qwen3.8-max 另有 100 万 token、90 天 | 无 | $0.308 / $0.925，约合 ¥2.07 / ¥6.21，相对刊例约 83% |
| deepseek-v4.1-flash-1017 | 忙时 ¥2 / ¥8，闲时 ¥1 / ¥4。忙时 08:00–22:00 北京时间 | 无 | $0.00718 / $0.0335，约合 ¥0.048 / ¥0.225 |
| glm-5.3 | ¥8 / ¥28。另有 100 万 token、90 天 | 有 | $0.00115 / $0.00416，约合 ¥0.0077 / ¥0.028 |

价格表声明表内输入价不含缓存价，并举例「显式缓存创建按输入的 125%，命中按 10%」。这三个模型的表行没有单独印出缓存单价，所以 10% 只是页面举例，不是这三个模型的已核对单价。

| 预购产品 | 适用 | 价格 | 期限和结转 | 普通 DashScope 能不能扣 |
|---|---|---|---|---|
| 大语言模型资源包 | 只列了 qwen-plus / qwen-plus-latest，以及 qwen-max。按模型名严格匹配。没有 qwen3.8-max-0902、DeepSeek、GLM | qwen-plus 1,200 万 token ¥11.66，1.1 亿 ¥114.4。qwen-max 1,800 万到 19.5 亿，¥57.6 到 ¥6,250 | 购买起算，3 个月、6 个月或 1 年；qwen-max 包是 1 年。到期剩余作废。未使用部分可退，已使用不退 | 能。通用 API key 和 Base URL 自动抵扣 |
| 其他模型节省计划 | 文本模型族，含千问 Max、DeepSeek、GLM、Kimi、MiniMax 的阿里直供。不含带供应商前缀的三方直供。不抵扣缓存、Batch、工具调用 | 20 元到 50 万元各档都无折扣，按刊例 1:1 扣 | 20 元 1 个月，100 元 3 个月，1,000 元 6 个月，5,000 元及以上 1 年。过期余额作废，不退款 | 能。没有单独接口 |
| AI 通用型节省计划 | A 类千问有折扣。C 类 DeepSeek、GLM、Kimi、MiniMax 可抵扣但无折扣，按刊例 1:1。只限阿里直供 | A 类全预付最深是月承诺 100 万元以上、24 个月的 5.3 折。例：月承诺 1 万元、12 个月、全预付，千问文本 8 折。零预付要商务开通，折扣更浅 | 动态月发放。当月剩余清零，不结转。已发生抵扣的不支持退订。余额和订单不能跨账号转移，也不能变成现金 | 能 |
| Token Plan | 另一套 key、另一套地址。个人版禁止共用和自动化转售 | 见此前套餐表。Pro ¥312 / 20 万 Credits | 按订阅周年，不结转。用尽是 429，不落入按量 | 不能。普通 `sk-` 扣不到这套 Credits |

抵扣顺序：免费额度，资源包，其他模型节省计划，AI 通用型节省计划，然后按量。

正常采购折扣到不了这些卖价。千问最深的公开折扣是 5.3 折，qwen3.8-max-0902 的输入成本仍是 ¥6.36，Surplus 卖价约 ¥2.07，还低 67%。DeepSeek 和 GLM 在节省计划里是 C 类，折扣是 0。资源包根本不包括这两个模型，也不包括 qwen3.8-max-0902。

临期清仓在规则上可能发生：动态月结束时剩余额度作废，而且不能提现、不能转给别的账号。那时候多卖一 token 的增量成本接近零。这是规则，不是账单。没有一家中转站公开了「持有百炼节省计划或资源包，在 Surplus 卖出剩余，并给出买入价、主业收入、剩余额度和二级市场利润」。代理商软文里的「月消费 80 万可以到 3 折」「额度可累加」和官方表格、官方「不结转、不跨账号」直接冲突，不采用。

## 能算完的利润

能算完的公开经营只有 Venice DIEM：KR1 的 5.45% 公允价值年化，以及 Gondola 卖方实得面值的 65.7%。两者都不是 Mistral 订阅，也不是百炼预购。

对这三个货源，公开材料停在这里：官方折扣的下限高于二级市场地板；临期额度的增量成本可以接近零；没有一份把采购、主业、剩余额度和二级市场卖出连在一起的账单。
