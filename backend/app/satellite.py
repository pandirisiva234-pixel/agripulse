"""Real satellite NDVI + topsoil data. No API keys needed.

* NDVI  : NASA MODIS MOD13Q1 (250 m, 16-day composites) via the ORNL DAAC web service.
* Soil  : ISRIC SoilGrids 2.0 (250 m), pH and organic carbon of the top 30 cm.

Every fetcher returns None on any failure (and logs why) so callers keep the existing values.
"""
from __future__ import annotations

import logging
import statistics
from datetime import date, timedelta

import httpx

log = logging.getLogger("agripulse.satellite")

MODIS_URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
SOIL_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
NDVI_BAND = "250m_16_days_NDVI"
SOIL_DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}      # label -> thickness (cm), for weighting
SOIL_FACTOR = {"phh2o": 10.0, "soc": 10.0}                   # fallback if the response has no d_factor


def _clip(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def _modis_day(d: date) -> str:
    return f"A{d.year}{d.timetuple().tm_yday:03d}"


# ---------------------------------------------------------------- NDVI (MODIS)
def parse_modis(payload: dict) -> dict | None:
    """Turn an ORNL MOD13Q1 subset response into {ndvi, ndvi_trend, ndvi_date}."""
    scale = float(payload.get("scale") or 0.0001)
    by_date: dict[str, float] = {}
    for item in payload.get("subset", []):
        # valid MOD13Q1 NDVI is -2000..10000; -3000 is the no-data fill value
        px = [v for v in item.get("data", []) if v is not None and -2000 <= v <= 10000]
        if px:  # median of the surrounding pixels is robust to roads, water and cloud edges
            by_date[item.get("calendar_date") or item.get("modis_date")] = statistics.median(px) * scale
    if not by_date:
        return None
    days = sorted(by_date)
    latest = days[-1]
    out = {"ndvi": round(_clip(by_date[latest], 0.05, 0.95), 3), "ndvi_date": latest}
    if len(days) >= 2:
        prev = days[-2]
        try:
            gap = (date.fromisoformat(latest) - date.fromisoformat(prev)).days or 16
        except ValueError:
            gap = 16
        trend = (by_date[latest] - by_date[prev]) * 14 / gap      # normalise to a 2-week change
        out["ndvi_trend"] = round(_clip(trend, -0.3, 0.3), 3)
    return out


def fetch_modis_ndvi(lat: float, lon: float, timeout: float = 30.0) -> dict | None:
    end = date.today() - timedelta(days=20)   # composites appear a couple of weeks after acquisition
    start = end - timedelta(days=100)
    params = {
        "latitude": lat, "longitude": lon, "band": NDVI_BAND,
        "startDate": _modis_day(start), "endDate": _modis_day(end),
        "kmAboveBelow": 1, "kmLeftRight": 1,
    }
    try:
        r = httpx.get(MODIS_URL, params=params, headers={"Accept": "application/json"}, timeout=timeout)
        r.raise_for_status()
        return parse_modis(r.json())
    except Exception as e:
        log.warning("MODIS NDVI fetch failed: %r", e)
        return None


# ---------------------------------------------------------------- soil (SoilGrids)
def parse_soilgrids(payload: dict) -> dict | None:
    """Turn a SoilGrids properties/query response into {soil_ph, soil_organic_carbon (%)}."""
    vals: dict[str, float] = {}
    for layer in payload.get("properties", {}).get("layers", []):
        name = layer.get("name")
        factor = float((layer.get("unit_measure") or {}).get("d_factor") or SOIL_FACTOR.get(name, 1.0))
        num = den = 0.0
        for d in layer.get("depths", []):
            m = (d.get("values") or {}).get("mean")
            if m is None:
                continue
            w = SOIL_DEPTHS.get(d.get("label"), 1)
            num, den = num + m * w, den + w
        if den:
            vals[name] = num / den / factor           # pH, or soc in g/kg
    out = {}
    if "phh2o" in vals:
        out["soil_ph"] = round(_clip(vals["phh2o"], 3.5, 9.5), 1)
    if "soc" in vals:
        out["soil_organic_carbon"] = round(_clip(vals["soc"] / 10, 0.1, 6.0), 2)   # g/kg -> %
    return out or None


_SOIL_CACHE: dict[tuple[float, float], dict] = {}   # soil barely changes, so remember good answers


def fetch_soilgrids(lat: float, lon: float, timeout: float = 8.0) -> dict | None:
    key = (round(lat, 2), round(lon, 2))
    if key in _SOIL_CACHE:
        return dict(_SOIL_CACHE[key])
    params = [("lon", lon), ("lat", lat), ("property", "phh2o"), ("property", "soc"), ("value", "mean")]
    params += [("depth", d) for d in SOIL_DEPTHS]
    try:
        r = httpx.get(SOIL_URL, params=params, timeout=timeout)
        if r.status_code == 429:
            log.warning("SoilGrids rate limit hit (fair use is ~5 calls/min). Wait a minute and retry.")
            return None
        r.raise_for_status()
        out = parse_soilgrids(r.json())
    except httpx.TimeoutException:
        log.warning("SoilGrids did not answer within %ss. The ISRIC REST API is a beta service and is often slow or down.", timeout)
        return None
    except Exception as e:
        log.warning("SoilGrids fetch failed: %r", e)
        return None
    if out:
        _SOIL_CACHE[key] = out
    return dict(out) if out else None