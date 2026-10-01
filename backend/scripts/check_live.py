"""Check the live data sources from YOUR machine.   Run from /backend:  python -m scripts.check_live"""
import logging

import httpx

from app import satellite, weather

logging.basicConfig(level=logging.WARNING, format="  ! %(message)s")
LAT, LON = 12.52, 76.90   # Mandya, Karnataka


def show(title, value):
    print(f"\n{title}\n  ->", value if value else "FAILED (see the '!' line above, if any)")


show("NASA POWER weather", weather.fetch_nasa_power(LAT, LON))
show("MODIS NDVI (ORNL DAAC)", satellite.fetch_modis_ndvi(LAT, LON))
show("SoilGrids topsoil (ISRIC)", satellite.fetch_soilgrids(LAT, LON))

# If MODIS failed, show the raw server answer so the problem is visible
if satellite.fetch_modis_ndvi(LAT, LON) is None:
    from datetime import date, timedelta
    end = date.today() - timedelta(days=20)
    r = httpx.get(satellite.MODIS_URL, timeout=30, headers={"Accept": "application/json"}, params={
        "latitude": LAT, "longitude": LON, "band": satellite.NDVI_BAND, "kmAboveBelow": 1, "kmLeftRight": 1,
        "startDate": satellite._modis_day(end - timedelta(days=100)), "endDate": satellite._modis_day(end)})
    print("\nRaw MODIS reply:", r.status_code, r.text[:400])