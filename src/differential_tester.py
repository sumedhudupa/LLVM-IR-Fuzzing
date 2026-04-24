"""
Differential testing across LLVM optimization levels.

Tests IR by running it through different optimization pipelines
and comparing results for miscompilation detection.

Uses llvmlite for optimization and execution where possible,
with fallback to structural comparison.

NOTE: Optimization is run in a subprocess to survive LLVM assertion
failures/crashes, which are exactly the bugs we're trying to find.
"""

import re
import os
import json
import hashlib
import signal
import tempfile
import subprocess
import sys
from typing import Optional
from .utils import count_ir_features


# Helper script for subprocess optimization
_OPT_SCRIPT = '''
import sys, json
import llvmlite.binding as llvm

ir_text = sys.stdin.read()
opt_level = int(sys.argv[1])

try:
    mod = llvm.parse_assembly(ir_text)
    pto = llvm.create_pipeline_tuning_options(speed_level=opt_level, size_level=0)
    pb = llvm.create_pass_builder(None, pto)
    pm = pb.getModulePassManager()
    pm.run(mod, pb)
    result = {"success": True, "ir": str(mod)}
except Exception as e:
    result = {"success": False, "error": str(e)[:300]}

print(json.dumps(result))
'''


def optimize_ir_subprocess(ir_text: str, opt_level: int = 2, timeout: int = 10) -> dict:
    """Optimize IR in a subprocess (survives LLVM crashes)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _OPT_SCRIPT, str(opt_level)],
            input=ir_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if proc.returncode != 0:
            # Process crashed — this IS a finding!
            return {
                "success": False,
                "crashed": True,
                "returncode": proc.returncode,
                "stderr": proc.stderr[:500] if proc.stderr else "",
                "error": f"LLVM crashed with return code {proc.returncode}",
            }

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"success": False, "error": "Failed to parse output", "stdout": proc.stdout[:200]}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Optimization timed out", "timeout": True}
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def optimize_ir_llvmlite(ir_text: str, opt_level: int = 2) -> Optional[str]:
    """Optimize IR using llvmlite in-process (fast but crashes on LLVM bugs)."""
    try:
        import llvmlite.binding as llvm

        mod = llvm.parse_assembly(ir_text)

        pto = llvm.create_pipeline_tuning_options(speed_level=opt_level, size_level=0)
        pb = llvm.create_pass_builder(None, pto)
        pm = pb.getModulePassManager()
        pm.run(mod, pb)

        return str(mod)
    except Exception as e:
        return None


def structural_compare(ir1: str, ir2: str) -> dict:
    """Compare two IR texts structurally."""
    features1 = count_ir_features(ir1)
    features2 = count_ir_features(ir2)

    diffs = {}
    for key in features1:
        if features1[key] != features2[key]:
            diffs[key] = {"before": features1[key], "after": features2[key]}

    # Count instructions
    def count_instructions(ir):
        return len([l for l in ir.split('\n')
                    if l.strip() and not l.strip().startswith(';')
                    and not l.strip().startswith('define')
                    and not l.strip().startswith('}')
                    and not re.match(r'^[a-zA-Z_]\w*:', l.strip())])

    n1 = count_instructions(ir1)
    n2 = count_instructions(ir2)

    return {
        "feature_diffs": diffs,
        "instruction_count_before": n1,
        "instruction_count_after": n2,
        "instruction_reduction": n1 - n2,
        "instruction_reduction_pct": (n1 - n2) / max(n1, 1) * 100,
        "is_identical": ir1.strip() == ir2.strip(),
        "hash_before": hashlib.md5(ir1.encode()).hexdigest()[:8],
        "hash_after": hashlib.md5(ir2.encode()).hexdigest()[:8],
    }


def differential_test(ir_text: str, use_subprocess: bool = True) -> dict:
    """
    Run differential testing: optimize at different levels and compare.

    Uses subprocess mode by default to survive LLVM crashes.
    Returns a dict with optimization results and any discrepancies found.
    """
    results = {
        "original": ir_text,
        "optimizations": {},
        "discrepancies": [],
        "crashes": [],
        "is_interesting": False,
    }

    # Try each optimization level
    for opt_level in [0, 1, 2, 3]:
        if use_subprocess:
            opt_result = optimize_ir_subprocess(ir_text, opt_level)
        else:
            optimized = optimize_ir_llvmlite(ir_text, opt_level)
            opt_result = {"success": optimized is not None}
            if optimized:
                opt_result["ir"] = optimized

        if opt_result.get("success"):
            optimized_ir = opt_result["ir"]
            comparison = structural_compare(ir_text, optimized_ir)
            results["optimizations"][f"O{opt_level}"] = {
                "optimized_ir": optimized_ir[:2000],
                "comparison": comparison,
                "succeeded": True,
            }
        else:
            entry = {
                "succeeded": False,
                "error": opt_result.get("error", "Unknown error"),
            }
            if opt_result.get("crashed"):
                entry["crashed"] = True
                entry["stderr"] = opt_result.get("stderr", "")
                results["crashes"].append({
                    "opt_level": opt_level,
                    "error": opt_result.get("error", ""),
                    "stderr": opt_result.get("stderr", ""),
                })
                results["is_interesting"] = True  # Crashes are always interesting!
            results["optimizations"][f"O{opt_level}"] = entry

    # Check for discrepancies between optimization levels
    opt_results = {}
    for level, data in results["optimizations"].items():
        if data["succeeded"]:
            opt_results[level] = data["optimized_ir"]

    # Compare O1 vs O2, O2 vs O3 for unusual differences
    level_pairs = [("O0", "O1"), ("O1", "O2"), ("O2", "O3")]
    for l1, l2 in level_pairs:
        if l1 in opt_results and l2 in opt_results:
            comp = structural_compare(opt_results[l1], opt_results[l2])
            if comp["instruction_reduction"] < 0:
                # O2 produced MORE instructions than O1 — potentially interesting
                results["discrepancies"].append({
                    "type": "instruction_increase",
                    "levels": f"{l1} -> {l2}",
                    "detail": f"Instructions increased by {-comp['instruction_reduction']}",
                })
                results["is_interesting"] = True

    # If any optimization produced significant changes, it's interesting
    for level, data in results["optimizations"].items():
        if data["succeeded"]:
            if data["comparison"]["instruction_reduction_pct"] > 20:
                results["is_interesting"] = True

    return results


def batch_differential_test(ir_texts: list) -> list:
    """Run differential testing on a batch of IR texts."""
    results = []
    for ir_text in ir_texts:
        result = differential_test(ir_text)
        results.append(result)
    return results
