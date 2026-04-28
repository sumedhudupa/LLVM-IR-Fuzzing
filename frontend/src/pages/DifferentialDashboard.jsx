/**
 * DifferentialDashboard.jsx – Screen: "Differential Testing Dashboard"
 * Source: CONTEXT.json → ui.screens[3]
 * Navigation: Primary analysis page after validation.
 */
import { useEffect, useState } from "react";
import { runDifferential, getDifferentialResults } from "../api";

const OPT_LEVELS = ["-O0", "-O1", "-O2", "-O3", "-Os"];

export default function DifferentialDashboard({ onCompare }) {
  const [results, setResults] = useState([]);
  const [baselineOpt, setBaselineOpt] = useState("-O0");
  const [targetOpt, setTargetOpt] = useState("-O2");
  const [mutatorFilter, setMutatorFilter] = useState("all");
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDifferentialResults()
      .then((d) => setResults(d.results))
      .catch(() => {}); // no results yet is fine
  }, []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const data = await runDifferential({ baseline_opt: baselineOpt, target_opt: targetOpt });
      setSummary(data);
      const fresh = await getDifferentialResults();
      setResults(fresh.results);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  const filtered = mutatorFilter === "all"
    ? results
    : results.filter((r) => r.mutator_type === mutatorFilter);

  const totalMismatches = filtered.filter((r) => r.is_mismatch === "true" || r.is_mismatch === true).length;
  const mismatchRate = filtered.length > 0
    ? ((totalMismatches / filtered.length) * 100).toFixed(1)
    : "—";

  return (
    <section className="page diff-dashboard">
      <h2>Differential Testing Dashboard</h2>

      {/* SummaryCards */}
      <div id="summary-cards" className="summary-cards">
        <div className="card"><span className="card-label">Valid Mutants</span><span className="card-value">{filtered.length}</span></div>
        <div className="card"><span className="card-label">Mismatches</span><span className="card-value">{totalMismatches}</span></div>
        <div className="card"><span className="card-label">Mismatch Rate</span><span className="card-value">{mismatchRate}%</span></div>
      </div>

      {/* FilterControls */}
      <div id="filter-controls" className="filter-controls">
        <label>Baseline Opt
          <select value={baselineOpt} onChange={(e) => setBaselineOpt(e.target.value)}>
            {OPT_LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <label>Target Opt
          <select value={targetOpt} onChange={(e) => setTargetOpt(e.target.value)}>
            {OPT_LEVELS.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <label>Mutator Type
          <select value={mutatorFilter} onChange={(e) => setMutatorFilter(e.target.value)}>
            <option value="all">all</option>
            <option value="llm">llm</option>
            <option value="grammar">grammar</option>
          </select>
        </label>
        <button id="run-differential-btn" className="btn primary" onClick={handleRun} disabled={running}>
          {running ? "Running…" : "Run Differential"}
        </button>
        <button id="compare-view-btn" className="btn secondary" onClick={onCompare}>
          Comparison View →
        </button>
      </div>

      {error && <p className="status error">Error: {error}</p>}

      {/* DifferentialResultsTable */}
      {filtered.length > 0 ? (
        <table id="differential-results-table">
          <thead>
            <tr>
              <th>Mutant ID</th>
              <th>Baseline</th>
              <th>Target</th>
              <th>Mismatch?</th>
              <th>Mismatch Type</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => (
              <tr key={i} className={(r.is_mismatch === "true" || r.is_mismatch === true) ? "mismatch" : ""}>
                <td><code>{r.mutant_id}</code></td>
                <td>{r.baseline_level}</td>
                <td>{r.target_level}</td>
                <td>{(r.is_mismatch === "true" || r.is_mismatch === true) ? "⚠️" : "✅"}</td>
                <td>{r.mismatch_type ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">No differential results yet. Run a differential test first.</p>
      )}
    </section>
  );
}
