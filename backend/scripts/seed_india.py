"""Add sample fields across India.  Run while the backend is running:  python scripts/seed_india.py"""
import json
import random
import urllib.request

API = "http://localhost:8000"
rng = random.Random(65)

# climate -> (ndvi, trend, temp, humidity, rain30, moisture)
CLIMATE = {
    "humid": ((0.58, 0.74), (-0.04, 0.02), (25, 29), (66, 80), (80, 160), (0.26, 0.34)),
    "cool":  ((0.62, 0.78), (-0.01, 0.03), (16, 22), (50, 70), (20, 70), (0.22, 0.30)),
    "dry":   ((0.42, 0.60), (-0.05, 0.01), (29, 35), (40, 60), (15, 70), (0.12, 0.22)),
    "mild":  ((0.58, 0.74), (-0.03, 0.03), (23, 28), (55, 75), (60, 120), (0.22, 0.32)),
}

# name, district, state, crop, lat, lon, area_ha, climate
FIELDS = [
    ("Amritsar Wheat Farm", "Amritsar", "Punjab", "wheat", 31.63, 74.87, 7.5, "cool"),
    ("Karnal Wheat Farm", "Karnal", "Haryana", "wheat", 29.69, 76.99, 6.0, "cool"),
    ("Lucknow Wheat Plot", "Lucknow", "Uttar Pradesh", "wheat", 26.85, 80.95, 5.2, "cool"),
    ("Varanasi Paddy Field", "Varanasi", "Uttar Pradesh", "rice", 25.32, 82.97, 4.0, "humid"),
    ("Patna Paddy Field", "Patna", "Bihar", "rice", 25.59, 85.14, 3.6, "humid"),
    ("Burdwan Paddy Field", "Purba Bardhaman", "West Bengal", "rice", 23.23, 87.86, 5.8, "humid"),
    ("Cuttack Paddy Field", "Cuttack", "Odisha", "rice", 20.46, 85.88, 4.4, "humid"),
    ("Jorhat Paddy Field", "Jorhat", "Assam", "rice", 26.75, 94.20, 3.9, "humid"),
    ("Raipur Paddy Field", "Raipur", "Chhattisgarh", "rice", 21.25, 81.63, 6.3, "humid"),
    ("Indore Maize Plot", "Indore", "Madhya Pradesh", "maize", 22.72, 75.86, 5.5, "mild"),
    ("Vidisha Wheat Farm", "Vidisha", "Madhya Pradesh", "wheat", 23.52, 77.81, 6.8, "cool"),
    ("Ganganagar Cotton Field", "Sri Ganganagar", "Rajasthan", "cotton", 29.92, 73.88, 9.0, "dry"),
    ("Kota Maize Plot", "Kota", "Rajasthan", "maize", 25.21, 75.86, 4.8, "dry"),
    ("Rajkot Cotton Field", "Rajkot", "Gujarat", "cotton", 22.30, 70.80, 8.2, "dry"),
    ("Anand Maize Plot", "Anand", "Gujarat", "maize", 22.56, 72.95, 3.5, "mild"),
    ("Nagpur Cotton Field", "Nagpur", "Maharashtra", "cotton", 21.15, 79.09, 7.7, "dry"),
    ("Warangal Cotton Field", "Warangal", "Telangana", "cotton", 17.97, 79.59, 6.4, "dry"),
    ("Nizamabad Paddy Field", "Nizamabad", "Telangana", "rice", 18.67, 78.09, 4.6, "humid"),
    ("Guntur Cotton Field", "Guntur", "Andhra Pradesh", "cotton", 16.31, 80.44, 8.8, "humid"),
    ("Krishna Delta Paddy", "Krishna", "Andhra Pradesh", "rice", 16.61, 80.72, 5.1, "humid"),
    ("Coimbatore Maize Plot", "Coimbatore", "Tamil Nadu", "maize", 11.02, 76.96, 4.2, "mild"),
    ("Palakkad Paddy Field", "Palakkad", "Kerala", "rice", 10.78, 76.65, 2.9, "humid"),
    ("Solan Tomato Farm", "Solan", "Himachal Pradesh", "tomato", 30.91, 77.10, 1.2, "mild"),
]


def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def obs_for(crop, climate):
    (nd, tr, tp, hu, ra, mo) = CLIMATE[climate]
    u = lambda lohi, d=2: round(rng.uniform(*lohi), d)
    return dict(crop=crop, ndvi=u(nd), ndvi_trend=u(tr, 3), soil_ph=round(rng.uniform(5.9, 7.6), 1),
                soil_organic_carbon=round(rng.uniform(0.6, 1.4), 1), soil_moisture=u(mo),
                rainfall_mm_30d=round(rng.uniform(*ra)), avg_temp_c=u(tp, 1), humidity_pct=round(rng.uniform(*hu)))


if __name__ == "__main__":
    existing = {f["name"] for f in call("/fields")}
    added = 0
    for name, district, state, crop, lat, lon, area, climate in FIELDS:
        if name in existing:
            continue
        call("/fields", dict(name=name, district=district, state=state, lat=lat, lon=lon, area_ha=area, observation=obs_for(crop, climate)))
        added += 1
    fields = call("/fields")
    print(f"Added {added} fields. Total now {len(fields)} across {len({f['state'] for f in fields})} states.")
    print("High:", sum(f['pest']['level'] == 'High' for f in fields), "| Medium:", sum(f['pest']['level'] == 'Medium' for f in fields), "| Low:", sum(f['pest']['level'] == 'Low' for f in fields))