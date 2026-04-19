/**
 * MutationJobForm.jsx – Screen: "Mutation Job Form"
 * Source: CONTEXT.json → ui.screens[1]
 * Navigation: Reached from Seed IR List via Generate Mutants button.
 */
import { useState } from "react";
import { generateMutants } from "../api";

const MUTATOR_TYPES = ["llm", "grammar"];

export default function MutationJobForm({ seeds, initialSeed, onJobComplete }) {
  const [seedName, setSeedName] = useState(initialSeed ?? (seeds?.[0] ?? ""));
  const [mutatorType, setMutatorType] = useState("llm");
  const [count, setCount] = useState(5);
  const [status, setStatus] = useState(null);  // "running" | "done" | "error"
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("running");
    try {
      const data = await generateMutants({ seed_name: seedName, mutator_type: mutatorType, count });
      setResult(data);
      setStatus("done");
      onJobComplete?.(data);
    } catch (err) {
      setResult({ error: err.message });
      setStatus("error");
    }
  }

  return (
    <section className="page mutation-form">
      <h2>Mutation Job Form</h2>
      <form id="mutation-job-form" onSubmit={handleSubmit}>
        <label htmlFor="seed-dropdown">Seed File</label>
        <select id="seed-dropdown" value={seedName} onChange={(e) => setSeedName(e.target.value)}>
          {(seeds ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <label htmlFor="mutator-type-dropdown">Mutator Type</label>
        <select id="mutator-type-dropdown" value={mutatorType} onChange={(e) => setMutatorType(e.target.value)}>
          {MUTATOR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>

        <label htmlFor="mutant-count-input">Mutant Count</label>
        <input
          id="mutant-count-input"
          type="number"
          min={1}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
        />

        <button id="mutation-submit-btn" type="submit" className="btn primary" disabled={status === "running"}>
          {status === "running" ? "Running…" : "Submit"}
        </button>
      </form>

      {/* JobStatusIndicator */}
      {status && (
        <div id="job-status-indicator" className={`status-badge ${status}`}>
          {status === "running" && "⏳ Generating mutants…"}
          {status === "done" && `✅ Done – ${result.mutant_count} mutant(s) generated`}
          {status === "error" && `❌ Error: ${result?.error}`}
        </div>
      )}
    </section>
  );
}
