/**
 * SeedList.jsx – Screen: "Seed IR List"
 * Source: CONTEXT.json → ui.screens[0]
 * Navigation: default landing page; accessible from home navbar.
 */
import { useEffect, useState } from "react";
import { getSeeds } from "../api";

export default function SeedList({ onGenerate }) {
  const [seeds, setSeeds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSeeds()
      .then((data) => setSeeds(data.seeds))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="status">Loading seeds…</p>;
  if (error) return <p className="status error">Error: {error}</p>;

  return (
    <section className="page seed-list">
      <h2>Seed IR Files</h2>
      {seeds.length === 0 ? (
        <p className="empty">No seed files found in <code>seeds/</code>. Add <code>.ll</code> files to get started.</p>
      ) : (
        <table id="seed-file-table">
          <thead>
            <tr>
              <th>Seed Name</th>
              <th>Size (bytes)</th>
              <th>Created At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {seeds.map((s) => (
              <tr key={s.name}>
                <td><code>{s.name}</code></td>
                <td>{s.size_bytes.toLocaleString()}</td>
                <td>{new Date(s.created_at).toLocaleString()}</td>
                <td>
                  <button
                    id={`generate-btn-${s.name}`}
                    className="btn primary"
                    onClick={() => onGenerate(s.name)}
                  >
                    Generate Mutants
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
