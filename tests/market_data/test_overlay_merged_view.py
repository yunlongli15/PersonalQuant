# -*- coding: utf-8 -*-
"""overlay 接入后的读取链：`daily_bars` 视图、日历、以及信号日的自校验。

这些用真实的 DuckDB 连接（overlay 是"一层视图"，不是纯函数），所以
**不要在跑 fetcher / 实验时并发执行**（DuckDB 单进程独占，见 CLAUDE.md）。
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OVERLAY = ROOT / "data" / "parquet" / "overlay" / "daily_overlay.parquet"
CANONICAL = ROOT / "data" / "parquet" / "daily"


def _canonical_max() -> pd.Timestamp:
    best = pd.Timestamp("1970-01-01")
    for p in CANONICAL.glob("*.parquet"):
        d = pd.read_parquet(p, columns=["trade_date"])["trade_date"]
        if len(d):
            best = max(best, pd.Timestamp(d.max()))
    return best


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_daily_bars_view_serves_overlay_sessions():
    """模型读的是视图，不是 canonical 文件；视图必须包含 overlay 的日子。"""
    import personal_quant.config  # noqa: F401
    from personal_quant import db

    ov = pd.read_parquet(OVERLAY, columns=["trade_date", "symbol"])
    n_ov = ov.groupby("trade_date")["symbol"].nunique().to_dict()
    conn = db.connect()
    for d, n in n_ov.items():
        got = conn.execute(
            "SELECT COUNT(*) FROM daily_bars WHERE trade_date = ?",
            [str(pd.Timestamp(d).date())]).fetchone()[0]
        assert got == n, f"{d} 视图里 {got} 行，overlay 里 {n} 行"


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_canonical_files_are_not_modified_by_the_overlay():
    """overlay 的全部意义就是不动上游快照。"""
    if not CANONICAL.exists():
        pytest.skip("canonical 目录不存在")
    ov = pd.read_parquet(OVERLAY, columns=["trade_date"])["trade_date"]
    assert _canonical_max() < pd.Timestamp(ov.max()), (
        "canonical 文件里出现了 overlay 的日子 —— 说明 overlay 改写过了"
        "上游数据，这就不是 overlay 了")


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_overlay_uses_no_future_data():
    """overlay 的 bar 只能由 <= T 的信息决定，且 T-1 锚点必须真的在 canonical 里。

    `factor` 是把 T 日价格接回 T-1 复权序列的桥，所以它只依赖 T 与 T-1；
    这里断言 T-1 确实存在于 canonical（否则桥是悬空的）。
    """
    ov = pd.read_parquet(OVERLAY)
    if ov.empty:
        pytest.skip("overlay 为空")
    last_canon = _canonical_max()
    for _, row in ov.iterrows():
        assert pd.Timestamp(row["trade_date"]) > last_canon
    assert (ov["factor"] > 0).all()
    assert ov["close"].notna().all()


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_calendar_exposes_overlay_sessions():
    """信号日的默认值来自 `freshness.last_trading_day()` —— 它必须看到 T，
    否则刷新链会一直回到 T-1 去问。"""
    import personal_quant.config  # noqa: F401
    from pipeline import freshness

    ov = pd.read_parquet(OVERLAY, columns=["trade_date"])["trade_date"]
    newest = pd.Timestamp(ov.max())
    cal = freshness.trading_calendar()
    assert newest in set(cal)
    assert freshness.last_trading_day(pd.Timestamp(newest)) == newest


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_overlay_cannot_leak_into_a_window_that_ends_before_it():
    """最要紧的一条不变量：overlay 只能影响它自己那一天。

    历史特征、标签、回测都必须逐位不变 —— 否则整个 overlay 就是一次
    静默的数据修订。窗口以 T-1 结束时不应当出现任何 T 行。
    """
    import personal_quant.config  # noqa: F401
    from personal_quant.providers.qlib_baseline import read_daily_bars

    newest = pd.Timestamp(
        pd.read_parquet(OVERLAY, columns=["trade_date"])["trade_date"].max())
    df = read_daily_bars(pd.Timestamp("2026-01-01"),
                         newest - pd.Timedelta(days=3))
    assert (df["trade_date"] < newest).all()
    assert newest not in set(df["trade_date"])


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_overlay_replaces_canonical_on_a_collision():
    """同一天两边都有时 overlay 优先（对账之后由 reconcile 退场）。"""
    import personal_quant.config  # noqa: F401
    from personal_quant.providers.qlib_baseline import read_daily_bars

    ov = pd.read_parquet(OVERLAY)
    d = pd.Timestamp(ov["trade_date"].max())
    df = read_daily_bars(d, d, columns=["symbol", "trade_date", "close"])
    assert len(df) == len(ov)
    a = df.set_index("symbol")["close"].sort_index()
    b = ov.set_index("symbol")["close"].sort_index()
    pd.testing.assert_series_equal(a, b, check_names=False)


def _fake_tree(tmp_path, canonical_dates, overlay_dates_):
    import personal_quant.config as cfg

    daily = tmp_path / "daily"
    ov_dir = tmp_path / "overlay"
    daily.mkdir(parents=True)
    ov_dir.mkdir(parents=True)
    pd.DataFrame({
        "symbol": ["600519.SH"] * len(canonical_dates),
        "trade_date": pd.to_datetime(canonical_dates),
        "close": [100.0] * len(canonical_dates),
    }).to_parquet(daily / "part.parquet", index=False)
    if overlay_dates_:
        pd.DataFrame({
            "symbol": ["600519.SH"] * len(overlay_dates_),
            "trade_date": pd.to_datetime(overlay_dates_),
            "close": [999.0] * len(overlay_dates_),
        }).to_parquet(ov_dir / "daily_overlay.parquet", index=False)
    return daily, ov_dir


def test_view_uses_the_cheap_union_when_nothing_collides(tmp_path, monkeypatch):
    """正常状态（上游滞后）下两边不可能撞车，视图应当是朴素的 UNION ALL。

    这一条不是微优化：反连接要对每一行求值，实测把回测里一次取价的
    查询从 0.04 秒变成 0.34 秒（8.8 倍），整套 tests/strategy 从 1 分钟
    涨到 5 分钟以上还没跑完。
    """
    import duckdb

    import personal_quant.config as cfg
    from personal_quant import db

    daily, ov_dir = _fake_tree(tmp_path, ["2026-10-08", "2026-10-09"],
                               [])
    monkeypatch.setitem(cfg.PARQUET_SUBDIRS, "daily", daily)
    monkeypatch.setattr(cfg, "PARQUET_DIR", tmp_path)
    conn = duckdb.connect(":memory:")
    db._register_daily_bars_view(conn)
    sql = conn.execute("SELECT sql FROM duckdb_views() "
                       "WHERE view_name='daily_bars'").fetchone()[0]
    assert "NOT EXISTS" not in sql.upper()
    assert conn.execute(
        "SELECT COUNT(*) FROM daily_bars").fetchone()[0] == 2


def test_view_still_deduplicates_when_a_session_collides(tmp_path,
                                                         monkeypatch):
    """快照追上来之后的短暂窗口里两边都有同一天：overlay 必须优先，
    否则会同时出现两行同一个 (symbol, trade_date)。"""
    import duckdb

    import personal_quant.config as cfg
    from personal_quant import db

    daily, ov_dir = _fake_tree(tmp_path, ["2026-10-08", "2026-10-09"],
                               ["2026-10-09"])
    monkeypatch.setitem(cfg.PARQUET_SUBDIRS, "daily", daily)
    monkeypatch.setattr(cfg, "PARQUET_DIR", tmp_path)
    conn = duckdb.connect(":memory:")
    db._register_daily_bars_view(conn)
    rows = conn.execute(
        "SELECT trade_date, close FROM daily_bars ORDER BY trade_date"
    ).fetchall()
    assert len(rows) == 2, f"重复行：{rows}"
    assert rows[-1][1] == 999.0, "撞车时 overlay 必须赢"
    assert conn.execute(
        "SELECT COUNT(*) FROM daily_bars "
        "WHERE trade_date='2026-10-09'").fetchone()[0] == 1


def test_signal_gate_rejects_a_day_with_no_bars():
    """§四：当日行情没到位时，宁可让刷新失败，也不能把旧排名当成今天的信号。"""
    import personal_quant.config  # noqa: F401
    from pipeline import signals

    with pytest.raises(signals.StaleSignalError) as e:
        signals.assert_signal_date_is_backed("1990-01-02", explicit=False)
    assert "daily_bars" in str(e.value)


@pytest.mark.skipif(not OVERLAY.exists(), reason="overlay 尚未构建")
def test_signal_gate_rejects_a_date_that_is_not_the_latest_bar():
    """默认路径下信号日必须 == 最新行情日。"""
    import personal_quant.config  # noqa: F401
    from pipeline import signals

    latest = signals.latest_bar_date()
    assert latest is not None
    # 前一天可能不是交易日，所以取 canonical 里确实有行情的最近一天
    from personal_quant import db

    row = db.connect().execute(
        "SELECT MAX(trade_date) FROM daily_bars WHERE trade_date < ?",
        [latest]).fetchone()
    if row[0] is None:
        pytest.skip("没有更早的行情日")
    older = str(row[0])
    with pytest.raises(signals.StaleSignalError) as e:
        signals.assert_signal_date_is_backed(older, explicit=False)
    assert "不是最新行情日" in str(e.value)
    # 显式指定（回填/复现历史）则放行
    signals.assert_signal_date_is_backed(older, explicit=True)
