"""
app/services/differential_service.py
Service layer for differential testing and result retrieval.
Source: CONTEXT.json → architecture.components[Differential Tester]
        CONTEXT.json → architecture.components[Comparison Engine]
        CONTEXT.json → architecture.data_flow steps 4 and 5
        CONTEXT.json → database.tables[differential_results]
"""
import csv
import datetime
from app.config import VALID_DIR, LOGS_DIR
from app.models.differential import (
    DifferentialRunRequest,
    DifferentialRunResponse,
    DifferentialResult,
    DifferentialResultsResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

RESULTS_CSV = LOGS_DIR / "results.csv"

# CSV column order matches CONTEXT.json database.tables[differential_results]
CSV_FIELDNAMES = [
    "mutant_id", "baseline_level", "target_level",
    "is_mismatch", "mismatch_type",
    "runtime_ms_baseline", "runtime_ms_target", "created_at",
]


class DifferentialService:
    """
    Orchestrates differential testing and result aggregation.

    Responsibilities (per CONTEXT.json architecture.components):
      - Differential Tester : compile valid IR at -O0 vs -O2, compare outputs
      - Comparison Engine   : aggregate validity_rate, bug_rate, failure_categories
    """

    # ── Run ─────────────────────────────────────────────────────────────────

    # ── Run ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def run(req: DifferentialRunRequest) -> DifferentialRunResponse:
        """
        Compile valid IR at baseline vs target opt levels and compare.
        Source: CONTEXT.json → architecture.components[Differential Tester]
        """
        import subprocess
        import time
        from pathlib import Path

        if not VALID_DIR.exists():
            raise FileNotFoundError("valid_mutants/ directory missing")

        ll_files = list(VALID_DIR.glob("*.ll"))
        if not ll_files:
            raise FileNotFoundError("no valid mutants found in valid_mutants/")

        # Apply cap
        if req.max_mutants and req.max_mutants > 0:
            ll_files = ll_files[:req.max_mutants]

        total_valid = len(ll_files)
        total_mismatches = 0
        now_ts = datetime.datetime.utcnow().isoformat() + "Z"

        for ll_path in ll_files:
            mutant_id = ll_path.stem
            
            # Paths for temporary binaries
            bin_base = Path(f"/tmp/{mutant_id}_O0")
            bin_tgt  = Path(f"/tmp/{mutant_id}_O2")
            
            is_mismatch = False
            mismatch_type = None
            rt_base = None
            rt_tgt = None

            # 1. Compile Baseline
            comp_base = subprocess.run(
                ["clang", req.baseline_opt, str(ll_path), "-o", str(bin_base)],
                capture_output=True, text=True
            )
            
            # 2. Compile Target
            comp_tgt = subprocess.run(
                ["clang", req.target_opt, str(ll_path), "-o", str(bin_tgt)],
                capture_output=True, text=True
            )

            if comp_base.returncode != 0 or comp_tgt.returncode != 0:
                is_mismatch = True
                if "main" in (comp_base.stderr + comp_tgt.stderr):
                    mismatch_type = "unknown" # Missing main
                else:
                    mismatch_type = "crash"   # Compiler crash
            else:
                # 3. Run and compare
                try:
                    # Run Baseline
                    start = time.time()
                    run_base = subprocess.run([str(bin_base)], capture_output=True, text=True, timeout=5)
                    rt_base = (time.time() - start) * 1000
                    
                    # Run Target
                    start = time.time()
                    run_tgt = subprocess.run([str(bin_tgt)], capture_output=True, text=True, timeout=5)
                    rt_tgt = (time.time() - start) * 1000
                    
                    if run_base.returncode != run_tgt.returncode:
                        is_mismatch = True
                        mismatch_type = "crash"
                    elif run_base.stdout != run_tgt.stdout:
                        is_mismatch = True
                        mismatch_type = "wrong_output"
                        
                except subprocess.TimeoutExpired:
                    is_mismatch = True
                    mismatch_type = "crash" # Or timeout? schema says crash/unknown
                except Exception:
                    is_mismatch = True
                    mismatch_type = "unknown"

            if is_mismatch:
                total_mismatches += 1

            # 4. Log Result
            result_row = {
                "mutant_id": mutant_id,
                "baseline_level": req.baseline_opt,
                "target_level": req.target_opt,
                "is_mismatch": str(is_mismatch).lower(),
                "mismatch_type": mismatch_type,
                "runtime_ms_baseline": round(rt_base, 2) if rt_base else "",
                "runtime_ms_target": round(rt_tgt, 2) if rt_tgt else "",
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            DifferentialService.write_results_row(result_row)

            # Cleanup
            for b in [bin_base, bin_tgt]:
                if b.exists(): b.unlink()

        return DifferentialRunResponse(
            total_valid=total_valid,
            total_mismatches=total_mismatches,
            mismatch_rate=round(total_mismatches / total_valid, 4) if total_valid > 0 else 0.0,
            status="completed",
            log_file=str(RESULTS_CSV),
        )


    # ── Results ─────────────────────────────────────────────────────────────

    @staticmethod
    async def get_results() -> DifferentialResultsResponse:
        """
        Read RESULTS_CSV and return typed DifferentialResult rows.
        Raises FileNotFoundError when logs/results.csv does not exist.
        """
        if not RESULTS_CSV.exists():
            raise FileNotFoundError(f"results file not found: {RESULTS_CSV}")

        rows: list[DifferentialResult] = []
        with open(RESULTS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(
                    DifferentialResult(
                        mutant_id=row["mutant_id"],
                        baseline_level=row["baseline_level"],
                        target_level=row["target_level"],
                        is_mismatch=row["is_mismatch"].lower() == "true",
                        mismatch_type=row.get("mismatch_type") or None,
                        runtime_ms_baseline=float(row["runtime_ms_baseline"])
                            if row.get("runtime_ms_baseline") else None,
                        runtime_ms_target=float(row["runtime_ms_target"])
                            if row.get("runtime_ms_target") else None,
                        created_at=row["created_at"],
                    )
                )
        logger.info("get_results: %d rows from %s", len(rows), RESULTS_CSV)
        return DifferentialResultsResponse(results=rows)

    # ── Helper ──────────────────────────────────────────────────────────────

    @staticmethod
    def write_results_row(row: dict) -> None:
        """Append a single differential result row to RESULTS_CSV."""
        write_header = not RESULTS_CSV.exists()
        with open(RESULTS_CSV, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    @staticmethod
    async def get_comparison() -> dict:
        """Compute and return comparison metrics using Comparison Engine."""
        from app.comparison import compute_comparison_metrics
        return compute_comparison_metrics()

