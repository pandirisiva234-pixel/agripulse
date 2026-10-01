import PlotlyChart from "./PlotlyChart.jsx";

export const RISK_COLOR = { Low: "#4caf50", Medium: "#f5b301", High: "#e53935" };

export default function FieldMap({ fields, selectedId, onSelect }) {
  const data = [{
    type: "scattermapbox",
    mode: "markers",
    lat: fields.map((f) => f.lat),
    lon: fields.map((f) => f.lon),
    text: fields.map((f) => `${f.name}<br>${f.crop} | pest risk: ${f.pest.level}`),
    hoverinfo: "text",
    customdata: fields.map((f) => f.id),
    marker: {
      size: fields.map((f) => (f.id === selectedId ? 22 : 15)),
      color: fields.map((f) => RISK_COLOR[f.pest.level]),
      opacity: 0.95,
    },
  }];
  const layout = {
    mapbox: { style: "open-street-map", center: { lat: 22.5, lon: 80 }, zoom: 3.4 },
    margin: { l: 0, r: 0, t: 0, b: 0 },
  };
  const click = (e) => { const id = e.points?.[0]?.customdata; if (id != null) onSelect(id); };
  return (
    <>
      <PlotlyChart data={data} layout={layout} height={420} onClick={click} />
      <div className="legend">
        {Object.entries(RISK_COLOR).map(([k, c]) => (<span key={k}><i style={{ background: c }} />{k} risk</span>))}
        <span>Click a marker to open the field</span>
      </div>
    </>
  );
}