import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import FieldMap from "./components/FieldMap.jsx";
import FieldList from "./components/FieldList.jsx";
import Detail from "./components/Detail.jsx";
import RegionSummary from "./components/RegionSummary.jsx";
import Overview from "./components/Overview.jsx";
import Compare from "./components/Compare.jsx";

const TABS = [["overview", "Overview"], ["compare", "Compare"], ["explorer", "Field explorer"]];

export default function App() {
  const [fields, setFields] = useState([]);
  const [meta, setMeta] = useState(null);
  const [regions, setRegions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");

  const load = useCallback(async () => {
    try {
      const [f, r] = await Promise.all([api.fields(), api.regions()]);
      setFields(f); setRegions(r);
      setSelected((cur) => cur ?? f[0]?.id ?? null);
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => {
    load();
    api.meta().then(setMeta).catch((e) => setError(e.message));
    api.modelInfo().then(setInfo).catch(() => {});
  }, [load]);

  // clicking a field anywhere jumps to the explorer with that field open
  const openField = useCallback((id) => { setSelected(id); setTab("explorer"); }, []);

  const field = fields.find((f) => f.id === selected);
  const high = fields.filter((f) => f.pest.level === "High").length;

  return (
    <div className="app">
      <header>
        <div>
          <h1>AgriPulse <span className="tag">AI</span></h1>
          <div className="muted">Sense the field. Predict the risk. Act before the loss.</div>
        </div>
        <div className="stats">
          <div><b>{fields.length}</b><span>fields</span></div>
          <div><b style={{ color: "#e53935" }}>{high}</b><span>high risk</span></div>
          {info && <div><b>{Math.round(info.metrics.pest_accuracy * 100)}%</b><span>pest acc.*</span></div>}
        </div>
      </header>

      <nav className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? "tab active" : "tab"} onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>

      {error && <div className="error">API error: {error}. Is the backend running on port 8000?</div>}

      {tab === "overview" && <Overview fields={fields} onSelectField={openField} />}
      {tab === "compare" && <Compare fields={fields} meta={meta} onSelectField={openField} />}
      {tab === "explorer" && (
        <main>
          <section className="left">
            <div className="card nopad"><FieldMap fields={fields} selectedId={selected} onSelect={setSelected} /></div>
            <FieldList fields={fields} selectedId={selected} onSelect={setSelected} />
            <RegionSummary regions={regions} />
          </section>
          <section className="right">
            {field && meta ? <Detail key={field.id} field={field} meta={meta} allFields={fields} onWeatherRefreshed={load} /> : <div className="card">Loading...</div>}
          </section>
        </main>
      )}
      <footer className="muted small">*Model metrics are measured on synthetic training data. Connect real satellite/soil/weather data to calibrate for production use.</footer>
    </div>
  );
}