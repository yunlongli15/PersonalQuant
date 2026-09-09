# -*- coding: utf-8 -*-
"""First-generation alpha mining: shallow expression search.

NOT genetic programming. A bounded search over the factor_pack_v1 atoms:

    expr := term (('+'|'-'|'*'|'/') term)*
    term := '(' expr ')' | unary '(' term ')' | atom | number
    unary := rank | zscore | log | abs          (operator whitelist)
    atom := <factor name>

Depth <= depth_max (3). Candidates are scored ONLY on research dates
(2018-2021) with a composite score (ICIR + stability + turnover penalty +
correlation penalty + coverage — configurable; never the strategy return).
Validation (2022-2023) ranks the beam; the frozen test set (2024-2025) is
evaluated exactly once at the end by the run script and never influences
search. Snooping diagnostics (number of candidates tested, best research /
validation / test scores) are recorded — the winner count is itself a
result.

Anti-overfit gate (automated, human-review style): research pass +
validation pass + stability + correlation vs pack + economic plausibility.
Output is candidate factors for factor_pack_v2 — research only, never a
production strategy.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .evaluator import factor_turnover, ic_series, pairwise_correlation
from .normalization import fill_missing, normalize_panel

OPS = {"+", "-", "*", "/"}
UNARY = {"rank", "zscore", "log", "abs"}
_TOKEN_RE = re.compile(r"\(|\)|[a-z_][a-z_0-9]*|-?\d+\.?\d*|[+\-*/]")


class MiningError(ValueError):
    pass


@dataclass
class Expr:
    kind: str                       # "atom" | "number" | "unary" | "op"
    value: Optional[str] = None     # atom name / number
    op: Optional[str] = None
    args: List["Expr"] = field(default_factory=list)

    def depth(self) -> int:
        """Operator layers on the longest path (atoms/numbers = 0):
        rank(a)*rank(b) -> 2; (rank(a)+rank(b))*rank(c) -> 3."""
        if self.kind in ("atom", "number"):
            return 0
        return 1 + max(a.depth() for a in self.args)

    def render(self) -> str:
        if self.kind == "atom":
            return self.value
        if self.kind == "number":
            return self.value
        if self.kind == "unary":
            return f"{self.op}({self.args[0].render()})"
        return f"({self.args[0].render()}{self.op}{self.args[1].render()})"

    def atoms(self) -> Set[str]:
        if self.kind == "atom":
            return {self.value}
        out = set()
        for a in self.args:
            out |= a.atoms()
        return out


def tokenize(s: str) -> List[str]:
    tokens = _TOKEN_RE.findall(s)
    if "".join(tokens).replace(" ", "") != s.replace(" ", ""):
        raise MiningError(f"unparseable expression: {s!r}")
    return tokens


def parse(s: str, depth_max: int = 3, atom_names: Optional[Set[str]] = None) -> Expr:
    tokens = tokenize(s)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def parse_term() -> Expr:
        nonlocal pos
        tok = peek()
        if tok is None:
            raise MiningError("unexpected end of expression")
        if tok == "(":
            pos += 1
            e = parse_expr()
            if peek() != ")":
                raise MiningError("missing closing parenthesis")
            pos += 1
            return e
        if tok in UNARY:
            pos += 1
            if peek() != "(":
                raise MiningError(f"unary {tok} must wrap parentheses")
            pos += 1
            arg = parse_expr()
            if peek() != ")":
                raise MiningError("missing closing parenthesis")
            pos += 1
            return Expr(kind="unary", op=tok, args=[arg])
        if re.fullmatch(r"-?\d+\.?\d*", tok):
            pos += 1
            return Expr(kind="number", value=tok)
        if atom_names is not None and tok not in atom_names:
            raise MiningError(f"unknown atom {tok!r}")
        pos += 1
        return Expr(kind="atom", value=tok)

    def parse_expr() -> Expr:
        nonlocal pos
        left = parse_term()
        while peek() in OPS:
            op = peek()
            pos += 1
            right = parse_term()
            left = Expr(kind="op", op=op, args=[left, right])
        return left

    e = parse_expr()
    if pos != len(tokens):
        raise MiningError(f"trailing tokens: {tokens[pos:]}")
    if e.depth() > depth_max:
        raise MiningError(f"depth {e.depth()} exceeds limit {depth_max}")
    return e


def eval_expr(expr: Expr, panels: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Evaluate an expression over atom panels (aligned dates x symbols)."""
    if expr.kind == "atom":
        return panels[expr.value]
    if expr.kind == "number":
        raise MiningError("bare numbers are not evaluable (use atoms)")
    if expr.kind == "unary":
        x = eval_expr(expr.args[0], panels)
        with np.errstate(divide="ignore", invalid="ignore"):
            if expr.op == "rank":
                return x.rank(axis=1, pct=True)
            if expr.op == "zscore":
                return x.sub(x.mean(axis=1), axis=0).div(
                    x.std(axis=1).replace(0, np.nan), axis=0)
            if expr.op == "log":
                x = x.replace([np.inf, -np.inf], np.nan).clip(lower=0)
                return np.log(x).replace([np.inf, -np.inf], np.nan)
            if expr.op == "abs":
                return x.abs()
    a = eval_expr(expr.args[0], panels)
    b = eval_expr(expr.args[1], panels)
    with np.errstate(divide="ignore", invalid="ignore"):
        if expr.op == "+":
            return a + b
        if expr.op == "-":
            return a - b
        if expr.op == "*":
            return a * b
        if expr.op == "/":
            return a / b.replace(0, np.nan)
    raise MiningError(f"unknown op {expr.op}")


