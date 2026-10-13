# -*- coding: utf-8 -*-
"""Same-session daily overlay: the bridge, its gates, and its idempotency.

Everything here is offline and synthetic. The point of the module under
test is that a WRONG bar is far worse than a MISSING one — a missing bar
leaves the signal date honestly at T-1, while a wrong bar silently feeds
the model fabricated prices, a fabricated factor, or a fabricated volume
scale. So most of these tests assert that something is REFUSED.
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "scripts" / "quant" / "update_daily_overlay.py"


@pytest.fixture(scope="module")
def ov():
    spec = importlib.util.spec_from_file_location("overlay_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


T1 = pd.Timestamp("2026-10-09")
T = pd.Timestamp("2026-10-12")


def prev_frame(close=100.0, factor=0.25, symbols=("600519.SH",),
               volume=1000.0):
    return pd.DataFrame({
        "symbol": list(symbols),
        "trade_date": [T1] * len(symbols),
        "close": [close] * len(symbols),
        # T-1 volume is in CANONICAL units; `volume` here feeds the
        # snapshot-recovery test, which works from that side.
        "volume": [volume] * len(symbols),
        "factor": [factor] * len(symbols),
    })


def quotes_frame(symbol="600519.SH", close=110.0, prev_close=100.0,
                 open_=105.0, high=112.0, low=104.0, shares=200_000.0,
                 amount_yuan=22_000_000.0, quote_time="20261012151000",
                 name="测试"):
    """Provider 的输出契约是**真实单位**：股 / 元（两边源各自换算过）。"""
    return pd.DataFrame({
        "symbol": [symbol], "name": [name], "close": [close],
        "prev_close": [prev_close], "open": [open_], "high": [high],
        "low": [low], "volume_shares": [shares], "amount_yuan": [amount_yuan],
        "quote_time": [quote_time],
    })


def anchor_frame(symbol="600519.SH", C=0.01, U=0.01):
    return pd.DataFrame({"symbol": [symbol], "C": [C], "U": [U]})


# ---------------------------------------------------------------------------
# the bridge itself
# ---------------------------------------------------------------------------

def test_bridge_keeps_raw_prices_and_only_derives_factor(ov):
    """Canonical stores RAW prices + `factor`; the overlay must not fold the
    factor into the price columns (that double-applies it)."""
    df, _ = ov.bridge(prev_frame(), quotes_frame(), anchor_frame())
    row = df.iloc[0]
    assert row["open"] == 105.0
    assert row["high"] == 112.0
    assert row["low"] == 104.0
    assert row["close"] == 110.0
    assert row["vwap"] == pytest.approx(22_000_000.0 / 200_000.0)


def test_adjusted_series_is_continuous_across_the_gap(ov):
    """The invariant the whole fix rests on: adjusted(T)/adjusted(T-1) must
    equal the live return, so nothing the model sees jumps."""
    df, _ = ov.bridge(prev_frame(close=100.0, factor=0.25), quotes_frame(
        close=110.0, prev_close=100.0), anchor_frame())
    row = df.iloc[0]
    adj_prev = 100.0 * 0.25
    adj_now = row["close"] * row["factor"]
    assert adj_now / adj_prev == pytest.approx(1.10, rel=1e-12)
    assert adj_prev / adj_prev == pytest.approx(1.0)


def test_ex_rights_day_is_bridged_on_the_reference_price(ov):
    """`prev_close` is the 除权除息参考价 on an action day, so `close/prev-1`
    is already the true total return — the split must NOT show up as a -33%
    crash in the adjusted series."""
    # 10送5: raw T-1 close 150, reference price 100, T close 101.
    prev = prev_frame(close=150.0, factor=0.2)
    q = quotes_frame(close=101.0, prev_close=100.0, open_=100.5, high=102.0,
                     low=100.0)
    df, report = ov.bridge(prev, q, anchor_frame())
    row = df.iloc[0]
    assert report["corporate_actions"] == 1
    # A(T-1) = 150*0.2 = 30 ; true return = 101/100-1 = +1% ; A(T) = 30.3
    assert row["close"] * row["factor"] / (150.0 * 0.2) == pytest.approx(1.01)
    # ...so factor(T) = 30.3/101 = 0.3, i.e. exactly the 1.5x split ratio
    assert row["factor"] == pytest.approx(0.3)
    assert row["factor"] / 0.2 == pytest.approx(1.5)


def test_suspended_names_are_omitted_not_zero_filled(ov):
    """Tencent reports open/high/low = 0 for a halted name. Writing a bar of
    zeros would be a fabricated -100% day."""
    q = pd.concat([quotes_frame(symbol="600519.SH"),
                   quotes_frame(symbol="000001.SZ", open_=0.0, high=0.0,
                                low=0.0, shares=0.0, close=11.0,
                                prev_close=11.0)],
                  ignore_index=True)
    prev = prev_frame(symbols=("600519.SH", "000001.SZ"))
    df, report = ov.bridge(prev, q, anchor_frame("600519.SH"))
    assert list(df["symbol"]) == ["600519.SH"]
    assert report["suspended"] == 1
    assert "000001.SZ" in report["suspended_symbols"]


def test_name_without_anchor_keeps_price_but_nulls_volume(ov):
    """No unit calibration => prices still exact, volume NaN. A guessed
    scale would inject a wrong VMA/VSTD; NaN is what the model already
    treats as unknown."""
    a = anchor_frame("600519.SH")          # 000001.SZ has no anchor
    q = pd.concat([quotes_frame(symbol="600519.SH"),
                   quotes_frame(symbol="000001.SZ", close=11.0,
                                prev_close=11.0, open_=11.0, high=11.2,
                                low=10.9)],
                  ignore_index=True)
    prev = prev_frame(symbols=("600519.SH", "000001.SZ"))
    df, report = ov.bridge(prev, q, a)
    assert len(df) == 2, "价格是准的，bar 必须保留"
    missing = df[df["symbol"] == "000001.SZ"].iloc[0]
    assert pd.isna(missing["volume"]) and pd.isna(missing["amount"])
    ok = df[df["symbol"] == "600519.SH"].iloc[0]
    assert ok["volume"] > 0
    assert report["missing_C"] == 1


def test_volume_uses_the_exact_factor_coupled_scale(ov):
    """canonical_volume = C * real_shares / factor. Getting this wrong is
    the whole reason the market_scale table could not be used directly."""
    df, _ = ov.bridge(prev_frame(), quotes_frame(shares=200_000.0),
                      anchor_frame(C=0.01, U=0.01))
    row = df.iloc[0]
    assert row["volume"] == pytest.approx(0.01 * 200_000.0 / row["factor"])


# ---------------------------------------------------------------------------
# anchor selection — which bar do we bridge FROM?
# ---------------------------------------------------------------------------

def test_anchor_is_the_session_right_before_the_new_one(ov):
    cal = pd.bdate_range("2026-10-01", "2026-10-12")
    assert ov.resolve_anchor_date(pd.Timestamp("2026-10-09"),
                                  pd.Timestamp("2026-10-12"),
                                  pd.Timestamp("2026-10-13"), cal) \
        == pd.Timestamp("2026-10-12")


def test_anchor_uses_the_overlay_when_canonical_is_behind(ov):
    """2026-10-13 实况：快照下载失败，canonical 停在 10-09，而 overlay 里
    已经有 10-12 了。

    锚点取 canonical 的话，桥就会拿「10-12→10-13 的当日收益」去乘
    「10-09 的复权价」—— 10-09→10-12 那两天的收益**凭空消失**，
    写出来的是一根假 bar，而且校验还过得去（因为 factor 就是这么定义的）。
    """
    cal = pd.bdate_range("2026-10-01", "2026-10-12")
    got = ov.resolve_anchor_date(pd.Timestamp("2026-10-09"),
                                 pd.Timestamp("2026-10-12"),
                                 pd.Timestamp("2026-10-13"), cal)
    assert got == pd.Timestamp("2026-10-12"), "应锚在 overlay 的 10-12，而不是 canonical 的 10-09"


def test_anchor_refuses_when_a_session_is_missing(ov):
    """中间缺了交易日就补不出来：一天的行情只能还原一天的收益。"""
    cal = pd.bdate_range("2026-10-01", "2026-10-12")
    with pytest.raises(ov.OverlayRefused) as e:
        ov.resolve_anchor_date(pd.Timestamp("2026-10-08"), None,
                               pd.Timestamp("2026-10-13"), cal)
    assert "缺" in str(e.value) or "落后" in str(e.value)


def test_anchor_treats_an_already_present_session_as_done(ov):
    cal = pd.bdate_range("2026-10-01", "2026-10-13")
    assert ov.resolve_anchor_date(pd.Timestamp("2026-10-09"),
                                  pd.Timestamp("2026-10-13"),
                                  pd.Timestamp("2026-10-13"), cal) is None


def test_anchor_on_force_rebuilds_from_the_previous_session(ov):
    """--force 重建已有的 session 时，锚点回退到它的前一个交易日。"""
    cal = pd.bdate_range("2026-10-01", "2026-10-13")
    assert ov.resolve_anchor_date(pd.Timestamp("2026-10-12"),
                                  pd.Timestamp("2026-10-13"),
                                  pd.Timestamp("2026-10-13"), cal,
                                  force=True) == pd.Timestamp("2026-10-12")


# ---------------------------------------------------------------------------
# validation gates — every one of these must BLOCK publication
# ---------------------------------------------------------------------------

def _good(ov):
    df, rep = ov.bridge(prev_frame(), quotes_frame(), anchor_frame())
    return df, rep


def _as_overlay(ov, df, date=T):
    """Bridge output -> the row shape `write_overlay` persists."""
    cols = ["symbol", "trade_date", "open", "high", "low", "close", "volume",
            "amount", "vwap", "factor", "source"]
    out = df.copy()
    out["trade_date"] = date
    out["source"] = "tencent_batch_quote"
    return out[cols]


def test_validation_accepts_a_clean_session(ov):
    df, rep = _good(ov)
    v = ov.validate(df, rep, T, expected=1)
    # expected=1 < MIN_TRADED, so this only checks the non-coverage gates
    assert all("high" not in e and "low" not in e and "NaN" not in e
               for e in v["errors"])


def test_validation_blocks_impossible_ohlc(ov):
    """A high below the close cannot come from the bridge (one positive
    factor scales all four), so it means the SOURCE was broken."""
    df, rep = _good(ov)
    df.loc[0, "high"] = df.loc[0, "close"] - 1.0
    v = ov.validate(df, rep, T, expected=1000)
    assert not v["ok"]
    assert any("high <" in e for e in v["errors"])


def test_validation_blocks_low_coverage(ov):
    df, rep = _good(ov)
    v = ov.validate(df, rep, T, expected=100_000)
    assert not v["ok"]
    assert any("覆盖率" in e for e in v["errors"])


def test_validation_blocks_nonpositive_factor(ov):
    df, rep = _good(ov)
    df.loc[0, "factor"] = 0.0
    v = ov.validate(df, rep, T, expected=1000)
    assert not v["ok"]
    assert any("factor" in e for e in v["errors"])


def test_validation_blocks_duplicate_symbols(ov):
    df, rep = _good(ov)
    df = pd.concat([df, df], ignore_index=True)
    v = ov.validate(df, rep, T, expected=1000)
    assert not v["ok"]
    assert any("重复" in e for e in v["errors"])


# ---------------------------------------------------------------------------
# session proof — the layer must never invent a trading day
# ---------------------------------------------------------------------------

def _batch(quote_time):
    return SimpleNamespace(quotes=pd.DataFrame({"quote_time": quote_time}))


def test_feed_session_reads_the_session_from_the_data(ov):
    target, newest = ov.feed_session(_batch(["20261012151000"]))
    assert target == T
    assert newest == "20261012151000"


def test_intraday_feed_is_refused(ov):
    """A 11:20 fetch would freeze a half-formed bar into the model input —
    a worse error than being one session behind."""
    target, newest = ov.feed_session(_batch(["20261012112000"]))
    with pytest.raises(ov.OverlayRefused) as e:
        ov.ensure_session(target, newest)
    assert "尚未收盘" in str(e.value)


def test_mixed_sessions_are_refused(ov):
    with pytest.raises(ov.OverlayRefused) as e:
        ov.feed_session(_batch(["20261012151000", "20261013151000"]))
    assert "session" in str(e.value)


def test_weekend_is_refused(ov):
    with pytest.raises(ov.OverlayRefused):
        ov.ensure_session(pd.Timestamp("2026-10-10"), "20261010151000")


def test_closed_session_is_accepted(ov):
    ov.ensure_session(T, "20261012161500")     # must not raise


# ---------------------------------------------------------------------------
# write path: idempotent, atomic, and does not touch canonical
# ---------------------------------------------------------------------------

def test_write_overlay_is_idempotent_per_session(ov, tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "OVERLAY_BARS", tmp_path / "daily_overlay.parquet")
    monkeypatch.setattr(ov, "CALENDAR_EXTRA", tmp_path / "calendar_extra.parquet")
    monkeypatch.setattr(ov, "MANIFEST", tmp_path / "overlay_manifest.json")
    monkeypatch.setattr(ov, "OVERLAY_DIR", tmp_path)

    batch = SimpleNamespace(request_count=1, fetched_at=pd.Timestamp.now(),
                            sha256="abc", failures=[])
    df, rep = _good(ov)
    v = ov.validate(df, rep, T, expected=1000)
    for _ in range(3):
        out = ov.write_overlay(df, T, rep, v, batch, None)
    assert len(out) == 1, "同一天重复跑不能产生重复行"

    # a second session accumulates rather than replacing
    df2, rep2 = ov.bridge(prev_frame(), quotes_frame(close=111.0,
                                                     prev_close=110.0),
                          anchor_frame())
    out2 = ov.write_overlay(df2, pd.Timestamp("2026-10-13"), rep2, v, batch,
                            None)
    assert len(out2) == 2
    assert sorted(str(d.date()) for d in out2["trade_date"].unique()) == \
        ["2026-10-12", "2026-10-13"]


def test_write_overlay_leaves_canonical_files_alone(ov, tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "OVERLAY_BARS", tmp_path / "daily_overlay.parquet")
    monkeypatch.setattr(ov, "CALENDAR_EXTRA", tmp_path / "calendar_extra.parquet")
    monkeypatch.setattr(ov, "MANIFEST", tmp_path / "overlay_manifest.json")
    monkeypatch.setattr(ov, "OVERLAY_DIR", tmp_path)
    canonical = tmp_path / "daily" / "bars_2026.parquet"
    canonical.parent.mkdir()
    canonical.write_bytes(b"original")
    batch = SimpleNamespace(request_count=1, fetched_at=pd.Timestamp.now(),
                            sha256="abc", failures=[])
    df, rep = _good(ov)
    ov.write_overlay(df, T, rep, ov.validate(df, rep, T, 1000), batch, None)
    assert canonical.read_bytes() == b"original"


# ---------------------------------------------------------------------------
# §五 reconciliation: hand the session back once the snapshot carries it
# ---------------------------------------------------------------------------

def test_reconcile_retires_sessions_the_snapshot_has_caught_up_on(
        ov, tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "OVERLAY_BARS", tmp_path / "daily_overlay.parquet")
    monkeypatch.setattr(ov, "CALENDAR_EXTRA", tmp_path / "calendar_extra.parquet")
    monkeypatch.setattr(ov, "MANIFEST", tmp_path / "overlay_manifest.json")
    monkeypatch.setattr(ov, "RECON_PATH", tmp_path / "reconciliation.json")
    monkeypatch.setattr(ov, "OVERLAY_DIR", tmp_path)

    df, rep = _good(ov)
    overlay = _as_overlay(ov, df, T)
    overlay.to_parquet(tmp_path / "daily_overlay.parquet", index=False)

    # the "snapshot" now carries the same session, very slightly different
    canon = overlay.copy()
    canon["close"] = canon["close"] * 1.0001
    monkeypatch.setattr(ov, "_read_canonical", lambda **kw: canon)

    recs = ov.reconcile(retire=True)
    assert len(recs) == 1
    assert recs[0]["trade_date"] == "2026-10-12"
    assert recs[0]["close_median_reldiff"] == pytest.approx(1e-4, rel=0.05)
    # retired: the overlay must not shadow the authoritative row
    assert len(pd.read_parquet(tmp_path / "daily_overlay.parquet")) == 0


def test_reconcile_keeps_sessions_the_snapshot_lacks(ov, tmp_path, monkeypatch):
    monkeypatch.setattr(ov, "OVERLAY_BARS", tmp_path / "daily_overlay.parquet")
    monkeypatch.setattr(ov, "CALENDAR_EXTRA", tmp_path / "calendar_extra.parquet")
    monkeypatch.setattr(ov, "RECON_PATH", tmp_path / "reconciliation.json")
    monkeypatch.setattr(ov, "OVERLAY_DIR", tmp_path)
    df, rep = _good(ov)
    overlay = _as_overlay(ov, df, T)
    overlay.to_parquet(tmp_path / "daily_overlay.parquet", index=False)
    monkeypatch.setattr(ov, "_read_canonical", lambda **kw: prev_frame())
    assert ov.reconcile(retire=True) == []
    assert len(pd.read_parquet(tmp_path / "daily_overlay.parquet")) == 1


# ---------------------------------------------------------------------------
# the anchor algebra
# ---------------------------------------------------------------------------

def test_recover_C_from_a_prior_snapshot(ov, tmp_path, monkeypatch):
    """C = canonical_volume * factor / real_shares is exact for any session
    where both sides are known — which the stored snapshot provides."""
    import json

    raw = tmp_path / "batch_quote"
    raw.mkdir()
    (raw / "quotes_20261009.json").write_text(json.dumps({
        "quotes": [{"symbol": "920000.BJ", "volume_lots": 10.0}],
    }), encoding="utf-8")
    import personal_quant.providers.batch_quote as bq
    monkeypatch.setattr(bq, "RAW_DIR", raw)

    bars = pd.DataFrame({
        "symbol": ["920000.BJ"], "trade_date": [T1],
        "volume": [250.0], "factor": [0.5],
    })
    anchor = pd.DataFrame({"symbol": ["920000.BJ"], "C": [None]})
    got = ov.recover_C_from_snapshots(anchor, bars)
    # C = canonical_volume * factor / real_shares = 250 * 0.5 / (10 lots * 100)
    assert got.iloc[0]["C_snapshot"] == pytest.approx(0.125)


def test_recover_skips_sessions_absent_from_canonical(ov, tmp_path, monkeypatch):
    import json

    raw = tmp_path / "batch_quote"
    raw.mkdir()
    (raw / "quotes_20261012.json").write_text(json.dumps({
        "quotes": [{"symbol": "920000.BJ", "volume_lots": 10.0}],
    }), encoding="utf-8")
    import personal_quant.providers.batch_quote as bq
    monkeypatch.setattr(bq, "RAW_DIR", raw)
    bars = pd.DataFrame({"symbol": ["920000.BJ"], "trade_date": [T1],
                         "volume": [250.0], "factor": [0.5]})
    anchor = pd.DataFrame({"symbol": ["920000.BJ"], "C": [None]})
    got = ov.recover_C_from_snapshots(anchor, bars)
    assert got.empty, "快照的 session 不在 canonical 里，不能拿来算 C"
