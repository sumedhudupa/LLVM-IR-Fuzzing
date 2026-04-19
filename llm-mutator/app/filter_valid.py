"""
filter_valid.py – Validity filtering via llvm-as + opt -passes=verify -disable-output.
Source: CONTEXT.json → architecture.components[Validity Filter]
        CONTEXT.json → apis.endpoints[POST /api/v1/mutants/validate]
        CONTEXT.json → database.tables[validity_logs]
"""
import subprocess
import datetime
import json
import shutil
import re
from pathlib import Path
from typing import Literal

from .config import MUTANT_DIR, GRAMMAR_DIR, VALID_DIR, INVALID_DIR, LOGS_DIR


ErrorType = Literal["syntax", "ssa", "type", "cfg", "undef", "other"] | None


def _classify_error(stderr: str) -> ErrorType:
    """Classify LLVM verifier output into structured error types."""
    stderr_lower = stderr.lower()
    if "syntax error" in stderr_lower or "expected" in stderr_lower:
        return "syntax"
    if "dominate" in stderr_lower or "phi" in stderr_lower:
        return "ssa"
    if "type" in stderr_lower or "pointer" in stderr_lower or "mismatch" in stderr_lower:
        return "type"
    if "terminate" in stderr_lower or "successor" in stderr_lower or "cfg" in stderr_lower:
        return "cfg"
    if "undef" in stderr_lower:
        return "undef"
    return "other"


def validate_mutant(mutant_id: str, mutator_type: str = "llm") -> dict:
    """
    Run llvm-as + opt -S -verify on the mutant IR file.
    Moves file to VALID_DIR or INVALID_DIR and logs result.
    """
    # 1. Determine source path
    src_dir = MUTANT_DIR if mutator_type == "llm" else GRAMMAR_DIR
    ll_path = src_dir / f"{mutant_id}.ll"
    bc_path = src_dir / f"{mutant_id}.bc"

    if not ll_path.exists():
        raise FileNotFoundError(f"Mutant file not found: {ll_path}")

    is_valid = False
    error_type: ErrorType = None
    verifier_output = ""

    # 2. Run llvm-as
    as_proc = subprocess.run(
        ["llvm-as", str(ll_path), "-o", str(bc_path)],
        capture_output=True,
        text=True
    )

    if as_proc.returncode != 0:
        is_valid = False
        error_type = "syntax"
        verifier_output = as_proc.stderr
    else:
        # 3. Run opt -passes=verify -disable-output
        opt_proc = subprocess.run(
            ["opt", "-S", "-passes=verify", str(bc_path), "-o", "/dev/null"],
            capture_output=True,
            text=True
        )
        if opt_proc.returncode != 0:
            is_valid = False
            error_type = _classify_error(opt_proc.stderr)
            verifier_output = opt_proc.stderr
        else:
            is_valid = True
            error_type = None
            verifier_output = "Verification successful."

    # 4. Move file
    target_dir = VALID_DIR if is_valid else INVALID_DIR
    shutil.move(str(ll_path), target_dir / ll_path.name)
    
    # Cleanup .bc if it exists
    if bc_path.exists():
        bc_path.unlink()

    # 5. Prepare log entry
    log_entry = {
        "mutant_id": mutant_id,
        "is_valid": is_valid,
        "error_type": error_type,
        "verifier_output": verifier_output.strip(),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    # 6. Append to logs/validity_logs.json
    log_file = LOGS_DIR / "validity_logs.json"
    logs = []
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    
    logs.append(log_entry)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

    return log_entry


def validate_batch(mutant_ids: list[str]) -> list[dict]:
    """Validate a list of mutant IDs and return per-mutant results."""
    results = []
    for mid in mutant_ids:
        # Try both locations if type unknown, or default to llm
        try:
            # We check llm first as it's the main path
            results.append(validate_mutant(mid, "llm"))
        except FileNotFoundError:
            try:
                results.append(validate_mutant(mid, "grammar"))
            except FileNotFoundError:
                # Log as error in results but continue
                results.append({
                    "mutant_id": mid,
                    "is_valid": False,
                    "error_type": "other",
                    "verifier_output": "File not found in llm or grammar dirs.",
                    "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                })
    return results
