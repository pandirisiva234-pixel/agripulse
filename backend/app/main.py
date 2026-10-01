"""AgriPulse API.  Run: uvicorn app.main:app --reload"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import satellite, service, weather
from .data import DEMO_FIELDS
from .db import FieldRow, PredictionLog, get_session, init_db
from .model import AgriModel
from .schemas import FieldCreate, Observation

_model: AgriModel | None = None


def model() -> AgriModel:
    global _model
    if _model is None:
        _model = AgriModel.load_or_train()
    return _model


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(DEMO_FIELDS)
    model()
    yield


app = FastAPI(
    title="AgriPulse API",
    version="1.0.0",
    description="Sense -> Predict -> Explain -> Act. Localized crop yield & pest early-warning intelligence.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])


def _summary(f: FieldRow, analysis: dict) -> dict:
    return {
        "id": f.id, "name": f.name, "district": f.district, "state": f.state, "crop": f.crop,
        "lat": f.lat, "lon": f.lon, "area_ha": f.area_ha, "updated_at": f.updated_at,
        "expected_production_t": round(analysis["yield"]["value_t_ha"] * f.area_ha, 1),
        **analysis,
    }


def _get(s: Session, field_id: int) -> FieldRow:
    f = s.get(FieldRow, field_id)
    if not f:
        raise HTTPException(404, "Field not found")
    return f


def _analyze_field(s: Session, f: FieldRow, log: bool = False) -> dict:
    a = service.analyze(model(), {"crop": f.crop, **f.obs})
    if log:
        s.add(PredictionLog(field_id=f.id, yield_t_ha=a["yield"]["value_t_ha"], pest_level=a["pest"]["level"], risk_index=a["pest"]["risk_index"]))
        s.commit()
    return _summary(f, a)


@app.get("/health")
def health():
    return {"status": "ok", "model_metrics": model().metrics}


@app.get("/meta")
def meta():
    return service.meta()


@app.get("/model/info")
def model_info():
    return {"metrics": model().metrics, "note": "Metrics are on a held-out split of the training data (synthetic by default)."}


@app.post("/predict")
def predict(obs: Observation):
    """Stateless what-if prediction for any observation."""
    return service.analyze(model(), obs.model_dump())


@app.get("/fields")
def list_fields(s: Session = Depends(get_session)):
    """All fields ranked by pest-risk (highest first) - the advisor's priority list."""
    items = [_analyze_field(s, f) for f in s.query(FieldRow).all()]
    return sorted(items, key=lambda x: x["pest"]["risk_index"], reverse=True)


@app.post("/fields", status_code=201)
def create_field(body: FieldCreate, s: Session = Depends(get_session)):
    obs = body.observation.model_dump()
    f = FieldRow(name=body.name, district=body.district, state=body.state, crop=obs.pop("crop"),
                 lat=body.lat, lon=body.lon, area_ha=body.area_ha, obs=obs)
    s.add(f)
    s.commit()
    return _analyze_field(s, f, log=True)


@app.get("/fields/{field_id}")
def get_field(field_id: int, s: Session = Depends(get_session)):
    return _analyze_field(s, _get(s, field_id), log=True)


@app.get("/fields/{field_id}/timeline")
def field_timeline(field_id: int, s: Session = Depends(get_session)):
    f = _get(s, field_id)
    points = service.build_timeline(model(), {"crop": f.crop, **f.obs}, seed=f.id)
    return {"simulated": True, "points": points, "forecast": service.forecast_risk(points)}


@app.post("/fields/{field_id}/refresh-weather")
def refresh_weather(field_id: int, s: Session = Depends(get_session)):
    """Replace weather inputs with the last 30 days from NASA POWER, then re-predict."""
    f = _get(s, field_id)
    live = weather.fetch_nasa_power(f.lat, f.lon)
    if live is None:
        raise HTTPException(502, "Could not reach NASA POWER; keeping existing weather values.")
    window = live.pop("window")
    f.obs = {**f.obs, **live}
    s.commit()
    out = _analyze_field(s, f, log=True)
    out["weather_window"] = window
    return out


@app.post("/fields/{field_id}/refresh-satellite")
def refresh_satellite(field_id: int, s: Session = Depends(get_session)):
    """Replace NDVI + soil inputs with real MODIS NDVI and SoilGrids topsoil values, then re-predict."""
    f = _get(s, field_id)
    with ThreadPoolExecutor(max_workers=2) as ex:
        ndvi_job = ex.submit(satellite.fetch_modis_ndvi, f.lat, f.lon)
        soil_job = ex.submit(satellite.fetch_soilgrids, f.lat, f.lon)
        ndvi, soil = ndvi_job.result(), soil_job.result()
    if ndvi is None and soil is None:
        raise HTTPException(502, "Could not reach MODIS / SoilGrids; keeping existing values.")
    updates, used, missing = {}, {}, []
    if ndvi:
        ndvi = dict(ndvi)
        used["ndvi"] = f"MODIS NDVI composite {ndvi.pop('ndvi_date')}"
        updates.update(ndvi)
    else:
        missing.append("NDVI")
    if soil:
        updates.update(soil)
        used["soil"] = "SoilGrids topsoil (0-30 cm)"
    else:
        missing.append("soil")
    f.obs = {**f.obs, **updates}
    s.commit()
    out = _analyze_field(s, f, log=True)
    out["satellite_sources"], out["satellite_missing"] = used, missing
    return out


@app.get("/regions/summary")
def regions(s: Session = Depends(get_session)):
    """Resource-planner view: production, area and risk aggregated by state."""
    agg: dict[str, dict] = {}
    for f in (_analyze_field(s, r) for r in s.query(FieldRow).all()):
        g = agg.setdefault(f["state"], dict(state=f["state"], fields=0, area_ha=0.0, expected_production_t=0.0, high_risk_fields=0, _risk=0.0))
        g["fields"] += 1
        g["area_ha"] += f["area_ha"]
        g["expected_production_t"] += f["expected_production_t"]
        g["high_risk_fields"] += f["pest"]["level"] == "High"
        g["_risk"] += f["pest"]["risk_index"]
    out = []
    for g in agg.values():
        g["avg_risk_index"] = round(g.pop("_risk") / g["fields"], 3)
        g["area_ha"] = round(g["area_ha"], 1)
        g["expected_production_t"] = round(g["expected_production_t"], 1)
        out.append(g)
    return sorted(out, key=lambda x: x["avg_risk_index"], reverse=True)