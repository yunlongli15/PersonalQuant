# -*- coding: utf-8 -*-
"""§51：每个页面都能渲染，且不因数据为空而崩溃。

用 Streamlit 官方的 AppTest 真正**执行**页面脚本 —— 不是只 import。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app"
PAGES = sorted((APP / "pages").glob("*.py"))
NAMES = [p.stem for p in PAGES]


@pytest.mark.parametrize("page", PAGES, ids=NAMES)
def test_page_renders_without_exception(page):
    at = AppTest.from_file(str(page), default_timeout=180)
    at.run()
    assert not at.exception, (
        f"{page.name} 渲染抛异常：{[e.value for e in at.exception]}")


@pytest.mark.parametrize("page", PAGES, ids=NAMES)
def test_page_has_a_title(page):
    at = AppTest.from_file(str(page), default_timeout=180)
    at.run()
    assert len(at.title) >= 1, f"{page.name} 没有标题"


def test_dashboard_shows_assets_and_strategy():
    at = AppTest.from_file(str(APP / "pages" / "dashboard.py"),
                           default_timeout=180)
    at.run()
    # 标题、副标题、指标、说明都算页面内容
    blob = " ".join(
        str(x.value) for x in (list(at.markdown) + list(at.caption)
                               + list(at.subheader) + list(at.title)
                               + list(at.metric)))
    assert "资产" in blob, "仪表盘没有资产区块"
    assert "策略" in blob, "仪表盘没有策略区块"
    assert "净值" in blob, "仪表盘没有净值区块"


def test_paper_live_says_not_enough_data_when_empty():
    # 注意文件名：不能叫 paper_live.py —— 那会与 paper_live/ 包同名，
    # Streamlit 把页面目录放进 sys.path 后会遮蔽真实包。
    at = AppTest.from_file(str(APP / "pages" / "paper_live_monitor.py"),
                           default_timeout=180)
    at.run()
    blob = " ".join(str(x.value) for x in list(at.markdown) + list(at.warning)
                    + list(at.info) + list(at.caption))
    assert "NOT ENOUGH DATA" in blob or "尚无观测" in blob
    # §29：绝不对短样本年化
    assert "年化" not in blob or "不做年化" in blob or "不年化" in blob


def test_recommendation_page_has_no_submit_order_button():
    """§27：只有 Export，没有 Submit Order。"""
    at = AppTest.from_file(str(APP / "pages" / "recommendations.py"),
                           default_timeout=180)
    at.run()
    labels = [b.label for b in at.button] + \
             [b.label for b in at.get("download_button")]
    joined = " ".join(labels)
    for bad in ("下单", "执行交易", "Submit", "Order", "买入"):
        assert bad not in joined, f"推荐页出现了疑似下单按钮：{bad}"
