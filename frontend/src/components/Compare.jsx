import { useCallback, useMemo, useState } from "react";
import PlotlyChart from "./PlotlyChart.jsx";
import { RISK_COLOR } from "./FieldMap.jsx";
import { CROP_COLOR, GRID, LEVELS, RISK_SCALE, mean } from "../theme.js";

const X_AXES = [
  ["humidity_pct", "Humidity (%)"], ["avg_temp_c", "Temperature (C)"], ["rainfall_mm_30d", "Rainfall 30d (mm)"],
  ["soil_moisture", "Soil moisture"], ["ndvi", "NDVI"], ["ndvi_trend", "NDVI 2-week trend"],
  ["soil_ph", "Soil pH"], ["soil_organic_carbon", "Soil organic carbon (%)"],
];

export default function Compare({ fields, meta, onSelectField }) {
  const [xKey, setXKey] = useState("humidity_pct");
  const [yKey, setYKey] = useState("risk");
  const [colorBy, setColorBy] = useState("risk");

  const typical = meta?.typical_yield_t_ha || {};
  const gap = useCallback((f) => (typical[f.crop] ? (f.yield.value_t_ha / typical[f.crop] - 1) * 100 : 0), [typical]);
  const Y_AXES = {
    risk: ["Pest risk index (%)", (f) => f.pest.risk_index * 100],
    gap: ["Yield vs crop typical (%)", gap],
    yield: ["Predicted yield (t/ha)", (f) => f.yield.value_t_ha],
  };

  const onClick = useCallback((e) => {
    const id = e?.points?.[0]?.customdata?.[0];
    if (id != null) onSelectField(id);
  }, [onSelectField]);

  const crops = useMemo(() => [...new Set(fields.map((f) => f.crop))].sort(), [fields]);
  const states = useMemo(() => [...new Set(fields.map((f) => f.state))].sort(), [fields]);

  if (!fields.length) return <div className="card">Loading...</div>;

  // ---- scatter / bubble ----
  const xLabel = X_AXES.find(([k]) => k === xKey)[1];
  const [yLabel, yGet] = Y_AXES[yKey];
  const maxArea = Math.max(...fields.map((f) => f.area_ha));
  const groups = colorBy === "risk" ? LEVELS : crops;
  const scatter = groups.map((g) => {
    const fs = fields.filter((f) => (colorBy === "risk" ? f.pest.level === g : f.crop === g));
    return {
      type: "scatter", mode: "markers", name: g, x: fs.map((f) => f.observation[xKey]), y: fs.map(yGet),
      customdata: fs.map((f) => [f.id, f.name, f.crop, f.area_ha, f.pest.level]),
      marker: {
        size: fs.map((f) => f.area_ha), sizemode: "area", sizeref: (2 * maxArea) / 34 ** 2, sizemin: 7, opacity: 0.85,
        color: colorBy === "risk" ? RISK_COLOR[g] : CROP_COLOR[g], line: { color: "#0f1a13", width: 1 },
      },
      hovertemplate: `<b>%{customdata[1]}</b><br>%{customdata[2]} · %{customdata[3]} ha · %{customdata[4]} risk<br>${xLabel}: %{x:.2f}<br>${yLabel}: %{y:.1f}<extra></extra>`,
    };
  }).filter((t) => t.x.length);
  const scatterLayout = {
    margin: { l: 60, r: 16, t: 10, b: 50 }, hovermode: "closest", legend: { orientation: "h", y: 1.12 },
    xaxis: { title: xLabel, gridcolor: GRID }, yaxis: { title: yLabel, gridcolor: GRID, zeroline: yKey === "gap" },
  };

  // ---- heatmap: crop x state average risk ----
  const cell = (c, s) => fields.filter((f) => f.crop === c && f.state === s);
  const z = crops.map((c) => states.map((s) => { const fs = cell(c, s); return fs.length ? mean(fs.map((f) => f.pest.risk_index)) * 100 : null; }));
  const cnt = crops.map((c) => states.map((s) => cell(c, s).length));
  const heat = [{
    type: "heatmap", x: states, y: crops, z, text: cnt, colorscale: RISK_SCALE, zmin: 0, zmax: 100, xgap: 2, ygap: 2,
    hoverongaps: false, texttemplate: "%{z:.0f}", textfont: { color: "#fff", size: 11 },
    hovertemplate: "%{y} in %{x}<br>avg risk %{z:.0f}%<br>%{text} field(s)<extra></extra>",
    colorbar: { title: { text: "risk %" }, thickness: 10 },
  }];
  const heatLayout = { margin: { l: 60, r: 10, t: 10, b: 110 }, xaxis: { tickangle: -40 } };

  // ---- yield vs typical, by crop ----
  const gaps = crops.map((c) => mean(fields.filter((f) => f.crop === c).map(gap)));
  const ns = crops.map((c) => fields.filter((f) => f.crop === c).length);
  const gapBars = [{
    type: "bar", x: crops, y: gaps, marker: { color: gaps.map((g) => (g >= 0 ? "#81c784" : "#e57373")) },
    text: gaps.map((g, i) => `${g >= 0 ? "+" : ""}${g.toFixed(0)}% (n=${ns[i]})`), textposition: "outside", cliponaxis: false,
    hovertemplate: "%{x}: %{y:+.1f}% vs typical<extra></extra>",
  }];
  const gapLayout = { margin: { l: 60, r: 16, t: 24, b: 40 }, yaxis: { title: "vs typical yield (%)", gridcolor: GRID, zeroline: true, zerolinecolor: "#8fa896", range: [Math.min(0, ...gaps) - 10, Math.max(0, ...gaps) + 10] } };

  return (
    <div className="stack">
      <div className="card">
        <div className="row between wrap gap">
          <h3>Field comparison <span className="muted">(bubble size = area · click a bubble to open that field)</span></h3>
          <div className="controls">
            <label>X axis <select value={xKey} onChange={(e) => setXKey(e.target.value)}>{X_AXES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
            <label>Y axis <select value={yKey} onChange={(e) => setYKey(e.target.value)}>{Object.entries(Y_AXES).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}</select></label>
            <label>Colour <select value={colorBy} onChange={(e) => setColorBy(e.target.value)}><option value="risk">Risk level</option><option value="crop">Crop</option></select></label>
          </div>
        </div>
        <PlotlyChart data={scatter} layout={scatterLayout} height={400} onClick={onClick} />
      </div>

      <div className="grid2">
        <div className="card"><h3>Risk heatmap <span className="muted">(crop × state, avg risk %)</span></h3><PlotlyChart data={heat} layout={heatLayout} height={340} /></div>
        <div className="card"><h3>Predicted yield vs crop typical</h3><PlotlyChart data={gapBars} layout={gapLayout} height={340} /></div>
      </div>
    </div>
  );
}