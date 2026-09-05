# -*- coding: utf-8 -*-
"""PersonalQuant data infrastructure package (STEP 2).

Layering (RAW / CANONICAL / DERIVED):
- data/raw/      : original metadata, raw responses, optionally cached PDFs
- data/parquet/  : canonical data layer (unified schema, Parquet)
- data/duckdb/   : query database (DuckDB) over the canonical layer
- DERIVED (factors/models) is a later stage and must not be written into
  the canonical layer.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

__version__ = "0.1.0"
