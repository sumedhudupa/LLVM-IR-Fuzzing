"""Shared utilities for the LLVM IR generation and testing project."""

import re
import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class ErrorCategory(Enum):
    SSA_VIOLATION = "ssa_violation"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_TERMINATOR = "missing_terminator"
    INVALID_PHI = "invalid_phi"
    USE_BEFORE_DEF = "use_before_def"
    INVALID_OPCODE = "invalid_opcode"
    BROKEN_CONTROL_FLOW = "broken_control_flow"
    WRONG_ARG_COUNT = "wrong_arg_count"
    MISSING_DECLARATION = "missing_declaration"
    SYNTAX_ERROR = "syntax_error"
    SEMANTICALLY_USELESS = "semantically_useless"
    UNKNOWN = "unknown"


@dataclass
class IRValidationResult:
    is_valid: bool
    errors: list = field(default_factory=list)
    error_categories: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    rule_check_passed: bool = False
    semantic_check_passed: bool = False
    llvm_verify_passed: bool = False

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "error_categories": [e.value if isinstance(e, ErrorCategory) else e for e in self.error_categories],
            "warnings": self.warnings,
            "rule_check_passed": self.rule_check_passed,
            "semantic_check_passed": self.semantic_check_passed,
            "llvm_verify_passed": self.llvm_verify_passed,
        }


@dataclass
class GenerationResult:
    source: str  # "llm", "grammar", "random"
    ir_text: str
    validation: Optional[IRValidationResult] = None
    generation_time_s: float = 0.0
    prompt_used: str = ""
    seed_ir: str = ""
    mutation_type: str = ""
    is_interesting: bool = False  # Exercises non-trivial paths
    opt_differential: dict = field(default_factory=dict)  # Results from differential testing

    def to_dict(self):
        return {
            "source": self.source,
            "ir_text": self.ir_text,
            "validation": self.validation.to_dict() if self.validation else None,
            "generation_time_s": self.generation_time_s,
            "mutation_type": self.mutation_type,
            "is_interesting": self.is_interesting,
            "opt_differential": self.opt_differential,
        }


def extract_ir_from_response(response: str) -> str:
    """Extract LLVM IR from an LLM response that may contain markdown or explanation."""
    # Try to extract from code blocks first
    code_block_pattern = r'```(?:llvm|ir|llvm-ir)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, response, re.DOTALL)
    if matches:
        return matches[0].strip()

    # Try to find IR by looking for 'define' keyword
    lines = response.split('\n')
    ir_lines = []
    in_ir = False
    brace_depth = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('define ') or stripped.startswith('declare '):
            in_ir = True
        if in_ir:
            ir_lines.append(line)
            brace_depth += line.count('{') - line.count('}')
            if brace_depth <= 0 and ir_lines:
                break

    if ir_lines:
        return '\n'.join(ir_lines).strip()

    # Fallback: return the whole response
    return response.strip()


def compute_ir_hash(ir_text: str) -> str:
    """Compute a normalized hash of IR for deduplication."""
    # Normalize: strip comments, whitespace, register names
    normalized = re.sub(r';.*$', '', ir_text, flags=re.MULTILINE)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def count_ir_features(ir_text: str) -> dict:
    """Count structural features in an IR snippet."""
    features = {
        "num_blocks": len(re.findall(r'^[a-zA-Z_][a-zA-Z0-9_.]*:', ir_text, re.MULTILINE)),
        "num_instructions": sum(
            1 for l in ir_text.split('\n')
            if l.strip()
            and not l.strip().startswith(';')
            and not l.strip().startswith('define')
            and not l.strip().startswith('}')
            and not re.match(r'^[a-zA-Z_]\w*:', l.strip())
        ),
        "has_phi": 'phi ' in ir_text,
        "has_branch": 'br ' in ir_text,
        "has_loop": bool(re.search(r'br.*label\s+%(\w+).*\1:', ir_text)),
        "has_switch": 'switch ' in ir_text,
        "has_select": 'select ' in ir_text,
        "has_memory_ops": any(op in ir_text for op in ['load ', 'store ', 'alloca ', 'getelementptr ']),
        "has_float": any(op in ir_text for op in ['fadd ', 'fsub ', 'fmul ', 'fdiv ', 'fcmp ']),
        "has_nsw_nuw": 'nsw' in ir_text or 'nuw' in ir_text,
        "has_call": 'call ' in ir_text,
        "num_phi_nodes": ir_text.count('phi '),
        "num_branches": ir_text.count('br '),
    }
    # Count entry block
    if 'entry:' in ir_text or (features["num_blocks"] == 0 and 'define' in ir_text):
        features["num_blocks"] = max(features["num_blocks"], 1)
    return features


def format_ir_stats(results: list) -> str:
    """Format experiment results into a readable summary."""
    total = len(results)
    if total == 0:
        return "No results to summarize."

    valid = sum(1 for r in results if r.validation and r.validation.is_valid)
    interesting = sum(1 for r in results if r.is_interesting)

    # Error category breakdown
    error_counts = {}
    for r in results:
        if r.validation:
            for cat in r.validation.error_categories:
                cat_name = cat.value if isinstance(cat, ErrorCategory) else str(cat)
                error_counts[cat_name] = error_counts.get(cat_name, 0) + 1

    summary = f"""
=== IR Generation Statistics ===
Total generated: {total}
Valid IR: {valid} ({100*valid/total:.1f}%)
Interesting (non-trivial): {interesting} ({100*interesting/total:.1f}%)
Invalid: {total - valid} ({100*(total-valid)/total:.1f}%)

Error Breakdown:
"""
    for cat, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        summary += f"  {cat}: {count} ({100*count/(total-valid):.1f}% of invalid)\n"

    return summary
