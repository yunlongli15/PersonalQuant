# -*- coding: utf-8 -*-
"""Streamlit 页面共用件：布局、状态标签、格式化、缓存、导出。

纪律（spec §4 / §55）：
- 页面只做展示 / 输入 / 查询，**不算金融**；
- 所有数字来自 `services/`，页面不 import wealth/pipeline/factors 引擎；
- 状态**必须同时有文字**，不能只靠颜色（§57）；
- 空数据要显示明确的 NO DATA，不是 Traceback（§60 / §67）。
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd
import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Streamlit 会把**主脚本所在目录**放进 sys.path，所以页面能 `import _shared`；
# 但项目根目录（services / wealth / pipeline）还得自己加。
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@functools.lru_cache(maxsize=1)
def gui_config() -> dict:
    p = PROJECT_ROOT / "config" / "gui.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))["gui"]


def cfg(path: str, default=None):
    """按 "a.b.c" 取配置。"""
    cur = gui_config()
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


# ---------------------------------------------------------------------------
# 缓存（§40：首页必须快，不重跑 LightGBM、不扫全量新闻）
# ---------------------------------------------------------------------------

def cached(ttl: int = 300, key: str = ""):
    """包装 services 调用：Streamlit 缓存 + 明确的刷新入口。"""
    def deco(fn):
        @st.cache_data(ttl=ttl, show_spinner=False)
        def _inner(*a, **kw):
            return fn(*a, **kw)
        return _inner
    return deco


# ---------------------------------------------------------------------------
# 格式化
# ---------------------------------------------------------------------------

def money(v, digits: Optional[int] = None) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    d = cfg("precision.money", 2) if digits is None else digits
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def pct(v, digits: Optional[int] = None, signed: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    d = cfg("precision.pct", 2) if digits is None else digits
    try:
        s = f"{float(v) * 100:+.{d}f}%" if signed else f"{float(v) * 100:.{d}f}%"
        return s
    except (TypeError, ValueError):
        return "—"


def num(v, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def nocolor_pct(v, digits: int = 2) -> str:
    """带符号但不依赖颜色的百分比（颜色不是唯一信息载体）。"""
    return pct(v, digits, signed=True)


# ---------------------------------------------------------------------------
# 状态标签（§57：颜色 + 文字，缺一不可）
# ---------------------------------------------------------------------------

def status_chip(text: str, kind: str = "") -> str:
    """返回一段 HTML 状态标签；**文字始终存在**，颜色只是辅助。"""
    colors = cfg("theme.status_colors", {}) or {}
    key = (kind or text).upper().replace(" ", "_")
    color = colors.get(key, "#6B7280")
    return (f"<span style='display:inline-block;padding:2px 8px;"
            f"border-radius:10px;background:{color}1A;color:{color};"
            f"border:1px solid {color}55;font-size:12px;"
            f"font-weight:600;margin-right:6px'>{text}</span>")


def render_chips(chips: Sequence[tuple]) -> None:
    """chips = [(文字, 颜色键), ...]"""
    st.markdown("".join(status_chip(t, k) for t, k in chips),
                unsafe_allow_html=True)


def no_data(reason: str = "暂无数据") -> None:
    st.info(f"**NO DATA** — {reason}")


def unavailable_block(payload: dict, default: str = "数据不可用") -> bool:
    """统一处理 services 的 {"available": False}。返回 True 表示已渲染空态。"""
    if payload is None or payload.get("available") is False:
        no_data((payload or {}).get("reason", default))
        return True
    return False


# ---------------------------------------------------------------------------
# 数据时间戳（§62：别让用户以为数据是实时的）
# ---------------------------------------------------------------------------

def data_timestamps() -> None:
    from services import health_service, market_service

    sig = None
    try:
        from pipeline.signals import signals_state
        sig = signals_state()
    except Exception:                                          # noqa: BLE001
        sig = None
    parts = [
        f"行情 **{market_service.price_date() or '—'}**",
        f"信号 **{(sig or {}).get('as_of') or '—'}**",
    ]
    st.caption(" ｜ ".join(parts) +
               "　·　数据非实时，请以券商/平台为准")


# ---------------------------------------------------------------------------
# 导出（§64）
# ---------------------------------------------------------------------------

def export_button(rows: Sequence[dict], filename: str,
                  label: str = "导出 CSV") -> None:
    if not cfg("export.enabled", True):
        return
    if not rows:
        return
    df = pd.DataFrame(rows)
    st.download_button(
        label, df.to_csv(index=False,
                         encoding=cfg("export.encoding", "utf-8-sig")),
        file_name=filename, mime="text/csv")


# ---------------------------------------------------------------------------
# 图表
# ---------------------------------------------------------------------------

def line_chart(series: Sequence[dict], x: str = "date", y: str = "value",
               height: Optional[int] = None) -> None:
    """单序列折线。单一序列不需要图例，标题说明它是什么。"""
    if not series:
        no_data()
        return
    df = pd.DataFrame(series)
    if x not in df.columns or y not in df.columns:
        no_data("曲线数据格式不正确")
        return
    df[x] = pd.to_datetime(df[x], errors="coerce")
    df = df.dropna(subset=[x]).set_index(x)
    st.line_chart(df[[y]], height=height or cfg("chart.height", 320),
                  color="#0072B2")


def multi_line_chart(frame: pd.DataFrame, height: Optional[int] = None,
                     colors: Optional[list] = None) -> None:
    """多序列折线：**必须有图例**（st.line_chart 自带），且颜色固定顺序。"""
    if frame is None or frame.empty:
        no_data()
        return
    st.line_chart(frame, height=height or cfg("chart.height", 320),
                  color=colors or ["#0072B2", "#D55E00", "#009E73",
                                   "#CC79A7"])


def bar_chart(series: pd.Series, height: Optional[int] = None) -> None:
    if series is None or len(series) == 0:
        no_data()
        return
    st.bar_chart(series, height=height or cfg("chart.height_small", 200),
                 color="#0072B2")


# ---------------------------------------------------------------------------
# 页面骨架
# ---------------------------------------------------------------------------

def page_setup(title: str, icon: str = "📈") -> None:
    st.set_page_config(page_title=title, page_icon=icon,
                       layout="wide",
                       initial_sidebar_state="expanded")
    st.title(title)
    data_timestamps()
    safety_footer()


def safety_footer() -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**本系统只做研究与记录**\n\n"
        "· 不连接券商、不自动下单\n\n"
        "· 不构成投资建议\n\n"
        "· 个人数据只在本机")
