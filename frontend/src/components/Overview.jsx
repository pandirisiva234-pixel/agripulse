import { useMemo } from "react";
import PlotlyChart from "./PlotlyChart.jsx";
import { RISK_COLOR } from "./FieldMap.jsx";
import { GRID, LEVELS, RISK_SCALE, fmt, mean } from "../theme.js";

function Tile({ icon, label, value, sub, color }) {
  return (
    <div className="tile">
      <div className="tile-icon">{icon}</div>
      <div>
        <div className="muted">{label}</div>
        <div className="tile-value" style={color ? { color } : undefined}>{value}</div>
        {sub && <div className="muted small">{sub}</div>}
      </div>
    </div>
  );
}

export default function Overview({ fields, onSelectField }) {
  const s = useMemo(() => {
    const counts = { Low: 0, Medium: 0, High: 0 };
    fields.forEach((f) => { counts[f.pest.level] += 1; });
    const byState = {};
    fields.forEach((f) => { (byState[f.state] ||= []).push(f); });
    const states = Object.entries(byState).map(([state, fs]) => ({
      state, fields: fs, n: fs.length, avgRisk: mean(fs.map((f) => f.pest.risk_index)) * 100,
      high: fs.filter((f) => f.pest.level === "High").length,
    })).sort((a, b) => b.avgRisk - a.avgRisk);
    const crops = [...new Set(fields.map((f) => f.crop))].sort();
    return {
      counts, states, crops,
      area: fields.reduce((a, f) => a + f.area_ha, 0),
      prod: fields.reduce((a, f) => a + f.expected_production_t, 0),
      avgRisk: mean(fields.map((f) => f.pest.risk_index)) * 100,
      top: fields.slice(0, 5), // /fields is already sorted by risk
    };
  }, [fields]);

  const n = fields.length;

  const donut = [{
    type: "pie", hole: 0.62, sort: false, labels: LEVELS, values: LEVELS.map((l) => s.counts[l]),
    marker: { colors: LEVELS.map((l) => RISK_COLOR[l]), line: { color: "#16251b", width: 2 } },
    textinfo: "label+value", hovertemplate: "%{label}: %{value} fields (%{percent})<extra></extra>",
  }];
  const donutLayout = { showlegend: false, margin: { l: 10, r: 10, t: 10, b: 10 }, annotations: [{ text: `<b>${n}</b><br>fields`, showarrow: false, font: { size: 18 } }] };

  const cropMix = LEVELS.map((l) => ({
    type: "bar", name: l, x: s.crops, y: s.crops.map((c) => fields.filter((f) => f.crop === c && f.pest.level === l).length),
    marker: { color: RISK_COLOR[l] },
  }));
  const cropLayout = { barmode: "stack", legend: { orientation: "h", y: 1.15 }, yaxis: { title: "fields", gridcolor: GRID }, margin: { l: 50, r: 16, t: 24, b: 40 } };

  const stateBars = [{
    type: "bar", orientation: "h", y: s.states.map((r) => r.state), x: s.states.map((r) => r.avgRisk),
    marker: { color: s.states.map((r) => r.avgRisk), colorscale: RISK_SCALE, cmin: 0, cmax: 100 },
    text: s.states.map((r) => `${Math.round(r.avgRisk)}%`), textposition: "outside", cliponaxis: false,
    customdata: s.states.map((r) => [r.n, r.high]),
    hovertemplate: "%{y}<br>avg risk %{x:.0f}%<br>%{customdata[0]} fields · %{customdata[1]} high risk<extra></extra>",
  }];
  const stateLayout = { margin: { l: 120, r: 40, t: 8, b: 36 }, xaxis: { range: [0, 105], gridcolor: GRID, title: "average risk index (%)" }, yaxis: { autorange: "reversed" } };
  const chartH = Math.max(280, s.states.length * 26 + 50);

  const tree = useMemo(() => {
    const ids = ["all"], labels = ["All fields"], parents = [""], values = [0], colors = [s.avgRisk];
    s.states.forEach((st) => { ids.push("s:" + st.state); labels.push(st.state); parents.push("all"); values.push(0); colors.push(st.avgRisk); });
    fields.forEach((f) => { ids.push("f:" + f.id); labels.push(f.name); parents.push("s:" + f.state); values.push(f.expected_production_t); colors.push(f.pest.risk_index * 100); });
    return [{
      type: "treemap", ids, labels, parents, values, branchvalues: "remainder", pathbar: { visible: false },
      marker: { colors, colorscale: RISK_SCALE, cmin: 0, cmax: 100, colorbar: { title: { text: "risk %" }, thickness: 10, len: 0.8 } },
      texttemplate: "%{label}<br>%{value:.0f} t", hovertemplate: "%{label}<br>%{value:.0f} t expected<br>risk %{color:.0f}%<extra></extra>",
    }];
  }, [fields, s]);

  if (!n) return <div className="card">Loading...</div>;

  return (
    <div className="stack">
      <div className="tiles">
        <Tile icon="🌾" label="Fields monitored" value={n} sub={`${s.states.length} states · ${s.crops.length} crops`} />
        <Tile icon="📐" label="Total area" value={`${fmt(s.area, 1)} ha`} />
        <Tile icon="⚖️" label="Expected production" value={`${fmt(s.prod)} t`} />
        <Tile icon="🚨" label="High-risk fields" value={s.counts.High} sub={`${Math.round((s.counts.High / n) * 100)}% of all fields`} color={RISK_COLOR.High} />
        <Tile icon="📈" label="Average risk index" value={`${Math.round(s.avgRisk)}%`} sub="0% = Low · 100% = High" />
      </div>

      <div className="grid2">
        <div className="card"><h3>Risk distribution</h3><PlotlyChart data={donut} layout={donutLayout} height={280} /></div>
        <div className="card"><h3>Crop mix by risk level</h3><PlotlyChart data={cropMix} layout={cropLayout} height={280} /></div>
      </div>

      <div className="grid2">
        <div className="card"><h3>Average pest risk by state</h3><PlotlyChart data={stateBars} layout={stateLayout} height={chartH} /></div>
        <div className="card"><h3>Expected production by state <span className="muted">(colour = risk)</span></h3><PlotlyChart data={tree} layout={{ margin: { l: 4, r: 4, t: 4, b: 4 } }} height={chartH} /></div>
      </div>

      <div className="card">
        <h3>Needs attention first <span className="muted">(click to open the field)</span></h3>
        <ul className="fieldlist short">
          {s.top.map((f) => (
            <li key={f.id} onClick={() => onSelectField(f.id)}>
              <span className="dot" style={{ background: RISK_COLOR[f.pest.level] }} />
              <div className="grow"><strong>{f.name}</strong><div className="muted">{f.crop} · {f.district}, {f.state} · {f.area_ha} ha</div></div>
              <div className="rt"><span className="pill" style={{ background: RISK_COLOR[f.pest.level] }}>{f.pest.level} · {Math.round(f.pest.risk_index * 100)}%</span></div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}