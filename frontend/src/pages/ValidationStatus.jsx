/**
 * ValidationStatus.jsx – Screen: "Validation Status"
 * Source: CONTEXT.json → ui.screens[2]
 * Navigation: Reached after job completion or from navbar.
 */
import { useEffect, useState } from "react";
import { validateMutants, listMutants, getDifferentialResults } from "../api";

export default function ValidationStatus({ mutantIds = [] }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [existingMutants, setExistingMutants] = useState({ valid: [], invalid: [] });
  const [loadedMutantIds, setLoadedMutantIds] = useState([]);
  const [historySummary, setHistorySummary] = useState({
    checked: false,
    totalRows: 0,
    uniqueMutants: 0,
  });
  const [hasLoadedExisting, setHasLoadedExisting] = useState(false);

  const activeMutantIds = mutantIds.length > 0 ? mutantIds : loadedMutantIds;

  // Check differential history on mount if no mutantIds were passed.
  useEffect(() => {
    async function loadHistorySummary() {
      if (mutantIds.length === 0) {
        try {
          const data = await getDifferentialResults();
          const unique = new Set((data.results ?? []).map((r) => r.mutant_id));
          setHistorySummary({
            checked: true,
            totalRows: (data.results ?? []).length,
            uniqueMutants: unique.size,
          });
        } catch (e) {
          setHistorySummary({ checked: true, totalRows: 0, uniqueMutants: 0 });
        }
      }
    }
    loadHistorySummary();
  }, [mutantIds]);

  const totalMutants = activeMutantIds.length;
  const validatedCount = results.filter((r) => r.is_valid).length;
  const invalidCount = results.filter((r) => !r.is_valid).length;
  const progress = totalMutants > 0 ? (results.length / totalMutants) * 100 : 0;

  const existingTotal = existingMutants.valid.length + existingMutants.invalid.length;

  async function handleLoadAllValidatedMutants() {
    setLoading(true);
    setError(null);
    try {
      const data = await listMutants();
      setExistingMutants(data);
      setHasLoadedExisting(true);
      setLoadedMutantIds([...(data.valid ?? []), ...(data.invalid ?? [])]);
      setResults([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleValidate() {
    if (activeMutantIds.length === 0) {
      setError("No mutants selected. Run a mutation job or load existing mutants first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await validateMutants({ mutant_ids: activeMutantIds });
      setResults(data.results);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page validation-status">
      <h2>Validation Status</h2>

      {/* ProgressBar */}
      <div className="progress-bar-wrapper">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
        <span className="progress-label">
          {results.length}/{totalMutants} validated &nbsp;|&nbsp;
          ✅ {validatedCount} valid &nbsp;|&nbsp; ❌ {invalidCount} invalid
        </span>
      </div>

      <button id="revalidate-btn" className="btn secondary" onClick={handleValidate} disabled={loading}>
        {loading ? "Validating…" : "Revalidate"}
      </button>

      {mutantIds.length === 0 && (
        <button
          type="button"
          className="btn secondary"
          onClick={handleLoadAllValidatedMutants}
          disabled={loading}
          style={{ marginLeft: 8 }}
        >
          Load All Validated Mutants
        </button>
      )}

      {error && <p className="status error">Error: {error}</p>}

      {mutantIds.length === 0 && historySummary.checked && (
        <div className="status" style={{ marginTop: 12, padding: 10, background: "#f5f5f5", borderRadius: 4 }}>
          <strong>Existing Differential History:</strong><br />
          Rows in results.csv: {historySummary.totalRows}<br />
          Unique mutants covered: {historySummary.uniqueMutants}
        </div>
      )}

      {/* Existing Mutants Summary */}
      {totalMutants === 0 && hasLoadedExisting && existingTotal > 0 && (
        <div className="status" style={{ marginTop: 12, padding: 10, background: "#f5f5f5", borderRadius: 4 }}>
          <strong>Existing Validated Mutants:</strong><br />
          ✅ Valid: {existingMutants.valid.length} mutants<br />
          ❌ Invalid: {existingMutants.invalid.length} mutants<br />
          <em>Upload seeds and run mutation jobs to generate new mutants.</em>
        </div>
      )}

      {totalMutants === 0 && hasLoadedExisting && existingTotal === 0 && (
        <div className="status" style={{ marginTop: 12, padding: 10, background: "#f5f5f5", borderRadius: 4 }}>
          <em>No validated mutants found. Go to the Seeds page to upload seed files and generate mutants.</em>
        </div>
      )}

      {/* MutantTable */}
      {results.length > 0 && (
        <table id="mutant-validation-table">
          <thead>
            <tr>
              <th>Mutant ID</th>
              <th>Valid?</th>
              <th>Error Type</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.mutant_id} className={r.is_valid ? "valid" : "invalid"}>
                <td><code>{r.mutant_id}</code></td>
                <td>{r.is_valid ? "✅" : "❌"}</td>
                <td>{r.error_type ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
