# AgriPulse: Localized Crop Yield & Pest Early-Warning Intelligence

**HackConquest Hackathon 2026 · Team HCQ_G65 · Theme: AI for Sustainable Agriculture · PS 05: AI-Based Crop Yield & Pest Prediction**

> **Sense the field. Predict the risk. Act before the loss.**

![AgriPulse dashboard](docs/dashboard.png)

AgriPulse turns satellite, soil, weather and crop data into **field-level yield and pest-risk predictions**, explains *why* each prediction was made, and converts it into **specific actions** for irrigation, pest prevention and resource planning.

```
Sense  ->  Predict  ->  Explain  ->  Act
```

## Features

- **Predict:** Random Forest models estimate yield (t/ha) and pest risk (Low / Medium / High, plus a 0-1 risk index) with confidence scores.
- **Explain:** every prediction shows which factors (humidity, rainfall, NDVI trend, soil moisture...) pushed it up or down.
- **Act:** a rule engine turns predictions into prioritised, field-specific recommendations.
- **Live data:** one click pulls real **NASA POWER** weather and **NASA MODIS** satellite NDVI for a field's location. **ISRIC SoilGrids** soil data is supported on a best-effort basis, because that service is sometimes slow or unavailable. If a source fails, the app keeps the previous values and says so.
- **Dashboard (React + Plotly):**
  - **Overview:** risk distribution, state-level risk, expected production, and a "needs attention first" list.
  - **Compare:** bubble chart with selectable axes, crop-by-state risk heatmap, yield vs crop-typical.
  - **Field explorer:** risk map, gauges, driver charts, peer radar, 12-week trend with a 4-week outlook, and a **what-if simulator**.
- **API (FastAPI):** ranked field list, what-if predictions, regional summary, live-data refresh, and interactive docs at `/docs`.
- **Quality:** automated tests (pytest) and GitHub Actions CI. Docker Compose with PostgreSQL/PostGIS.

## How the deck maps to the code

| Idea | Implementation |
|---|---|
| Sense: satellite + soil + weather | `backend/app/data.py` (feature schema), `weather.py` (NASA POWER), `satellite.py` (MODIS NDVI, SoilGrids) |
| Predict: yield + pest risk | `backend/app/model.py` (Random Forest regressor and classifier) |
| Confidence + human validation | tree-spread yield confidence, class-probability pest confidence, advisory disclaimer on every response |
| Explain: main drivers | occlusion analysis in `model.explain` |
| Act: localized recommendations | `backend/app/recommend.py` |
| Advisors / FPOs: prioritise | `GET /fields` ranked by risk, Overview and Compare tabs |
| Resource planners | `GET /regions/summary`: area, expected output, high-risk fields per state |
| Early warning | 4-week risk outlook (trend projection) in `service.forecast_risk` |

## Architecture

```mermaid
flowchart LR
  A[Satellite NDVI<br/>NASA MODIS] --> F
  B[Weather<br/>NASA POWER] --> F
  C[Soil<br/>ISRIC SoilGrids] --> F
  F[Fuse & feature engineering] --> M[Yield model + Pest-risk model]
  M --> X[Explainability<br/>driver analysis]
  X --> R[Recommendation engine]
  R --> API[FastAPI]
  API <--> DB[(SQLite / PostgreSQL-PostGIS)]
  API --> UI[React dashboard<br/>map, charts, what-if]
```

## Quick start

### Option A: Docker (backend + frontend + PostgreSQL/PostGIS)
```bash
docker compose up --build
# Dashboard: http://localhost:8080     API docs: http://localhost:8000/docs
```

### Option B: Local (Windows PowerShell / macOS / Linux)

**Backend**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload         # http://localhost:8000/docs (models train automatically on first start)
```

**Frontend** (new terminal)
```powershell
cd frontend
npm install
npm run dev                           # http://localhost:5173
```

**Useful scripts** (run from `backend`, with the backend running for the first one)
```powershell
python scripts/seed_india.py          # adds 23 sample fields across Indian states
python -m scripts.check_live          # tests NASA POWER, MODIS and SoilGrids from your machine
pytest -q                             # run the tests
```

SQLite is used by default. To use PostgreSQL set `DATABASE_URL`, e.g. `postgresql+psycopg2://user:pass@localhost:5432/agripulse`.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/fields` | All fields with yield, pest risk, drivers and actions, ranked by risk |
| GET | `/fields/{id}` | One field's full analysis |
| POST | `/fields` | Register a field with its latest observation |
| POST | `/fields/{id}/refresh-weather` | Last 30 days of weather from NASA POWER, then re-predict |
| POST | `/fields/{id}/refresh-satellite` | MODIS NDVI and SoilGrids soil, then re-predict |
| GET | `/fields/{id}/timeline` | 12-week history and 4-week outlook (**simulated** demo history) |
| POST | `/predict` | Stateless what-if prediction |
| GET | `/regions/summary` | Production and risk aggregated by state |
| GET | `/model/info`, `/meta`, `/health` | Metrics, feature ranges, health |

## Honest limitations

- **Training data is synthetic.** It is generated from agronomic rules (`app/data.py`) so the platform runs without large downloads. The reported metrics (about 86% pest-risk accuracy) are measured against those rules and show that the pipeline works, **not** real-world accuracy.
- **Sample fields are illustrative.** Live weather and satellite values are real for each field's coordinates, but the fields themselves are example locations.
- **The 12-week history and 4-week outlook are demo-level:** history is simulated and the outlook is a linear trend projection.
- **Satellite source:** NASA MODIS (250 m, 16-day composites) is used because it needs no login. Sentinel-2 (10 m) is the planned higher-resolution upgrade.
- **Not yet integrated:** FAOSTAT historical yields. Retrain on real data with `python -m scripts.train --csv your_data.csv` (columns are listed in `scripts/train.py`).
- Recommendations are decision support and should be validated with a local agronomist.

## Roadmap
Pilot region → multiple districts → multi-crop intelligence → mobile + voice assistant → IoT sensor integration → continuous model learning.

## Team
Team **HCQ_G65**. Leader: Pandiri Sivaramakrishna. HackConquest Hackathon 2026. License: MIT