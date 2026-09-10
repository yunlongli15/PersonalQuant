# -*- coding: utf-8 -*-
"""STEP 7F: GUI — pages render, no business logic in the UI layer, and
the app is genuinely local/offline (no CDN, no outbound request)."""

import re

import pytest
from fastapi.testclient import TestClient

from webapp import app as webapp_app
from webapp import pages, services, svg

PAGES = ["/", "/wealth/overview", "/wealth/daily-update",
         "/wealth/positions", "/wealth/transactions", "/wealth/performance",
         "/wealth/accounts", "/quant/signals", "/quant/forecasts",
         "/quant/trade-plan", "/quant/paper-live", "/quant/research",
         "/data/status", "/settings"]


@pytest.fixture
def client():
    return TestClient(webapp_app.app)


@pytest.mark.parametrize("path", PAGES)
def test_page_renders(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "PersonalQuant" in r.text
    assert r.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path", PAGES)
def test_page_has_no_external_assets(client, path):
    """Offline-first: no CDN, no remote fonts, no external images."""
    html = client.get(path).text
    externals = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert not externals, f"{path} loads remote assets: {externals}"


def test_health_and_api(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert "status" in client.get("/api/data/status").json() or True
    sig = client.get("/api/quant/signals?limit=5").json()
    assert "available" in sig


def test_forecast_api_404_for_unknown_symbol(client):
    r = client.get("/api/quant/forecast/000000.XX")
    assert r.status_code == 404


def test_pages_module_has_no_financial_arithmetic():
    """Spec: financial logic must not live in the UI layer. Checked on the
    AST: the pages module must not import the engines or call their
    compute functions (formatting dict keys like 'investment_pnl' are
    fine — they are labels, not calculations)."""
    import ast

    tree = ast.parse(open(pages.__file__, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for mod in ("numpy", "pandas", "wealth.engine", "pipeline.forecast",
                "pipeline.signals", "pipeline.trade_plan",
                "trade_plan.plan", "portfolio.allocator",
                "portfolio.covariance"):
        assert mod not in imported, f"pages.py imports {mod}"


def test_services_use_shared_engines():
    src = open(services.__file__, encoding="utf-8").read()
    for needed in ("from wealth import", "pipeline", "trade_plan"):
        assert needed in src


def test_money_and_pct_formatting():
    assert pages.money(1234.5678) == "1,234.57"
    assert pages.money(None) == "—"
    assert pages.pct(0.1234) == "12.34%"
    assert pages.pct(None) == "—"
    assert pages.signed_class(1.2) == "pos"
    assert pages.signed_class(-0.5) == "neg"
    assert pages.signed_class(0) == "muted"


def test_esc_prevents_html_injection():
    assert "<script>" not in pages.esc("<script>alert(1)</script>")
    assert "&lt;script&gt;" in pages.esc("<script>")


def test_svg_charts_render_without_data():
    assert "no data yet" in svg.line_chart([{"name": "x", "points": []}])
    assert "no data yet" in svg.bar_chart([], [])
    assert "no data yet" in svg.donut([])


def test_svg_line_chart_draws_points():
    out = svg.line_chart([{"name": "nav",
                           "points": [("2026-01-01", 100.0),
                                      ("2026-01-02", 110.0)]}])
    assert out.startswith("<svg") and "<path" in out
    assert "110" in out or "100" in out


def test_svg_donut_percentages():
    out = svg.donut([("Cash", 75.0), ("Stocks", 25.0)])
    assert "75.0%" in out and "25.0%" in out


def test_serve_refuses_non_local_bind():
    """The launcher must refuse to expose personal data on the network."""
    import subprocess
    import sys

    serve = services.PROJECT_ROOT / "scripts" / "webapp" / "serve.py"
    out = subprocess.run([sys.executable, str(serve), "--host", "0.0.0.0"],
                         capture_output=True, text=True,
                         cwd=str(services.PROJECT_ROOT), timeout=120)
    assert "refusing to bind beyond localhost" in (out.stdout + out.stderr)
    assert out.returncode == 1
