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
import os
import multiprocessing as mp
from pathlib import Path
from typing import Literal

from .config import MUTANT_DIR, GRAMMAR_DIR, RANDOM_DIR, VALID_DIR, INVALID_DIR, LOGS_DIR, SEED_DIR, ENABLE_RULE_VALIDATION, ENABLE_DEDUPLICATION, VALIDATION_TIMEOUT
from .utils.semantic_helpers import is_semantically_trivial
from .utils.rule_validation import prevalidate_ir
from .utils.ir_helpers import compute_ir_hash


ErrorType = Literal["syntax", "ssa", "type", "cfg", "undef", "other", "timeout"] | None


_MUTANT_ID_RE = re.compile(
    r"^(?P<seed>.+?)_(?P<mutator>llm|grammar|random)(?:_(?P<run_tag>[A-Za-z0-9-]+))?_mut_\d+$"
)


def _parse_mutant_id(mutant_id: str) -> dict | None:
    match = _MUTANT_ID_RE.match(mutant_id)
    if not match:
        return None
    return match.groupdict()


def _extract_seed_name(mutant_id: str) -> str | None:
    """Extract seed name from mutant_id like 'seed_arith_llm_x_mut_0' -> 'seed_arith.ll'."""
    parsed = _parse_mutant_id(mutant_id)
    if not parsed:
        return None
    base = parsed.get("seed") or ""
    if not base:
        return None
    # The base might have underscores from original filename
    # Try common extensions
    for ext in [".ll", ""]:
        candidate = base + ext
        if (SEED_DIR / candidate).exists():
            return candidate
    return None


def _extract_run_tag(mutant_id: str) -> str | None:
    parsed = _parse_mutant_id(mutant_id)
    if not parsed:
        return None
    return parsed.get("run_tag") or None


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


# In-memory hash set for session-based deduplication
_seen_ir_hashes: set[str] = set()


