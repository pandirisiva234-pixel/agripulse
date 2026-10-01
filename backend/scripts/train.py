"""Train and save the models.  python -m scripts.train [--csv path] [--rows 6000]

CSV must contain: crop, ndvi, ndvi_trend, soil_ph, soil_organic_carbon, soil_moisture,
rainfall_mm_30d, avg_temp_c, humidity_pct, yield_t_ha, pest_level (0=Low,1=Medium,2=High).
"""
import argparse

import pandas as pd

from app.data import generate_dataset
from app.model import AgriModel

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--rows", type=int, default=6000)
    a = ap.parse_args()
    df = pd.read_csv(a.csv) if a.csv else generate_dataset(a.rows)
    m = AgriModel.train(df)
    m.save()
    print("Saved models. Metrics:", m.metrics)
