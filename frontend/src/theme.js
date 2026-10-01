// Shared chart styling helpers
export const GRID = "#2d4433";
export const LEVELS = ["Low", "Medium", "High"];
export const RISK_SCALE = [[0, "#4caf50"], [0.5, "#f5b301"], [1, "#e53935"]];
export const CROP_COLOR = { rice: "#64b5f6", wheat: "#ffd54f", maize: "#ffb74d", cotton: "#e0e0e0", tomato: "#ef5350" };
export const FEATURE_SHORT = {
  ndvi: "NDVI", ndvi_trend: "NDVI trend", soil_ph: "Soil pH", soil_organic_carbon: "Organic C",
  soil_moisture: "Soil moisture", rainfall_mm_30d: "Rainfall", avg_temp_c: "Temperature", humidity_pct: "Humidity",
};
export const mean = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : 0);
export const fmt = (n, d = 0) => Number(n).toLocaleString("en-IN", { maximumFractionDigits: d });