def validate_mutant(mutant_id: str, mutator_type: str = "llm") -> dict:
    """
    Run rule-based pre-validation, then llvm-as + opt -S -verify on the mutant IR file.
    Moves file to VALID_DIR or INVALID_DIR and logs result.
    """
    # 1. Determine source path
    if mutator_type == "llm":
        src_dir = MUTANT_DIR
    elif mutator_type == "random":
        src_dir = RANDOM_DIR
    else:
        src_dir = GRAMMAR_DIR
    ll_path = src_dir / f"{mutant_id}.ll"
    bc_path = src_dir / f"{mutant_id}.bc"

    if not ll_path.exists():
        raise FileNotFoundError(f"Mutant file not found: {ll_path}")

    is_valid = False
    error_type: ErrorType = None
    verifier_output = ""
    rule_check_passed = None
    is_duplicate = False
    content_hash = None

    # Read IR content for deduplication and rule validation
    ir_text = ll_path.read_text(encoding="utf-8")

    # 2. Compute content hash for deduplication
    if ENABLE_DEDUPLICATION:
        content_hash = compute_ir_hash(ir_text)
        if content_hash in _seen_ir_hashes:
            is_duplicate = True
        else:
            _seen_ir_hashes.add(content_hash)

    # 3. Rule-based pre-validation (if enabled)
    if ENABLE_RULE_VALIDATION:
        rule_result = prevalidate_ir(ir_text)
        if not rule_result.is_valid:
            is_valid = False
            error_type = rule_result.error_type
            verifier_output = "; ".join(rule_result.issues)
            rule_check_passed = False
        else:
            rule_check_passed = True

    # 4. Run llvm-as (only if rule validation passed or disabled)
    timeout_occurred = False
    if rule_check_passed is not False:
        try:
            as_proc = subprocess.run(
                ["llvm-as", str(ll_path), "-o", str(bc_path)],
                capture_output=True,
                text=True,
                timeout=VALIDATION_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            timeout_occurred = True
            is_valid = False
            error_type = "timeout"
            verifier_output = f"llvm-as timed out after {VALIDATION_TIMEOUT} seconds"

        if not timeout_occurred:
            if as_proc.returncode != 0:
                is_valid = False
                error_type = "syntax"
                verifier_output = as_proc.stderr
            else:
                # 5. Run opt -passes=verify -disable-output
                try:
                    opt_proc = subprocess.run(
                        ["opt", "-S", "-passes=verify", str(bc_path), "-o", os.devnull],
                        capture_output=True,
                        text=True,
                        timeout=VALIDATION_TIMEOUT
                    )
                except subprocess.TimeoutExpired:
                    timeout_occurred = True
                    is_valid = False
                    error_type = "timeout"
                    verifier_output = f"opt -passes=verify timed out after {VALIDATION_TIMEOUT} seconds"

                if not timeout_occurred:
                    if opt_proc.returncode != 0:
                        is_valid = False
                        error_type = _classify_error(opt_proc.stderr)
                        verifier_output = opt_proc.stderr
                    else:
                        is_valid = True
                        error_type = None
                        verifier_output = "Verification successful."

    # 6. Move file
    target_dir = VALID_DIR if is_valid else INVALID_DIR
    shutil.move(str(ll_path), target_dir / ll_path.name)

    # Cleanup .bc if it exists
    if bc_path.exists():
        bc_path.unlink()

    # 7. Check semantic equivalence if valid
    is_trivial = False
    if is_valid:
        seed_name = _extract_seed_name(mutant_id)
        if seed_name:
            seed_path = SEED_DIR / seed_name
            target_path = target_dir / ll_path.name
            is_trivial = is_semantically_trivial(seed_path, target_path)

    # 8. Prepare log entry
    log_entry = {
        "mutant_id": mutant_id,
        "seed_name": _extract_seed_name(mutant_id) or "",
        "run_tag": _extract_run_tag(mutant_id),
        "mutator_type": mutator_type,
        "mutation_strategy": "",
        "is_valid": is_valid,
        "error_type": error_type,
        "verifier_output": verifier_output.strip(),
        "trivial": is_trivial,
        "is_duplicate": is_duplicate,
        "content_hash": content_hash,
        "rule_check_passed": rule_check_passed,
        "timeout_occurred": timeout_occurred,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }

    # 9. Append to logs/validity_logs.json
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


def _validate_mutant_worker(mutant_id: str, mutator_type: str, queue: mp.Queue) -> None:
    try:
        queue.put(validate_mutant(mutant_id, mutator_type))
    except Exception as exc:
        queue.put({
            "mutant_id": mutant_id,
            "seed_name": _extract_seed_name(mutant_id) or "",
            "run_tag": _extract_run_tag(mutant_id),
            "mutator_type": mutator_type,
            "mutation_strategy": "",
            "is_valid": False,
            "error_type": "other",
            "verifier_output": f"Validation worker failed: {exc}",
            "trivial": False,
            "is_duplicate": False,
            "content_hash": None,
            "rule_check_passed": None,
            "timeout_occurred": False,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })


def _run_validation_isolated(mutant_id: str, mutator_type: str) -> dict:
    """
    Isolate each validation task in a child Python process so one mutant cannot
    poison the whole API batch.
    """
    src_dir = {
        "llm": MUTANT_DIR,
        "grammar": GRAMMAR_DIR,
        "random": RANDOM_DIR,
    }[mutator_type]
    ll_path = src_dir / f"{mutant_id}.ll"
    if not ll_path.exists():
        raise FileNotFoundError(f"Mutant file not found: {ll_path}")

    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_validate_mutant_worker, args=(mutant_id, mutator_type, queue))
    proc.start()
    proc.join(VALIDATION_TIMEOUT * 2 + 5)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {
            "mutant_id": mutant_id,
            "seed_name": _extract_seed_name(mutant_id) or "",
            "run_tag": _extract_run_tag(mutant_id),
            "mutator_type": mutator_type,
            "mutation_strategy": "",
            "is_valid": False,
            "error_type": "timeout",
            "verifier_output": "Validation worker timed out and was terminated.",
            "trivial": False,
            "is_duplicate": False,
            "content_hash": None,
            "rule_check_passed": None,
            "timeout_occurred": True,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    if proc.exitcode not in (0, None) and queue.empty():
        return {
            "mutant_id": mutant_id,
            "seed_name": _extract_seed_name(mutant_id) or "",
            "run_tag": _extract_run_tag(mutant_id),
            "mutator_type": mutator_type,
            "mutation_strategy": "",
            "is_valid": False,
            "error_type": "other",
            "verifier_output": f"Validation worker crashed with exit code {proc.exitcode}.",
            "trivial": False,
            "is_duplicate": False,
            "content_hash": None,
            "rule_check_passed": None,
            "timeout_occurred": False,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    if queue.empty():
        return {
            "mutant_id": mutant_id,
            "seed_name": _extract_seed_name(mutant_id) or "",
            "run_tag": _extract_run_tag(mutant_id),
            "mutator_type": mutator_type,
            "mutation_strategy": "",
            "is_valid": False,
            "error_type": "other",
            "verifier_output": "Validation worker exited without returning a result.",
            "trivial": False,
            "is_duplicate": False,
            "content_hash": None,
            "rule_check_passed": None,
            "timeout_occurred": False,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    return queue.get()


def validate_batch(mutant_ids: list[str]) -> list[dict]:
    """Validate a list of mutant IDs and return per-mutant results."""
    results = []
    for mid in mutant_ids:
        # If the mutant was already validated and moved to VALID_DIR/INVALID_DIR,
        # avoid re-running llvm-as/opt which looks for files in the original
        # mutator output directories. Prefer returning the existing log entry
        # when present, otherwise report current on-disk status.
        log_file = LOGS_DIR / "validity_logs.json"
        if (VALID_DIR / f"{mid}.ll").exists() or (INVALID_DIR / f"{mid}.ll").exists():
            existing_entry = None
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        logs = json.load(f)
                    for e in logs:
                        if e.get("mutant_id") == mid:
                            existing_entry = e
                            break
                except Exception:
                    existing_entry = None

            if existing_entry is not None:
                results.append(existing_entry)
                continue
            else:
                # No log entry found — return a best-effort status from file location
                is_in_valid = (VALID_DIR / f"{mid}.ll").exists()
                results.append({
                    "mutant_id": mid,
                    "seed_name": _extract_seed_name(mid) or "",
                    "run_tag": _extract_run_tag(mid),
                    "mutator_type": "unknown",
                    "mutation_strategy": "",
                    "is_valid": bool(is_in_valid),
                    "error_type": None if is_in_valid else "other",
                    "verifier_output": "Already validated (no log entry).",
                    "trivial": False,
                    "is_duplicate": False,
                    "content_hash": None,
                    "rule_check_passed": None,
                    "timeout_occurred": False,
                    "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                })
                continue
        candidate_types = ["llm", "grammar", "random"]
        validated = False
        for candidate_type in candidate_types:
            try:
                results.append(_run_validation_isolated(mid, candidate_type))
                validated = True
                break
            except FileNotFoundError:
                continue

        if not validated:
            results.append({
                "mutant_id": mid,
                "seed_name": _extract_seed_name(mid) or "",
                "run_tag": _extract_run_tag(mid),
                "mutator_type": "unknown",
                "mutation_strategy": "",
                "is_valid": False,
                "error_type": "other",
                "verifier_output": "File not found in llm, grammar, or random dirs.",
                "trivial": False,
                "is_duplicate": False,
                "content_hash": None,
                "rule_check_passed": None,
                "timeout_occurred": False,
                "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            })

    from .services.manifest_service import ManifestTracker
    ManifestTracker(LOGS_DIR).save_manifest(SEED_DIR)
    return results
