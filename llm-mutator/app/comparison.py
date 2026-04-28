"""
comparison.py – Metrics comparison: LLM-based vs grammar-based mutation.
Source: CONTEXT.json → architecture.components[Comparison Engine]
        CONTEXT.json → ui.screens[Comparison View]
        CONTEXT.json → database.tables[differential_results]
"""
import csv
import json
import datetime
from pathlib import Path

from .config import LOGS_DIR

RAW_MUTANTS_LOG = LOGS_DIR / "raw_mutants.json"
VALIDITY_LOG    = LOGS_DIR / "validity_logs.json"
RESULTS_CSV     = LOGS_DIR / "results.csv"
SUMMARY_CSV     = LOGS_DIR / "comparison_summary.csv"


def _load_json_log(path: Path) -> list[dict]:
    """Robustly load either a JSON list or newline-delimited JSON objects."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    if content.startswith("["):
        try: return json.loads(content)
        except json.JSONDecodeError: pass
    
    # Try newline-delimited
    objs = []
    for line in content.splitlines():
        try: objs.append(json.loads(line))
        except json.JSONDecodeError: continue
    return objs


def compute_comparison_metrics() -> dict:
    """
    Read logs and compute metrics for 'llm' and 'grammar' mutators.
    Source: CONTEXT.json → architecture.components[Comparison Engine]
    """
    # 1. Load data
    raw_mutants    = _load_json_log(RAW_MUTANTS_LOG)
    validity_logs  = _load_json_log(VALIDITY_LOG)
    
    # Results CSV
    results_map = {}
    if RESULTS_CSV.exists():
        with open(RESULTS_CSV, "r", newline="") as f:
            for row in csv.DictReader(f):
                results_map[row["mutant_id"]] = row

    # 2. Join and Aggregate
    # metrics[type] = { "generated": 0, "valid": 0, "mismatch": 0, ...cats }
    def _init_stats():
        return {
            "generated": 0, "valid": 0, "mismatch": 0,
            "broken_ssa": 0, "type_errors": 0, "invalid_phi": 0,
            "other_invalid": 0, "trivial_valid": 0,
            "compile_or_link_errors": 0, "runtime_failures": 0,
        }
    
    stats = {"llm": _init_stats(), "grammar": _init_stats()}
    
    # Map IDs for fast lookup
    type_map = {m.get("id"): m.get("mutator_type", "unknown") for m in raw_mutants}
    
    # Process Validity
    for vlog in validity_logs:
        m_id = vlog["mutant_id"]
        m_type = type_map.get(m_id)
        if not m_type or m_type not in stats:
            continue
        
        stats[m_type]["generated"] += 1
        if vlog["is_valid"]:
            stats[m_type]["valid"] += 1
            # Check if semantically trivial (valid but equivalent to seed)
            if vlog.get("trivial", False):
                stats[m_type]["trivial_valid"] += 1
            # Check for mismatch if valid
            res = results_map.get(m_id)
            if res and res["is_mismatch"].lower() == "true":
                stats[m_type]["mismatch"] += 1
                mt = (res.get("mismatch_type") or "").strip().lower()
                if mt in {"compile_error", "link_error", "missing_main"}:
                    stats[m_type]["compile_or_link_errors"] += 1
                if mt in {"runtime_crash", "timeout"}:
                    stats[m_type]["runtime_failures"] += 1
        else:
            # Breakdown error_type
            etype = vlog["error_type"]
            if etype == "ssa": stats[m_type]["broken_ssa"] += 1
            elif etype == "type": stats[m_type]["type_errors"] += 1
            elif etype == "cfg": stats[m_type]["invalid_phi"] += 1
            else: stats[m_type]["other_invalid"] += 1

    # 3. Per-strategy breakdown
    # Strategy stats: per_strategy[mutator_type][strategy_name] = {generated, valid, validity_rate}
    per_strategy = {"llm": {}, "grammar": {}}

    # Build mutant_id -> strategy lookup from raw_mutants
    strategy_map = {m.get("id"): m.get("strategy", "unknown") for m in raw_mutants}

    # Group validity logs by (mutator_type, strategy)
    for vlog in validity_logs:
        m_id = vlog["mutant_id"]
        m_type = type_map.get(m_id)
        strategy = strategy_map.get(m_id, "unknown")
        if not m_type or m_type not in per_strategy:
            continue

        if strategy not in per_strategy[m_type]:
            per_strategy[m_type][strategy] = {"generated": 0, "valid": 0}

        per_strategy[m_type][strategy]["generated"] += 1
        if vlog["is_valid"]:
            per_strategy[m_type][strategy]["valid"] += 1

    # Calculate validity rates per strategy
    for m_type in ["llm", "grammar"]:
        for strategy in per_strategy[m_type]:
            s = per_strategy[m_type][strategy]
            s["validity_rate"] = round(s["valid"] / s["generated"], 4) if s["generated"] > 0 else 0.0

    # 4. Format results matching UI schema
    results = {}
    for m_type in ["llm", "grammar"]:
        s = stats[m_type]
        gen = s["generated"] or 1 # avoid div zero
        val = s["valid"] or 1

        results[m_type] = {
            "validity_rate": round(s["valid"] / gen, 4),
            "bug_rate":      round(s["mismatch"] / val, 4),
            "broken_ssa":    s["broken_ssa"],
            "type_errors":   s["type_errors"],
            "invalid_phi":   s["invalid_phi"],
            "other_invalid": s["other_invalid"],
            "trivial_valid": s["trivial_valid"],
            "compile_or_link_errors": s["compile_or_link_errors"],
            "runtime_failures": s["runtime_failures"],
        }

    results["per_strategy"] = per_strategy

    # 4. Output Summary CSV
    # Columns: mutator_type, validity_rate, bug_rate, broken_ssa, type_errors, invalid_phi, trivial
    cols = ["mutator_type"] + list(results["llm"].keys())
    with open(SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        # Only write flat summary rows; skip nested sections like "per_strategy".
        for m_type in ("llm", "grammar"):
            metrics = results.get(m_type, {})
            row = {"mutator_type": m_type}
            row.update(metrics)
            writer.writerow(row)

    return results


def write_results_row(row: dict) -> None:
    """Helper to write to results.csv (redefined here for convenience)."""
    # This exists in DifferentialService too; consistent with CONTEXT.json
    CSV_COLUMNS = [
        "mutant_id", "baseline_level", "target_level",
        "is_mismatch", "mismatch_type",
        "runtime_ms_baseline", "runtime_ms_target", "created_at",
    ]
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

