# -*- coding: utf-8 -*-
"""§13 / §65：GUI 里不能有任何通往券商的路径。"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUI_DIRS = [ROOT / "app", ROOT / "services"]

BROKER_HINTS = ("easytrader", "vnpy", "ctp", "xtquant", "ths_trader",
                "broker_api", "place_order", "submit_order", "send_order",
                "下单", "委托买入", "委托卖出", "券商接口")


def _sources():
    for d in GUI_DIRS:
        for f in sorted(d.rglob("*.py")):
            yield f, f.read_text(encoding="utf-8")


def test_no_broker_library_is_imported():
    for f, text in _sources():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.lower() for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.lower()]
            for n in names:
                for hint in BROKER_HINTS:
                    assert hint not in n, f"{f.name} import 了 {n}"


def test_no_order_sending_code():
    for f, text in _sources():
        code = "\n".join(ln for ln in text.splitlines()
                         if not ln.strip().startswith("#"))
        for hint in ("place_order", "submit_order", "send_order",
                     "easytrader"):
            assert hint not in code.lower(), f"{f.name} 含 {hint}"


def test_no_network_calls_from_the_gui():
    """GUI 不做任何出网调用（数据全部来自本地文件/本地库）。"""
    for f, text in _sources():
        for bad in ("requests.get", "requests.post", "urlopen",
                    "http://", "https://"):
            assert bad not in text, f"{f.name} 含 {bad}"


def test_safety_flags_are_off():
    from app._shared import cfg
    assert cfg("safety.allow_broker") is False
    assert cfg("safety.allow_freeze_change") is False


def test_launcher_refuses_non_local_bind():
    import subprocess
    r = subprocess.run([sys.executable, "scripts/run_app.py",
                        "--host", "0.0.0.0"],
                       cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    assert r.returncode == 1
    assert "refusing to bind beyond localhost" in (r.stderr + r.stdout)


def test_services_expose_no_order_api():
    """服务层不得出现"下单/委托"语义的**可调用**接口。

    只看 callable 且按词边界匹配 —— 常量名（ASSET_CLASS_ORDER）里含
    "order" 不代表它是下单接口。
    """
    import inspect
    import re

    from services import portfolio_service, recommendation_service

    pattern = re.compile(r"(^|_)(order|place|submit|send)($|_)")
    allow = {"add_transaction", "transactions", "reorder_nothing"}
    for mod in (portfolio_service, recommendation_service):
        for n, obj in inspect.getmembers(mod):
            if n.startswith("_") or not callable(obj) or n in allow:
                continue
            assert not pattern.search(n.lower()), \
                f"{mod.__name__}.{n} 名字像下单接口"
