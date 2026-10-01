"""Yield regression + pest-risk classification with uncertainty and occlusion-based explanations."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

from .data import CROPS, FEATURES, LABELS, NUMERIC, PEST_LEVELS, generate_dataset

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
BUNDLE_PATH = MODEL_DIR / "agripulse.joblib"
RISK_WEIGHTS = np.array([0.0, 0.5, 1.0])  # Low, Medium, High -> 0..1 risk index


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [("crop", OneHotEncoder(categories=[CROPS], sparse_output=False), ["crop"])],
        remainder="passthrough", sparse_threshold=0,
    )


class AgriModel:
    def __init__(self, pre, reg, clf, baseline: dict, metrics: dict):
        self.pre, self.reg, self.clf = pre, reg, clf
        self.baseline, self.metrics = baseline, metrics

    # ---------- training / persistence ----------
    @classmethod
    def train(cls, df: pd.DataFrame | None = None, seed: int = 42) -> "AgriModel":
        df = generate_dataset(seed=seed) if df is None else df
        train, test = train_test_split(df, test_size=0.2, random_state=seed)
        pre = _preprocessor().fit(train[FEATURES])
        Xtr, Xte = pre.transform(train[FEATURES]), pre.transform(test[FEATURES])
        reg = RandomForestRegressor(n_estimators=150, min_samples_leaf=3, n_jobs=-1, random_state=seed)
        clf = RandomForestClassifier(n_estimators=150, min_samples_leaf=3, n_jobs=-1, random_state=seed)
        reg.fit(Xtr, train["yield_t_ha"])
        clf.fit(Xtr, train["pest_level"])
        yp, cp = reg.predict(Xte), clf.predict(Xte)
        metrics = {
            "train_rows": int(len(train)), "test_rows": int(len(test)),
            "yield_r2": round(float(r2_score(test["yield_t_ha"], yp)), 4),
            "yield_mae_t_ha": round(float(mean_absolute_error(test["yield_t_ha"], yp)), 4),
            "pest_accuracy": round(float(accuracy_score(test["pest_level"], cp)), 4),
            "pest_macro_f1": round(float(f1_score(test["pest_level"], cp, average="macro")), 4),
        }
        baseline = {c: df[df.crop == c][NUMERIC].median().to_dict() for c in CROPS}
        return cls(pre, reg, clf, baseline, metrics)

    def save(self, path: Path = BUNDLE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(dict(pre=self.pre, reg=self.reg, clf=self.clf, baseline=self.baseline, metrics=self.metrics), path)
        (path.parent / "metrics.json").write_text(json.dumps(self.metrics, indent=2))

    @classmethod
    def load_or_train(cls, path: Path = BUNDLE_PATH) -> "AgriModel":
        if path.exists():
            try:
                return cls(**joblib.load(path))
            except Exception:  # version mismatch etc. -> retrain
                pass
        model = cls.train()
        model.save(path)
        return model

    # ---------- inference ----------
    def _raw(self, df: pd.DataFrame):
        X = self.pre.transform(df[FEATURES])
        yhat = self.reg.predict(X)
        ystd = np.stack([t.predict(X) for t in self.reg.estimators_]).std(axis=0)
        proba = self.clf.predict_proba(X)
        return yhat, ystd, proba

    def predict(self, obs: dict) -> dict:
        row = pd.DataFrame([obs])
        y, ystd, p = self._raw(row)
        y, ystd, p = float(y[0]), float(ystd[0]), p[0]
        level_idx = int(np.argmax(p))
        rel = ystd / max(y, 1e-6)
        return {
            "yield": {
                "value_t_ha": round(y, 2),
                "range_t_ha": [round(max(y - 1.645 * ystd, 0), 2), round(y + 1.645 * ystd, 2)],
                "confidence": round(float(np.clip(1 - rel / 0.15, 0, 1)), 2),
            },
            "pest": {
                "level": PEST_LEVELS[level_idx],
                "risk_index": round(float(p @ RISK_WEIGHTS), 3),
                "probabilities": {lv: round(float(pr), 3) for lv, pr in zip(PEST_LEVELS, p)},
                "confidence": round(float(p[level_idx]), 2),
            },
        }

    def risk_index_many(self, rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
        y, _, p = self._raw(pd.DataFrame(rows))
        return y, p @ RISK_WEIGHTS

    def explain(self, obs: dict, top: int = 5) -> dict:
        """Occlusion: swap each feature for its crop-typical value; the change in prediction is its effect."""
        base = self.baseline[obs["crop"]]
        rows = [dict(obs)] + [{**obs, f: base[f]} for f in NUMERIC]
        y, risk = self.risk_index_many(rows)
        out_y, out_p = [], []
        for i, f in enumerate(NUMERIC, start=1):
            common = {"feature": f, "label": LABELS[f], "value": round(float(obs[f]), 3), "typical": round(float(base[f]), 3)}
            out_y.append({**common, "effect": round(float(y[0] - y[i]), 3)})
            out_p.append({**common, "effect": round(float(risk[0] - risk[i]), 3)})
        key = lambda d: -abs(d["effect"])
        return {"yield": sorted(out_y, key=key)[:top], "pest": sorted(out_p, key=key)[:top]}
