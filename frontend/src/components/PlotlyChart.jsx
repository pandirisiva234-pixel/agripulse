import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

// Thin wrapper: draws with Plotly.react on every data change, cleans up on unmount.
export default function PlotlyChart({ data, layout, height = 260, onClick }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const full = {
      autosize: true,
      height,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#d7e6d9", size: 12 },
      margin: { l: 50, r: 16, t: 24, b: 40 },
      ...layout,
    };
    Plotly.react(el, data, full, { responsive: true, displayModeBar: false });
    if (onClick) {
      el.removeAllListeners?.("plotly_click");
      el.on("plotly_click", onClick);
    }
  }, [data, layout, height, onClick]);

  useEffect(() => () => ref.current && Plotly.purge(ref.current), []);
  return <div ref={ref} style={{ width: "100%" }} />;
}
