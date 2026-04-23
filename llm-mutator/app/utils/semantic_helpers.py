"""
app/utils/semantic_helpers.py
Semantic analysis utilities for LLVM IR mutation detection.
"""
import subprocess
import re
from pathlib import Path


def _normalize_ir(ir_text: str) -> str:
    """
    Normalize IR for semantic comparison.
    - Strips comments (lines starting with ;)
    - Strips leading/trailing whitespace
    - Collapses multiple whitespace to single space
    - Strips module ID and source metadata lines
    """
    lines = ir_text.splitlines()
    normalized_lines = []

    for line in lines:
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            continue
        # Skip comment lines (but not inline comments)
        if stripped.startswith(';'):
            continue
        # Skip module metadata lines
        if stripped.startswith('ModuleID') or stripped.startswith('source'):
            continue
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', stripped)
        normalized_lines.append(cleaned)

    return '\n'.join(normalized_lines)


def _run_opt_normalize(ir_path: Path) -> str | None:
    """
    Run opt -S -passes=instcombine,simplifycfg on the IR file.
    Returns the normalized output or None if the command fails.
    """
    try:
        result = subprocess.run(
            ["opt", "-S", "-passes=instcombine,simplifycfg", str(ir_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def is_semantically_trivial(seed_path: Path, mutant_path: Path) -> bool:
    """
    Check if a mutant is semantically equivalent to its seed.

    This is done by:
    1. Running both through opt -S -passes=instcombine,simplifycfg to normalize
    2. Stripping comments and whitespace
    3. Comparing the normalized outputs

    Args:
        seed_path: Path to the original seed IR file
        mutant_path: Path to the mutant IR file

    Returns:
        True if the mutant is semantically equivalent to the seed
    """
    # If either file doesn't exist, can't compare
    if not seed_path.exists() or not mutant_path.exists():
        return False

    # Run both through normalization passes
    seed_normalized = _run_opt_normalize(seed_path)
    mutant_normalized = _run_opt_normalize(mutant_path)

    # If normalization failed for either, assume not trivial
    if seed_normalized is None or mutant_normalized is None:
        return False

    # Normalize further (strip comments, whitespace)
    seed_clean = _normalize_ir(seed_normalized)
    mutant_clean = _normalize_ir(mutant_normalized)

    # Compare
    return seed_clean == mutant_clean
