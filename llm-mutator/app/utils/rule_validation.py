"""
app/utils/rule_validation.py
Rule-based pre-validation for LLVM IR structural checks.
Source: requirements.md → Requirement 4: Rule-Based Pre-Validation

Performs lightweight structural checks before invoking expensive LLVM tools.
"""
import re
from typing import Literal
from dataclasses import dataclass, field

ErrorCategory = Literal["syntax", "ssa", "type", "cfg", "undef", "other"]


@dataclass
class RuleValidationResult:
    """Result of rule-based pre-validation."""
    is_valid: bool
    error_type: ErrorCategory | None = None
    issues: list[str] = field(default_factory=list)


def prevalidate_ir(ir_text: str) -> RuleValidationResult:
    """
    Pre-validate LLVM IR using lightweight structural checks.

    Checks performed (in order):
      1. Function definitions exist (regex: define\\s+\\S+\\s+@\\w+)
      2. Balanced braces (equal counts of '{' and '}')
      3. Basic blocks end with terminator instructions
      4. SSA property (no multiple definitions of same register)
      5. PHI node placement (must be first in block)
      6. Branch targets reference existing labels
      7. Basic type consistency (int ops use int types, float ops use float types)

    Returns:
        RuleValidationResult with is_valid, error_type, and issues list
    """
    issues: list[str] = []

    # Check 1: Function definitions
    func_pattern = r"define\s+\S+\s+@\w+"
    if not re.search(func_pattern, ir_text):
        return RuleValidationResult(
            is_valid=False,
            error_type="syntax",
            issues=["No function definitions found (missing 'define' statements)"]
        )

    # Check 2: Balanced braces
    open_braces = ir_text.count('{')
    close_braces = ir_text.count('}')
    if open_braces != close_braces:
        return RuleValidationResult(
            is_valid=False,
            error_type="syntax",
            issues=[f"Unbalanced braces: {open_braces} open, {close_braces} close"]
        )

    # Check 3: Basic blocks end with terminators
    # Terminator instructions: ret, br, switch, unreachable, resume, cleanupret
    terminator_pattern = r'\b(ret|br|switch|unreachable|resume|cleanupret|indirectbr)\b'
    blocks = _extract_basic_blocks(ir_text)
    for block_name, block_content in blocks:
        if block_content.strip():
            # Check if last instruction is a terminator
            last_instr = block_content.strip().split('\n')[-1].strip()
            if last_instr and not re.search(terminator_pattern, last_instr):
                issues.append(f"Block '{block_name}' does not end with terminator: {last_instr[:50]}")

    if issues:
        return RuleValidationResult(
            is_valid=False,
            error_type="cfg",
            issues=issues
        )

    # Check 4: SSA property - no multiple definitions of same register
    ssa_violations = _check_ssa_property(ir_text)
    if ssa_violations:
        return RuleValidationResult(
            is_valid=False,
            error_type="ssa",
            issues=ssa_violations
        )

    # Check 5: PHI node placement
    phi_violations = _check_phi_placement(ir_text)
    if phi_violations:
        return RuleValidationResult(
            is_valid=False,
            error_type="ssa",
            issues=phi_violations
        )

    # Check 6: Branch targets reference existing labels
    branch_violations = _check_branch_targets(ir_text)
    if branch_violations:
        return RuleValidationResult(
            is_valid=False,
            error_type="cfg",
            issues=branch_violations
        )

    # Check 7: Basic type consistency
    type_violations = _check_type_consistency(ir_text)
    if type_violations:
        return RuleValidationResult(
            is_valid=False,
            error_type="type",
            issues=type_violations
        )

    # All checks passed
    return RuleValidationResult(is_valid=True, issues=[])


def _extract_basic_blocks(ir_text: str) -> list[tuple[str, str]]:
    """
    Extract basic blocks from IR text.
    Returns list of (block_name, block_content) tuples.
    """
    blocks = []
    # Match block labels like: entry:, loop:, etc.
    # A block starts with a label or function header and ends with next label or closing brace

    lines = ir_text.split('\n')
    current_block_name = None
    current_block_content: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Check for block label (e.g., "entry:", "loop:")
        label_match = re.match(r'^(\w+):\s*$', stripped)
        if label_match:
            # Save previous block if exists
            if current_block_name is not None:
                blocks.append((current_block_name, '\n'.join(current_block_content)))
            current_block_name = label_match.group(1)
            current_block_content = []
        elif current_block_name is not None:
            # Check if we've reached end of function
            if stripped == '}':
                blocks.append((current_block_name, '\n'.join(current_block_content)))
                current_block_name = None
                current_block_content = []
            else:
                current_block_content.append(stripped)

    return blocks


