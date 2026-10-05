# -*- coding: utf-8 -*-
"""S3_v1 vs S3_v2 —— 特征重要性、逐年 IC、回测与选股重合度

    python scripts/news/compare_s3_versions.py

只读两个 run 目录里已经落盘的产物（不重训、不改模型）：

    experiments/news/strategy/           S3_v1（生产，冻结）
    experiments/news/strategy_s3_v2/     S3_v2（修好新闻采集后重训）

回答 spec §十二~§十五 的问题：换掉新闻数据之后，

1. 新闻特征在模型里的权重到底变了没有（split / gain 占比）；
2. 逐年的模型排序能力（rank IC）有没有变化；
3. 冻结测试段（2024-2025）的回测指标——收益、夏普、回撤、换手、Calmar；
4. 两个版本每月选出来的股票重合多少（Top-K overlap）。

**纪律**：2024-2025 是冻结测试集，只在最后评估一次；本脚本只读数、
不参与任何选择。S3_v1 的产物是冻结件，绝不覆盖。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS = {
    "S3_v1": PROJECT_ROOT / "experiments" / "news" / "strategy",
    "S3_v2": PROJECT_ROOT / "experiments" / "news" / "strategy_s3_v2",
}
OUT = PROJECT_ROOT / "reports" / "s3_v1_vs_v2_comparison.md"


def _need(d: Path, name: str) -> Path:
    p = d / name
    if not p.exists():
        raise FileNotFoundError(f"缺少 {p}（S3_v2 还没训练？）")
    return p


# --- 逐年回测指标（从已落盘的 nav 切片，不重跑引擎）-------------------------

def yearly_metrics(nav: pd.Series, turnover: pd.Series = None) -> list:
    out = []
    for y, g in nav.groupby(pd.DatetimeIndex(nav.index).year):
        g = g.dropna()
        if len(g) < 20:
            continue
        ret = float(g.iloc[-1] / g.iloc[0] - 1.0)
        dr = g.pct_change().dropna()
        vol = float(dr.std() * np.sqrt(252)) if len(dr) else np.nan
        sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) \
            if len(dr) and dr.std() else np.nan
        dd = float((g / g.cummax() - 1.0).min())
        row = {"year": int(y), "return": ret, "vol": vol, "sharpe": sharpe,
               "mdd": dd, "calmar": ret / abs(dd) if dd else np.nan}
        if turnover is not None:
            t = turnover[pd.DatetimeIndex(turnover.index).year == y]
            row["turnover"] = float(t.sum()) if len(t) else np.nan
        out.append(row)
    return out


def model_rank_ic(preds: pd.DataFrame) -> list:
    """逐年 rank IC（Spearman），以及正向比例。"""
    out = []
    p = preds.copy()
    p["year"] = pd.DatetimeIndex(p["date"]).year
    for y, g in p.groupby("year"):
        ics = []
        for _, gg in g.groupby("date"):
            if len(gg) < 30:
                continue
            ics.append(gg["prediction"].rank().corr(gg["label"].rank()))
        ics = [i for i in ics if not np.isnan(i)]
        if not ics:
            continue
        out.append({"year": int(y), "n_dates": len(ics),
                    "rank_ic": float(np.mean(ics)),
                    "icir": float(np.mean(ics) / np.std(ics))
                    if np.std(ics) else np.nan,
                    "pos": float(np.mean(np.array(ics) > 0))})
    return out


# --- 特征重要性（§十五）-----------------------------------------------------

def importance(run_dir: Path) -> pd.DataFrame:
    """LightGBM 的 split 次数与 gain，按新闻特征 / 其他分列。"""
    import lightgbm as lgb

    booster = lgb.Booster(model_file=str(run_dir / "model.txt"))
    names = booster.feature_name()
    gain = booster.feature_importance(importance_type="gain")
    split = booster.feature_importance(importance_type="split")
    return pd.DataFrame({"feature": names, "gain": gain, "split": split})


def news_weight(df: pd.DataFrame, news_features: list) -> dict:
    m = df["feature"].isin(news_features)
    g_all, s_all = df["gain"].sum(), df["split"].sum()
    return {
        "features": int(m.sum()),
        "gain_share": float(df.loc[m, "gain"].sum() / g_all) if g_all else 0.0,
        "split_share": float(df.loc[m, "split"].sum() / s_all) if s_all else 0.0,
        "top": df[m].sort_values("gain", ascending=False)[
            ["feature", "gain", "split"]].to_dict("records"),
    }


# --- Top-K 重合度 -----------------------------------------------------------

def topk_sets(run_dir: Path, top_k: int) -> dict:
    p = _need(run_dir, "monthly_predictions.parquet")
    df = pd.read_parquet(p)
    out = {}
    for d, g in df.groupby("date"):
        out[pd.Timestamp(d)] = set(g.nlargest(top_k, "prediction")["symbol"])
    return out


def overlap(a: dict, b: dict, top_k: int) -> dict:
    common = sorted(set(a) & set(b))
    if not common:
        return {"n_dates": 0}
    vals = [len(a[d] & b[d]) / top_k for d in common]
    return {"n_dates": len(common), "mean_overlap": float(np.mean(vals)),
            "min": float(np.min(vals)), "max": float(np.max(vals)),
            "identical_dates": int(sum(v == 1.0 for v in vals))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=20)
    args = ap.parse_args()

    if not RUNS["S3_v2"].exists():
        raise SystemExit(f"S3_v2 还没训练：{RUNS['S3_v2']} 不存在")

    res = {}
    for name, d in RUNS.items():
        _need(d, "nav.parquet")
        nav = pd.read_parquet(d / "nav.parquet")["nav"]
        nav.index = pd.to_datetime(nav.index)
        turn = None
        if (d / "turnover.parquet").exists():
            turn = pd.read_parquet(d / "turnover.parquet")["turnover"]
            turn.index = pd.to_datetime(turn.index)
        preds = pd.read_parquet(_need(d, "predictions.parquet"))
        preds["date"] = pd.to_datetime(preds["date"])
        summ = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        res[name] = {
            "dir": str(d.relative_to(PROJECT_ROOT)),
            "nav": nav, "turnover": turn, "preds": preds,
            "summary": summ,
            "yearly": yearly_metrics(nav, turn),
            "yearly_ic": model_rank_ic(preds),
            "importance": importance(d),
            "features": summ["features"],
            "news_features": [f for f in summ["features"]
                              if f in _news_names()],
        }
        res[name]["news_weight"] = news_weight(res[name]["importance"],
                                               res[name]["news_features"])

    ov = overlap(topk_sets(RUNS["S3_v1"], args.top_k),
                 topk_sets(RUNS["S3_v2"], args.top_k), args.top_k)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(res, ov, args.top_k), encoding="utf-8")
    print(f"wrote {OUT}")
    for name in ("S3_v1", "S3_v2"):
        w = res[name]["news_weight"]
        print(f"  {name}: 新闻特征 {w['features']} 个 / split {w['split_share']:.2%} "
              f"/ gain {w['gain_share']:.2%}")
    print(f"  Top-{args.top_k} 月均重合 {ov.get('mean_overlap', float('nan')):.1%}")
    return 0


def _news_names() -> set:
    from factors.registry import FACTOR_REGISTRY

    return {n for n, m in FACTOR_REGISTRY.items() if m["category"] == "news"}


def _fmt(v, pct=False, nd=4):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:.1%}" if pct else f"{v:.{nd}f}"


def render(res: dict, ov: dict, top_k: int) -> str:
    L = ["# S3_v1 vs S3_v2 — 修好新闻采集之后，模型到底变了什么", "",
         "> 生成：`python scripts/news/compare_s3_versions.py`", "",
         "| | S3_v1 | S3_v2 |", "|---|---|---|",
         "| 新闻数据 | `news_events`（SSE 只含定期报告） | "
         "`news_events_v2`（SSE 全量公告） |",
         "| 产出目录 | `experiments/news/strategy/` | "
         "`experiments/news/strategy_s3_v2/` |", "",
         "**2024-2025 是冻结测试集**，本页只做一次最终评估，不参与任何选择。",
         "", "---", ""]

    # 1. 特征集
    L += ["## 1. 特征集", ""]
    for name in ("S3_v1", "S3_v2"):
        f = res[name]["features"]
        n = res[name]["news_features"]
        L += [f"**{name}**（{len(f)} 个自定义特征，其中新闻 {len(n)} 个）：",
              "", "```", ", ".join(f), "```", ""]
    L += ["> 非新闻特征两版完全一致 —— 只换了新闻。", "", "---", ""]

    # 2. 新闻特征权重
    L += ["## 2. 新闻特征在模型里的权重", "",
          "| | S3_v1 | S3_v2 |", "|---|---|---|"]
    for key, label in (("split_share", "分裂次数占比"), ("gain_share", "增益占比")):
        a = res["S3_v1"]["news_weight"][key]
        b = res["S3_v2"]["news_weight"][key]
        L.append(f"| 新闻特征{label} | {a:.2%} | {b:.2%} |")
    L += ["", "各版新闻特征明细（按 gain 排序）：", ""]
    for name in ("S3_v1", "S3_v2"):
        rows = res[name]["news_weight"]["top"]
        if not rows:
            L += [f"- {name}：没有新闻特征进入模型", ""]
            continue
        L += [f"**{name}**", "", "| 特征 | gain | split |", "|---|---|---|"]
        for r in rows:
            L.append(f"| `{r['feature']}` | {r['gain']:.0f} | {r['split']} |")
        L.append("")

    # 3. 逐年模型排序能力
    L += ["---", "", "## 3. 逐年模型排序能力（rank IC）", "",
          "| 年份 | S3_v1 IC | S3_v1 ICIR | S3_v2 IC | S3_v2 ICIR |",
          "|---|---|---|---|---|"]
    years = sorted({r["year"] for n in res for r in res[n]["yearly_ic"]})
    idx = {n: {r["year"]: r for r in res[n]["yearly_ic"]} for n in res}
    for y in years:
        a, b = idx["S3_v1"].get(y), idx["S3_v2"].get(y)
        L.append(f"| {y} | {_fmt(a['rank_ic']) if a else '—'} | "
                 f"{_fmt(a['icir']) if a else '—'} | "
                 f"{_fmt(b['rank_ic']) if b else '—'} | "
                 f"{_fmt(b['icir']) if b else '—'} |")
    L += ["", "> 2022-2023 是验证期、2024-2025 是冻结测试期；"
              "2022 年之前的样本在训练集里，没有预测输出（模型只对 "
              "valid+test 出预测）。", ""]

    # 4. 回测
    L += ["---", "", "## 4. 冻结测试段回测（2024-2025）", "",
          "| 指标 | S3_v1 | S3_v2 |", "|---|---|---|"]
    keys = [("cumulative_return", "累计收益", True),
            ("annualized_return", "年化收益", True),
            ("annualized_volatility", "年化波动", True),
            ("sharpe", "夏普", False), ("max_drawdown", "最大回撤", True),
            ("calmar", "Calmar", False),
            ("win_rate_monthly", "月度胜率", True),
            ("n_trades", "成交笔数", False)]
    for k, label, pct in keys:
        a = res["S3_v1"]["summary"]["strategy_metrics"].get(k)
        b = res["S3_v2"]["summary"]["strategy_metrics"].get(k)
        L.append(f"| {label} | {_fmt(a, pct)} | {_fmt(b, pct)} |")
    if all(res[n]["turnover"] is not None for n in res):
        L.append(f"| 换手合计 | {_fmt(res['S3_v1']['turnover'].sum(), True)} | "
                 f"{_fmt(res['S3_v2']['turnover'].sum(), True)} |")
    L += ["", "### 逐年", "",
          "| 年份 | 策略 | 收益 | 波动 | 夏普 | 最大回撤 | Calmar | 换手 |",
          "|---|---|---|---|---|---|---|---|"]
    for y in years:
        for name in ("S3_v1", "S3_v2"):
            r = next((x for x in res[name]["yearly"] if x["year"] == y), None)
            if r is None:
                continue
            L.append(f"| {y} | {name} | {_fmt(r['return'], True)} | "
                     f"{_fmt(r['vol'], True)} | {_fmt(r['sharpe'])} | "
                     f"{_fmt(r['mdd'], True)} | {_fmt(r['calmar'])} | "
                     f"{_fmt(r.get('turnover'), True)} |")
    L.append("")

    # 5. 选股重合度
    L += ["---", "", f"## 5. 每月 Top-{top_k} 选股重合度", ""]
    if ov.get("n_dates"):
        L += [f"共同调仓日 **{ov['n_dates']}** 个，平均重合 "
              f"**{ov['mean_overlap']:.1%}**（最少 {ov['min']:.1%}，"
              f"最多 {ov['max']:.1%}），完全一致的月份 {ov['identical_dates']} 个。",
              "", "> 重合度高说明两个版本选出来的股票差别不大；"
                  "重合度低说明新闻特征确实改变了排序。", ""]
    else:
        L += ["（两个版本没有共同的调仓日）", ""]

    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
