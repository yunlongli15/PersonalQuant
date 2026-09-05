# Financial Document Extraction（按需年报提取管线）

## 设计

```
Report metadata (report_documents)
   ↓ 业务代码请求某指标
get_financial_metric(symbol, metric, as_of_date)
   ↓ 缺该指标 → 找最新可用年报（PIT）
ReportDocumentProvider.get_report()   [ONLINE，单份]
   ↓ HTTP 获取（重试/退避/礼貌延迟）+ %PDF magic + 最小尺寸 + SHA256
FinancialDocumentExtractor (PyMuPDF + pdfplumber)
   ↓ 文本/表格 → 定位章节 → 匹配行标签 → 解析数值与单位
Normalized records + sanity checks
   ↓
DuckDB financial_metrics（LEVEL 2 永久缓存）+ extraction_audit
   ↓
删除临时 PDF（除非 cache=True / PQ_PDF_CACHE=1）
```

**PDF 是临时原始输入，不是必须永久保存的核心数据库。**

## 提取器策略（SSE 年报有强制披露格式）

1. 章节定位（`_locate_sections`）：
   - A = 主要会计数据（前 15 页）
   - B = 合并资产负债表（第 10 页后，200 页内）
   - C = 合并利润表
   每章节取**全部候选锚点页**，逐窗口实际找行，**先命中者胜**
   （审计报告/目录/引用页会自动被跳过）。
2. 表格路径（pdfplumber ruled tables）：
   - 列映射支持两种表头：显式年份（`2023年`/`2022年`）与相对表头
     （`期末余额`/`期初余额`、`本期发生额`/`上期发生额`）；
     `增减(%)` 列永不当作数据列。
   - 行标签匹配：精确/前缀 + 非 CJK 边界（`负债合计` 不匹配
     `流动负债合计`；`营业收入` 不匹配 `营业收入增长率`）。
3. 行级兜底（PyMuPDF 文本行）：标签行 + 向后最多 6 行取数值
   （兼容"标签 / 空行 / 数值逐行"的文本布局）。
4. 单位识别：`单位：万元`、`（人民币百万元）`、
   `（除另有标明外，所有金额均以人民币百万元列示）`、`金额单位为人民币…`
   等 5 类写法；未识别到单位时按元处理并在审计注明。
5. 上年列：仅当列映射确认存在上年列才取（表格）或标签后第二个数值（行级）；
   取不到 → 增长指标 EXTRACTION_FAILED，**绝不猜**。

## 指标集（Phase 1）

- 提取：revenue, cost_of_revenue, net_profit, total_assets,
  total_liabilities, net_assets, operating_cash_flow, roe（报告值）
- 派生（记录 derivation，含 sanity check）：gross_margin, net_margin,
  roa, debt_to_asset, revenue_growth, net_profit_growth
- 银行/保险无营业成本 → cost_of_revenue/gross_margin 诚实返回
  EXTRACTION_FAILED（not applicable），不猜。

## 合理性校验（sanity checks）

- roe（报告值） vs net_profit / net_assets（期末口径，一阶近似）差 >2pp →
  VALIDATION_WARNING
- net_margin 与 revenue/net_profit 交叉核对；debt_to_asset、gross_margin、
  roa 落在合理区间，否则 VALIDATION_WARNING
- 失败/警告都写入 audit 的 validation_status / validation_note

## 已验证结果（6 份真实年报）

| 报告 | 指标 | 结果 |
| --- | --- | --- |
| 茅台 FY2023 | 14/14 | 营收 1476.94 亿、净利 747.34 亿、ROE 34.19%、负债 490.43 亿、增长 19.01%/19.16% 全部与披露一致 |
| 茅台 FY2022 | 14/14 | 营收 1241.00 亿、净利 627.16 亿、ROE 30.26% ✓ |
| 中国平安 FY2023 | 12/14 | 营收 9137.89 亿、净利 856.65 亿、ROE 9.70%、总负债 10.35 万亿 ✓（保险无营业成本） |
| 招商银行 FY2023 | 12/14 | 营收 3391.23 亿、净利 1466.02 亿、ROE 16.16%、负债率 0.90 ✓ |
| 浦发银行 FY2023 | 12/14 | 营收 1734.34 亿、总资产 9.007 万亿、总负债 8.274 万亿 ✓ |
| 中芯国际 FY2024 | 14/14 | 营收 577.96 亿、净利 36.99 亿、毛利率 18.6%、增长 28.4%/-23.3% ✓ |

覆盖：大型消费/制造、保险、银行、半导体；年度 2022/2023/2024。

## 运行

```bash
python scripts/demo_financial_extraction.py [SYMBOL] [FISCAL_YEAR]
```

Demo 自动选择有可靠 metadata 的股票/年份（默认 4 组），打印 SUCCESS 及
指标、来源 URL、sha256、页码、提取方法。
