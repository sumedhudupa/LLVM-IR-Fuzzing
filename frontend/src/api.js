/**
 * api.js – Centralised API client.
 * Source: CONTEXT.json → apis.endpoints
 *
 * All base paths match CONTEXT.json routes exactly.
 * Adjust BASE_URL by setting VITE_API_BASE_URL in frontend/.env
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// GET /api/v1/seeds
export const getSeeds = () => request("GET", "/api/v1/seeds");

// POST /api/v1/mutants/generate
// body: { seed_name, mutator_type, count }
export const generateMutants = (body) =>
  request("POST", "/api/v1/mutants/generate", body);

// POST /api/v1/mutants/validate
// body: { mutant_ids }
export const validateMutants = (body) =>
  request("POST", "/api/v1/mutants/validate", body);

// POST /api/v1/differential/run
// body: { baseline_opt, target_opt, max_mutants }
export const runDifferential = (body) =>
  request("POST", "/api/v1/differential/run", body);

// GET /api/v1/differential/results
export const getDifferentialResults = () =>
  request("GET", "/api/v1/differential/results");

// GET /api/v1/differential/comparison
export const getComparisonMetrics = () =>
  request("GET", "/api/v1/differential/comparison");

