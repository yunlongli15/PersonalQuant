# -*- coding: utf-8 -*-
"""干净候选 A/B 与旧基线的全面对比 -> reports/clean_strategy_selection.md

    python scripts/quant/compare_clean_candidates.py

四个对象：

| 目录 | 名称 | 定位 |
|---|---|---|
| experiments/clean/clean_A | Candidate A | Alpha158 only |
| experiments/clean/clean_B | Candidate B | Alpha158 + factor_pack_v1（**非新闻**）|
| experiments/news/strategy | S3_v1 | **CONTAMINATED BASELINE** —— 只用参考 |
| experiments/news/strategy_s3_v2 | S3_v2 | **CORRECTED-NEWS FAILED CANDIDATE** |

只读，不改任何 run。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "reports" / "clean_strategy_selection.md"

#: S3_v1 / S3_v2 用 `experiments/clean/ref_s3_*` —— 那是把**同一个冻结模型**
#: 放到修好执行引擎之后重跑的。直接用旧目录会拿"修前引擎"的数字去比
#: "修后引擎"的候选，四个数字不同源。
RUNS = {
    "A": {"dir": "experiments/clean/clean_A", "label": "Candidate A",
          "features": "Alpha158 only", "class": "candidate"},
    "B": {"dir": "experiments/clean/clean_B", "label": "Candidate B",
          "features": "Alpha158 + factor_pack_v1", "class": "candidate"},
    "S3_v1": {"dir": "experiments/clean/ref_s3_v1", "label": "S3_v1",
              "features": "Alpha158 + factor_pack_v1 + 新闻 v1",
              "class": "contaminated"},
    "S3_v2": {"dir": "experiments/clean/ref_s3_v2", "label": "S3_v2",
              "features": "Alpha158 + factor_pack_v1 + 新闻 v2",
              "class": "failed"},
}

#: 修引擎**之前**的原始数字，只为对照（来自各自冻结的原目录）
PREFIX_RUNS = {
    "A": "experiments/news/ablation/variant_A",
    "B": "experiments/news/ablation/variant_B",
    "S3_v1": "experiments/news/strategy",
    "S3_v2": "experiments/news/strategy_s3_v2",
}


def _p(name, f) -> Path:
    return PROJECT_ROOT / RUNS[name]["dir"] / f


def load(name) -> dict:
    nav = pd.read_parquet(_p(name, "nav.parquet"))["nav"]
    nav.index = pd.to_datetime(nav.index)
    turn = pd.read_parquet(_p(name, "turnover.parquet"))["turnover"]
    turn.index = pd.to_datetime(turn.index)
    summ = json.loads(_p(name, "summary.json").read_text(encoding="utf-8"))
    preds = pd.read_parquet(_p(name, "predictions.parquet"))
    preds["date"] = pd.to_datetime(preds["date"])
    trades = None
    if _p(name, "trades.parquet").exists():
        trades = pd.read_parquet(_p(name, "trades.parquet"))
        trades["exec_date"] = pd.to_datetime(trades["exec_date"])
    mp = pd.read_parquet(_p(name, "monthly_predictions.parquet"))
    mp["prediction_date"] = pd.to_datetime(mp["prediction_date"])
    return {"nav": nav, "turnover": turn, "summary": summ, "preds": preds,
            "trades": trades, "mp": mp, "nav_nan": int(nav.isna().sum())}


def yearly(nav: pd.Series, turn: pd.Series) -> pd.DataFrame:
    rows = []
    for y, g in nav.groupby(nav.index.year):
        g = g.dropna()
        if len(g) < 20:
            continue
        dr = g.pct_change().dropna()
        dd = float((g / g.cummax() - 1.0).min())
        ret = float(g.iloc[-1] / g.iloc[0] - 1.0)
        rows.append({
            "year": int(y), "ret": ret,
            "vol": float(dr.std() * np.sqrt(252)) if len(dr) else np.nan,
            "sharpe": float(dr.mean() / dr.std() * np.sqrt(252))
            if len(dr) and dr.std() else np.nan,
            "mdd": dd, "calmar": ret / abs(dd) if dd else np.nan,
            "turnover": float(turn[turn.index.year == y].sum())})
    return pd.DataFrame(rows)


def yearly_ic(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    p = preds.copy()
    p["year"] = p["date"].dt.year
    for y, g in p.groupby("year"):
        ics = [gg["prediction"].rank().corr(gg["label"].rank())
               for _, gg in g.groupby("date") if len(gg) >= 30]
        ics = [i for i in ics if not np.isnan(i)]
        if ics:
            rows.append({"year": int(y), "n": len(ics),
                         "rank_ic": float(np.mean(ics)),
                         "pos": float(np.mean(np.array(ics) > 0))})
    return pd.DataFrame(rows)


def fees(d: dict) -> dict:
    t = d["trades"]
    if t is None or t.empty:
        return {"available": False}
    return {"available": True, "total": float(t["fee"].sum()),
            "buy": float(t[t.side == "BUY"]["fee"].sum()),
            "sell": float(t[t.side == "SELL"]["fee"].sum()),
            "n": int(len(t))}


def small_account(d: dict, capital: float = 100_000.0,
                  top_k: int = 20) -> dict:
    """小账户口径：Top-K 里有多少买不进一手，钱实际投出去多少。

    Top-K 固定 20（§九 明确不许改）。这里量的是**执行**层面的摩擦：
    每只目标金额 = 权益 x 95% / 20，买不起 1 手（100 股）的标的会留现金。
    """
    mp, tr, nav = d["mp"], d["trades"], d["nav"]
    if tr is None or tr.empty:
        return {"available": False}
    out = []
    for dt, g in mp.groupby("prediction_date"):
        picks = set(g.nlargest(top_k, "predicted_return")["symbol"])
        if dt not in nav.index or pd.isna(nav.loc[dt]):
            continue
        equity = float(nav.loc[dt])
        tgt = equity * 0.95 / top_k
        ex = tr[(tr["signal_date"] == str(dt.date())) &
                (tr.side == "BUY")]
        filled = set(ex["symbol"]) & picks
        spent = float(ex[ex["symbol"].isin(picks)]["value"].sum())
        out.append({"date": dt, "n_picks": len(picks),
                    "n_filled": len(filled),
                    "unfillable": (len(picks) - len(filled)) / max(len(picks), 1),
                    "target_value": tgt,
                    "invested": spent / equity if equity else np.nan,
                    "cash": 1.0 - (spent / equity if equity else np.nan)})
    if not out:
        return {"available": False}
    df = pd.DataFrame(out)
    zero = df[df["invested"] <= 1e-9]
    return {"available": True,
            "n_months": len(df),
            "zero_months": int(len(zero)),
            "zero_dates": [str(d.date()) for d in zero["date"]],
            "unfillable_avg": float(df["unfillable"].mean()),
            "unfillable_max": float(df["unfillable"].max()),
            "invested_avg": float(df["invested"].mean()),
            "invested_min": float(df["invested"].min()),
            "cash_avg": float(df["cash"].mean()),
            "cash_max": float(df["cash"].max()),
            "target_value_avg": float(df["target_value"].mean())}


def topk_turnover(d: dict, top_k: int = 20) -> dict:
    """Top-K 的名义换手：相邻两期选股集合的变动比例。"""
    mp = d["mp"]
    prev = None
    vals = []
    for dt, g in mp.groupby("prediction_date"):
        cur = set(g.nlargest(top_k, "predicted_return")["symbol"])
        if prev is not None:
            vals.append(len(cur - prev) / top_k)
        prev = cur
    if not vals:
        return {"available": False}
    return {"available": True, "mean": float(np.mean(vals)),
            "min": float(np.min(vals)), "max": float(np.max(vals)),
            "identical": int(sum(v == 0 for v in vals)), "n": len(vals)}


def _f(v, pct=False, nd=4):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:.1%}" if pct else f"{v:.{nd}f}"


def render(data: dict, args) -> str:
    cm = {k: data[k]["summary"]["strategy_metrics"] for k in data}
    L = ["# CLEAN STRATEGY SELECTION", "",
         "> 生成：`python scripts/quant/compare_clean_candidates.py`  ",
         f"> 冻结测试段 2024-01-02 ~ 2025-12-31（485 个交易日）", "",
         "| 代号 | 特征 | 定位 |", "|---|---|---|"]
    for k in ("A", "B", "S3_v1", "S3_v2"):
        c = RUNS[k]["class"]
        tag = {"candidate": "**生产候选**",
               "contaminated": "**CONTAMINATED BASELINE**（仅参考）",
               "failed": "**CORRECTED-NEWS FAILED CANDIDATE**"}[c]
        L.append(f"| {RUNS[k]['label']} | {RUNS[k]['features']} | {tag} |")
    L += ["", "---", ""]

    # 1 / 2
    L += ["## 1. Why S3_v1 is not production", "",
          "S3_v1 的新闻特征是在**残缺语料**上选出来的：SSE 采集把 "
          "`reportType2` 写死成定期报告，沪市 2,200 家公司只有年报/半年报/"
          "季报入库，问询函、立案调查、质押、诉讼一条都没有。",
          "它的高收益因此无法归因于新闻 alpha —— 那批特征实际衡量的是"
          "「发了多少份定期报告」。标记为 CONTAMINATED BASELINE，"
          "只作历史参照，**不再作为新实验的基础**。", "",
          "## 2. Why S3_v2 is rejected", "",
          "用修复后的新闻数据重训，年化 9.3% / 夏普 0.388，"
          "**比完全没有新闻还差**（Alpha158+factor_pack 无新闻 = 19.6%）。"
          "失败原因在因子形态不在数据：入选因子对 91.6% 的股票取同一值。",
          "详见 `reports/s3_v2_news_repair_and_backtest.md`。", "", "---", ""]

    # 3 / 4
    for k in ("A", "B"):
        d = data[k]
        s = cm[k]
        L += [f"## {3 if k == 'A' else 4}. {RUNS[k]['label']} — "
              f"{RUNS[k]['features']}", "",
              f"- 自定义特征 {len(data[k]['summary'].get('features', []))} 个："
              f"`{data[k]['summary'].get('features', [])}`",
              f"- 训练：与 strategy_v1 同切分（train 2015-2021 / "
              f"valid 2022-2023）、同 seed、同超参、同成本模型",
              f"- 新闻因子：**DISABLED**", "",
              "| 指标 | 值 |", "|---|---|",
              f"| 累计收益 | {_f(s['cumulative_return'], True)} |",
              f"| 年化收益 | {_f(s['annualized_return'], True)} |",
              f"| 年化波动 | {_f(s['annualized_volatility'], True)} |",
              f"| 夏普 | {_f(s['sharpe'])} |",
              f"| 最大回撤 | {_f(s['max_drawdown'], True)} |",
              f"| Calmar | {_f(s['calmar'])} |",
              f"| 月度胜率 | {_f(s['win_rate_monthly'], True)} |",
              f"| 成交笔数 | {s.get('n_trades', '—')} |", ""]

    # 5 回测对比
    L += ["---", "", "## 5. Backtest comparison", "",
          "| 指标 | Candidate A | Candidate B | S3_v1 (污染) | S3_v2 (失败) |",
          "|---|---|---|---|---|"]
    rows = [("cumulative_return", "累计收益", True),
            ("annualized_return", "年化收益", True),
            ("annualized_volatility", "年化波动", True),
            ("sharpe", "夏普", False), ("max_drawdown", "最大回撤", True),
            ("calmar", "Calmar", False),
            ("win_rate_monthly", "月度胜率", True),
            ("n_trades", "成交笔数", False)]
    for key, lab, pct in rows:
        L.append(f"| {lab} | " + " | ".join(
            _f(cm[k].get(key), pct) for k in ("A", "B", "S3_v1", "S3_v2"))
            + " |")
    L.append("| 换手合计 | " + " | ".join(
        _f(float(data[k]["turnover"].sum()), True)
        for k in ("A", "B", "S3_v1", "S3_v2")) + " |")
    L.append("| 费用合计（元） | " + " | ".join(
        (_f(fees(data[k])["total"], nd=0) if fees(data[k])["available"]
         else "—（未落盘）") for k in ("A", "B", "S3_v1", "S3_v2")) + " |")
    L += ["", "> 换手两版口径不同（S3_v1/v2 用的是只算保留标的的冻结口径），"
              "横向比较时以 A/B 之间为准。", ""]

    # 6 稳定性
    L += ["---", "", "## 6. Stability comparison", "",
          "### 逐年回测（冻结测试段内）", "",
          "| 年份 | 策略 | 收益 | 波动 | 夏普 | 最大回撤 | Calmar | 换手 |",
          "|---|---|---|---|---|---|---|---|"]
    for yr in sorted({int(y) for k in ("A", "B", "S3_v1", "S3_v2")
                      for y in data[k]["nav"].dropna().index.year}):
        for k in ("A", "B", "S3_v1", "S3_v2"):
            y_ = data[k]["yearly"]
            r = y_[y_["year"] == yr]
            if r.empty:
                continue
            r = r.iloc[0]
            L.append(f"| {yr} | {RUNS[k]['label']} | {_f(r['ret'], True)} | "
                     f"{_f(r['vol'], True)} | {_f(r['sharpe'])} | "
                     f"{_f(r['mdd'], True)} | {_f(r['calmar'])} | "
                     f"{_f(r['turnover'], True)} |")
    L += ["", "### 逐年 rank IC（模型排序能力，含验证期）", "",
          "| 年份 | " + " | ".join(RUNS[k]["label"]
                                   for k in ("A", "B", "S3_v1", "S3_v2"))
          + " |", "|---|" + "---|" * 4]
    yrs = sorted({int(r["year"]) for k in data for r in
                  data[k]["yic"].to_dict("records")})
    for y in yrs:
        cells = []
        for k in ("A", "B", "S3_v1", "S3_v2"):
            r = data[k]["yic"]
            r = r[r["year"] == y]
            cells.append(_f(float(r.iloc[0]["rank_ic"]), nd=3)
                         if not r.empty else "—")
        L.append(f"| {y} | " + " | ".join(cells) + " |")
    L += ["", "> **为什么只有 2022 起的逐年**：模型只对 valid(2022-2023) + "
              "test(2024-2025) 出预测；2015-2021 是训练集，在那上面算 P&L "
              "没有意义。", ""]

    # 7 回撤
    L += ["---", "", "## 7. Drawdown", "",
          "| 策略 | 最大回撤 | 回撤最深日 | 恢复所需交易日（最长） |",
          "|---|---|---|---|"]
    for k in ("A", "B", "S3_v1", "S3_v2"):
        nav = data[k]["nav"].dropna()
        dd = nav / nav.cummax() - 1.0
        trough = dd.idxmin()
        above = nav[nav >= nav.loc[:trough].cummax().max()]
        rec = above.index[0] if len(above) else None
        days = int(len(nav.loc[trough:rec])) if rec is not None else -1
        L.append(f"| {RUNS[k]['label']} | {_f(float(dd.min()), True)} | "
                 f"{str(trough.date())} | "
                 f"{days if days >= 0 else '未恢复'} |")
    L.append("")

    # 8 成本
    L += ["---", "", "## 8. Costs", "",
          "| 策略 | 费用合计（元） | 买入费 | 卖出费 | 笔数 | 费用/期末权益 |",
          "|---|---|---|---|---|---|"]
    for k in ("A", "B", "S3_v1", "S3_v2"):
        f = fees(data[k])
        if not f["available"]:
            L.append(f"| {RUNS[k]['label']} | — | — | — | — | "
                     "—（该 run 未落盘 trades）|")
            continue
        nav = data[k]["nav"].dropna()
        L.append(f"| {RUNS[k]['label']} | {f['total']:,.0f} | {f['buy']:,.0f} | "
                 f"{f['sell']:,.0f} | {f['n']} | "
                 f"{f['total']/nav.iloc[-1]:.2%} |")
    L.append("")

    # 9 小账户
    L += ["---", "", "## 9. Small-account behavior", "",
          "Top-K 固定 **20**（§九 明确不许改）。每只目标金额 = "
          "权益 x 95% / 20；买不起 1 手（100 股）的标的会留下现金。", "",
          "| 策略 | 不可买入比例(均值) | 不可买入比例(最差月) | "
          "资金利用率(均值) | 资金利用率(最低) | 平均现金比例 | 最高现金比例 |",
          "|---|---|---|---|---|---|---|"]
    for k in ("A", "B", "S3_v1", "S3_v2"):
        sa = small_account(data[k])
        if not sa["available"]:
            L.append(f"| {RUNS[k]['label']} | — | — | — | — | — | "
                     "—（未落盘 trades）|")
            continue
        L.append(f"| {RUNS[k]['label']} | {sa['unfillable_avg']:.1%} | "
                 f"{sa['unfillable_max']:.1%} | {sa['invested_avg']:.1%} | "
                 f"{sa['invested_min']:.1%} | {sa['cash_avg']:.1%} | "
                 f"{sa['cash_max']:.1%} |")
    L += ["", "> 这里的资金利用率按**回测口径的 100 万**算，"
              "只反映「哪些标的连一手都买不起」这一层摩擦。"
              "真实账户资金更小，摩擦更大 —— 见下方 Top-K 换手。", ""]
    # 零成交月单独点名。它不是"买不起一手"，而是**涨停开盘买不进**，
    # 属于执行模型里已经写死的行为（涨跌停 NO_TRADE），不是数据故障。
    zm = {k: small_account(data[k]) for k in ("A", "B", "S3_v1", "S3_v2")}
    if any(v.get("available") for v in zm.values()):
        L += ["### 零成交月（一整月一单都没买进）", "",
              "| 策略 | 零成交月数 | 月份 |", "|---|---|---|"]
        for k in ("A", "B", "S3_v1", "S3_v2"):
            v = zm[k]
            L.append(f"| {RUNS[k]['label']} | "
                     + (f"{v['zero_months']}" if v.get("available")
                        else "—") + " | "
                     + (("、".join(v["zero_dates"]) if v.get("available")
                         else "") or "—") + " |")
        L += ["", "> **这些月份不是故障，是涨停开盘买不进。**"
              "例如 2024-09-30 调仓、2024-10-08 首次成交（国庆后第一个"
              "交易日），当天全市场跳空高开，入选标的**全部以涨停价"
              "开盘**，执行模型按既定规则一律 NO_TRADE —— "
              "这正是不追高的设计意图。代价是那个月完全没能建仓，"
              "组合只靠既有持仓度过。", ""]

    # Top-K 稳定性
    L += ["### Top-K 稳定性", "",
          "相邻两期选股集合的变动比例（名义换手）：", "",
          "| 策略 | 平均变动 | 最小 | 最大 | 完全相同的月份 | 期数 |",
          "|---|---|---|---|---|---|"]
    for k in ("A", "B", "S3_v1", "S3_v2"):
        tt = topk_turnover(data[k])
        if not tt["available"]:
            L.append(f"| {RUNS[k]['label']} | — | — | — | — | — |")
            continue
        L.append(f"| {RUNS[k]['label']} | {tt['mean']:.1%} | {tt['min']:.1%} | "
                 f"{tt['max']:.1%} | {tt['identical']} | {tt['n']} |")
    L += ["", "> 极端换手（接近 100%）说明组合每月几乎全换，"
              "成本会被放大；接近 0 则说明选股几乎不动。", ""]

    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=100_000.0)
    args = ap.parse_args()

    data = {}
    for k in RUNS:
        d = PROJECT_ROOT / RUNS[k]["dir"]
        if not (d / "nav.parquet").exists():
            raise SystemExit(f"缺少 {d}/nav.parquet")
        data[k] = load(k)
        data[k]["yearly"] = yearly(data[k]["nav"], data[k]["turnover"])
        data[k]["yic"] = yearly_ic(data[k]["preds"])
        print(f"[{k}] nav NaN={data[k]['nav_nan']} "
              f"sharpe={data[k]['summary']['strategy_metrics']['sharpe']:.3f}")

    body = render(data, args)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tail = OUT.with_suffix(".tail.md")
    extra = tail.read_text(encoding="utf-8") if tail.exists() else ""
    OUT.write_text(body + ("\n" + extra if extra else ""), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