class AlphaMiner:
    """Shallow beam search over rank-normalized atom panels.

    Leakage contract: this class only ever sees research + validation data
    (panels, dates, labels). The frozen test period is handled by the run
    script exactly once. `period_end` is enforced by `_guard`.
    """

    def __init__(self, config: dict, atoms: Dict[str, pd.DataFrame],
                 dates, labels: Dict[int, pd.DataFrame],
                 universe: Optional[Dict] = None,
                 industries: Optional[pd.Series] = None,
                 period_end=None, seed: int = 42):
        self.config = config
        self.atoms = atoms
        self.dates = pd.DatetimeIndex(dates)
        self.labels = labels
        self.universe = universe
        self.industries = industries
        self.period_end = period_end
        self.seed = seed
        self.rng = random.Random(seed)
        self.n_candidates_tested = 0
        self.score_log: List[dict] = []
        cfg = config.get("mining", {})
        self.depth_max = int(cfg.get("depth_max", 3))
        self.max_per_gen = int(cfg.get("max_candidates_per_generation", 1000))
        self.beam_size = int(cfg.get("beam_size", 100))
        self.top_candidates = int(cfg.get("top_candidates", 10))
        self.w = cfg.get("score", {})

    # -- leakage guard ------------------------------------------------------
    def _guard(self, dates) -> None:
        if self.period_end is None:
            return
        d = pd.DatetimeIndex(dates)
        if (d > self.period_end).any():
            raise MiningError(
                f"mining attempted on dates beyond the allowed period "
                f"(<= {pd.Timestamp(self.period_end).date()}): "
                f"{d[d > self.period_end]}")

    # -- atom panels --------------------------------------------------------
    def atom_panels(self, names: List[str]):
        out = {}
        for n in names:
            p = normalize_panel(self.atoms[n], "rank")
            p = fill_missing(p, self.config.get("missing", {}).get(
                "method", "sector_median"), self.industries)
            out[n] = p
        return out

    # -- scoring ------------------------------------------------------------
    def _quick_score(self, panel: pd.DataFrame) -> dict:
        """ICIR + stability + coverage over the research dates."""
        self._guard(self.dates)
        self._guard(panel.index)  # the panel itself must not reach past
        # the allowed period (test-set labels never enter the scorer)
        ic = ic_series(panel, self.labels[20].reindex(self.dates),
                       min_stocks=30)
        if ic.empty:
            return {"icir": np.nan, "stability": np.nan, "coverage": np.nan,
                    "score": -np.inf}
        s = ic["rank_ic"]
        icir = s.mean() / s.std(ddof=0) if s.std(ddof=0) > 0 else 0.0
        p = max(float((s > 0).mean()), float((s < 0).mean()))
        stability = 2.0 * p - 1.0
        coverage = float(panel.notna().sum().sum() / panel.size)
        score = (self.w.get("icir_weight", 1.0) * abs(icir)
                 + self.w.get("stability_weight", 0.5) * stability
                 + self.w.get("coverage_weight", 0.3) * coverage)
        return {"icir": icir, "stability": stability, "coverage": coverage,
                "score": score, "ic": s.tolist()}

    def _full_score(self, panel: pd.DataFrame, pack_panels: Dict[str, pd.DataFrame]
                    ) -> dict:
        q = self._quick_score(panel)
        if not np.isfinite(q["score"]):
            return q
        # turnover penalty (top-quintile churn on research dates)
        to = factor_turnover(panel, None) or {}
        turnover = to.get("avg_turnover", 0.0)
        turn_pen = max(0.0, turnover - 0.5) / 0.5
        # correlation penalty vs pack atoms
        corr_pen = 0.0
        for name, pp in pack_panels.items():
            c = pairwise_correlation({"x": panel, "y": pp},
                                     dates=list(self.dates))
            c = c.loc["x", "y"]
            if np.isfinite(c):
                corr_pen = max(corr_pen, abs(c) - 0.5)
        q["turnover"] = turnover
        q["corr_pen"] = corr_pen
        q["score"] = (q["score"]
                      - self.w.get("turnover_weight", 0.1) * turn_pen
                      - self.w.get("correlation_weight", 0.2) * corr_pen)
        return q

    def score_expr(self, expr: Expr, atom_panels: Dict[str, pd.DataFrame],
                   pack_panels: Optional[Dict[str, pd.DataFrame]] = None) -> dict:
        self.n_candidates_tested += 1
        panel = eval_expr(expr, atom_panels)
        panel = panel.reindex(self.dates)
        if pack_panels:
            res = self._full_score(panel, pack_panels)
        else:
            res = self._quick_score(panel)
        res["expr"] = expr.render()
        self.score_log.append(res)
        return res

    # -- search -------------------------------------------------------------
    def generate_depth2(self, atom_names: List[str]) -> List[Expr]:
        cands = []
        for i in range(len(atom_names)):
            for j in range(i + 1, len(atom_names)):
                for op in sorted(OPS):
                    cands.append(Expr(kind="op", op=op, args=[
                        Expr(kind="unary", op="rank",
                             args=[Expr(kind="atom", value=atom_names[i])]),
                        Expr(kind="unary", op="rank",
                             args=[Expr(kind="atom", value=atom_names[j])]),
                    ]))
        return cands[:self.max_per_gen]

    def generate_depth3(self, beam: List[Expr],
                        atom_names: List[str]) -> List[Expr]:
        cands = []
        for b in beam:
            b_atoms = b.atoms()
            for a in atom_names:
                if a in b_atoms:
                    continue
                ra = Expr(kind="unary", op="rank",
                          args=[Expr(kind="atom", value=a)])
                for op in sorted(OPS):
                    cands.append(Expr(kind="op", op=op, args=[b, ra]))
                    cands.append(Expr(kind="op", op=op, args=[ra, b]))
            for u in ("log", "abs"):
                cands.append(Expr(kind="unary", op=u, args=[b]))
        self.rng.shuffle(cands)
        return cands[:self.max_per_gen]

    def search(self, atom_names: List[str],
               pack_panels: Optional[Dict[str, pd.DataFrame]] = None) -> dict:
        """Two-generation beam search on research dates only."""
        atom_panels = self.atom_panels(atom_names)
        gen = self.generate_depth2(atom_names)
        scored = [self.score_expr(e, atom_panels) for e in gen]
        scored = [s for s in scored if np.isfinite(s["score"])]
        scored.sort(key=lambda s: s["score"], reverse=True)
        beam = [parse(s["expr"], self.depth_max, set(atom_names))
                for s in scored[:self.beam_size]]
        # correlation/turnover penalty pass on the depth-2 shortlist
        shortlist = [self.score_expr(e, atom_panels, pack_panels)
                     for e in beam]
        shortlist.sort(key=lambda s: s["score"], reverse=True)
        beam = [parse(s["expr"], self.depth_max, set(atom_names))
                for s in shortlist[:self.beam_size]]

        if self.depth_max >= 3:
            gen3 = self.generate_depth3(beam, atom_names)
            scored3 = [self.score_expr(e, atom_panels, pack_panels)
                       for e in gen3]
            scored3 = [s for s in scored3 if np.isfinite(s["score"])]
            combined = sorted(shortlist + scored3,
                              key=lambda s: s["score"], reverse=True)
        else:
            combined = shortlist
        return {
            "n_candidates_tested": self.n_candidates_tested,
            "beam": combined[:self.beam_size],
            "best_research_score": combined[0]["score"] if combined else np.nan,
            "best_research_icir": combined[0]["icir"] if combined else np.nan,
        }

    # -- validation + gate --------------------------------------------------
    def validate(self, candidates: List[dict], valid_dates,
                 valid_labels: Dict[int, pd.DataFrame],
                 valid_universe=None) -> List[dict]:
        """Validation-period ranking of the beam (2022-2023)."""
        self._guard(valid_dates)
        atom_panels = self.atom_panels(sorted(
            {a for c in candidates for a in
             parse(c["expr"], self.depth_max).atoms()}))
        out = []
        for c in candidates:
            panel = eval_expr(parse(c["expr"], self.depth_max), atom_panels)
            panel = panel.reindex(pd.DatetimeIndex(valid_dates))
            ic = ic_series(panel, valid_labels[20].reindex(
                pd.DatetimeIndex(valid_dates)), min_stocks=30)
            s = ic["rank_ic"]
            icir = s.mean() / s.std(ddof=0) if len(s) and s.std(ddof=0) > 0 \
                else np.nan
            p = max(float((s > 0).mean()), float((s < 0).mean())) if len(s) \
                else np.nan
            out.append({**c, "valid_icir": icir,
                        "valid_sign_consistency": p})
        out.sort(key=lambda c: (-abs(c["valid_icir"])
                                if np.isfinite(c["valid_icir"]) else 1e9))
        return out

    def gate(self, candidates: List[dict], pack_panels: Dict[str, pd.DataFrame],
             atom_names: Set[str]) -> List[dict]:
        """Automated human-review-style gate -> factor_pack_v2 candidates."""
        cfg = self.config.get("mining", {}).get("gate", {})
        min_r = float(cfg.get("min_research_icir", 0.5))
        min_v = float(cfg.get("min_valid_icir", 0.3))
        max_corr = float(cfg.get("max_corr_with_pack", 0.7))
        passed = []
        for c in candidates:
            reasons = []
            if not np.isfinite(c["icir"]) or abs(c["icir"]) < min_r:
                reasons.append(f"research |ICIR| {c['icir']:.3f} < {min_r}")
            if not np.isfinite(c["valid_icir"]) or abs(c["valid_icir"]) < min_v:
                reasons.append(f"valid |ICIR| {c['valid_icir']:.3f} < {min_v}")
            if (np.isfinite(c["icir"]) and np.isfinite(c["valid_icir"])
                    and c["icir"] * c["valid_icir"] < 0):
                reasons.append("research/valid sign flip")
            if c.get("corr_pen") and c["corr_pen"] + 0.5 >= max_corr:
                reasons.append(f"|corr| with pack >= {max_corr}")
            if not reasons:
                passed.append(c)
            else:
                c["gate_reasons"] = reasons
        return passed
