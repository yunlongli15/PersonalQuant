# -*- coding: utf-8 -*-
"""Personal wealth management system (STEP 7).

独立于 quant 研究系统：Research DB 是 DuckDB/Parquet（只读研究数据），
Wealth DB 是本机 SQLite（个人账户的 operational database）。

分层（spec §55）：

    Research  ->  Signal  ->  Allocation / Trade Plan  ->  Personal Wealth

本包只回答最后一个问题：我真实存在哪里的钱、赚了多少、收益率是多少。

- db.py          SQLite 连接 + schema（data/wealth/wealth.db）
- models.py      枚举/数据类（平台/产品/交易类型/现金流类型）
- repository.py  账户、平台、产品、交易、快照、收益记录、审计的 CRUD
- seed.py        默认平台 / 资产类别 / benchmark
- engine.py      收益计算引擎（STEP 7B）

铁律：真实财富记录绝不进入 backtest；所有手工修改写入 audit_log。
"""
