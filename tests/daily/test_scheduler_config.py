# -*- coding: utf-8 -*-
"""§25 / §26：计划任务脚本 —— 默认 dry-run，绝不改执行策略。"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "scripts" / "install_scheduler.ps1"
UNINSTALL = ROOT / "scripts" / "uninstall_scheduler.ps1"


def _text(p: Path) -> str:
    return p.read_bytes().decode("utf-8-sig")


def _code_only(text: str) -> str:
    """去掉注释（含 <# #> 块注释）与 Write-Host 打印行。

    脚本里那句 "绝不连接券商、绝不下单" 是**打印给人看的说明**，
    不是在调用券商。断言必须只看真正会执行的代码。
    """
    out, in_block = [], False
    for ln in text.splitlines():
        t = ln.strip()
        if t.startswith("<#"):
            in_block = True
        if in_block:
            if t.endswith("#>"):
                in_block = False
            continue
        if not t or t.startswith("#") or t.startswith("Write-"):
            continue
        out.append(t)
    return "\n".join(out)


@pytest.mark.parametrize("p", [INSTALL, UNINSTALL])
def test_script_exists_and_has_bom(p):
    """Windows PowerShell 5.1 读无 BOM 的 UTF-8 会按 ANSI 解析，
    中文注释会直接破坏语法 —— 必须带 BOM。"""
    assert p.exists()
    assert p.read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("p", [INSTALL, UNINSTALL])
def test_script_parses(p):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$e=$null; $null=[System.Management.Automation.Language.Parser]"
         f"::ParseFile('{p}',[ref]$null,[ref]$e); "
         "if($e.Count -eq 0){'OK'}else{'BAD'}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120)
    assert "OK" in (r.stdout or ""), r.stdout


@pytest.mark.parametrize("p", [INSTALL, UNINSTALL])
def test_default_is_dry_run(p):
    t = _text(p)
    assert "-Apply" in t
    assert "DRY-RUN" in t
    # 不传 -Apply 时不注册/不删除
    assert "if (-not $Apply)" in t


@pytest.mark.parametrize("p", [INSTALL, UNINSTALL])
def test_never_changes_execution_policy(p):
    """§26：绝不修改 PowerShell 执行策略、绝不绕过安全策略。"""
    code = _code_only(_text(p))
    assert "Set-ExecutionPolicy" not in code
    assert "Bypass" not in code


def test_install_targets_the_daily_pipeline():
    t = _text(INSTALL)
    assert "run_daily.py" in t
    assert "PersonalQuant-Daily" in t


def test_task_survives_a_powered_off_computer():
    """§25：不假设一直开机 —— 必须 StartWhenAvailable（补跑）。"""
    assert "StartWhenAvailable" in _text(INSTALL)


def test_no_broker_or_trading_in_scheduler():
    for p in (INSTALL, UNINSTALL):
        code = _code_only(_text(p))
        for bad in ("easytrader", "place_order", "下单", "broker"):
            assert bad.lower() not in code.lower(), f"{p.name}: {bad}"
