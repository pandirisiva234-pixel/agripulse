import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api.js";
import PlotlyChart from "./PlotlyChart.jsx";
import { RISK_COLOR } from "./FieldMap.jsx";
import { FEATURE_SHORT, GRID } from "../theme.js";

const PRI_COLOR = { High: "#e53935", Medium: "#f5b301", Low: "#4caf50" };

function Drivers({ title, items, unit, goodPositive }) {
  const sorted = [...items].reverse();
  const data = [{
    type: "bar", orientation: "h",
    y: sorted.map((d) => `${d.label} (${d.value})`),
    x: sorted.map((d) => d.effect),
    marker: { color: sorted.map((d) => ((d.effect >= 0) === goodPositive ? "#81c784" : "#e57373")) },
    textposition: "none",
    text: sorted.map((d) => `${d.value} (typical ${d.typical})`),
    hovertemplate: "%{text}<br>effect %{x:+.3f}<extra></extra>",
  }];
  const layout = { margin: { l: 250, r: 16, t: 8, b: 32 }, xaxis: { title: unit, zeroline: true, gridcolor: "#2d4433" } };
  return (
    <div>
      <h4>{title}</h4>
      <PlotlyChart data={data} layout={layout} height={210} />
    </div>
  );
}

export default function Detail({ field, meta, allFields = [], onWeatherRefreshed }) {
  const baseObs = useMemo(() => ({ crop: field.crop, ...field.observation }), [field]);
  const [obs, setObs] = useState(baseObs);
  const [analysis, setAnalysis] = useState(field);
  const [timeline, setTimeline] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const timer = useRef(null);

  useEffect(() => { setObs(baseObs); setAnalysis(field); }, [baseObs, field]);
  useEffect(() => { api.timeline(field.id).then(setTimeline).catch(() => setTimeline(null)); }, [field.id, field.updated_at]);

  const changed = JSON.stringify(obs) !== JSON.stringify(baseObs);
  function update(key, value) {
    const next = { ...obs, [key]: value };
    setObs(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => api.predict(next).then(setAnalysis).catch((e) => setMsg(e.message)), 250);
  }
  function reset() { setObs(baseObs); setAnalysis(field); }

  async function refreshWeather() {
    setBusy(true); setMsg("");
    try {
      const r = await api.refreshWeather(field.id);
      setMsg(`Live NASA POWER weather applied (${r.weather_window}).`);
      onWeatherRefreshed();
    } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  }

  async function refreshSatellite() {
    setBusy(true); setMsg("");
    try {
      const r = await api.refreshSatellite(field.id);
      const used = Object.values(r.satellite_sources).join(" + ");
      const miss = r.satellite_missing.length ? ` (${r.satellite_missing.join(", ")} unavailable - kept previous values)` : "";
      setMsg(`Live data applied: ${used}${miss}.`);
      onWeatherRefreshed();
    } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  }

  const { pest, yield: y } = analysis;
  const probs = ["Low", "Medium", "High"].map((k) => pest.probabilities[k]);
  const typical = meta.typical_yield_t_ha[field.crop];

  // ---- gauges ----
  const riskPct = pest.risk_index * 100;
  const riskGauge = [{
    type: "indicator", mode: "gauge+number", value: riskPct, number: { suffix: "%", font: { size: 34 } },
    title: { text: `Pest risk index · ${pest.level}`, font: { size: 14 } },
    gauge: {
      axis: { range: [0, 100], tickcolor: "#8fa896" }, bar: { color: RISK_COLOR[pest.level], thickness: 0.35 },
      bgcolor: "rgba(0,0,0,0)", borderwidth: 0,
      steps: [{ range: [0, 33], color: "rgba(76,175,80,.22)" }, { range: [33, 66], color: "rgba(245,179,1,.22)" }, { range: [66, 100], color: "rgba(229,57,53,.22)" }],
    },
  }];
  const yieldMax = Math.max(typical * 1.6, y.value_t_ha * 1.1);
  const yieldGauge = [{
    type: "indicator", mode: "gauge+number+delta", value: y.value_t_ha, number: { suffix: " t/ha", font: { size: 30 } },
    delta: { reference: typical, relative: true, valueformat: ".0%", increasing: { color: "#81c784" }, decreasing: { color: "#e57373" } },
    title: { text: `Yield vs typical (${typical} t/ha)`, font: { size: 14 } },
    gauge: {
      axis: { range: [0, yieldMax], tickcolor: "#8fa896" }, bar: { color: "#81c784", thickness: 0.35 }, bgcolor: "rgba(0,0,0,0)", borderwidth: 0,
      steps: [{ range: [0, typical * 0.8], color: "rgba(229,57,53,.22)" }, { range: [typical * 0.8, typical * 1.1], color: "rgba(245,179,1,.22)" }, { range: [typical * 1.1, yieldMax], color: "rgba(76,175,80,.22)" }],
      threshold: { line: { color: "#fff", width: 3 }, thickness: 0.8, value: typical },
    },
  }];
  const gaugeLayout = { margin: { l: 30, r: 30, t: 50, b: 10 } };

  // ---- radar: this field vs peers (scaled 0-1 within the range seen across all fields) ----
  const radar = useMemo(() => {
    const feats = meta.features;
    const pool = allFields.filter((f) => f.id !== field.id);
    const peers = pool.filter((f) => f.crop === field.crop);
    const ref = peers.length ? peers : pool;
    if (!ref.length) return null;
    const everyone = allFields.length ? allFields : [field];
    const scale = feats.map((ft) => {
      const vals = everyone.map((f) => f.observation[ft.key]);
      const lo = Math.min(...vals), hi = Math.max(...vals);
      return { lo, span: hi - lo || 1 };
    });
    const score = (get) => feats.map((ft, i) => Math.min(1, Math.max(0, (get(ft.key) - scale[i].lo) / scale[i].span)));
    const avg = (key) => ref.reduce((a, f) => a + f.observation[key], 0) / ref.length;
    return {
      theta: feats.map((ft) => FEATURE_SHORT[ft.key] || ft.label),
      me: score((k) => Number(obs[k])), meRaw: feats.map((ft) => Number(obs[ft.key])),
      ref: score(avg), refRaw: feats.map((ft) => avg(ft.key)),
      refName: peers.length ? `Avg of ${peers.length} other ${field.crop} field${peers.length > 1 ? "s" : ""}` : "Fleet average",
    };
  }, [meta, allFields, field, obs]);

  const close = (a) => [...a, a[0]];
  const radarData = radar && [
    { type: "scatterpolar", name: radar.refName, r: close(radar.ref), theta: close(radar.theta), customdata: close(radar.refRaw), fill: "toself", fillcolor: "rgba(100,181,246,.15)", line: { color: "#64b5f6", dash: "dot" }, hovertemplate: "%{theta}: %{customdata:.2f}<extra>peers</extra>" },
    { type: "scatterpolar", name: "This field", r: close(radar.me), theta: close(radar.theta), customdata: close(radar.meRaw), fill: "toself", fillcolor: "rgba(129,199,132,.28)", line: { color: "#81c784" }, hovertemplate: "%{theta}: %{customdata:.2f}<extra>this field</extra>" },
  ];
  const radarLayout = {
    margin: { l: 50, r: 50, t: 20, b: 40 }, legend: { orientation: "h", y: -0.08 },
    polar: { bgcolor: "rgba(0,0,0,0)", radialaxis: { visible: true, range: [0, 1], showticklabels: false, gridcolor: GRID, linecolor: GRID }, angularaxis: { gridcolor: GRID, linecolor: GRID } },
  };

  // ---- 12-week trend (risk + humidity + yield) + 4-week outlook ----
  const wk = timeline && timeline.points.map((p) => -p.weeks_ago);
  const fc = timeline && timeline.forecast;
  const tlData = timeline && [
    { x: wk, y: timeline.points.map((p) => p.risk_index * 100), type: "scatter", mode: "lines+markers", name: "Pest risk %", line: { color: "#e57373" }, fill: "tozeroy", fillcolor: "rgba(229,115,115,.12)" },
    { x: wk, y: timeline.points.map((p) => p.humidity_pct), type: "scatter", mode: "lines", name: "Humidity %", line: { color: "#64b5f6", dash: "dot" } },
    { x: wk, y: timeline.points.map((p) => p.yield_t_ha), type: "scatter", mode: "lines", name: "Yield t/ha", yaxis: "y2", line: { color: "#ffd54f" } },
    ...(fc ? [{ x: [0, ...fc.map((p) => p.weeks_ahead)], y: [timeline.points[timeline.points.length - 1].risk_index * 100, ...fc.map((p) => p.risk_index * 100)], type: "scatter", mode: "lines+markers", name: "4-week outlook", line: { color: "#ff8a65", dash: "dash" } }] : []),
  ];
  const trendLayout = {
    margin: { l: 50, r: 50, t: 24, b: 40 },
    xaxis: { title: "weeks", gridcolor: GRID }, yaxis: { range: [0, 100], gridcolor: GRID, title: "%" },
    yaxis2: { overlaying: "y", side: "right", showgrid: false, title: "t/ha" }, legend: { orientation: "h", y: 1.2 },
  };

  return (
    <div className="card detail">
      <div className="row between wrap">
        <div>
          <h2>{field.name}</h2>
          <div className="muted">{field.crop} · {field.district}, {field.state} · {field.area_ha} ha · expected output ~{(y.value_t_ha * field.area_ha).toFixed(1)} t</div>
        </div>
        <div className="row gap wrap">
          {changed && <button className="ghost" onClick={reset}>Reset what-if</button>}
          <button onClick={refreshWeather} disabled={busy}>{busy ? "Fetching..." : "Use live weather (NASA POWER)"}</button>
          <button onClick={refreshSatellite} disabled={busy}>{busy ? "Fetching..." : "Use live satellite + soil (MODIS, SoilGrids)"}</button>
        </div>
      </div>
      {msg && <div className="note">{msg}</div>}
      {changed && <div className="note">What-if mode: showing predictions for your edited values.</div>}

      <div className="kpis">
        <div className="kpi">
          <div className="muted">Predicted yield</div>
          <div className="big">{y.value_t_ha} <small>t/ha</small></div>
          <div className="muted">range {y.range_t_ha[0]}-{y.range_t_ha[1]} · typical {typical} · confidence {Math.round(y.confidence * 100)}%</div>
        </div>
        <div className="kpi">
          <div className="muted">Pest / disease risk</div>
          <div className="big" style={{ color: RISK_COLOR[pest.level] }}>{pest.level}</div>
          <div className="muted">index {Math.round(pest.risk_index * 100)}% · confidence {Math.round(pest.confidence * 100)}%</div>
        </div>
        <div className="kpi">
          <PlotlyChart
            data={[{ type: "bar", x: ["Low", "Medium", "High"], y: probs.map((p) => p * 100), marker: { color: ["#4caf50", "#f5b301", "#e53935"] } }]}
            layout={{ margin: { l: 32, r: 4, t: 4, b: 24 }, yaxis: { range: [0, 100], gridcolor: "#2d4433" } }} height={110} />
        </div>
      </div>

      <div className="grid2">
        <div className="kpi"><PlotlyChart data={riskGauge} layout={gaugeLayout} height={210} /></div>
        <div className="kpi"><PlotlyChart data={yieldGauge} layout={gaugeLayout} height={210} /></div>
      </div>

      <div className="grid2">
        <Drivers title="Why this pest risk? (red = pushes risk up)" items={analysis.drivers.pest} unit="change in risk index" goodPositive={false} />
        <Drivers title="Why this yield? (green = raises yield)" items={analysis.drivers.yield} unit="t/ha vs typical conditions" goodPositive={true} />
      </div>

      <h4>Recommended actions</h4>
      <ul className="recs">
        {analysis.recommendations.map((r, i) => (
          <li key={i}>
            <span className="pill" style={{ background: PRI_COLOR[r.priority] }}>{r.priority}</span>
            <div><strong>{r.category}:</strong> {r.action}<div className="muted">{r.reason}</div></div>
          </li>
        ))}
      </ul>

      <div className="grid2">
        <div>
          <h4>Conditions vs peers <span className="muted">(0-1 scale across all fields)</span></h4>
          {radarData ? <PlotlyChart data={radarData} layout={radarLayout} height={300} /> : <div className="muted">Add more fields to compare.</div>}
        </div>
        <div>
          <h4>12-week trend + 4-week outlook <span className="muted">(demo history)</span></h4>
          {tlData && <PlotlyChart data={tlData} layout={trendLayout} height={300} />}
        </div>
      </div>

      <h4>What-if simulator</h4>
      <div className="sliders">
        {meta.features.map((f) => (
          <label key={f.key}>
            <span>{f.label}: <b>{Number(obs[f.key]).toFixed(f.max <= 1 ? 2 : 1)}</b> {f.unit}</span>
            <input type="range" min={f.min} max={f.max} step={(f.max - f.min) / 200} value={obs[f.key]} onChange={(e) => update(f.key, parseFloat(e.target.value))} />
          </label>
        ))}
      </div>
      <p className="muted small">{analysis.disclaimer}</p>
    </div>
  );
}