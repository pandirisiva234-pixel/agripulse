"""Feature schema, crop profiles, synthetic training data and demo fields.

The PPT names Sentinel-2 (NDVI), NASA POWER (weather), ISRIC SoilGrids (soil) and
FAOSTAT (crop stats) as data sources. Those need credentials / heavy downloads, so this
repo ships a *synthetic* generator built on agronomic rules to make the platform run
out-of-the-box. `python -m scripts.train --csv your.csv` retrains on real data with the
same columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CROP_PROFILES = {
    # typical yield t/ha, optimal temp C, temp tolerance, optimal pH, pest susceptibility
    "rice":   dict(base=4.5,  opt_temp=27, tol=6, ph=6.0, susc=0.70),
    "wheat":  dict(base=3.8,  opt_temp=20, tol=5, ph=6.5, susc=0.50),
    "maize":  dict(base=5.5,  opt_temp=25, tol=6, ph=6.3, susc=0.50),
    "cotton": dict(base=2.4,  opt_temp=28, tol=6, ph=6.8, susc=0.75),
    "tomato": dict(base=28.0, opt_temp=24, tol=5, ph=6.3, susc=0.90),
}
CROPS = list(CROP_PROFILES)

NUMERIC = [
    "ndvi", "ndvi_trend", "soil_ph", "soil_organic_carbon",
    "soil_moisture", "rainfall_mm_30d", "avg_temp_c", "humidity_pct",
]
FEATURES = ["crop"] + NUMERIC

# (min, max, unit, human label)
BOUNDS = {
    "ndvi":                (0.05, 0.95, "", "Vegetation health (NDVI)"),
    "ndvi_trend":          (-0.30, 0.30, "", "NDVI 2-week trend"),
    "soil_ph":             (3.5, 9.5, "pH", "Soil pH"),
    "soil_organic_carbon": (0.1, 6.0, "%", "Soil organic carbon"),
    "soil_moisture":       (0.02, 0.60, "m3/m3", "Soil moisture"),
    "rainfall_mm_30d":     (0.0, 600.0, "mm", "Rainfall (30 days)"),
    "avg_temp_c":          (0.0, 50.0, "C", "Average temperature"),
    "humidity_pct":        (5.0, 100.0, "%", "Relative humidity"),
}
LABELS = {k: v[3] for k, v in BOUNDS.items()}
PEST_LEVELS = ["Low", "Medium", "High"]


def clip_obs(obs: dict) -> dict:
    out = dict(obs)
    for k, (lo, hi, *_rest) in BOUNDS.items():
        if k in out:
            out[k] = float(min(max(out[k], lo), hi))
    return out


def pest_score(df: pd.DataFrame) -> np.ndarray:
    """Latent 0-1 pest/disease pressure: warm + humid + wet + stressed canopy + susceptible crop."""
    warm_humid = np.clip((df.humidity_pct - 60) / 30, 0, 1)
    temp_band = 1 - np.clip(np.abs(df.avg_temp_c - 28) / 10, 0, 1)
    rain = np.clip(df.rainfall_mm_30d / 200, 0, 1)
    stress = np.clip(-df.ndvi_trend / 0.08, 0, 1)
    susc = df.crop.map(lambda c: CROP_PROFILES[c]["susc"])
    return (0.35 * warm_humid + 0.25 * temp_band + 0.15 * rain + 0.15 * stress + 0.10 * susc).to_numpy()


def _level(score: np.ndarray) -> np.ndarray:
    return np.where(score < 0.38, 0, np.where(score < 0.55, 1, 2))


def generate_dataset(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    crop = rng.choice(CROPS, n)
    prof = pd.DataFrame([CROP_PROFILES[c] for c in crop])
    rain = np.clip(rng.gamma(2.0, 45.0, n), 0, 450)
    moisture = np.clip(0.12 + 0.0009 * rain + rng.normal(0, 0.05, n), 0.04, 0.5)
    df = pd.DataFrame({
        "crop": crop,
        "ndvi": np.clip(rng.normal(0.62, 0.14, n) + 0.15 * (moisture - 0.25), 0.12, 0.92),
        "ndvi_trend": np.clip(rng.normal(0, 0.04, n), -0.2, 0.2),
        "soil_ph": np.clip(rng.normal(6.6, 0.8, n), 4.5, 8.8),
        "soil_organic_carbon": np.clip(rng.normal(1.0, 0.45, n), 0.2, 3.5),
        "soil_moisture": moisture,
        "rainfall_mm_30d": rain,
        "avg_temp_c": np.clip(rng.normal(prof.opt_temp + 2, 5), 8, 42),
        "humidity_pct": np.clip(rng.normal(68, 15, n), 25, 98),
    })
    score = pest_score(df)
    df["pest_level"] = _level(score + rng.normal(0, 0.03, n))

    ndvi_f = 0.4 + 0.9 * df.ndvi
    temp_f = 0.5 + 0.5 * np.exp(-0.5 * ((df.avg_temp_c - prof.opt_temp) / prof.tol) ** 2)
    moist_f = np.clip(1 - 2.5 * np.abs(df.soil_moisture - 0.28), 0.5, 1.05)
    ph_f = np.clip(1 - 0.08 * np.abs(df.soil_ph - prof.ph), 0.6, 1.0)
    soc_f = 0.9 + 0.05 * np.minimum(df.soil_organic_carbon, 2.0)
    pest_f = 1 - 0.25 * score
    df["yield_t_ha"] = 1.7 * prof.base * ndvi_f * temp_f * moist_f * ph_f * soc_f * pest_f * rng.normal(1, 0.04, n)
    return df.round(4)


# Demo fields (latest observation snapshot). Illustrative values, not measurements.
DEMO_FIELDS = [
    dict(name="Mandya Paddy Block A", district="Mandya", state="Karnataka", crop="rice", lat=12.52, lon=76.90, area_ha=3.2,
         obs=dict(ndvi=0.55, ndvi_trend=-0.05, soil_ph=6.4, soil_organic_carbon=1.1, soil_moisture=0.33, rainfall_mm_30d=165, avg_temp_c=28, humidity_pct=86)),
    dict(name="Davangere Maize Plot 2", district="Davangere", state="Karnataka", crop="maize", lat=14.47, lon=75.92, area_ha=5.0,
         obs=dict(ndvi=0.68, ndvi_trend=0.01, soil_ph=6.8, soil_organic_carbon=0.9, soil_moisture=0.24, rainfall_mm_30d=60, avg_temp_c=26, humidity_pct=58)),
    dict(name="Raichur Cotton Field 7", district="Raichur", state="Karnataka", crop="cotton", lat=16.20, lon=77.36, area_ha=8.5,
         obs=dict(ndvi=0.48, ndvi_trend=-0.03, soil_ph=7.9, soil_organic_carbon=0.5, soil_moisture=0.14, rainfall_mm_30d=30, avg_temp_c=33, humidity_pct=52)),
    dict(name="Kolar Tomato Farm", district="Kolar", state="Karnataka", crop="tomato", lat=13.14, lon=78.13, area_ha=1.4,
         obs=dict(ndvi=0.62, ndvi_trend=-0.04, soil_ph=6.2, soil_organic_carbon=1.3, soil_moisture=0.30, rainfall_mm_30d=110, avg_temp_c=25, humidity_pct=84)),
    dict(name="Ludhiana Wheat Farm", district="Ludhiana", state="Punjab", crop="wheat", lat=30.90, lon=75.85, area_ha=6.0,
         obs=dict(ndvi=0.72, ndvi_trend=0.02, soil_ph=7.2, soil_organic_carbon=0.8, soil_moisture=0.27, rainfall_mm_30d=45, avg_temp_c=19, humidity_pct=64)),
    dict(name="Thanjavur Delta Paddy", district="Thanjavur", state="Tamil Nadu", crop="rice", lat=10.79, lon=79.14, area_ha=4.1,
         obs=dict(ndvi=0.70, ndvi_trend=0.00, soil_ph=6.1, soil_organic_carbon=1.2, soil_moisture=0.31, rainfall_mm_30d=95, avg_temp_c=29, humidity_pct=74)),
    dict(name="Nashik Tomato Farm", district="Nashik", state="Maharashtra", crop="tomato", lat=20.00, lon=73.79, area_ha=2.2,
         obs=dict(ndvi=0.66, ndvi_trend=0.01, soil_ph=6.5, soil_organic_carbon=1.0, soil_moisture=0.26, rainfall_mm_30d=70, avg_temp_c=24, humidity_pct=62)),
]
