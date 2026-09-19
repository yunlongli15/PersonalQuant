# -*- coding: utf-8 -*-
"""§25 / §33 / §34：forward 记录 append-only，不可覆盖、不可回填。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import pytest

from paper_live.store import ForwardStore


def test_identical_write_is_a_noop(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    r1 = st.write_frame("predictions", "2026-09-18", df)
    r2 = st.write_frame("predictions", "2026-09-18", df)
    assert r1.written and r1.revision == 0
    assert not r2.written and r2.reason == "unchanged"


def test_overwrite_is_refused(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [1]}))
    with pytest.raises(PermissionError, match="append-only"):
        st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [2]}))


def test_revision_requires_a_reason_and_keeps_the_old_version(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [1]}))
    with pytest.raises(ValueError, match="reason"):
        st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [2]}),
                       allow_revision=True)
    r = st.write_frame("predictions", "2026-09-18", pd.DataFrame({"a": [2]}),
                       allow_revision=True, reason="数据源 bug 修复")
    assert r.revision == 1
    # 旧版本必须还在
    assert st.read_frame("predictions", "2026-09-18", revision=0)["a"].iloc[0] == 1
    assert st.read_frame("predictions", "2026-09-18")["a"].iloc[0] == 2
    log = st.all_revisions()
    assert len(log) == 1 and "bug" in log[0]["reason"]


def test_json_writes_are_append_only_too(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_json("observations", "2026-09-18", {"status": "VALID"})
    with pytest.raises(PermissionError):
        st.write_json("observations", "2026-09-18", {"status": "INVALID"})


def test_time_never_goes_backwards(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_json("observations", "2026-09-20", {"x": 1})
    with pytest.raises(ValueError, match="严格向前"):
        st.assert_time_order(pd.Timestamp("2026-09-18"))
    st.assert_time_order(pd.Timestamp("2026-09-21"))     # 向前没问题


def test_state_is_a_pointer_and_logs_its_history(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_state("paper_portfolio", {"cash": 100.0})
    st.write_state("paper_portfolio", {"cash": 200.0})
    assert st.read_state("paper_portfolio")["cash"] == 200.0
    log = (st.root / "state" / "state_log.jsonl").read_text(encoding="utf-8")
    assert '"cash": 100.0' in log


def test_revisions_of_lists_every_version(tmp_path):
    st = ForwardStore(tmp_path / "fh")
    st.write_frame("metrics", "2026-09-18", pd.DataFrame({"a": [1]}))
    st.write_frame("metrics", "2026-09-18", pd.DataFrame({"a": [2]}),
                   allow_revision=True, reason="fix")
    assert st.revisions_of("metrics", "2026-09-18") == [0, 1]
