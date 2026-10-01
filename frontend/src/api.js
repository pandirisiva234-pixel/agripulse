const BASE = import.meta.env.VITE_API_URL || "/api";

async function req(path, opts) {
  const r = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch { /* ignore */ }
    throw new Error(typeof msg === "string" ? msg : "Request failed");
  }
  return r.json();
}

export const api = {
  meta: () => req("/meta"),
  fields: () => req("/fields"),
  timeline: (id) => req(`/fields/${id}/timeline`),
  regions: () => req("/regions/summary"),
  predict: (obs) => req("/predict", { method: "POST", body: JSON.stringify(obs) }),
  refreshWeather: (id) => req(`/fields/${id}/refresh-weather`, { method: "POST" }),
  refreshSatellite: (id) => req(`/fields/${id}/refresh-satellite`, { method: "POST" }),
  modelInfo: () => req("/model/info"),
};