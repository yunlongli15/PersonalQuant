# -*- coding: utf-8 -*-
"""Local web GUI (STEP 7F).

Runs on 127.0.0.1 only, serves its own CSS/SVG (no CDN, no external
request of any kind — the spec's "NO CLOUD" rule applies to the UI too),
and contains no financial logic: every number comes from
`webapp/services.py`, which calls the same wealth/quant engines the CLIs
use. Pages are rendering only (spec: 禁止把金融计算逻辑直接写在 UI 页面
代码中).
"""
