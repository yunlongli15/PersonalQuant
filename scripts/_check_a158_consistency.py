# -*- coding: utf-8 -*-
"""Temp: compare Alpha158 features (canonical provider vs qlib_data bins)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

TMP = Path(__file__).resolve().parents[1] / "data" / "derived" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

INSTS = ["600519.SH", "000001.SZ", "600036.SH", "601318.SH"]
RANGE = ("2024-01-02", "2024-01-31")

# 1) canonical-backed Alpha158
from personal_quant.strategy.qlib_provider import init_qlib_with_canonical

init_qlib_with_canonical()
from qlib.contrib.data.handler import Alpha158

h = Alpha158(instruments=INSTS, start_time=RANGE[0], end_time=RANGE[1],
             freq="day", learn_processors=[], infer_processors=[])
raw = h.fetch(col_set=h.CS_RAW, data_key=h.DK_R)
raw.to_pickle(TMP / "a158_canonical.pkl")
print("canonical shape:", raw.shape)

# 2) official qlib_data path (fresh process to reset providers)
import subprocess

code = f"""
import sys
sys.path.insert(0, r'{Path(__file__).resolve().parents[1]}')
import qlib
from qlib.constant import REG_CN
qlib.init(provider_uri=r'{Path(__file__).resolve().parents[1] / 'qlib_data'}', region=REG_CN)
from qlib.contrib.data.handler import Alpha158
h = Alpha158(instruments={INSTS!r}, start_time='{RANGE[0]}', end_time='{RANGE[1]}', freq='day', learn_processors=[], infer_processors=[])
raw = h.fetch(col_set=h.CS_RAW, data_key=h.DK_R)
raw.to_pickle(r'{TMP / 'a158_official.pkl'}')
print('official shape:', raw.shape)
"""
subprocess.run([sys.executable, "-c", code], check=True)

a = pd.read_pickle(TMP / "a158_canonical.pkl")
b = pd.read_pickle(TMP / "a158_official.pkl")
a = a.sort_index()
b = b.sort_index()
common = a.index.intersection(b.index)
a, b = a.loc[common], b.loc[common]
print("common rows:", len(common), "| cols:", len(a.columns))
maxdiff = {}
for c in a.columns:
    d = (a[c].astype(float) - b[c].astype(float)).abs()
    maxdiff[c] = float(d.max()) if len(d) else 0.0
vals = np.array(list(maxdiff.values()))
print(f"max |diff| over all columns: {vals.max():.3e}")
print(f"columns with maxdiff > 1e-4: {sum(vals > 1e-4)} / {len(vals)}")
bad = {k: v for k, v in maxdiff.items() if v > 1e-4}
if bad:
    print("worst columns:", dict(list(bad.items())[:5]))
