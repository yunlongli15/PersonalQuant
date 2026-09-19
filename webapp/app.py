# -*- coding: utf-8 -*-
"""FastAPI application (STEP 7F).

Local only: bind 127.0.0.1, no auth (single-user desktop app), no
outbound requests. JSON endpoints (/api/...) exist so the same engines
can be scripted or driven by a future richer front-end.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import pages, services

app = FastAPI(title="PersonalQuant", docs_url="/api/docs",
              redoc_url=None, openapi_url="/api/openapi.json")


def _today() -> str:
    return str(datetime.now().date())


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return pages.dashboard(services.wealth_dashboard(),
                           services.quant_signals(limit=10),
                           services.data_status_view())


@app.get("/wealth/overview", response_class=HTMLResponse)
def wealth_overview() -> str:
    return pages.wealth_overview(services.wealth_dashboard())


@app.get("/wealth/daily-update", response_class=HTMLResponse)
def daily_update_form(as_of: Optional[str] = None) -> str:
    return _render_daily(as_of or _today())


def _render_daily(as_of: str, result: Optional[dict] = None) -> str:
    from wealth import db as wdb
    from wealth import repository as repo
    from wealth.models import PRODUCT_TYPES

    conn = wdb.connect()
    return pages.daily_update_page(
        _update_products(), repo.list_platforms(conn), list(PRODUCT_TYPES),
        as_of, result)


def _update_products() -> list:
    """Rows for the Daily Update page.

    Fund products show 金额/收益; stock products additionally carry the
    cost basis, share count and buy date (read from the ledger) plus the
    unrealised P&L, because a stock's holding is 股数 × 现价, not "how
    much money is in the account".
    """
    from wealth import db as wdb
    from wealth import engine, repository as repo
    from wealth.models import EXTERNAL_FLOW_TYPES

    conn = wdb.connect()
    platforms = {x["platform_id"]: x["name"]
                 for x in repo.list_platforms(conn)}
    accounts = {a["account_id"]: a for a in repo.list_accounts(conn)}
    products = []
    for p in repo.list_products(conn):
        acct = accounts.get(p["account_id"], {})
        snaps = repo.list_snapshots(conn, product_id=p["product_id"])
        row = {
            **p,
            "platform": platforms.get(acct.get("platform_id"), "?"),
            "last_value": snaps[-1]["market_value"] if snaps else "",
        }
        if p["product_type"] in ("stock", "etf"):
            as_of = snaps[-1]["snap_date"] if snaps else _today()
            held = engine.positions_at(conn, p["product_id"], as_of)
            buys = [t for t in repo.list_transactions(
                conn, product_id=p["product_id"]) if t["txn_type"] == "buy"]
            mv = float(snaps[-1]["market_value"]) if snaps else 0.0
            row.update({
                "shares": int(held.units),
                "cost_price": held.avg_cost or None,
                "buy_date": buys[0]["txn_date"] if buys else None,
                "unrealized": (mv - held.units * held.avg_cost
                               if held.units else None),
            })
        products.append(row)
    return products


def _num(raw) -> Optional[float]:
    """Parse a user-typed number; None when blank, raises on garbage."""
    if raw is None or str(raw).strip() == "":
        return None
    return float(str(raw).replace(",", "").replace("，", ""))


@app.post("/wealth/daily-update", response_class=HTMLResponse)
async def daily_update_submit(request: Request) -> str:
    form = await request.form()
    as_of = str(form.get("as_of") or _today())
    warnings: List[str] = []
    from wealth import db as wdb
    from wealth import repository as repo
    from wealth.service import UpdateEntry, record_daily_update

    conn = wdb.connect()
    entries = []
    stock_created = False

    # ① 已有产品：amount_<pid> / income_<pid>
    for key, value in form.items():
        if not key.startswith("amount_"):
            continue
        pid = int(key.split("_")[1])
        try:
            amount = _num(value)
            income = _num(form.get(f"income_{pid}"))
        except ValueError:
            warnings.append(f"{key}: 不是数字（{value!r}）")
            continue
        if amount is None:
            continue
        entries.append(UpdateEntry(product_id=pid, market_value=amount,
                                   reported_income=income))

    # ② 已有股票/ETF：填今日现价即可（股数/成本从台账读）
    from wealth.service import StockEntry, record_stock_update

    stock_entries = []
    for key, value in form.items():
        if not key.startswith("stock_price_"):
            continue
        pid = int(key.split("_")[2])
        try:
            price = _num(value)
        except ValueError:
            warnings.append(f"股票现价不是数字（{value!r}）")
            continue
        if price is None:
            continue
        stock_entries.append(StockEntry(product_id=pid, price=price))
    if stock_entries:
        try:
            res = record_stock_update(conn, as_of, stock_entries)
            warnings.extend(res.warnings)
        except Exception as e:                               # noqa: BLE001
            warnings.append(f"股票录入失败：{type(e).__name__}: {e}")

    # ③ 新建产品（渠道可选已有的，或当场新建）
    new_name = str(form.get("new_product_name") or "").strip()
    new_amount = None
    try:
        new_amount = _num(form.get("new_amount"))
        new_income = _num(form.get("new_income"))
        new_price = _num(form.get("new_price"))
        new_shares = _num(form.get("new_shares"))
        new_cost = _num(form.get("new_cost_price"))
    except ValueError:
        new_income = new_price = new_shares = new_cost = None
        warnings.append("新建产品：金额不是数字")
    if new_name and new_amount is None and new_price is not None and \
            new_shares is not None:
        new_amount = new_price * new_shares      # 股票：市值 = 股数 × 现价
    if new_name and new_amount is not None:
        try:
            plat_name = str(form.get("new_platform_name") or "").strip() \
                or str(form.get("new_platform") or "").strip()
            if not plat_name:
                raise ValueError("请选择或填写渠道")
            plat = next((x for x in repo.list_platforms(conn)
                         if x["name"] == plat_name), None)
            if plat is None:
                pid_plat = repo.create_platform(conn, plat_name,
                                                "other", "每日录入新建")
                acct = repo.create_account(conn, pid_plat,
                                           f"{plat_name} 默认账户")
                warnings.append(f"已新建渠道「{plat_name}」")
            else:
                accts = repo.list_accounts(conn, plat["platform_id"])
                acct = accts[0]["account_id"]
            prod = next((x for x in repo.list_products(conn, include_inactive=True)
                         if x["account_id"] == acct and x["name"] == new_name),
                        None)
            ptype = str(form.get("new_product_type") or "other")
            ticker = str(form.get("new_ticker") or "").strip() or None
            if prod is None:
                pid_new = repo.create_product(conn, acct, new_name, ptype,
                                              ticker=ticker)
                warnings.append(f"已新建产品「{new_name}」")
            else:
                pid_new = prod["product_id"]
                if ticker and not prod.get("ticker"):
                    repo.update_product(conn, pid_new, ticker=ticker)
            if ptype in ("stock", "etf") and new_shares and new_price:
                sres = record_stock_update(conn, as_of, [StockEntry(
                    product_id=pid_new, price=new_price,
                    shares=int(new_shares), cost_price=new_cost,
                    buy_date=str(form.get("new_buy_date") or "") or None)])
                warnings.extend(sres.warnings)
                stock_created = True
                if not new_cost:
                    warnings.append(
                        f"{new_name}：未填成本价 → 只记录了市值，"
                        f"浮盈无法计算（可在「交易流水」补一笔买入）")
            else:
                entries.append(UpdateEntry(product_id=pid_new,
                                           market_value=new_amount,
                                           reported_income=new_income))
        except Exception as e:                               # noqa: BLE001
            warnings.append(f"新建产品失败：{type(e).__name__}: {e}")

    if not entries and not stock_entries and not stock_created:
        return _render_daily(as_of, {"ok": False,
                                     "error": "没有填写任何金额"})
    n_saved = len(stock_entries) + (1 if stock_created else 0)
    try:
        if entries:
            res = record_daily_update(conn, as_of, entries)
            warnings.extend(res.warnings)
            n_saved += len(res.updated)
        return _render_daily(as_of, {
            "ok": True, "n": n_saved, "as_of": as_of,
            "warnings": warnings})
    except Exception as e:                                   # noqa: BLE001
        return _render_daily(as_of, {
            "ok": False, "error": f"{type(e).__name__}: {e}"})


def _wealth_conn():
    from wealth import db as wdb

    return wdb.connect()


@app.get("/wealth/positions", response_class=HTMLResponse)
def positions() -> str:
    return pages.positions_page(services.wealth_positions())


@app.get("/wealth/transactions", response_class=HTMLResponse)
def transactions() -> str:
    return pages.transactions_page(services.wealth_transactions())


@app.get("/wealth/performance", response_class=HTMLResponse)
def performance() -> str:
    vm = services.wealth_dashboard()
    decomposition = None
    if vm.get("available") and vm.get("as_of"):
        start = str(datetime.now().replace(month=1, day=1).date())
        try:
            decomposition = services.wealth_breakdown(start,
                                                      vm["as_of"])
        except Exception:                                    # noqa: BLE001
            decomposition = None
    return pages.performance_page(vm, services.wealth_income(),
                                  decomposition)


@app.get("/wealth/accounts", response_class=HTMLResponse)
def accounts() -> str:
    return pages.accounts_page(services.accounts_overview())


@app.get("/quant/signals", response_class=HTMLResponse)
def signals() -> str:
    return pages.signals_page(services.quant_signals(limit=100))


@app.get("/quant/forecasts", response_class=HTMLResponse)
def forecasts() -> str:
    return pages.forecasts_page(services.quant_forecasts(limit=50))


@app.get("/quant/stock/{symbol}", response_class=HTMLResponse)
def stock(symbol: str) -> str:
    return pages.symbol_page(services.quant_forecast_for(symbol))


@app.get("/quant/trade-plan", response_class=HTMLResponse)
def trade_plan(rebuild: int = 0) -> str:
    return pages.trade_plan_page(
        services.trade_plan_view(rebuild=bool(rebuild)))


@app.get("/quant/paper-live", response_class=HTMLResponse)
def paper_live() -> str:
    return pages.paper_live_page(services.paper_live_view())


@app.get("/quant/research", response_class=HTMLResponse)
def research() -> str:
    return pages.research_page(services.research_view())


@app.get("/data/status", response_class=HTMLResponse)
def data_status() -> str:
    return pages.data_page(services.data_status_view())


@app.get("/settings", response_class=HTMLResponse)
def settings() -> str:
    return pages.settings_page(services.settings_view())


@app.post("/settings/backup")
def backup():
    from wealth import db as wdb

    target = wdb.backup(conn=wdb.connect())
    return RedirectResponse("/settings", status_code=303)


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "local_only": True}


@app.get("/api/wealth/summary")
def api_wealth() -> dict:
    vm = services.wealth_dashboard()
    vm.pop("curve_points", None)
    vm.pop("pnl_points", None)
    return vm


@app.get("/api/quant/signals")
def api_signals(limit: int = 50) -> dict:
    return services.quant_signals(limit=limit)


@app.get("/api/quant/forecast/{symbol}")
def api_forecast(symbol: str) -> dict:
    vm = services.quant_forecast_for(symbol)
    if not vm.get("available"):
        raise HTTPException(status_code=404, detail="暂无该标的预测")
    return vm


@app.get("/api/quant/trade-plan")
def api_trade_plan(rebuild: int = 0) -> dict:
    return services.trade_plan_view(rebuild=bool(rebuild))


@app.get("/api/data/status")
def api_data_status() -> dict:
    return services.data_status_view()


@app.get("/api/research")
def api_research() -> dict:
    return services.research_view()
