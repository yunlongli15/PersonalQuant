# -*- coding: utf-8 -*-
"""63 份说明文档：旧路径 -> 新中文路径。

约定：
- 分步文档统一用 `步骤N-主题.md`，方便排序和一眼看懂属于哪一步
- 不保留英文原名，但不用空格；分隔用半角 `-`
- README.md / CLAUDE.md 两个例外见文件末尾注释
"""

MAPPING = {
    # ---------- 根目录 ----------
    # README.md      -> 不改名（GitHub 首页靠它，改了仓库首页就空了）
    # CLAUDE.md      -> 不改名（Claude Code 按这个名字自动加载项目规范）
    "ROADMAP.md": "路线图.md",
    "DATA.md": "数据与模型清单.md",

    # ---------- docs/ ----------
    "docs/USER_GUIDE.md": "docs/使用说明.md",
    "docs/V1_FREEZE.md": "docs/V1.0冻结规则.md",
    "docs/V1_RELEASE.md": "docs/V1.0发布说明.md",
    "docs/WEEKLY_WORKFLOW.md": "docs/周度操作流程.md",
    "docs/data_quality.md": "docs/数据质量体系.md",
    "docs/data_schema.md": "docs/数据表结构.md",
    "docs/data_sources.md": "docs/数据来源与口径.md",
    "docs/environment_check.md": "docs/环境检查.md",
    "docs/financial_extraction.md": "docs/年报提取管线.md",
    "docs/forward_holdout.md": "docs/前瞻留出样本.md",
    "docs/forward_monitoring.md": "docs/前瞻监控.md",
    "docs/investment_terminal.md": "docs/投资终端.md",
    "docs/paper_live.md": "docs/模拟盘实验.md",
    "docs/paper_live_execution.md": "docs/模拟盘执行模型.md",
    "docs/point_in_time.md": "docs/时点正确性规则.md",
    "docs/sse_reports_integration.md": "docs/交易所公告库接入.md",
    "docs/strategy_freeze.md": "docs/策略冻结.md",
    "docs/step3_execution_model.md": "docs/步骤3-执行模型.md",
    "docs/step3_qlib_integration.md": "docs/步骤3-Qlib集成.md",
    "docs/step4_financial_factor_pit.md": "docs/步骤4-财务因子时点规则.md",
    "docs/step4_market_data_quality.md": "docs/步骤4-市场数据质量.md",
    "docs/step5_news_pit.md": "docs/步骤5-新闻时点规则.md",
    "docs/step6_portfolio_design.md": "docs/步骤6-组合优化设计.md",
    "docs/step11_existing_asset_system_audit.md": "docs/步骤11-既有资产系统审计.md",

    # ---------- reports/ ----------
    "reports/step1_qlib_baseline.md": "reports/步骤1-Qlib基线.md",
    "reports/step2_data_catalog.md": "reports/步骤2-数据目录.md",
    "reports/step2_data_crosscheck.md": "reports/步骤2-交叉验证.md",
    "reports/step2_financial_extraction_demo.md": "reports/步骤2-年报提取演示.md",
    "reports/step3_strategy_v1.md": "reports/步骤3-策略v1.md",
    "reports/step3_model_evaluation.md": "reports/步骤3-模型评估.md",
    "reports/step3_sanity_check.md": "reports/步骤3-人工核对.md",
    "reports/step3_point_in_time_audit.md": "reports/步骤3-时点正确性审计.md",
    "reports/step4_factor_research.md": "reports/步骤4-因子研究.md",
    "reports/step4_model_ablation.md": "reports/步骤4-模型消融.md",
    "reports/step4_financial_factor_coverage.md": "reports/步骤4-财务因子覆盖率.md",
    "reports/step5_news_coverage.md": "reports/步骤5-新闻覆盖率.md",
    "reports/step5_news_sources.md": "reports/步骤5-新闻来源审计.md",
    "reports/step5_news_factor_evaluation.md": "reports/步骤5-新闻因子评估.md",
    "reports/step5_news_ablation.md": "reports/步骤5-新闻消融.md",
    "reports/step5_news_pit_audit.md": "reports/步骤5-新闻时点审计.md",
    "reports/step5_news_manual_audit.md": "reports/步骤5-新闻人工抽查.md",
    "reports/step5_news_cost.md": "reports/步骤5-新闻成本.md",
    "reports/step5_news_strategy.md": "reports/步骤5-新闻策略.md",
    "reports/step5_incremental_alpha_check.md": "reports/步骤5-新闻增量alpha检查.md",
    "reports/step6_portfolio_optimization.md": "reports/步骤6-组合优化.md",
    "reports/step6_final_candidate.md": "reports/步骤6-最终候选.md",
    "reports/step8_micro_factors.md": "reports/步骤8-微结构因子.md",
    "reports/step9_independent_info.md": "reports/步骤9-独立信息研究.md",
    "reports/incremental_factor_selection_v2.md": "reports/增量IC因子筛选协议v2.md",
    "reports/step10_forward_holdout.md": "reports/步骤10-前瞻留出样本.md",
    "reports/step11_investment_terminal.md": "reports/步骤11-投资终端.md",
    "reports/paper_live_engine_validation.md": "reports/模拟盘-引擎验证.md",
    "reports/daily_exit_paper_v1_audit.md": "reports/前瞻实验-执行链审计.md",
    "reports/daily_exit_paper_v1_design.md": "reports/前瞻实验-架构设计.md",
    "reports/daily_exit_paper_v1_phase4_infrastructure_fix.md":
        "reports/前瞻实验-阶段4-基础设施修复.md",
    "reports/daily_exit_paper_v1_phase5_implementation.md":
        "reports/前瞻实验-阶段5-实现.md",
    "reports/daily_exit_paper_v1_phase6_prelaunch_validation.md":
        "reports/前瞻实验-阶段6-启动前验证.md",
    "reports/daily_exit_paper_v1_phase7_launch.md": "reports/前瞻实验-阶段7-启动.md",
    "reports/incident_20261004_news_events_index.md":
        "reports/事故-20261004-新闻事件索引.md",
}

