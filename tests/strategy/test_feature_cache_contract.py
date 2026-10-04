# -*- coding: utf-8 -*-
"""C3 修复的回归测试：特征缓存的**日期契约**。

旧格式 `data/derived/features/YYYY-MM.parquet` 只带月份，而文件内容其实
是"该月最后一次写入的那一天"：
  * 同月不同日互相覆盖（后写的赢）；
  * 读的时候不做任何日期校验，直接把整份文件当作"请求的那一天"；
  * `cache=False` 重算之后**照样**写共享的月文件 —— 于是生产信号刷新
    会污染所有 `cache=True` 的读者。

结果：请求 2026-09-18 会静默拿到 2026-09-29 的横截面，而且**在"事后回放"
时方向是真实的前视泄漏**（reports/daily_exit_paper_v1_audit.md §3.3）。

新契约：按日期存 `feature_<YYYY-MM-DD>.parquet`，文件内写 `feature_date`，
读写两侧都校验；任何不一致一律视为未命中。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import pytest

import personal_quant.strategy.features as fmod

COLS = pd.MultiIndex.from_tuples([("feature", "KMID"), ("feature", "KLEN")])
SYMS = ["S0000.SH", "S0001.SH", "S0002.SH"]


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """把缓存目录指到临时目录，绝不碰真实的 DERIVED 层。"""
    c = tmp_path / "features"
    c.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(fmod, "FEATURE_CACHE", c)
    return c


def _write(cache_dir: Path, date, value: float = 1.0,
           claimed_date=None) -> Path:
    """直接造一个缓存文件（不跑 qlib），日期由 `claimed_date` 决定。

    `claimed_date` 与文件名不同 = 制造"文件自称的日期不是它该是的那一天"。
    """
    d = pd.Timestamp(date)
    df = pd.DataFrame(np.full((len(SYMS), len(COLS)), value), columns=COLS,
                      index=SYMS)
    df.index.name = "symbol"
    df[("feature_date", "")] = (claimed_date if claimed_date is not None
                                else d.strftime("%Y-%m-%d"))
    p = cache_dir / f"feature_{d:%Y-%m-%d}.parquet"
    df.to_parquet(p)
    return p


def _no_worker(monkeypatch):
    """把真正的 qlib 子进程换成空操作：这样"有没有命中缓存"完全可观测。"""
    monkeypatch.setattr(fmod, "_compute_quarter_subprocess",
                        lambda *a, **k: None)


# ---------------------------------------------------------------------------
# 1. 命中 / 未命中
# ---------------------------------------------------------------------------

def test_correct_date_is_a_hit(cache_dir):
    """requested == 文件名日期 == 文件内 feature_date -> 命中。"""
    _write(cache_dir, "2026-09-29", value=7.0)
    df = fmod.read_feature_cache(pd.Timestamp("2026-09-29"))
    assert df is not None
    assert len(df) == len(SYMS)


def test_missing_file_is_a_miss(cache_dir):
    assert fmod.read_feature_cache(pd.Timestamp("2026-09-18")) is None


def test_wrong_date_in_the_file_is_a_miss_and_is_never_returned(cache_dir, capsys):
    """文件里装的是 09-29 的横截面，请求的却是 09-18 -> 必须未命中。

    这正是审计里实测到的场景：`2026-09.parquet` 的内容是 09-29。
    """
    _write(cache_dir, "2026-09-18", value=7.0, claimed_date="2026-09-29")

    assert fmod.read_feature_cache(pd.Timestamp("2026-09-18")) is None
    assert "缓存日期不匹配" in capsys.readouterr().out


def test_compute_features_never_returns_a_wrong_dated_frame(cache_dir, monkeypatch):
    """不命中时宁可返回空表，也不返回错误日期的特征。"""
    _write(cache_dir, "2026-09-18", value=7.0, claimed_date="2026-09-29")
    _no_worker(monkeypatch)

    out = fmod.compute_features(SYMS, [pd.Timestamp("2026-09-18")],
                                cache=True, verbose=False)
    df = out[pd.Timestamp("2026-09-18")]
    assert df.empty, "错误日期的缓存被当成命中了"
    assert 7.0 not in set(np.asarray(df).ravel().tolist())


def test_correct_date_hits_through_compute_features(cache_dir):
    """命中时不重算，且元数据列不会泄漏给调用方。"""
    _write(cache_dir, "2026-09-29", value=7.0)
    out = fmod.compute_features(SYMS, [pd.Timestamp("2026-09-29")],
                                cache=True, verbose=False)
    df = out[pd.Timestamp("2026-09-29")]
    assert not df.empty
    assert (df.to_numpy() == 7.0).all()
    # feature_date 是缓存自述用的元数据，不是特征
    assert not any(str(c).startswith(fmod.FEATURE_DATE_COL) for c in df.columns)
    assert list(df.columns) == list(COLS)


# ---------------------------------------------------------------------------
# 2. cache=False 绝不污染别的日期
# ---------------------------------------------------------------------------

def test_cache_false_does_not_touch_other_dates(cache_dir, monkeypatch):
    """`cache=False` = 不读缓存；重算结果只写**它自己那一天**的文件。

    旧实现里 `cache=False` 会把共享的月文件整个改写掉 —— 那正是
    2026-09-18 / 09-24 两次前瞻观测吃到错误日期特征的机制。
    """
    other = _write(cache_dir, "2026-09-29", value=9.0)
    before = other.read_bytes()

    def fake_worker(instruments, dates, kernels=10, verbose=True):
        for d in dates:
            _write(cache_dir, d, value=1.0)

    monkeypatch.setattr(fmod, "_compute_quarter_subprocess", fake_worker)
    out = fmod.compute_features(SYMS, [pd.Timestamp("2026-09-18")],
                                cache=False, verbose=False)

    assert other.read_bytes() == before, "cache=False 改动了别的日期的缓存"
    assert not out[pd.Timestamp("2026-09-18")].empty
    assert (out[pd.Timestamp("2026-09-18")].to_numpy() == 1.0).all()
    # 09-29 的读者仍然拿到它自己的数据
    df29 = fmod.read_feature_cache(pd.Timestamp("2026-09-29"))
    assert (df29.to_numpy() == 9.0).all()


def test_same_month_dates_do_not_overwrite_each_other(cache_dir, monkeypatch):
    """同一次调用请求同月两天 -> 两个文件，各自内容正确。"""
    def fake_worker(instruments, dates, kernels=10, verbose=True):
        for d in dates:
            _write(cache_dir, d, value=float(d.day))

    monkeypatch.setattr(fmod, "_compute_quarter_subprocess", fake_worker)
    a, b = pd.Timestamp("2026-09-18"), pd.Timestamp("2026-09-29")
    out = fmod.compute_features(SYMS, [a, b], cache=False, verbose=False)

    assert (out[a].to_numpy() == 18.0).all()
    assert (out[b].to_numpy() == 29.0).all()


# ---------------------------------------------------------------------------
# 3. 非交易日不落盘
# ---------------------------------------------------------------------------

def test_no_file_is_written_when_there_is_no_data(cache_dir, monkeypatch):
    """非交易日 / 当天没有行情 -> 不写文件，也不返回编造的数据。"""
    _no_worker(monkeypatch)
    d = pd.Timestamp("2026-09-20")            # 周日
    out = fmod.compute_features(SYMS, [d], cache=False, verbose=False)

    assert out[d].empty
    assert not list(cache_dir.glob("feature_2026-09-20.parquet"))


def test_worker_template_enforces_the_contract():
    """worker 是生成出来的子进程源码，单元测试摸不到 —— 对它的**源码契约**
    做结构化断言：按日期命名、空切片不落盘、写入 feature_date。"""
    t = fmod._QUARTER_WORKER
    assert '("feature_date", "")' in t
    assert '"feature_" + d.strftime("%Y-%m-%d") + ".parquet"' in t
    assert "if len(sub) == 0:" in t
    # 旧的按月命名必须彻底消失（注意 %Y-%m-%d 里也含 %Y-%m，要按整段匹配）
    assert "strftime('%Y-%m')" not in t
    assert 'strftime("%Y-%m")' not in t


# ---------------------------------------------------------------------------
# 4. 回放前视保护（C3 的硬测试）
# ---------------------------------------------------------------------------

def test_replay_never_uses_a_feature_date_after_the_replay_date(cache_dir,
                                                                monkeypatch):
    """回放 T 时，用到的一切特征日期必须 <= T。

    这里把 09-29 的数据放在 09-18 的文件里 —— 正是线上真实发生过的情况。
    回放 2026-09-18 绝不能拿到 2026-09-29 的横截面。
    """
    _write(cache_dir, "2026-09-18", value=7.0, claimed_date="2026-09-29")
    _no_worker(monkeypatch)

    used = []
    real_read = fmod.read_feature_cache

    def spy(date):
        df = real_read(date)
        if df is not None:
            used.append(pd.Timestamp(date))
        return df

    monkeypatch.setattr(fmod, "read_feature_cache", spy)
    T = pd.Timestamp("2026-09-18")
    out = fmod.compute_features(SYMS, [T], cache=True, verbose=False)

    assert all(u <= T for u in used), f"回放到 {T} 却用了 {used}"
    assert out[T].empty


def test_repo_has_no_manual_feature_cache_path_construction():
    """仓库源码里不得再出现手工拼接的按月特征缓存路径。

    缓存契约只在 features.py 里实现；任何一处旁路自拼路径，都会让"日期
    校验"变成摆设（修复前 scripts/ 下就有两处）。
    """
    root = Path(__file__).resolve().parents[2]
    skip_files = {Path(fmod.__file__).resolve(), Path(__file__).resolve()}
    offenders = []
    for p in root.glob("**/*.py"):
        if set(p.parts) & {".venv", "site-packages", "experiments", "data",
                           "node_modules", "build", "dist"}:
            continue
        if p.resolve() in skip_files:
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        if ("derived" in txt and "features" in txt
                and ("strftime('%Y-%m')" in txt or 'strftime("%Y-%m")' in txt)):
            offenders.append(str(p.relative_to(root)))
    assert offenders == [], f"仍有手工按月拼接的特征缓存路径：{offenders}"
