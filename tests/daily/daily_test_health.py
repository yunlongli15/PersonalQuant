# -*- coding: utf-8 -*-
"""§28：系统健康 CLI —— 每项给人话，不把 Traceback 丢给用户。"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "system_health.py"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=600)


def test_health_script_exists():
    assert SCRIPT.exists()


def test_health_json_has_all_required_checks():
    r = _run("--json")
    assert r.returncode in (0, 1), r.stderr[-300:]
    data = json.loads(r.stdout)
    names = {i["name"] for i in data["items"]}
    required = {"Qlib", "Database", "Market data", "News", "Financial",
                "Model", "Paper live", "Forward holdout", "Portfolio",
                "Scheduler"}
    assert required <= names, f"缺检查项：{required - names}"


def test_every_check_has_status_and_human_detail():
    data = json.loads(_run("--json").stdout)
    for i in data["items"]:
        assert i["status"] in ("PASS", "WARNING", "FAIL"), i
        assert i["detail"], f"{i['name']} 没有说明"
        assert "Traceback" not in i["detail"]


def test_missing_scheduler_is_a_warning_not_a_failure():
    """没装计划任务只是 WARNING —— 手动跑 run_daily.py 完全可以。"""
    data = json.loads(_run("--json").stdout)
    sched = [i for i in data["items"] if i["name"] == "Scheduler"][0]
    assert sched["status"] in ("PASS", "WARNING")
    if sched["status"] == "WARNING":
        assert "SCHEDULER_NOT_INSTALLED" in sched["detail"]


def test_health_is_read_only():
    src = SCRIPT.read_text(encoding="utf-8")
    for banned in ("INSERT", "UPDATE ", "DELETE", "write_text", "to_parquet"):
        assert banned not in src, f"健康检查不应写入：{banned}"
