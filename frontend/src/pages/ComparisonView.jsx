/**
 * ComparisonView.jsx – Screen: "Comparison View"
 * Source: CONTEXT.json → ui.screens[4]
 * Navigation: Reached from Differential Testing Dashboard.
 */
import { useState } from "react";
import { getComparisonMetrics } from "../api";

const COLUMNS = ["validity_rate", "bug_rate", "broken_ssa", "type_errors", "invalid_phi", "trivial"];

export default function ComparisonView() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function loadMetrics() {
    setLoading(true);
    setError(null);
    try {
      const data = await getComparisonMetrics();
      // Format rates for display (e.g. 0.85 -> 85%)
      const formatted = {};
      ["llm", "grammar"].forEach(type => {
        formatted[type] = {
           ...data[type],
           validity_rate: `${(data[type].validity_rate * 100).toFixed(1)}%`,
           bug_rate: `${(data[type].bug_rate * 100).toFixed(1)}%`
        };
      });
      setMetrics(formatted);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }


  function downloadCSV() {
    if (!metrics) return;
    const header = ["mutator_type", ...COLUMNS].join(",");
    const rows = ["llm", "grammar"].map(
      (t) => [t, ...COLUMNS.map((c) => metrics[t][c])].join(",")
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "comparison.csv";
    a.click();
  }

  return (
    <section className="page comparison-view">
      <h2>Comparison View</h2>
      <button id="load-comparison-btn" className="btn primary" onClick={loadMetrics} disabled={loading}>
        {loading ? "Loading…" : "Load Metrics"}
      </button>
      {error && <p className="status error">Error: {error}</p>}

      {/* ComparisonTable */}
      {metrics && (
        <>
          <table id="comparison-table">
            <thead>
              <tr>
                <th>Mutator Type</th>
                {COLUMNS.map((c) => <th key={c}>{c.replace(/_/g, " ")}</th>)}
              </tr>
            </thead>
            <tbody>
              {["llm", "grammar"].map((t) => (
                <tr key={t}>
                  <td><strong>{t}</strong></td>
                  {COLUMNS.map((c) => (
                    <td key={c}>{metrics[t][c] ?? "—"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <button id="download-csv-btn" className="btn secondary" onClick={downloadCSV}>
            ⬇ Download CSV
          </button>
        </>
      )}
    </section>
  );
}
