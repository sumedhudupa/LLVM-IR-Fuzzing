/**
 * ComparisonView.jsx – Screen: "Comparison View"
 * Source: CONTEXT.json → ui.screens[4]
 * Navigation: Reached from Differential Testing Dashboard.
 */
import { useEffect, useState } from "react";
import { getComparisonMetrics, getInvalidTaxonomy, getSeeds, runControlledStudy, getSeedSensitivity, getStudyHistory } from "../api";

const COLUMNS = [
  "validity_rate",
  "bug_rate",
  "broken_ssa",
  "type_errors",
  "invalid_phi",
  "other_invalid",
  "trivial_valid",
  "compile_or_link_errors",
  "runtime_failures",
];

export default function ComparisonView() {
  const [metrics, setMetrics] = useState(null);
  const [taxonomy, setTaxonomy] = useState(null);
  const [studyResult, setStudyResult] = useState(null);
  const [availableSeeds, setAvailableSeeds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [studyRunning, setStudyRunning] = useState(false);
  const [selectedSeeds, setSelectedSeeds] = useState([]);
  const [countPerSeed, setCountPerSeed] = useState(5);
  const [error, setError] = useState(null);
  const [seedSensitivity, setSeedSensitivity] = useState(null);
  const [studyHistory, setStudyHistory] = useState(null);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    async function bootstrap() {
      try {
        const seedData = await getSeeds();
        const names = (seedData?.seeds ?? []).map((s) => s.name);
        setAvailableSeeds(names);
        setSelectedSeeds(names.length > 0 ? [names[0]] : []);
      } catch {
        // Ignore seed bootstrap failure and let explicit actions show errors.
      }
      await loadMetrics();
      await loadSeedSensitivity();
      await loadStudyHistory();
    }
    bootstrap();
  }, []);

  async function loadSeedSensitivity() {
    try {
      const data = await getSeedSensitivity();
      setSeedSensitivity(data);
    } catch (e) {
      // Non-critical, don't show error
      console.error("Failed to load seed sensitivity:", e);
    }
  }

  async function loadStudyHistory() {
    try {
      const data = await getStudyHistory();
      setStudyHistory(data);
    } catch (e) {
      // Non-critical, don't show error
      console.error("Failed to load study history:", e);
    }
  }

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
      const taxonomyData = await getInvalidTaxonomy();
      setTaxonomy(taxonomyData);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunStudy() {
    setStudyRunning(true);
    setError(null);
    try {
      const payload = {
        seed_names: selectedSeeds,
        count_per_seed: Number(countPerSeed),
        baseline_opt: "-O0",
        target_opt: "-O2",
        mutators: ["llm", "grammar"],
      };
      if (payload.seed_names.length === 0) {
        throw new Error("Select at least one seed file before starting the study.");
      }
      const data = await runControlledStudy(payload);
      setStudyResult(data);
      await loadMetrics();
    } catch (e) {
      setError(e.message);
    } finally {
      setStudyRunning(false);
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

  function toggleSeed(seedName) {
    setSelectedSeeds((prev) =>
      prev.includes(seedName)
        ? prev.filter((s) => s !== seedName)
        : [...prev, seedName]
    );
  }

  return (
    <section className="page comparison-view">
      <h2>Comparison View</h2>
      <button id="load-comparison-btn" className="btn primary" onClick={loadMetrics} disabled={loading}>
        {loading ? "Loading…" : "Load Metrics"}
      </button>
      {error && <p className="status error">Error: {error}</p>}
      <div style={{ margin: "12px 0", padding: "10px", border: "1px solid #ddd", borderRadius: 6 }}>
        <h3>Controlled Study Runner</h3>
        <p style={{ marginTop: 0 }}>
          Run the complete study from UI only (generate, validate, differential, aggregate metrics).
        </p>
        <div style={{ marginBottom: 8 }}>
          <strong>Seed selection</strong>
          {availableSeeds.length === 0 ? (
            <p className="status">No seeds available. Upload from the Seeds page first.</p>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 6, marginTop: 8 }}>
              {availableSeeds.map((seed) => (
                <label key={seed} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={selectedSeeds.includes(seed)}
                    onChange={() => toggleSeed(seed)}
                    disabled={studyRunning}
                  />
                  <code>{seed}</code>
                </label>
              ))}
            </div>
          )}
        </div>
        <label style={{ display: "block", marginBottom: 8 }}>
          Count per seed
          <input
            type="number"
            min={1}
            value={countPerSeed}
            onChange={(e) => setCountPerSeed(e.target.value)}
          />
        </label>
        <button className="btn secondary" onClick={handleRunStudy} disabled={studyRunning}>
          {studyRunning ? "Running Study..." : "Run Controlled LLM vs Grammar Study"}
        </button>
        {studyResult && (
          <p className="status">
            Last run: <code>{studyResult.run_id}</code> | validity {Math.round((studyResult.aggregate.validity_rate ?? 0) * 1000) / 10}% | mismatch-over-valid {Math.round((studyResult.aggregate.mismatch_rate_over_valid ?? 0) * 1000) / 10}%
          </p>
        )}
      </div>

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

      {/* Per-Strategy Breakdown */}
      {metrics?.per_strategy && (
        <div style={{ marginTop: 24 }}>
          <h3>Per-Strategy Breakdown</h3>
          <table>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>LLM Valid%</th>
                <th>Grammar Valid%</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                // Get all unique strategies from both mutator types
                const allStrategies = new Set([
                  ...Object.keys(metrics.per_strategy.llm || {}),
                  ...Object.keys(metrics.per_strategy.grammar || {}),
                ]);
                return Array.from(allStrategies).sort().map((strategy) => {
                  const llmData = metrics.per_strategy.llm?.[strategy];
                  const grammarData = metrics.per_strategy.grammar?.[strategy];
                  return (
                    <tr key={strategy}>
                      <td>{strategy}</td>
                      <td>{llmData ? `${(llmData.validity_rate * 100).toFixed(1)}%` : "—"}</td>
                      <td>{grammarData ? `${(grammarData.validity_rate * 100).toFixed(1)}%` : "—"}</td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      )}

      {taxonomy && (
        <div style={{ marginTop: 16 }}>
          <h3>Invalid Mutant Failure Taxonomy</h3>
          <p>Total invalid: {taxonomy.total_invalid}</p>
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(taxonomy.categories).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {taxonomy.top_errors?.length > 0 && (
            <>
              <h4>Top Recurring Errors</h4>
              <ul>
                {taxonomy.top_errors.map((e, idx) => (
                  <li key={`${idx}-${e.error}`}>
                    <code>{e.error}</code> ({e.count})
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* Seed Sensitivity Table */}
      {seedSensitivity && seedSensitivity.seeds?.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Seed Sensitivity Analysis</h3>
          <p>Validity rate by seed size (bytes)</p>
          <table>
            <thead>
              <tr>
                <th>Seed</th>
                <th>Size (bytes)</th>
                <th>LLM Generated</th>
                <th>LLM Valid%</th>
                <th>Grammar Generated</th>
                <th>Grammar Valid%</th>
              </tr>
            </thead>
            <tbody>
              {seedSensitivity.seeds.map((seed) => (
                <tr key={seed.seed_name}>
                  <td><code>{seed.seed_name}</code></td>
                  <td>{seed.seed_size_bytes}</td>
                  <td>{seed.llm_generated}</td>
                  <td>{(seed.llm_validity_rate * 100).toFixed(1)}%</td>
                  <td>{seed.grammar_generated}</td>
                  <td>{(seed.grammar_validity_rate * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Study History Section */}
      <div style={{ marginTop: 24 }}>
        <h3 onClick={() => setShowHistory(!showHistory)} style={{ cursor: "pointer" }}>
          Study Run History {showHistory ? "▼" : "▶"}
        </h3>
        {showHistory && studyHistory && (
          <>
            {studyHistory.runs?.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Started</th>
                    <th>Seeds</th>
                    <th>Count/Seed</th>
                    <th>Validity %</th>
                    <th>Mismatch %</th>
                  </tr>
                </thead>
                <tbody>
                  {studyHistory.runs.map((run) => (
                    <tr key={run.run_id}>
                      <td><code>{run.run_id}</code></td>
                      <td>{new Date(run.started_at).toLocaleString()}</td>
                      <td>{run.settings?.seed_names?.length || 0}</td>
                      <td>{run.settings?.count_per_seed || 0}</td>
                      <td>{(run.aggregate?.validity_rate * 100).toFixed(1)}%</td>
                      <td>{(run.aggregate?.mismatch_rate_over_valid * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">No study runs recorded yet.</p>
            )}
          </>
        )}
      </div>
    </section>
  );
}
