# AgriPulse — Localized Crop Yield & Pest Early-Warning Intelligence

**HackConquest Hackathon 2026 · Team HCQ_G65 · Theme: AI for Sustainable Agriculture · PS 05 — AI-Based Crop Yield & Pest Prediction**

> **Sense the field. Predict the risk. Act before the loss.**

AgriPulse turns satellite, soil, weather and crop data into **field-level yield and pest-risk predictions**, explains *why* each prediction was made, and converts it into **specific actions** for irrigation, pest prevention and resource planning.

```
Sense  ->  Predict  ->  Explain  ->  Act
```

## What's in the box

| Deck idea | Implementation |
|---|---|
| **Sense** — satellite + soil + weather + crop data | `backend/app/data.py` feature schema (NDVI, NDVI trend, soil pH / organic carbon / moisture, 30-day rainfall, temperature, humidity). Live weather via **NASA POWER** (`app/weather.py`). |
| **Predict** — yield + pest/disease risk | `backend/app/model.py`: Random Forest regressor (yield t/ha) and classifier (Low/Medium/High pest risk, plus a 0-1 risk index). |
| **Confidence + human validation** (risk table) | Yield confidence from tree-to-tree spread, pest confidence from class probability, and a decision-support disclaimer on every response. |
| **Explain** — main drivers | Occlusion explanations: each feature is swapped for its crop-typical value and the change in prediction is reported (`model.explain`). |
| **Act** — localized recommendations | Rule engine in `app/recommend.py` (pest, irrigation, soil, resource planning), prioritized High → Low. |
| **Advisors / FPOs** — prioritize interventions | `GET /fields` returns fields ranked by risk; dashboard priority list + map. |
| **Resource planners** — production & resources | `GET /regions/summary`: area, expected output and high-risk fields per state. |
| **Modular: new crops/regions** | Add a crop in `CROP_PROFILES`, retrain, done. Add fields via `POST /fields`. |
| **Tech stack** | Python, Pandas, NumPy, scikit-learn · FastAPI · PostgreSQL/PostGIS · React + Plotly maps/charts · Docker |

## Architecture

```mermaid
flowchart LR
  A[Satellite NDVI<br/>Sentinel-2] --> F
  B[Weather<br/>NASA POWER] --> F
  C[Soil<br/>SoilGrids] --> F
  D[Crop history<br/>FAOSTAT] --> F
  F[Fuse & feature engineering] --> M[Yield model + Pest-risk model]
  M --> X[Explainability<br/>driver analysis]
  X --> R[Recommendation engine]
  R --> API[FastAPI]
  API <--> DB[(PostgreSQL / PostGIS)]
  API --> UI[React dashboard<br/>map, charts, what-if]
```

## Quick start

### Option A — Docker (everything, incl. PostgreSQL/PostGIS)
```bash
docker compose up --build
# Dashboard: http://localhost:8080     API docs: http://localhost:8000/docs
```

### Option B — Local (Windows PowerShell / macOS / Linux)

**Backend**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.train               # trains models (~10 s); also auto-trains on first start
uvicorn app.main:app --reload         # http://localhost:8000/docs
pytest -q                             # run tests
```

**Frontend** (new terminal)
```powershell
cd frontend
npm install
npm run dev                           # http://localhost:5173  (proxies /api -> :8000)
```

SQLite is used by default. To use PostgreSQL set `DATABASE_URL`, e.g. `postgresql+psycopg2://user:pass@localhost:5432/agripulse`.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/fields` | All fields with yield, pest risk, drivers, actions — **ranked by risk** |
| GET | `/fields/{id}` | One field's full analysis |
| POST | `/fields` | Register a field with its latest observation |
| POST | `/fields/{id}/refresh-weather` | Pull last 30 days from NASA POWER and re-predict |
| GET | `/fields/{id}/timeline` | 12-week risk trend (**simulated** history for the demo) |
| POST | `/predict` | Stateless what-if prediction |
| GET | `/regions/summary` | Aggregated production/risk by state |
| GET | `/model/info`, `/meta`, `/health` | Metrics, feature ranges, health |

Example:
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{
  "crop":"rice","ndvi":0.55,"ndvi_trend":-0.05,"soil_ph":6.4,"soil_organic_carbon":1.1,
  "soil_moisture":0.33,"rainfall_mm_30d":165,"avg_temp_c":28,"humidity_pct":86}'
```

## Honest limitations (please read before presenting)

- **Training data is synthetic.** It is generated from agronomic rules (`app/data.py`) so the platform runs without credentials or large downloads. The reported metrics (`/model/info`) are therefore measured against those rules — they show the pipeline works, **not** real-world accuracy.
- **Demo fields are illustrative**, and the 12-week timeline is simulated.
- **Live data:** only NASA POWER weather is wired in. Sentinel-2 NDVI, SoilGrids and FAOSTAT are the intended sources; plug them in by writing a fetcher that returns the same feature columns as `NUMERIC` in `app/data.py`, or retrain on real data with `python -m scripts.train --csv your_data.csv` (columns listed in `scripts/train.py`).
- PostGIS is enabled in the Docker database for future spatial queries; coordinates are currently stored as lat/lon columns.
- Recommendations are decision support and should be validated with a local agronomist.

## Roadmap (from the deck)
Pilot region → multiple districts → multi-crop intelligence → mobile + voice assistant → IoT sensor integration → continuous model learning.

## Team
Team **HCQ_G65** — Leader: Pandiri Sivaramakrishna · HackConquest Hackathon 2026 · License: MIT