def _check_ssa_property(ir_text: str) -> list[str]:
    """
    Check for SSA violations - multiple definitions of the same register.
    Returns list of violation messages.
    """
    violations = []
    definitions: dict[str, int] = {}  # register -> definition count

    # Match register definitions: %name = ...
    def_pattern = r'%([a-zA-Z_][a-zA-Z0-9_]*)\s*='

    for match in re.finditer(def_pattern, ir_text):
        reg_name = match.group(1)
        if reg_name in definitions:
            definitions[reg_name] += 1
            if definitions[reg_name] == 2:
                violations.append(f"SSA violation: register '%{reg_name}' defined multiple times")
        else:
            definitions[reg_name] = 1

    return violations


def _check_phi_placement(ir_text: str) -> list[str]:
    """
    Check PHI node placement - must appear before non-PHI instructions in blocks.
    Returns list of violation messages.
    """
    violations = []

    blocks = _extract_basic_blocks(ir_text)
    for block_name, block_content in blocks:
        lines = block_content.strip().split('\n')
        seen_non_phi = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_phi = bool(re.match(r'%\w+\s*=\s*phi\b', stripped))

            if is_phi:
                if seen_non_phi:
                    violations.append(
                        f"Block '{block_name}': PHI instruction appears after non-PHI instruction"
                    )
            else:
                seen_non_phi = True

    return violations


def _check_branch_targets(ir_text: str) -> list[str]:
    """
    Check that branch targets reference existing block labels.
    Returns list of violation messages.
    """
    violations = []

    # Collect all block labels
    labels = set()
    label_pattern = r'^(\w+):\s*$'
    for line in ir_text.split('\n'):
        match = re.match(label_pattern, line.strip())
        if match:
            labels.add(match.group(1))

    # Check branch targets
    # Pattern: br i1 %cond, label %target1, label %target2
    # or: br label %target
    branch_pattern = r'br\s+(?:i1\s+%[\w.]+,\s+)?label\s+%(\w+)'

    for match in re.finditer(branch_pattern, ir_text):
        target = match.group(1)
        if target not in labels:
            violations.append(f"Branch target '%{target}' references non-existent label")

    # Also check switch targets
    switch_pattern = r'switch\s+\S+\s+,\s+label\s+%(\w+)(?:\s+\[[-\s\w%.,]+\])+ '
    for match in re.finditer(switch_pattern, ir_text):
        default_target = match.group(1)
        if default_target not in labels:
            violations.append(f"Switch default target '%{default_target}' references non-existent label")

    return violations


def _check_type_consistency(ir_text: str) -> list[str]:
    """
    Perform basic type consistency checks.
    Returns list of violation messages.
    """
    violations = []

    # Check: integer operations should use integer types
    int_ops = ['add', 'sub', 'mul', 'sdiv', 'udiv', 'srem', 'urem', 'and', 'or', 'xor', 'shl', 'lshr', 'ashr']
    for op in int_ops:
        # Pattern: op i32/i64/etc - should be fine
        # Pattern: op float/double - violation
        bad_type_pattern = rf'\b{op}\s+(float|double|fp128|x86_fp80)\b'
        for match in re.finditer(bad_type_pattern, ir_text):
            violations.append(f"Type error: integer op '{op}' used with float type '{match.group(1)}'")

    # Check: float operations should use float types
    float_ops = ['fadd', 'fsub', 'fmul', 'fdiv', 'frem']
    for op in float_ops:
        # Pattern: op i32/i64 - violation
        bad_type_pattern = rf'\b{op}\s+i(32|64|16|8)\b'
        for match in re.finditer(bad_type_pattern, ir_text):
            violations.append(f"Type error: float op '{op}' used with integer type 'i{match.group(1)}'")

    return violations
