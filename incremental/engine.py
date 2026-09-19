# -*- coding: utf-8 -*-
"""Walk-forward 配对引擎：M0（既有特征）vs M1（既有特征 + 单个候选因子）。

设计要点
--------
- **严格时间滚动**（§4）：每折 train_end < valid_start，验证年份逐年前推。
  禁止 2018-2023 一次性训练+验证——那等于对整个 validation 期过拟合。
- **标签越界保护**：验证年最后一个信号日的 20 日前瞻收益会落到下一年
  （2023-12-29 → 2024-01），用它就是把 2024 数据带进选择。越界信号日剔除。
- **严格配对**：M0 与 M1 用同一批训练行、同一模型参数、同一种子、同一标签、
  同一股票池、同一调仓日。唯一差别是 M1 多一列候选因子。
- **固定迭代、关闭子采样**（见 config 注释）：early stopping 需要验证集，
  而验证集正是被评估期；feature_fraction < 1 会让 M0/M1 的差异混入与
  特征个数相关的抽样噪声。两者都关掉，DeltaIC 才完全来自新增那一列。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .windows import assert_selection_window


# ---------------------------------------------------------------------------
# folds
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Fold:
    name: str
    train_start: str
    train_end: str
    valid_start: str
    valid_end: str
    train_dates: List[pd.Timestamp] = field(default_factory=list)
    valid_dates: List[pd.Timestamp] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "train": [self.train_start, self.train_end],
            "valid": [self.valid_start, self.valid_end],
            "n_train_dates": len(self.train_dates),
            "n_valid_dates": len(self.valid_dates),
            "valid_dates": [str(d.date()) for d in self.valid_dates],
        }


def label_safe_dates(dates: Sequence[pd.Timestamp], calendar: pd.DatetimeIndex,
                     horizon: int, fold_end: pd.Timestamp) -> List[pd.Timestamp]:
    """Drop signal dates whose `horizon`-day forward label crosses fold_end.

    2023-12-29 的 20 日前瞻收益要用到 2024 年的价格；留着它就等于让
    2024 的数据进入选择路径。
    """
    cal = pd.DatetimeIndex(calendar)
    pos = {d: i for i, d in enumerate(cal)}
    out = []
    for d in dates:
        i = pos.get(pd.Timestamp(d))
        if i is None or i + horizon >= len(cal):
            continue
        if cal[i + horizon] <= fold_end:
            out.append(pd.Timestamp(d))
    return out


def build_folds(cfg: dict, calendar: pd.DatetimeIndex,
                rebalance_dates: Sequence[pd.Timestamp],
                horizon: int) -> List[Fold]:
    """Build the walk-forward folds from config. Selection window only."""
    wf = cfg["factor_selection_v2"]["walk_forward"]
    reb = pd.DatetimeIndex(sorted(rebalance_dates))
    folds = []
    for spec in wf["folds"]:
        ts, te = (pd.Timestamp(x) for x in spec["train"])
        vs, ve = (pd.Timestamp(x) for x in spec["valid"])
        if te >= vs:
            raise ValueError(f"{spec['name']}: train_end {te.date()} 必须 "
                             f"早于 valid_start {vs.date()}")
        train = [d for d in reb if ts <= d <= te]
        valid = [d for d in reb if vs <= d <= ve]
        if wf.get("drop_labels_crossing_fold_end", True):
            valid = label_safe_dates(valid, calendar, horizon, ve)
        assert_selection_window(train + valid, f"fold {spec['name']}")
        folds.append(Fold(spec["name"], str(ts.date()), str(te.date()),
                          str(vs.date()), str(ve.date()), train, valid))
    return folds


# ---------------------------------------------------------------------------
# design matrices
# ---------------------------------------------------------------------------

class PanelStore:
    """按调仓日提供设计矩阵：Alpha158 + 自定义因子 + 标签 + 股票池。

    features: {date: DataFrame(symbol × feature)}  Alpha158（已 flatten）
    custom:   {date: DataFrame(symbol × factor)}  自定义因子（已 rank 归一）
    labels:   {date: Series(symbol -> 20 日前瞻收益)}
    universes:{date: [symbol, ...]}
    """

    def __init__(self, features: Dict, custom: Dict, labels: Dict,
                 universes: Dict):
        self.features = features
        self.custom = custom
        self.labels = labels
        self.universes = universes

    def matrix(self, date: pd.Timestamp, cols: Sequence[str],
               ) -> Optional[pd.DataFrame]:
        """Rows = universe members at `date`; columns = cols + ['label'].

        候选因子若在当日缺列（未选入 custom）则返回 None，调用方跳过。
        """
        univ = self.universes.get(date)
        if not univ:
            return None
        feat = self.features.get(date)
        cust = self.custom.get(date)
        lab = self.labels.get(date)
        if lab is None:
            return None
        parts = []
        if feat is not None and not feat.empty:
            parts.append(feat)
        if cust is not None and not cust.empty:
            parts.append(cust)
        if not parts:
            return None
        m = pd.concat(parts, axis=1)
        missing = [c for c in cols if c not in m.columns]
        if missing:
            return None
        m = m.reindex(index=univ)
        m = m[list(cols)].copy()
        m["label"] = lab.reindex(m.index)
        return m.dropna(subset=["label"])

    def stack(self, dates: Sequence[pd.Timestamp], cols: Sequence[str],
              ) -> pd.DataFrame:
        frames = []
        for d in dates:
            m = self.matrix(d, cols)
            if m is None or m.empty:
                continue
            m = m.copy()
            m["date"] = d
            frames.append(m)
        if not frames:
            return pd.DataFrame(columns=list(cols) + ["label", "date"])
        return pd.concat(frames, ignore_index=True)


def build_custom_frames(panels: Dict[str, pd.DataFrame],
                        universes: Dict[pd.Timestamp, list],
                        dates: Sequence[pd.Timestamp],
                        names: Sequence[str]) -> Dict[pd.Timestamp, pd.DataFrame]:
    """Per-date cross-sectional ranks of the custom factors.

    **这一处出过两次同类 bug**（step9 的 rank 轴、本驱动里的
    `normalize_panel(..., "rank")`）：面板是「日期 × 股票」，某一天的切片
    是「股票」为行、单列，`DataFrame.rank(axis=1)` 会去**跨列**排序 ——
    单列时每行都得到 1.0，整列退化成常数。模型看不到任何变化，
    DeltaIC 会精确等于 0，看起来像"这个因子没用"，其实是特征没进去。

    所以这里显式对 **Series** 调 `rank()`（沿股票方向），不用 normalize_panel。
    """
    out = {}
    for d in dates:
        univ = universes.get(d)
        if not univ:
            continue
        cols = []
        for n in names:
            panel = panels.get(n)
            if panel is None or d not in panel.index:
                continue
            x = panel.loc[d].reindex(univ)
            cols.append(x.rank(pct=True, method="average").rename(n))
        if cols:
            out[d] = pd.concat(cols, axis=1)
    return out


# ---------------------------------------------------------------------------
# fit / predict
# ---------------------------------------------------------------------------

def fit_predict(store: PanelStore, fold: Fold, cols: Sequence[str],
                cfg: dict) -> dict:
    """Train on fold.train_dates, predict on fold.valid_dates.

    返回 {prediction: DataFrame(date,symbol,prediction), model, importance,
          n_train_rows}。
    """
    from personal_quant.strategy.model import AlphaModel

    mcfg = cfg["factor_selection_v2"]["model"]
    params = dict(mcfg["params"])
    params["n_estimators"] = int(mcfg["fixed_num_boost_round"])
    if not mcfg.get("early_stopping", False):
        params.pop("early_stopping_rounds", None)

    train = store.stack(fold.train_dates, cols)
    if train.empty:
        raise RuntimeError(f"{fold.name}: 训练集为空")
    model = AlphaModel(params, seed=int(mcfg["seed"]))
    # 不传 valid：AlphaModel.fit 只在给了 valid 且 early_stopping_rounds
    # 存在时才启用早停，这里两者都没有 → 固定迭代，无泄漏。
    model.fit(train[list(cols)], train["label"])

    rows = []
    for d in fold.valid_dates:
        m = store.matrix(d, cols)
        if m is None or m.empty:
            continue
        pred = model.predict(m[list(cols)])
        rows.append(pd.DataFrame({
            "date": d, "symbol": m.index,
            "prediction": pred, "label": m["label"].to_numpy()}))
    pred_df = (pd.concat(rows, ignore_index=True) if rows else
               pd.DataFrame(columns=["date", "symbol", "prediction", "label"]))

    gain = np.asarray(model.model.feature_importance("gain"), dtype=float)
    importance = pd.Series(gain, index=list(cols), name="gain")
    return {"prediction": pred_df, "model": model,
            "model_version": fold.name, "importance": importance,
            "n_train_rows": int(len(train))}


# ---------------------------------------------------------------------------
# DeltaIC
# ---------------------------------------------------------------------------

def _ic_one(g: pd.DataFrame) -> dict:
    if len(g) < 10 or g["label"].std() == 0:
        return {}
    if g["prediction_0"].std() == 0 or g["prediction_1"].std() == 0:
        return {}
    return {
        "n": len(g),
        "ic0": g["prediction_0"].corr(g["label"]),
        "ic1": g["prediction_1"].corr(g["label"]),
        "rank_ic0": g["prediction_0"].corr(g["label"], method="spearman"),
        "rank_ic1": g["prediction_1"].corr(g["label"], method="spearman"),
    }


def delta_ic_table(pred0: pd.DataFrame, pred1: pd.DataFrame) -> pd.DataFrame:
    """Per-date paired IC / RankIC and their differences.

    pred0/pred1 必须覆盖同一批 (date, symbol)——配对比较的前提。
    """
    # 只取 pred1 的预测列：两张表都带 label，整表 merge 会变成
    # label_0 / label_1，后面按 "label" 取就直接 KeyError。
    m = pred0.merge(pred1[["date", "symbol", "prediction"]],
                    on=["date", "symbol"], suffixes=("_0", "_1"))
    if m.empty:
        return pd.DataFrame(columns=["date", "n", "ic0", "ic1", "delta_ic",
                                     "rank_ic0", "rank_ic1", "delta_rank_ic"])
    rows = []
    for d, g in m.groupby("date"):
        r = _ic_one(g)
        if not r:
            continue
        r["date"] = d
        r["delta_ic"] = r["ic1"] - r["ic0"]
        r["delta_rank_ic"] = r["rank_ic1"] - r["rank_ic0"]
        rows.append(r)
    out = pd.DataFrame(rows)
    return out.sort_values("date").reset_index(drop=True) if len(out) else \
        out.reindex(columns=["date", "n", "ic0", "ic1", "delta_ic",
                             "rank_ic0", "rank_ic1", "delta_rank_ic"])


# ---------------------------------------------------------------------------
# prediction impact (§8/§22)
# ---------------------------------------------------------------------------

def prediction_impact(pred0: pd.DataFrame, pred1: pd.DataFrame,
                      top_k: int = 20) -> dict:
    """候选因子对模型输出的实际影响。

    如果预测几乎不变（corr ≈ 1、top-20 名单不动），说明这个候选对模型
    没有实际作用——不管它的 DeltaIC 是多少。
    """
    m = pred0.merge(pred1[["date", "symbol", "prediction"]],
                    on=["date", "symbol"], suffixes=("_0", "_1"))
    if m.empty:
        return {"n_dates": 0}
    cors, dz, turns = [], [], []
    for _, g in m.groupby("date"):
        if len(g) < top_k + 1:
            continue
        a, b = g["prediction_0"], g["prediction_1"]
        if a.std() == 0 or b.std() == 0:
            continue
        cors.append(a.corr(b, method="spearman"))
        za = (a - a.mean()) / a.std()
        zb = (b - b.mean()) / b.std()
        dz.append(float((zb - za).abs().mean()))
        ta = set(g.nlargest(top_k, "prediction_0")["symbol"])
        tb = set(g.nlargest(top_k, "prediction_1")["symbol"])
        turns.append(len(ta - tb) / top_k)
    if not cors:
        return {"n_dates": 0}
    return {
        "n_dates": len(cors),
        "prediction_corr": float(np.mean(cors)),          # 截面 Spearman
        "prediction_delta": float(np.mean(dz)),           # 平均 |Δz|
        "topk_turnover": float(np.mean(turns)),           # top-K 名单换手
    }


# ---------------------------------------------------------------------------
# candidate metrics
# ---------------------------------------------------------------------------

def permutation_importance(store: PanelStore, fold: Fold, result: dict,
                           cols: Sequence[str], target: str,
                           n_shuffles: int = 20, seed: int = 0,
                           min_stocks: int = 30) -> dict:
    """打乱 target 列之后的 IC 下降（**解释用，不是 alpha 证据**，§21）。

    不重训模型：固定已拟合的模型，只把验证集上的目标列在各日期内部
    随机置换，看预测 IC 掉多少。IC 掉得多说明模型确实在用这一列。
    """
    rng = np.random.default_rng(seed)
    base_ic, perm_ic = [], []
    for d in fold.valid_dates:
        m = store.matrix(d, cols)
        if m is None or len(m) < min_stocks:
            continue
        pred = result["model"].predict(m[list(cols)]) if "model" in result \
            else None
        if pred is None:
            continue
        y = m["label"].to_numpy()
        base_ic.append(pd.Series(pred).corr(pd.Series(y), method="spearman"))
        drops = []
        for _ in range(n_shuffles):
            mm = m.copy()
            mm[target] = rng.permutation(mm[target].to_numpy())
            p = result["model"].predict(mm[list(cols)])
            drops.append(pd.Series(p).corr(pd.Series(y), method="spearman"))
        perm_ic.append(float(np.mean(drops)))
    if not base_ic:
        return {"permutation_ic_drop": np.nan, "n_dates": 0}
    return {
        "n_dates": len(base_ic),
        "ic_base": float(np.mean(base_ic)),
        "ic_permuted": float(np.mean(perm_ic)),
        "permutation_ic_drop": float(np.mean(base_ic) - np.mean(perm_ic)),
    }


def candidate_metrics(fold_ics: Dict[str, pd.DataFrame],
                      impacts: List[dict]) -> dict:
    """Aggregate per-fold DeltaIC tables into one candidate's metrics."""
    frames = []
    per_fold = {}
    for name, ic in fold_ics.items():
        if ic is None or ic.empty:
            continue
        frames.append(ic.assign(fold=name))
        per_fold[name] = {
            "delta_ic_mean": float(ic["delta_ic"].mean()),
            "delta_rank_ic_mean": float(ic["delta_rank_ic"].mean()),
            "n_dates": int(len(ic)),
        }
    if not frames:
        return {"n_dates": 0, "per_fold": per_fold}
    allic = pd.concat(frames, ignore_index=True).sort_values("date")

    def _agg(s: pd.Series) -> dict:
        s = s.dropna()
        if s.empty:
            return {"mean": np.nan, "median": np.nan, "std": np.nan,
                    "icir": np.nan, "positive_ratio": np.nan}
        sd = s.std(ddof=0)
        return {
            "mean": float(s.mean()), "median": float(s.median()),
            "std": float(sd),
            "icir": float(s.mean() / sd) if sd > 0 else np.nan,
            "positive_ratio": float((s > 0).mean()),
        }

    d_ic = _agg(allic["delta_ic"])
    d_ric = _agg(allic["delta_rank_ic"])
    # DeltaIC 与原始 IC 不同：负的 DeltaIC 不能靠"反向使用因子"救回来
    # （LightGBM 里没法给一列特征取负号），所以只认正向增量。
    signs = [v["delta_ic_mean"] for v in per_fold.values()]
    pos_fold = sum(1 for s in signs if s > 0)
    imp = [i for i in impacts if i.get("n_dates")]
    return {
        "n_dates": int(len(allic)),
        "n_folds": len(per_fold),
        "per_fold": per_fold,
        "delta_ic_mean": d_ic["mean"], "delta_ic_median": d_ic["median"],
        "delta_ic_std": d_ic["std"], "delta_icir": d_ic["icir"],
        "delta_ic_positive_ratio": d_ic["positive_ratio"],
        "delta_rank_ic_mean": d_ric["mean"],
        "delta_rank_ic_median": d_ric["median"],
        "delta_rank_ic_std": d_ric["std"],
        "delta_rank_icir": d_ric["icir"],
        "delta_rank_ic_positive_ratio": d_ric["positive_ratio"],
        "ic0_mean": float(allic["ic0"].mean()),
        "ic1_mean": float(allic["ic1"].mean()),
        "rank_ic0_mean": float(allic["rank_ic0"].mean()),
        "rank_ic1_mean": float(allic["rank_ic1"].mean()),
        "positive_fold_ratio": float(pos_fold / len(per_fold))
        if per_fold else np.nan,
        "n_positive_folds": int(pos_fold),
        "prediction_corr": float(np.mean([i["prediction_corr"] for i in imp]))
        if imp else np.nan,
        "prediction_delta": float(np.mean([i["prediction_delta"] for i in imp]))
        if imp else np.nan,
        "topk_turnover": float(np.mean([i["topk_turnover"] for i in imp]))
        if imp else np.nan,
        "ic_series": allic,
    }
