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
import re
import subprocess
import tempfile
import time
from pathlib import Path

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
    "mutator_type", "execution_mode", "failure_stage", "harness_entry",
    "runtime_ms_baseline", "runtime_ms_target", "created_at", "run_id",
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
        if not VALID_DIR.exists():
            raise FileNotFoundError("valid_mutants/ directory missing")

        ll_files = list(VALID_DIR.glob("*.ll"))
        if not ll_files:
            raise FileNotFoundError("no valid mutants found in valid_mutants/")

        if req.mutant_ids:
            wanted = set(req.mutant_ids)
            ll_files = [p for p in ll_files if p.stem in wanted]
            if not ll_files:
                raise FileNotFoundError("requested mutant_ids not found in valid_mutants/")

        # Apply cap
        if req.max_mutants and req.max_mutants > 0:
            ll_files = ll_files[:req.max_mutants]

        total_valid = len(ll_files)
        total_mismatches = 0
        for ll_path in ll_files:
            mutant_id = ll_path.stem
            mutator_type = DifferentialService._infer_mutator_type(mutant_id)
            has_main = DifferentialService._has_main(ll_path)
            harness_entry = None
            execution_mode = "direct" if has_main else "harness"

            # Paths for temporary binaries
            tmp_root = Path(tempfile.gettempdir())
            bin_base = tmp_root / f"{mutant_id}_base.out"
            bin_tgt = tmp_root / f"{mutant_id}_target.out"

            is_mismatch = False
            mismatch_type = None
            failure_stage = None
            rt_base = None
            rt_tgt = None

            verify_proc = subprocess.run(
                ["opt", "-passes=verify", "-disable-output", str(ll_path)],
                capture_output=True,
                text=True,
            )
            if verify_proc.returncode != 0:
                is_mismatch = True
                mismatch_type = "verification_error"
                failure_stage = "verify"
            else:
                harness_path = None
                if execution_mode == "harness":
                    harness_entry = DifferentialService._find_harness_entry(ll_path)
                    if harness_entry is None:
                        is_mismatch = True
                        mismatch_type = "missing_main"
                        failure_stage = "entry_discovery"
                    else:
                        harness_path = DifferentialService._write_harness(mutant_id, harness_entry)

                if not is_mismatch:
                    comp_base = DifferentialService._compile_binary(
                        ll_path, bin_base, req.baseline_opt, harness_path
                    )
                    comp_tgt = DifferentialService._compile_binary(
                        ll_path, bin_tgt, req.target_opt, harness_path
                    )

                    if comp_base.returncode != 0 or comp_tgt.returncode != 0:
                        is_mismatch = True
                        stderr_all = f"{comp_base.stderr}\n{comp_tgt.stderr}".lower()
                        failure_stage = "compile"
                        if "undefined reference to `main`" in stderr_all or "undefined reference to 'main'" in stderr_all:
                            mismatch_type = "missing_main"
                        elif "ld returned" in stderr_all or "undefined reference" in stderr_all:
                            mismatch_type = "link_error"
                        else:
                            mismatch_type = "compile_error"
                    else:
                        # 3. Run and compare
                        try:
                            start = time.time()
                            run_base = subprocess.run(
                                [str(bin_base)], capture_output=True, text=True, timeout=5
                            )
                            rt_base = (time.time() - start) * 1000

                            start = time.time()
                            run_tgt = subprocess.run(
                                [str(bin_tgt)], capture_output=True, text=True, timeout=5
                            )
                            rt_tgt = (time.time() - start) * 1000

                            if run_base.returncode != run_tgt.returncode:
                                is_mismatch = True
                                mismatch_type = "runtime_crash"
                                failure_stage = "execute"
                            elif run_base.stdout != run_tgt.stdout:
                                is_mismatch = True
                                mismatch_type = "output_mismatch"
                                failure_stage = "compare"
                        except subprocess.TimeoutExpired:
                            is_mismatch = True
                            mismatch_type = "timeout"
                            failure_stage = "execute"
                        except Exception:
                            is_mismatch = True
                            mismatch_type = "unknown"
                            failure_stage = "execute"
                if harness_path and harness_path.exists():
                    harness_path.unlink(missing_ok=True)

            if is_mismatch:
                total_mismatches += 1

            # 4. Log Result
            result_row = {
                "mutant_id": mutant_id,
                "baseline_level": req.baseline_opt,
                "target_level": req.target_opt,
                "is_mismatch": str(is_mismatch).lower(),
                "mismatch_type": mismatch_type,
                "mutator_type": mutator_type,
                "execution_mode": execution_mode,
                "failure_stage": failure_stage,
                "harness_entry": harness_entry,
                "runtime_ms_baseline": round(rt_base, 2) if rt_base else "",
                "runtime_ms_target": round(rt_tgt, 2) if rt_tgt else "",
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                "run_id": req.run_id or "",
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
                try:
                    mismatch_val = DifferentialService._normalize_mismatch_type(
                        row.get("mismatch_type")
                    )
                    rt_base_raw = DifferentialService._safe_str(row.get("runtime_ms_baseline"))
                    rt_tgt_raw = DifferentialService._safe_str(row.get("runtime_ms_target"))

                    rows.append(
                        DifferentialResult(
                            mutant_id=DifferentialService._safe_str(row.get("mutant_id")),
                            baseline_level=DifferentialService._safe_str(row.get("baseline_level")),
                            target_level=DifferentialService._safe_str(row.get("target_level")),
                            is_mismatch=DifferentialService._safe_str(row.get("is_mismatch")).lower() == "true",
                            mismatch_type=mismatch_val,
                            mutator_type=DifferentialService._safe_str(row.get("mutator_type"), "unknown"),
                            execution_mode=DifferentialService._safe_str(row.get("execution_mode"), "unknown"),
                            failure_stage=DifferentialService._safe_str(row.get("failure_stage")) or None,
                            harness_entry=DifferentialService._safe_str(row.get("harness_entry")) or None,
                            runtime_ms_baseline=float(rt_base_raw) if rt_base_raw else None,
                            runtime_ms_target=float(rt_tgt_raw) if rt_tgt_raw else None,
                            created_at=DifferentialService._safe_str(row.get("created_at")),
                        )
                    )
                except Exception as exc:
                    logger.warning("Skipping malformed differential row: %s", exc)
                    continue
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
    def _infer_mutator_type(mutant_id: str) -> str:
        if "_llm_" in mutant_id:
            return "llm"
        if "_grammar_" in mutant_id:
            return "grammar"
        return "unknown"

    @staticmethod
    def _safe_str(value: object, default: str = "") -> str:
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def _normalize_mismatch_type(raw_value: object) -> str | None:
        val = DifferentialService._safe_str(raw_value).strip(" \"'").lower()
        if not val or val == "null":
            return None

        legacy_map = {
            "crash": "runtime_crash",
            "runtime_error": "runtime_crash",
            "compile": "compile_error",
            "verification": "verification_error",
        }
        val = legacy_map.get(val, val)

        allowed = {
            "output_mismatch",
            "runtime_crash",
            "timeout",
            "verification_error",
            "compile_error",
            "link_error",
            "missing_main",
            "unknown",
        }
        return val if val in allowed else "unknown"

    @staticmethod
    def _has_main(ll_path: Path) -> bool:
        ir = ll_path.read_text(encoding="utf-8", errors="ignore")
        return bool(re.search(r"^\s*define\s+\w+\s+@main\s*\(", ir, re.MULTILINE))

    @staticmethod
    def _find_harness_entry(ll_path: Path) -> str | None:
        """
        Find a simple callable function for a generated harness:
        - non-declaration function
        - no args
        - integer or void return
        """
        ir = ll_path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(
            r"^\s*define\s+(?P<ret>void|i\d+)\s+@(?P<name>[A-Za-z0-9_$.]+)\s*\((?P<args>[^)]*)\)",
            ir,
            re.MULTILINE,
        ):
            name = m.group("name")
            if name == "main":
                continue
            if m.group("args").strip():
                continue
            return name
        return None

    @staticmethod
    def _write_harness(mutant_id: str, entry_name: str) -> Path:
        harness_path = Path(tempfile.gettempdir()) / f"{mutant_id}_harness.c"
        harness_code = (
            f"extern int {entry_name}(void);\n"
            "int main(void) {\n"
            f"  return {entry_name}();\n"
            "}\n"
        )
        harness_path.write_text(harness_code, encoding="utf-8")
        return harness_path

    @staticmethod
    def _compile_binary(
        ll_path: Path,
        out_bin: Path,
        opt_level: str,
        harness_path: Path | None = None,
    ) -> subprocess.CompletedProcess:
        cmd = ["clang", opt_level, str(ll_path)]
        if harness_path is not None:
            cmd.append(str(harness_path))
        cmd.extend(["-o", str(out_bin)])
        return subprocess.run(cmd, capture_output=True, text=True)

    @staticmethod
    async def get_comparison() -> dict:
        """Compute and return comparison metrics using Comparison Engine."""
        from app.comparison import compute_comparison_metrics
        return compute_comparison_metrics()