#: 新路径 -> 中文 H1 标题（第一行 `# ...`）。
#: 注意：reports/ 里约 18 份是**脚本生成的**，它们的 H1 由生成器写出，
#: 改这里不够——必须同步改生成器里的标题字符串，否则下次运行会被覆盖回英文。
TITLES = {
    "README.md": "PersonalQuant — 个人 A 股量化投资系统",
    "路线图.md": "路线图 — 分阶段开发计划与进度",
    "数据与模型清单.md": "数据与模型清单",
    "CLAUDE.md": "CLAUDE.md — 本项目 AI 协作开发规范",

    "docs/使用说明.md": "PersonalQuant 使用说明",
    "docs/V1.0冻结规则.md": "V1.0 冻结规则",
    "docs/V1.0发布说明.md": "PersonalQuant 发布说明",
    "docs/周度操作流程.md": "周度调仓操作流程",
    "docs/数据质量体系.md": "数据质量体系（步骤 2）",
    "docs/数据表结构.md": "数据表结构与字段（步骤 2）",
    "docs/数据来源与口径.md": "数据来源与口径（步骤 2）",
    "docs/环境检查.md": "步骤 1 环境检查报告",
    "docs/年报提取管线.md": "年报提取管线（按需提取，绝不批量下载）",
    "docs/前瞻留出样本.md": "前瞻留出样本 — 干净的样本外",
    "docs/前瞻监控.md": "前瞻监控 — 只观察，不反馈",
    "docs/投资终端.md": "个人投资终端（Streamlit）",
    "docs/模拟盘实验.md": "模拟盘实验 — 每天真实地向前走",
    "docs/模拟盘执行模型.md": "模拟盘执行模型 — T+1 开盘，真实约束",
    "docs/时点正确性规则.md": "时点正确性（PIT）规则",
    "docs/交易所公告库接入.md": "交易所公告库接入",
    "docs/策略冻结.md": "策略冻结 — 能证明它没变",
    "docs/步骤3-执行模型.md": "步骤 3 执行模型",
    "docs/步骤3-Qlib集成.md": "步骤 3 Qlib 集成方案（决策记录）",
    "docs/步骤4-财务因子时点规则.md": "步骤 4 财务因子时点（PIT）规则",
    "docs/步骤4-市场数据质量.md": "步骤 4 市场数据质量审计与修复",
    "docs/步骤5-新闻时点规则.md": "步骤 5 新闻/公告时点（PIT）规则",
    "docs/步骤6-组合优化设计.md": "步骤 6 组合优化设计",
    "docs/步骤11-既有资产系统审计.md": "步骤 11 既有个人资产系统审计",

    "reports/步骤1-Qlib基线.md": "步骤 1 基线实验：Qlib LightGBM + Alpha158",
    "reports/步骤2-数据目录.md": "步骤 2 数据目录",
    "reports/步骤2-交叉验证.md": "步骤 2 交叉验证报告（Qlib vs Canonical）",
    "reports/步骤2-年报提取演示.md": "步骤 2 年报提取演示报告",
    "reports/步骤3-策略v1.md": "步骤 3 策略报告：strategy_v1",
    "reports/步骤3-模型评估.md": "步骤 3 模型评估报告（strategy_v1）",
    "reports/步骤3-人工核对.md": "步骤 3 人工核对（sanity check）",
    "reports/步骤3-时点正确性审计.md": "步骤 3 时点正确性审计（泄漏检查）",
    "reports/步骤4-因子研究.md": "步骤 4 因子研究报告（factor_pack_v1）",
    "reports/步骤4-模型消融.md": "步骤 4 模型消融（A/B/C/D）",
    "reports/步骤4-财务因子覆盖率.md": "步骤 4 财务因子覆盖率",
    "reports/步骤5-新闻覆盖率.md": "步骤 5 新闻覆盖率",
    "reports/步骤5-新闻来源审计.md": "步骤 5 新闻来源审计",
    "reports/步骤5-新闻因子评估.md": "步骤 5 新闻因子评估",
    "reports/步骤5-新闻消融.md": "步骤 5 新闻消融",
    "reports/步骤5-新闻时点审计.md": "步骤 5 新闻时点审计",
    "reports/步骤5-新闻人工抽查.md": "步骤 5 新闻人工抽查样本",
    "reports/步骤5-新闻成本.md": "步骤 5 新闻成本报告",
    "reports/步骤5-新闻策略.md": "步骤 5 新闻策略（strategy_v1_news）",
    "reports/步骤5-新闻增量alpha检查.md": "步骤 5 新闻增量 alpha 预检查",
    "reports/步骤6-组合优化.md": "步骤 6 组合优化",
    "reports/步骤6-最终候选.md": "步骤 6 最终候选（strategy_v2）",
    "reports/步骤8-微结构因子.md": "步骤 8 微结构因子挖掘与回测",
    "reports/步骤9-独立信息研究.md": "步骤 9 独立信息研究",
    "reports/增量IC因子筛选协议v2.md": "增量 IC 因子筛选协议 v2",
    "reports/步骤10-前瞻留出样本.md": "步骤 10 前瞻留出样本与模拟盘监控",
    "reports/步骤11-投资终端.md": "步骤 11 个人投资终端（Streamlit）",
    "reports/模拟盘-引擎验证.md": "模拟盘引擎历史验证",
    "reports/前瞻实验-执行链审计.md": "前瞻实验 daily_exit_paper_v1 执行链审计",
    "reports/前瞻实验-架构设计.md": "前瞻实验 daily_exit_paper_v1 架构设计",
    "reports/前瞻实验-阶段4-基础设施修复.md": "前瞻实验 阶段 4 基础设施修复",
    "reports/前瞻实验-阶段5-实现.md": "前瞻实验 阶段 5 实现",
    "reports/前瞻实验-阶段6-启动前验证.md": "前瞻实验 阶段 6 启动前验证",
    "reports/前瞻实验-阶段7-启动.md": "前瞻实验 阶段 7 启动",
    "reports/事故-20261004-新闻事件索引.md": "事故 2026-10-04 新闻事件索引失配",
}


if __name__ == "__main__":
    import pathlib
    missing = [k for k in MAPPING if not pathlib.Path(k).exists()]
    print(f"映射 {len(MAPPING)} 条")
    print("不存在:", missing or "（无）")
    dup = [v for v in MAPPING.values() if list(MAPPING.values()).count(v) > 1]
    print("目标重名:", dup or "（无）")
