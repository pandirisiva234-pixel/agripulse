"""Live weather from NASA POWER (no API key). Returns None on any failure so callers can fall back."""
from __future__ import annotations

from datetime import date, timedelta

import httpx

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def fetch_nasa_power(lat: float, lon: float, days: int = 30, timeout: float = 15.0) -> dict | None:
    end = date.today() - timedelta(days=3)  # POWER has a few days of latency
    start = end - timedelta(days=days - 1)
    params = {
        "parameters": "T2M,PRECTOTCORR,RH2M", "community": "AG",
        "latitude": lat, "longitude": lon,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON",
    }
    try:
        r = httpx.get(URL, params=params, timeout=timeout)
        r.raise_for_status()
        p = r.json()["properties"]["parameter"]
        clean = lambda series: [v for v in series.values() if v is not None and v > -900]
        t, rain, rh = clean(p["T2M"]), clean(p["PRECTOTCORR"]), clean(p["RH2M"])
        if not (t and rain and rh):
            return None
        return {
            "avg_temp_c": round(sum(t) / len(t), 2),
            "rainfall_mm_30d": round(sum(rain), 1),
            "humidity_pct": round(sum(rh) / len(rh), 1),
            "window": f"{start.isoformat()} to {end.isoformat()}",
        }
    except Exception:
        return None
