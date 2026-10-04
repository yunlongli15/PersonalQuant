# Data Sources（STEP 2）

## 数据源总览（2026-09-05 实测可达性）

| 源 | 用途 | 接口 | 状态 |
| --- | --- | --- | --- |
| chenditc/investment_data | 日线/日历/instruments 基线 | qlib_data 本地数据（release 2026-09-04） | ✅ 本地 |
| sse-reports-archive | SSE 年报 metadata/URL/coverage/lifecycle | GitHub 仓库 metadata | ✅ 本地 |
| CNINFO static | 年报 PDF 按需下载 | static.cninfo.com.cn | ✅ 可达 |
| 上交所官方 | SSE 证券列表（含上市/退市日期、CSRC 行业） | query.sse.com.cn | ✅ 可达 |
| 深交所官方 | SZ 证券列表（含上市日期、CSRC 行业） | www.szse.cn（akshare 封装） | ✅ 可达 |
| 北交所官方 | BJ 证券列表 | bse.cn（akshare 封装） | ✅ 可达 |
| 腾讯行情 | 全市场估值快照（PE/PB/市值/换手）+ 日线对照 | proxy.finance.qq.com / web.ifzq.gtimg.cn | ✅ 可达 |
| 新浪财经 | 交易日历对照 | finance.sina.com.cn | ✅ 可达 |
| 东财数据中心 | 分红送配（公司行为） | datacenter-web.eastmoney.com | ✅ 可达 |
| **东财 push2/clist** | （原计划）估值快照 | push2.eastmoney.com | ❌ WAF 间歇封禁本机 IP |
| **东财 push2his** | （原计划）日线对照 | push2his.eastmoney.com | ⚠️ 时通时断（已有腾讯回退） |

## 关键决策记录

1. **日线基线用 Qlib 数据包**（chenditc/investment_data 2026-09-04，官方
   README 推荐源，STEP 1 已落地到 qlib_data/）。全市场导入 canonical 层。
2. **东财快照 API（push2）被 WAF 封禁**：估值快照改用**腾讯行情排行 API**
   （单次 ~24 页请求全市场；pe_ttm/pn(PB)/zsz/ltsz/hsl 字段已与已知股票
   公开值核对一致）。`ps`（市销率）该源缺失 → canonical 中为 NULL（诚实留空）。
3. **东财日线接口（push2his）时断时续**：`fetch_daily_history` 已实现
   腾讯 K 线回退（`web.ifzq.gtimg.cn`，空 fqt=不复权），单接口失败不阻塞
   整个 pipeline（用户要求：不要因为一个接口失败而停止 STEP 2）。

   2026-10-04 实测补充：被封时不是返回 403，而是**直接断连**
   （`RemoteDisconnected`，约 0.2s 失败），并且**会持续数分钟以上**——
   8 分钟内每 8 秒探一次全部失败。因此"每个标的都试一次主源"没有意义：
   60 个标的会得到 60 次同样的失败。现在**每轮只试一次**，失败后本轮
   全部走腾讯；`AkShareMarketProvider.eastmoney_blocked` 记录原因，
   `refresh_live_prices.py` 把它写进 `live_prices.json`，并且每次抓到的
   每一行都带 `source` 列——**数据实际来自哪一家必须可查**，不能靠
   "我们本来打算用 EastMoney"来标注。实测同一次运行 60 个标的中
   `failed: []`、`not_newer: 60`，降级期间不丢任何数据。
4. **价格口径（重要）**：chenditc 数据集的 `$close/$open/$high/$low/$vwap`
   是 **Yahoo 调整价**，`$factor` 为调整因子，原始价 = 值 ÷ factor
   （实测：茅台 2023-12-29 close/factor = 1726.00 = 交易所原始收盘价）。
   canonical `daily_bars` 存储**原始价格**并保留 `factor` 列，
   与腾讯/东财不复权数据直接可比（交叉验证平均相对差 ~3e-8）。
5. **volume/amount 单位 caveat**：源数据的 volume 与 amount/vwap 在数量级上
   不满足 股×元 恒等式（amount 实测为真实成交额元；volume 存在源侧缩放）。
   canonical 原样保留并注明；需要股数时用 `amount / vwap`。
6. **上市日期**：来自上交所/深交所官方列表（非快照/qlib 起始日）；
   qlib-only 的退市股票 list_date=NULL（不伪造）。
7. **代理**：本机 Windows 系统代理（127.0.0.1:7890）间歇拒绝连接；
   `personal_quant.config` 默认直连（`PQ_USE_SYSTEM_PROXY=1` 可切回）。
8. **礼貌抓取**：单连接、随机 1-3s 延迟、指数退避、所有原始响应缓存到
   `data/raw/`（支持离线重跑）。无高并发、无绕过 WAF、无代理池。

## 数据源注册

所有导入在 `source_registry` 登记（source_name/data_type/url/version/
file/sha256/parser_version），可追溯每一次 bootstrap 的来源。
