"""Sense -> Predict -> Explain -> Act pipeline."""
from __future__ import annotations

import numpy as np

from .data import BOUNDS, clip_obs
from .model import AgriModel
from .recommend import recommend


def analyze(model: AgriModel, obs: dict) -> dict:
    obs = clip_obs(obs)
    result = model.predict(obs)
    result["drivers"] = model.explain(obs)
    result["recommendations"] = recommend(obs, result)
    result["observation"] = obs
    result["disclaimer"] = "Decision support only - validate high-impact actions with a local agronomist."
    return result


def build_timeline(model: AgriModel, obs: dict, seed: int, weeks: int = 12) -> list[dict]:
    """SIMULATED history ending at the current observation (demo stand-in for stored time series)."""
    rng = np.random.default_rng(seed * 7 + 1)
    scale = {"humidity_pct": 8, "avg_temp_c": 2, "rainfall_mm_30d": 30, "soil_moisture": 0.04, "ndvi": 0.05, "ndvi_trend": 0.02}
    rows = []
    for w in range(weeks - 1, -1, -1):
        age = w / (weeks - 1)
        rows.append(clip_obs({**obs, **{k: obs[k] + rng.normal(0, s) * age for k, s in scale.items()}}))
    yields, risk = model.risk_index_many(rows)
    return [
        {"weeks_ago": weeks - 1 - i, "risk_index": round(float(risk[i]), 3), "yield_t_ha": round(float(yields[i]), 2),
         **{k: round(rows[i][k], 3) for k in ("ndvi", "humidity_pct", "avg_temp_c", "rainfall_mm_30d")}}
        for i in range(weeks)
    ]


def forecast_risk(points: list[dict], weeks: int = 4) -> list[dict]:
    """Early-warning outlook: linear trend of the last 6 weekly risk values, projected forward (slope capped)."""
    recent = points[-6:]
    xs = np.array([-p["weeks_ago"] for p in recent], dtype=float)
    ys = np.array([p["risk_index"] for p in recent], dtype=float)
    slope = float(np.clip(np.polyfit(xs, ys, 1)[0], -0.08, 0.08))
    last = float(ys[-1])
    return [{"weeks_ahead": k, "risk_index": round(float(np.clip(last + slope * k, 0, 1)), 3)} for k in range(1, weeks + 1)]


def meta() -> dict:
    from .data import CROP_PROFILES, CROPS
    return {
        "crops": CROPS,
        "typical_yield_t_ha": {c: CROP_PROFILES[c]["base"] for c in CROPS},
        "features": [{"key": k, "min": v[0], "max": v[1], "unit": v[2], "label": v[3]} for k, v in BOUNDS.items()],
    }