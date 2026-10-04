# -*- coding: utf-8 -*-
"""别再有"写了但永远不会被收集"的测试。

2026-10-05 发现：9 个文件用了 `<前缀>_test_<主题>.py` 的命名
（daily_test_alerts.py / forward_test_lot_rounding.py / ...），
而 pytest 默认只收 `test_*.py` 与 `*_test.py` —— 两个都不匹配。

于是 **50 条测试从来没被执行过**：`pytest tests/` 收不到它们，
所以任何一次"全量 N passed"里都不含它们；但它们单独跑是通过的，
所以也没有任何东西会报错。这正是本项目最怕的那种失败：**看起来有保护，
实际没有**。

这里用 pytest 自己的 python_files 配置去比对，而不是写死模式 ——
将来改了配置，这个守卫跟着走。
"""

import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

TESTS_DIR = Path(__file__).resolve().parent

#: 一个文件里出现这些才算"装着测试"
_TEST_DEF = re.compile(r"^\s*(async\s+)?def test_", re.M)


def _collectable_patterns() -> list:
    from _pytest.config import get_config

    cfg = get_config()
    cfg.parse([])
    return list(cfg.getini("python_files"))


def test_every_file_containing_tests_is_collectable():
    patterns = _collectable_patterns()
    offenders = []
    for p in sorted(TESTS_DIR.rglob("*.py")):
        if "__pycache__" in p.parts or p.name == "conftest.py":
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not _TEST_DEF.search(src):
            continue
        if not any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
            rel = p.relative_to(TESTS_DIR.parent).as_posix()
            n = len(_TEST_DEF.findall(src))
            offenders.append(f"{rel}（{n} 条测试）")
    assert not offenders, (
        "这些文件里有测试，但文件名不匹配 pytest 的 python_files="
        f"{patterns}，永远不会被收集：\n  " + "\n  ".join(offenders) +
        "\n请改成 test_*.py（注意同一目录树内不要重名，否则 import 冲突）")


def test_no_duplicate_test_module_basenames():
    """pytest 默认按文件名导入；不同目录里的同名测试文件会直接报
    `import file mismatch`。改名前先看这条。"""
    seen = {}
    for p in sorted(TESTS_DIR.rglob("test_*.py")):
        if "__pycache__" in p.parts:
            continue
        seen.setdefault(p.name, []).append(
            p.relative_to(TESTS_DIR.parent).as_posix())
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"测试文件重名会导致收集失败：{dupes}"
