import { RISK_COLOR } from "./FieldMap.jsx";

export default function FieldList({ fields, selectedId, onSelect }) {
  return (
    <div className="card">
      <h3>Priority list <span className="muted">(highest pest risk first)</span></h3>
      <ul className="fieldlist">
        {fields.map((f) => (
          <li key={f.id} className={f.id === selectedId ? "sel" : ""} onClick={() => onSelect(f.id)}>
            <span className="dot" style={{ background: RISK_COLOR[f.pest.level] }} />
            <div className="grow">
              <strong>{f.name}</strong>
              <div className="muted">{f.crop} · {f.district}, {f.state} · {f.area_ha} ha</div>
            </div>
            <div className="rt">
              <span className="pill" style={{ background: RISK_COLOR[f.pest.level] }}>{f.pest.level}</span>
              <div className="muted">{f.yield.value_t_ha} t/ha</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}