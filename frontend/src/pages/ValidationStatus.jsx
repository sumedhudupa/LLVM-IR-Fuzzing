/**
 * ValidationStatus.jsx – Screen: "Validation Status"
 * Source: CONTEXT.json → ui.screens[2]
 * Navigation: Reached after job completion or from navbar.
 */
import { useState } from "react";
import { validateMutants } from "../api";

export default function ValidationStatus({ mutantIds = [] }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const totalMutants = mutantIds.length;
  const validatedCount = results.filter((r) => r.is_valid).length;
  const invalidCount = results.filter((r) => !r.is_valid).length;
  const progress = totalMutants > 0 ? (results.length / totalMutants) * 100 : 0;

  async function handleValidate() {
    setLoading(true);
    setError(null);
    try {
      const data = await validateMutants({ mutant_ids: mutantIds });
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

      {error && <p className="status error">Error: {error}</p>}

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
