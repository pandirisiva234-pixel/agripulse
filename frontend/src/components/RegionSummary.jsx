export default function RegionSummary({ regions }) {
  return (
    <div className="card">
      <h3>Regional planning view</h3>
      <table>
        <thead><tr><th>State</th><th>Fields</th><th>Area (ha)</th><th>Expected output (t)</th><th>High-risk</th><th>Avg risk</th></tr></thead>
        <tbody>
          {regions.map((r) => (
            <tr key={r.state}>
              <td>{r.state}</td><td>{r.fields}</td><td>{r.area_ha}</td><td>{r.expected_production_t}</td>
              <td>{r.high_risk_fields}</td><td>{Math.round(r.avg_risk_index * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
