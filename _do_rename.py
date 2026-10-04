# -*- coding: utf-8 -*-
"""执行改名：git mv 文件，然后把全仓库对旧名的引用改成新名。

用法：
    python _do_rename.py --dry-run     # 只报告要改什么
    python _do_rename.py               # 真改

原则：
- 只动 git 跟踪的文本文件
- 排除第三方内容（data/raw/）和本脚本自身
- 引用替换按**完整文件名**（含 .md）做，所以 `docs/x.md`、`reports/x.md`、
  裸 `x.md`、以及代码里 `"x.md"` 字符串都会被覆盖
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _rename_map import MAPPING

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
             ".mypy_cache", "mlruns", "qlib_data", "qlib_data_old"}
SKIP_PREFIX = ("data/raw/",)
SKIP_FILES = {"_rename_map.py", "_do_rename.py"}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                         encoding="utf-8").stdout.split("\n")
    keep = []
    for f in out:
        if not f:
            continue
        parts = Path(f).parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        if f.startswith(SKIP_PREFIX) or f in SKIP_FILES:
            continue
        keep.append(f)
    return keep


def main() -> int:
    dry = "--dry-run" in sys.argv
    old_to_new = {Path(k).name: Path(v).name for k, v in MAPPING.items()}
    old_names = sorted(old_to_new, key=len, reverse=True)

    total_refs = 0
    files_touched = 0
    # 注意：要改名的文件本身也要更新内容（它们会引用别的同类文档）。
    # 先改内容再 git mv，内容自然跟着走。
    for f in tracked_files():
        p = Path(f)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        orig = text
        n_here = 0
        for name in old_names:
            if name in text:
                n_here += text.count(name)
                text = text.replace(name, old_to_new[name])
        if text != orig:
            total_refs += n_here
            files_touched += 1
            print(f"  {f}  ({n_here} 处)")
            if not dry:
                p.write_text(text, encoding="utf-8", newline="")

    print(f"\n引用替换：{files_touched} 个文件，{total_refs} 处")

    if dry:
        print("\n[dry-run] 未改名、未写文件")
        return 0

    # 改文件名（用 git mv 保留历史）
    for old, new in MAPPING.items():
        r = subprocess.run(["git", "mv", old, new], capture_output=True,
                           text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"  git mv 失败: {old} -> {new}: {r.stderr.strip()}")
    print(f"已改名 {len(MAPPING)} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
