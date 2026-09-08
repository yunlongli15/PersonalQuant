# -*- coding: utf-8 -*-
"""LightGBM cross-sectional model wrapper (fixed params from config).

The model predicts the future 20-trading-day adjusted return of each stock
in the universe at a signal date. Training is strictly time-forward: the
training data rows carry their signal dates and the caller enforces the
train < valid < test ordering (tested in tests/strategy/).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import lightgbm as lgb
import numpy as np
import pandas as pd


class AlphaModel:
    def __init__(self, params: dict, seed: int = 42):
        self.params = dict(params)
        self.params["seed"] = seed
        self.params["objective"] = self.params.get("objective", "regression")
        self.params["verbosity"] = -1
        self.seed = seed
        self.model: Optional[lgb.Booster] = None
        self.feature_columns: Optional[list] = None
        self.best_iteration: Optional[int] = None

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
    ) -> dict:
        self.feature_columns = list(X_train.columns)
        n_estimators = self.params.pop("n_estimators", 400)
        early = self.params.pop("early_stopping_rounds", None)
        callbacks = None
        valid_sets = None
        if X_valid is not None and early:
            valid_sets = [lgb.Dataset(X_valid, label=y_valid)]
            callbacks = [lgb.early_stopping(early, verbose=False)]
        ds = lgb.Dataset(X_train, label=y_train)
        self.model = lgb.train(
            self.params, ds, num_boost_round=n_estimators,
            valid_sets=valid_sets, callbacks=callbacks,
        )
        self.best_iteration = (
            self.model.best_iteration or n_estimators if callbacks else n_estimators
        )
        return {
            "best_iteration": self.best_iteration,
            "train_rmse": float(np.sqrt(np.mean((self.predict(X_train) - y_train) ** 2))),
            "valid_rmse": float(np.sqrt(np.mean((self.predict(X_valid) - y_valid) ** 2)))
            if X_valid is not None and y_valid is not None else None,
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("model not fitted")
        return self.model.predict(X[self.feature_columns], num_iteration=self.best_iteration)

    def predict_series(self, X: pd.DataFrame, index) -> pd.Series:
        return pd.Series(self.predict(X), index=index)

    def save(self, path: Path) -> None:
        if self.model is None:
            raise RuntimeError("model not fitted")
        self.model.save_model(str(path))

    @classmethod
    def load(cls, path: Path, params: dict, seed: int = 42) -> "AlphaModel":
        obj = cls(params, seed)
        obj.model = lgb.Booster(model_file=str(path))
        obj.feature_columns = obj.model.feature_name()
        obj.best_iteration = None
        return obj


def compute_ic(
    predictions: pd.DataFrame,  # columns: date, symbol, prediction, label
) -> pd.DataFrame:
    """Monthly cross-sectional IC / RankIC series."""
    rows = []
    for date, g in predictions.groupby("date"):
        if len(g) < 10 or g["label"].std() == 0:
            continue
        ic = g["prediction"].corr(g["label"])
        ric = g["prediction"].corr(g["label"], method="spearman")
        rows.append({"date": date, "ic": ic, "rank_ic": ric, "n": len(g)})
    return pd.DataFrame(rows)
