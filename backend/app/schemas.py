from typing import Literal

from pydantic import BaseModel, Field

Crop = Literal["rice", "wheat", "maize", "cotton", "tomato"]


class Observation(BaseModel):
    """One field observation: satellite (NDVI), soil, weather."""
    crop: Crop
    ndvi: float = Field(ge=0.05, le=0.95, description="Sentinel-2 NDVI")
    ndvi_trend: float = Field(ge=-0.3, le=0.3, description="NDVI change over 2 weeks")
    soil_ph: float = Field(ge=3.5, le=9.5)
    soil_organic_carbon: float = Field(ge=0.1, le=6.0, description="percent")
    soil_moisture: float = Field(ge=0.02, le=0.6, description="volumetric m3/m3")
    rainfall_mm_30d: float = Field(ge=0, le=600)
    avg_temp_c: float = Field(ge=0, le=50)
    humidity_pct: float = Field(ge=5, le=100)


class FieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    district: str = "Unknown"
    state: str = "Unknown"
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    area_ha: float = Field(gt=0, le=100000)
    observation: Observation
