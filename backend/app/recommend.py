"""Rule-based action engine: turns predictions + drivers into localized recommendations."""
from __future__ import annotations

from .data import CROP_PROFILES

_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def recommend(obs: dict, analysis: dict) -> list[dict]:
    recs: list[dict] = []
    add = lambda cat, pri, action, why: recs.append(dict(category=cat, priority=pri, action=action, reason=why))
    pest = analysis["pest"]["level"]
    y = analysis["yield"]["value_t_ha"]
    typical = CROP_PROFILES[obs["crop"]]["base"]

    # Pest & disease
    if pest == "High":
        add("Pest & disease", "High", "Scout the field within 48 hours and start integrated pest management (traps, targeted bio/chemical control as advised locally).",
            f"Pest risk is High ({analysis['pest']['probabilities']['High']:.0%} probability).")
    elif pest == "Medium":
        add("Pest & disease", "Medium", "Increase scouting to twice a week and place pheromone/sticky traps.", "Pest risk is Medium and could escalate.")
    else:
        add("Pest & disease", "Low", "Continue routine weekly scouting.", "Pest risk is Low.")
    if obs["humidity_pct"] >= 80 and 20 <= obs["avg_temp_c"] <= 32:
        add("Pest & disease", "High" if pest == "High" else "Medium", "Improve canopy airflow and avoid evening overhead irrigation to limit fungal disease.",
            f"Humidity {obs['humidity_pct']:.0f}% with {obs['avg_temp_c']:.0f} C favours fungal/bacterial spread.")
    if obs["ndvi_trend"] <= -0.04:
        add("Crop health", "High" if pest != "Low" else "Medium", "Inspect the canopy for water, nutrient or pest stress in the affected zone.",
            f"NDVI is falling ({obs['ndvi_trend']:+.2f} over 2 weeks).")

    # Irrigation
    if obs["soil_moisture"] < 0.18:
        add("Irrigation", "High", "Irrigate now; prefer drip/short frequent cycles to reduce loss.", f"Soil moisture is low ({obs['soil_moisture']:.2f} m3/m3).")
    elif obs["soil_moisture"] > 0.38 or obs["rainfall_mm_30d"] > 180:
        add("Irrigation", "Medium", "Hold irrigation, check drainage and delay top-dressing fertilizer.", "Soil is wet or recent rainfall is high; waterlogging and nutrient leaching risk.")
    else:
        add("Irrigation", "Low", "Keep the current irrigation schedule.", "Soil moisture is in a healthy range.")

    # Soil
    if obs["soil_ph"] < 5.5:
        add("Soil", "Medium", "Take a soil test and consider liming to raise pH.", f"Soil is acidic (pH {obs['soil_ph']:.1f}).")
    elif obs["soil_ph"] > 7.8:
        add("Soil", "Medium", "Add organic matter/gypsum as per soil-test advice; choose tolerant varieties.", f"Soil is alkaline (pH {obs['soil_ph']:.1f}).")
    if obs["soil_organic_carbon"] < 0.6:
        add("Soil", "Medium", "Add compost/farmyard manure or green manure to build organic carbon.", f"Organic carbon is low ({obs['soil_organic_carbon']:.1f}%).")

    # Resource planning
    if y < 0.8 * typical:
        add("Resource planning", "Medium", f"Plan for a below-typical harvest (~{y:.1f} t/ha vs ~{typical:.1f} t/ha) when arranging labour, storage and sales.",
            "Predicted yield is more than 20% under the crop's typical level.")
    else:
        add("Resource planning", "Low", f"Expect ~{y:.1f} t/ha; plan storage and transport accordingly.", "Yield outlook is near or above typical.")

    return sorted(recs, key=lambda r: _ORDER[r["priority"]])
