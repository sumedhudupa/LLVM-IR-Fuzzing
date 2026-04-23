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

  const [uploading, setUploading] = useState(false);

  const fetchSeeds = () => {
    setLoading(true);
    getSeeds()
      .then((data) => setSeeds(data.seeds))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSeeds();
  }, []);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    setUploading(true);
    setError(null);
    try {
      // Import missing uploadSeed lazily or at top level. Let's assume we import it correctly.
      // Wait, we need to import it properly at the top. Let's do it in another replace if needed.
      const { uploadSeed } = await import("../api");
      await uploadSeed(file);
      fetchSeeds(); // reload seeds
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  if (loading && !uploading) return <p className="status">Loading seeds…</p>;
  if (error) return <p className="status error">Error: {error}</p>;

  return (
    <section className="page seed-list">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Seed IR Files</h2>
        <div>
          <input 
            type="file" 
            accept=".ll" 
            id="seed-upload" 
            style={{ display: 'none' }} 
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <button 
            className="btn secondary" 
            onClick={() => document.getElementById("seed-upload").click()}
            disabled={uploading}
          >
            {uploading ? "Uploading..." : "Upload Seed"}
          </button>
        </div>
      </div>
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
