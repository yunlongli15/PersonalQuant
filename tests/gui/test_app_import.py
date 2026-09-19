# -*- coding: utf-8 -*-
"""§51：应用与服务层能被导入；GUI 只调 services，不碰金融引擎。"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

APP = Path(__file__).resolve().parents[2] / "app"


def test_app_entry_exists():
    assert (APP / "app.py").exists()
    assert (APP / "_shared.py").exists()


def test_all_twelve_pages_exist():
    pages = sorted((APP / "pages").glob("*.py"))
    assert len(pages) == 12, [p.name for p in pages]


def test_services_import():
    from services import (backtest_service, factor_service, health_service,
                          market_service, news_service, performance_service,
                          portfolio_service, recommendation_service,
                          risk_service, strategy_service)
    for mod in (backtest_service, factor_service, health_service,
                market_service, news_service, performance_service,
                portfolio_service, recommendation_service, risk_service,
                strategy_service):
        assert mod is not None


def test_pages_do_not_import_quant_engines():
    """§4 / §5：GUI 不得自己算 alpha / 因子 / 回测 / PIT / 成本。

    与 webapp 的 AST 纪律一致：页面只允许调 `services`。
    （`pandas` 允许 —— 只用于把结果摆成表格，不做金融计算；
    `numpy` 不允许，因为一旦出现它基本就意味着在算数。）
    """
    banned = ("numpy", "wealth", "pipeline", "trade_plan", "portfolio",
              "factors", "news", "personal_quant", "incremental",
              "paper_live")
    offenders = []
    for f in sorted((APP / "pages").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for n in names:
                if n in banned:
                    offenders.append(f"{f.name}: {n}")
    assert not offenders, f"页面直接 import 了量化引擎：{offenders}"


def test_pages_only_import_shared_and_services():
    """白名单：只允许 streamlit / pandas / _shared / services。"""
    allowed = {"streamlit", "pandas", "sys", "pathlib", "_shared", "services",
               "__future__", "app"}
    offenders = []
    for f in sorted((APP / "pages").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for n in names:
                if n and n not in allowed:
                    offenders.append(f"{f.name}: {n}")
    assert not offenders, f"页面 import 了白名单之外的模块：{offenders}"


def test_shared_module_is_the_only_path_bootstrap():
    text = (APP / "_shared.py").read_text(encoding="utf-8")
    assert "sys.path.insert" in text


def test_no_page_writes_to_the_wealth_ledger_directly():
    """页面可以触发服务层，但不能自己写库（审计要走 repository）。"""
    for f in sorted((APP / "pages").glob("*.py")):
        text = f.read_text(encoding="utf-8")
        assert "INSERT INTO" not in text, f.name
        assert "DELETE FROM" not in text, f.name
