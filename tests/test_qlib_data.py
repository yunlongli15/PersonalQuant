# -*- coding: utf-8 -*-
"""STEP 1: Qlib 中国市场示例数据读取验证。

验证内容：
1. qlib 可以初始化
2. 可以读取交易日历
3. 可以读取 A 股股票列表
4. 可以读取某只股票的历史日线数据
5. 数据时间索引正常
6. 数据中没有明显的结构性损坏

注意：针对 qlib 0.9.x API（D.calendar 返回 np.ndarray；
instrument 列表用 D.list_instruments；代码使用市场前缀命名，如 SH600519）。
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QLIB_DATA_PATH = PROJECT_ROOT / "qlib_data"


@pytest.fixture(scope="module")
def qlib_session():
    import qlib
    from qlib.constant import REG_CN

    qlib.init(provider_uri=str(QLIB_DATA_PATH), region=REG_CN)
    yield qlib
    # qlib 无官方 uninit 接口，fixture 结束后保持初始化状态即可


def test_qlib_import_and_version():
    import qlib

    assert qlib is not None
    assert isinstance(qlib.__version__, str) and qlib.__version__
    print(f"qlib version: {qlib.__version__}")


def test_qlib_init(qlib_session):
    from qlib.config import C

    assert C is not None
    data_path = str(C.provider_uri["__DEFAULT_FREQ"])
    assert Path(data_path).resolve() == QLIB_DATA_PATH.resolve(), f"provider_uri 不符: {data_path}"
    assert C.region == "cn", f"region 不符: {C.region}"
    print(f"provider_uri: {data_path}, region: {C.region}")


def test_trading_calendar(qlib_session):
    from qlib.data import D

    cal = D.calendar(start_time="2020-01-01", end_time="2020-01-31", freq="day")
    assert isinstance(cal, (list, np.ndarray)) and len(cal) > 0, "交易日历为空"
    # 2020 年 1 月应有约 16 个交易日
    assert 15 <= len(cal) <= 23, f"2020-01 交易日数量异常: {len(cal)}"
    # 日历内不应包含周末
    weekends = [d for d in cal if pd.Timestamp(d).dayofweek >= 5]
    assert not weekends, f"日历包含周末: {weekends[:3]}"


def test_instruments_cn(qlib_session):
    from qlib.data import D

    inst = D.list_instruments(instruments=D.instruments(market="all"), as_list=True)
    assert isinstance(inst, list) and len(inst) > 0, "instrument 列表为空"

    # 中国市场应包含沪市(SH 前缀)与深市(SZ 前缀)股票
    sh = [i for i in inst if i.startswith("SH")]
    sz = [i for i in inst if i.startswith("SZ")]
    assert len(sh) > 1000, f"沪市股票数量异常: {len(sh)}"
    assert len(sz) > 1000, f"深市股票数量异常: {len(sz)}"
    print(f"total instruments: {len(inst)}, SH: {len(sh)}, SZ: {len(sz)}")

    # 抽样验证知名股票存在
    for code in ["SH600519", "SZ000001", "SH600000"]:
        assert code in inst, f"缺少 {code}"


def test_single_stock_daily_data(qlib_session):
    from qlib.data import D

    df = D.features(
        ["SH600519"],
        ["$open", "$high", "$low", "$close", "$volume", "$vwap"],
        start_time="2015-01-01",
        end_time="2015-12-31",
        freq="day",
    )
    assert df is not None and not df.empty, "SH600519 2015 年日线数据为空"

    # 时间索引正常
    assert isinstance(df.index, pd.MultiIndex)
    assert df.index.names[0] == "instrument" and df.index.names[1] == "datetime"
    dates = df.index.get_level_values("datetime")
    assert dates.is_monotonic_increasing, "时间索引非单调递增"
    assert dates.min() >= pd.Timestamp("2015-01-01")
    assert dates.max() <= pd.Timestamp("2015-12-31")

    # 约 244 个交易日（2015 年贵州茅台无长期停牌）
    n_days = len(dates)
    assert 200 <= n_days <= 250, f"交易日数量异常: {n_days}"
    # vwap 列有有效数据（Alpha158 依赖该字段）
    assert df["$vwap"].notna().all(), "$vwap 含 NaN"
    print(f"SH600519 2015 trading days: {n_days}")


def test_data_structure_integrity(qlib_session):
    from qlib.data import D

    codes = ["SH600519", "SZ000001", "SZ000002", "SH601318", "SH600000"]
    df = D.features(
        codes,
        ["$close", "$volume", "$high", "$low"],
        start_time="2018-01-01",
        end_time="2018-12-31",
        freq="day",
    )
    assert df is not None and not df.empty

    close = df["$close"].astype(float)
    high = df["$high"].astype(float)
    low = df["$low"].astype(float)
    volume = df["$volume"].astype(float)

    # 价格均为正数
    assert (close > 0).all(), "存在非正收盘价"
    # 高价 >= 低价
    assert (high >= low).all(), "存在 high < low 的结构性损坏"
    # 收盘价在 [low, high] 之间（考虑浮点误差）
    eps = 1e-6
    assert ((close + eps >= low) & (close - eps <= high)).all(), "收盘价越出高低区间"
    # 无 NaN / Inf
    assert not np.isnan(close).any() and not np.isinf(close).any(), "收盘价含 NaN/Inf"
    assert not np.isnan(volume).any(), "成交量含 NaN"
    # 成交量非负
    assert (volume >= 0).all(), "存在负成交量"
    # 每只股票都有数据
    for code in codes:
        sub = df.xs(code, level="instrument")
        assert len(sub) > 200, f"{code} 2018 年数据不足 200 个交易日: {len(sub)}"


def test_calendar_has_cn_holidays(qlib_session):
    """验证日历符合中国节假日（如 2020 年春节假期无交易日）。"""
    from qlib.data import D

    cal = D.calendar(start_time="2020-01-20", end_time="2020-02-05", freq="day")
    cal_set = {pd.Timestamp(d) for d in cal}
    # 2020 年春节：1/24–1/30 休市
    for day in ["2020-01-24", "2020-01-27", "2020-01-28", "2020-01-29", "2020-01-30"]:
        assert pd.Timestamp(day) not in cal_set, f"春节假期 {day} 不应是交易日"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))
