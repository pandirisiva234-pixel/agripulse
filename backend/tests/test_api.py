from app import weather

OBS = dict(crop="rice", ndvi=0.6, ndvi_trend=0.0, soil_ph=6.3, soil_organic_carbon=1.0,
           soil_moisture=0.28, rainfall_mm_30d=80, avg_temp_c=27, humidity_pct=65)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["model_metrics"]["yield_r2"] > 0.9


def test_meta(client):
    m = client.get("/meta").json()
    assert "rice" in m["crops"] and len(m["features"]) == 8


def test_predict_shape(client):
    r = client.post("/predict", json=OBS).json()
    assert r["pest"]["level"] in {"Low", "Medium", "High"}
    assert r["yield"]["value_t_ha"] > 0
    assert len(r["drivers"]["pest"]) == 5 and r["recommendations"]


def test_predict_validation(client):
    assert client.post("/predict", json={**OBS, "crop": "banana"}).status_code == 422
    assert client.post("/predict", json={**OBS, "humidity_pct": 150}).status_code == 422


def test_humid_warm_raises_pest_risk(client):
    dry = client.post("/predict", json={**OBS, "humidity_pct": 40, "rainfall_mm_30d": 10}).json()
    wet = client.post("/predict", json={**OBS, "humidity_pct": 92, "rainfall_mm_30d": 220, "ndvi_trend": -0.08}).json()
    assert wet["pest"]["risk_index"] > dry["pest"]["risk_index"]


def test_fields_ranked_by_risk(client):
    fields = client.get("/fields").json()
    assert len(fields) >= 7
    risks = [f["pest"]["risk_index"] for f in fields]
    assert risks == sorted(risks, reverse=True)


def test_field_detail_timeline_regions(client):
    fid = client.get("/fields").json()[0]["id"]
    assert client.get(f"/fields/{fid}").status_code == 200
    tl = client.get(f"/fields/{fid}/timeline").json()
    assert tl["simulated"] and len(tl["points"]) == 12
    assert client.get("/regions/summary").json()[0]["fields"] >= 1
    assert client.get("/fields/99999").status_code == 404


def test_create_field(client):
    body = dict(name="Test plot", lat=12.9, lon=77.6, area_ha=2, observation=OBS)
    r = client.post("/fields", json=body)
    assert r.status_code == 201 and r.json()["name"] == "Test plot"


def test_refresh_weather_live_and_failure(client, monkeypatch):
    fid = client.get("/fields").json()[0]["id"]
    monkeypatch.setattr(weather, "fetch_nasa_power", lambda lat, lon: {"avg_temp_c": 30.0, "rainfall_mm_30d": 12.0, "humidity_pct": 55.0, "window": "x to y"})
    r = client.post(f"/fields/{fid}/refresh-weather")
    assert r.status_code == 200 and r.json()["observation"]["avg_temp_c"] == 30.0
    monkeypatch.setattr(weather, "fetch_nasa_power", lambda lat, lon: None)
    assert client.post(f"/fields/{fid}/refresh-weather").status_code == 502
