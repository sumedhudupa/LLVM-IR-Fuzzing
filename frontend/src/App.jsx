/**
 * App.jsx – Root application with client-side routing.
 * Source: CONTEXT.json → ui.navigation_flow
 *
 * Navigation flow (state-based, no router dep required for prototype):
 *   home → SeedList → MutationJobForm → ValidationStatus
 *        → DifferentialDashboard → ComparisonView
 */
import { useState, useEffect } from "react";
import { getSeeds } from "./api";
import SeedList from "./pages/SeedList";
import MutationJobForm from "./pages/MutationJobForm";
import ValidationStatus from "./pages/ValidationStatus";
import DifferentialDashboard from "./pages/DifferentialDashboard";
import ComparisonView from "./pages/ComparisonView";
import "./App.css";

const NAV_ITEMS = [
  { key: "seeds", label: "Seeds" },
  { key: "mutate", label: "Mutate" },
  { key: "validate", label: "Validate" },
  { key: "diff", label: "Differential" },
  { key: "compare", label: "Compare" },
];

export default function App() {
  const [page, setPage] = useState("seeds");
  const [seeds, setSeeds] = useState([]);
  const [selectedSeed, setSelectedSeed] = useState(null);
  const [lastJobResult, setLastJobResult] = useState(null);

  useEffect(() => {
    getSeeds()
      .then((d) => setSeeds(d.seeds.map((s) => s.name)))
      .catch(() => {});
  }, []);

  function handleGenerate(seedName) {
    setSelectedSeed(seedName);
    setPage("mutate");
  }

  function handleJobComplete(result) {
    setLastJobResult(result);
    setPage("validate");
  }

  return (
    <div className="app">
      {/* Navbar */}
      <header className="navbar">
        <div className="navbar-brand">
          <span className="brand-icon">⚙️</span>
          <span>LLVM IR Fuzzer</span>
        </div>
        <nav className="navbar-nav" role="navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              id={`nav-${item.key}`}
              className={`nav-link ${page === item.key ? "active" : ""}`}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main className="main-content">
        {page === "seeds" && (
          <SeedList onGenerate={handleGenerate} />
        )}
        {page === "mutate" && (
          <MutationJobForm
            seeds={seeds}
            initialSeed={selectedSeed}
            onJobComplete={handleJobComplete}
          />
        )}
        {page === "validate" && (
          <ValidationStatus
            mutantIds={lastJobResult?.mutant_ids ?? []}
          />
        )}
        {page === "diff" && (
          <DifferentialDashboard onCompare={() => setPage("compare")} />
        )}
        {page === "compare" && <ComparisonView />}
      </main>
    </div>
  );
}
