# -*- coding: utf-8 -*-
"""新闻因子研究引擎：加载事件 -> 建流 -> 算因子 -> 评估。

只读。不改 `news/`、不改任何快照、不训练模型、不碰生产路径。
`load_research_events()` 的输出缓存到
`data/derived/news/news_events_research.parquet`（派生物，可重建）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEWS_DIR = PROJECT_ROOT / "data" / "derived" / "news"
RESEARCH_EVENTS = NEWS_DIR / "news_events_research.parquet"
FACTOR_DAILY = NEWS_DIR / "news_factor_daily.parquet"

#: 研究层使用的新闻数据版本。**固定 v2**（修复 SSE 采集后的集合）。
NEWS_VERSION = "v2"
FEATURE_VERSION = "news_research_0.1"

#: taxonomy 版本。**改了 taxonomy 而不改这个数，缓存就会把旧分类当成
#: 新分类返回** —— 报告里写的类别和实际算出来的类别从此对不上，而且
#: 没有任何一层会报警。加规则 / 改规则 / 调 severity 都必须 +1。
TAXONOMY_VERSION = "1"
_CACHE_SIDECAR = RESEARCH_EVENTS.with_suffix(".taxonomy.json")


# ---------------------------------------------------------------------------
# 1. 事件层：加 taxonomy
# ---------------------------------------------------------------------------

def load_research_events(rebuild: bool = False) -> pd.DataFrame:
    """读 v2 事件 + 标题，套研究层 taxonomy，结果缓存。

    缓存存在的意义纯粹是速度：2M 行的逐行字符串匹配要几分钟，
    而 taxonomy 是纯函数（同样输入必然同样输出），缓存不改变结果。
    """
    if RESEARCH_EVENTS.exists() and not rebuild and _cache_is_current():
        return pd.read_parquet(RESEARCH_EVENTS)

    from personal_quant import db
    from .taxonomy import classify

    # 全程走 DataFrame。2M 行如果用 db.query（返回 list[dict]）光是
    # Python 对象就要几个 GB，而这里只需要一次 join + 一次逐行匹配。
    conn = db.connect()
    ev = conn.execute(f"""
        SELECT e.event_id, e.symbol, e.event_type, e.publication_time,
               e.availability_time, e.availability_unknown, e.novelty,
               d.title
        FROM news_events_{NEWS_VERSION} e
        JOIN news_documents_{NEWS_VERSION} d USING(document_id)
    """).fetch_df()

    # 逐行匹配是纯 CPU：用 dict 查表在 Python 里反而比 pandas.apply 快，
    # 且不复制整表。标题用 itertuples 取，避免 iterrows 的 Series 开销。
    theme = [""] * len(ev)
    mat = [""] * len(ev)
    dh = [""] * len(ev)
    sev = [0.0] * len(ev)
    btype = ev["event_type"].tolist()
    title = ev["title"].tolist()
    for i in range(len(ev)):
        a, b, c, d = classify(title[i] or "", btype[i])
        theme[i] = a; mat[i] = b; dh[i] = c; sev[i] = d
    ev["theme"] = theme
    ev["materiality"] = mat
    ev["dir_hint"] = dh
    ev["severity"] = sev
    ev = ev.drop(columns=["title"])

    ev["availability_time"] = pd.to_datetime(ev["availability_time"],
                                             errors="coerce", utc=True)
    ev = ev.dropna(subset=["availability_time"])
    ev["avail_local"] = ev["availability_time"].dt.tz_convert("Asia/Shanghai")
    ev = ev.drop(columns=["availability_time"])

    cal = trading_calendar()
    ev["sdate"] = _snap_to_trading_day(ev["avail_local"].dt.normalize(), cal)
    ev = ev.dropna(subset=["sdate"])
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    ev.drop(columns=["avail_local"]).to_parquet(RESEARCH_EVENTS, index=False)
    _CACHE_SIDECAR.write_text(
        json.dumps({"taxonomy_version": TAXONOMY_VERSION,
                    "news_version": NEWS_VERSION,
                    "rows": int(len(ev))}, indent=2), encoding="utf-8")
    return ev


def _cache_is_current() -> bool:
    """缓存是不是用**当前这版 taxonomy** 算出来的。

    读不到 sidecar 一律视为过期 —— 宁可多算一遍，也不能拿旧分类冒充新分类。
    """
    if not _CACHE_SIDECAR.exists():
        return False
    try:
        meta = json.loads(_CACHE_SIDECAR.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return False
    return (meta.get("taxonomy_version") == TAXONOMY_VERSION
            and meta.get("news_version") == NEWS_VERSION)


def _snap_to_trading_day(days: pd.Series, cal: pd.DatetimeIndex) -> pd.Series:
    """把公告可用日对齐到**当日或之后的第一个交易日**。

    非交易日公告（周末/节假日）本身在 PIT 上就是次一交易日才可用
    （docs/步骤5-新闻时点规则.md），这里只是把口径落到日历上。
    """
    pos = cal.searchsorted(days.values, side="left")
    ok = pos < len(cal)
    out = pd.Series(pd.NaT, index=days.index, dtype="datetime64[ns]")
    out.iloc[np.flatnonzero(ok)] = cal[pos[ok]]
    return out


def trading_calendar() -> pd.DatetimeIndex:
    p = PROJECT_ROOT / "data" / "derived" / "factors" / "calendar.parquet"
    if p.exists():
        return pd.DatetimeIndex(
            pd.to_datetime(pd.read_parquet(p)["trade_date"]))
    from personal_quant import db
    return pd.DatetimeIndex(pd.to_datetime(
        db.query("SELECT trade_date FROM trading_calendar WHERE is_open "
                 "ORDER BY trade_date")[0]["trade_date"]))


def research_start() -> pd.Timestamp:
    """研究窗口起点 = 逐股覆盖起点里最晚的那一批之后。

    覆盖起点之前的日期对该股票是"没抓取"，不是"没有公告"，
    必须 NaN 而不是 0（STEP 5 铁律）。整段窗口取覆盖最全的区间，
    避免把大量 NaN 混进 IC 计算。
    """
    return pd.Timestamp("2018-01-01")


def coverage() -> pd.DataFrame:
    p = NEWS_DIR / f"news_coverage_{NEWS_VERSION}.parquet"
    c = pd.read_parquet(p)
    c["start_date"] = pd.to_datetime(c["start_date"])
    return c


# ---------------------------------------------------------------------------
# 2. 流 -> 日频宽表
# ---------------------------------------------------------------------------

def stream_panel(streams: pd.DataFrame, name: str,
                 cal: pd.DatetimeIndex,
                 start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """一个流的 (交易日 x 股票) 宽表，缺失日填 0。

    `streams` 里没有该 (symbol, date) 的行 = 那天**确实没有**该事件
    （覆盖问题在最后用 news_coverage 单独 NaN 掉），所以填 0。
    """
    sub = streams.loc[streams["sdate"] >= start - pd.Timedelta(days=400),
                      ["symbol", "sdate", name]]
    cal = cal[(cal >= start - pd.Timedelta(days=400)) & (cal <= end)]
    wide = sub.pivot_table(index="sdate", columns="symbol", values=name,
                           aggfunc="sum")
    return wide.reindex(cal).fillna(0.0)


# ---------------------------------------------------------------------------
# 3. 因子计算（按 kind 分派）
# ---------------------------------------------------------------------------

#: 指数衰减的权重基准：0.5 ** (龄 / HALF_LIFE)，龄按交易日。
#: 取 10 是 spec §七E 说的"简单透明、不优化"。
DECAY_HALF_LIFE = 10
BASELINE_DAYS = 120


def compute_panel(spec, streams: pd.DataFrame, cal: pd.DatetimeIndex,
                  start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """按 spec.kind 算出因子的完整体（交易日 x 股票）。"""
    W = spec.window
    if spec.kind == "sum":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        return P.rolling(W).sum()

    if spec.kind == "decay":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        out = None
        for lag in range(W):
            w = 0.5 ** (lag / DECAY_HALF_LIFE)
            term = P.shift(lag) * w
            out = term if out is None else out + term
        return out

    if spec.kind == "streak":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        # "截至 t 连续为 1 的长度" = t 的位置 − 上一个 0 的位置。
        # 用（行号 - 上一个零的行号）在 numpy 上整块算，比
        # `has.groupby((has==0).cumsum()).cumsum()` 靠谱 —— 后者在
        # DataFrame 上会抛 "Grouper not 1-dimensional"，逐列循环又太慢。
        h = (P.to_numpy() > 0)
        idx = np.arange(h.shape[0])[:, None]
        last_zero = np.maximum.accumulate(np.where(h, -1, idx), axis=0)
        streak = np.where(h, idx - last_zero, 0).astype(float)
        return pd.DataFrame(streak, index=P.index,
                            columns=P.columns).rolling(W).max()

    if spec.kind == "first":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        C = P.cumsum()
        prior = C.shift(180).fillna(0.0)
        # 当日之前 180 个交易日内没有任何负面事件 -> 今天是"首次"
        is_first = (P > 0) & ((C - P - prior) <= 0)
        return is_first.astype(float).rolling(W).sum()

    if spec.kind == "balance":
        pos = stream_panel(streams, spec.source_streams[0], cal,
                           start, end).rolling(W).sum()
        neg = stream_panel(streams, spec.source_streams[1], cal,
                           start, end).rolling(W).sum()
        return (pos - neg) / (pos + neg + 1.0)

    if spec.kind == "ratio2":
        pos = stream_panel(streams, spec.source_streams[0], cal,
                           start, end).rolling(W).sum()
        neg = stream_panel(streams, spec.source_streams[1], cal,
                           start, end).rolling(W).sum()
        return neg / (pos + 1.0)

    if spec.kind == "ratio":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        short = P.rolling(W).sum()
        base = P.rolling(BASELINE_DAYS).sum() / (BASELINE_DAYS / W)
        return short / (base + 1.0)

    if spec.kind == "zscore":
        P = stream_panel(streams, spec.source_streams[0], cal, start, end)
        short = P.rolling(W).sum()
        mu = short.rolling(BASELINE_DAYS).mean()
        sd = short.rolling(BASELINE_DAYS).std()
        return (short - mu) / (sd + 1e-6)

    raise ValueError(f"未知的 kind {spec.kind!r}（因子 {spec.name}）")


def mask_uncovered(panel: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """覆盖起点之前的格子置 NaN —— 那些是"没抓取"，不是"没有公告"。"""
    cov = coverage().set_index("symbol")["start_date"]
    out = panel.reindex(dates)
    cols = out.columns
    starts = cov.reindex(cols)
    sd = starts.to_numpy(dtype="datetime64[ns]")
    for d in dates:
        out.loc[d, cols[sd > np.datetime64(d)]] = np.nan
    return out


# ---------------------------------------------------------------------------
# 4. 评估
# ---------------------------------------------------------------------------

def spearman(a: pd.Series, b: pd.Series, min_n: int = 30) -> float:
    """横截面 rank IC。

    只要求因子有 ≥2 个不同取值：0/1 型因子（例如「首次负面事件」）
    是合法的，要求 ≥3 会把它们整类误杀 —— 而它们恰恰是 spec §十八
    点名的重点候选。样本量由 min_n 兜底。
    """
    df = pd.concat([a.rename("f"), b.rename("y")], axis=1).dropna()
    if len(df) < min_n or df["f"].nunique() < 2 or df["y"].nunique() < 3:
        return np.nan
    return float(df["f"].rank().corr(df["y"].rank()))


def ic_series(panel: pd.DataFrame, labels: dict, dates) -> pd.Series:
    """逐信号日的 rank IC。"""
    out = {}
    for d in dates:
        d = pd.Timestamp(d)
        if d not in panel.index or d not in labels:
            continue
        out[d] = spearman(panel.loc[d].dropna(), labels[d])
    return pd.Series(out).dropna()


def dispersion(panel: pd.DataFrame, dates) -> dict:
    """横截面分辨力 —— spec §十二。"""
    uniq, miss, std, med, ties = [], [], [], [], []
    for d in dates:
        d = pd.Timestamp(d)
        if d not in panel.index:
            continue
        s = panel.loc[d]
        n = len(s)
        if n == 0:
            continue
        miss.append(float(s.isna().mean()))
        v = s.dropna()
        if len(v) < 30:
            continue
        # 唯一值比例：所有股票取同一个值 -> 完全没有横截面信息
        uniq.append(float(v.nunique() / len(v)))
        ties.append(float(v.value_counts().iloc[0] / len(v)))
        std.append(float(v.std()))
        med.append(float(v.median()))
    f = lambda x: float(np.mean(x)) if x else float("nan")
    return {"unique_ratio": f(uniq), "missing_rate": f(miss),
            "cs_std": f(std), "cs_median": f(med),
            "max_tie_share": f(ties)}


def quantiles(panel: pd.DataFrame, labels: dict, dates, q: int = 5) -> dict:
    """分层测试 —— spec §十一。"""
    rows = {i: [] for i in range(q)}
    spreads = []
    for d in dates:
        d = pd.Timestamp(d)
        if d not in panel.index or d not in labels:
            continue
        f = panel.loc[d].dropna()
        y = labels[d]
        both = f.index.intersection(y.index)
        if len(both) < q * 10:
            continue
        f, y = f[both], y[both]
        try:
            bucket = pd.qcut(f.rank(method="first"), q, labels=False)
        except ValueError:
            continue
        means = {}
        for b in range(q):
            m = bucket == b
            if m.sum() == 0:
                continue
            means[b] = float(y[m].mean())
            rows[b].append(means[b])
        if q - 1 in means and 0 in means:
            spreads.append(means[q - 1] - means[0])
    out = {f"Q{i+1}": float(np.mean(v)) if v else np.nan
           for i, v in rows.items()}
    out["Qhigh-Qlow"] = float(np.mean(spreads)) if spreads else np.nan
    out["n_dates"] = len(spreads)
    return out


def subgroup_ic(panel: pd.DataFrame, labels: dict, dates,
                mask_fn) -> dict:
    """按子样本算 IC 均值/ICIR（交易所、流动性分组等）。"""
    ics = []
    for d in dates:
        d = pd.Timestamp(d)
        if d not in panel.index or d not in labels:
            continue
        f = panel.loc[d].dropna()
        y = labels[d]
        both = f.index.intersection(y.index)
        if len(both) < 30:
            continue
        f, y = f[both], y[both]
        keep = mask_fn(pd.Index(f.index), d)
        if keep is None:
            continue
        ics.append(spearman(f[keep], y[keep]))
    s = pd.Series(ics).dropna()
    if len(s) < 5:
        return {"n": int(len(s)), "ic": np.nan, "icir": np.nan,
                "pos_pct": np.nan}
    return {"n": int(len(s)), "ic": float(s.mean()),
            "icir": float(s.mean() / s.std()) if s.std() else np.nan,
            "pos_pct": float((s > 0).mean())}
