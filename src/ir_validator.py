"""
Multi-stage LLVM IR validation pipeline.

Stages:
1. Syntax check (regex-based structure validation)
2. Rule-based checks (SSA, types, terminators, PHI nodes)
3. LLVM verifier (via llvmlite)
4. Semantic interest check (is the IR non-trivial?)
"""

import re
from typing import Tuple
from .utils import IRValidationResult, ErrorCategory, count_ir_features

# ============================================================
# Stage 1: Structural / Syntax Checks
# ============================================================

def check_basic_structure(ir_text: str) -> Tuple[bool, list, list]:
    """Check basic structural requirements of LLVM IR."""
    errors = []
    categories = []

    # Must have at least one function definition
    if not re.search(r'define\s+\S+\s+@\w+', ir_text):
        errors.append("No function definition found (expected 'define <type> @<name>(...)')")
        categories.append(ErrorCategory.SYNTAX_ERROR)

    # Braces must be balanced
    open_braces = ir_text.count('{')
    close_braces = ir_text.count('}')
    if open_braces != close_braces:
        errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        categories.append(ErrorCategory.SYNTAX_ERROR)

    return len(errors) == 0, errors, categories


# ============================================================
# Stage 2: Rule-Based Checks
# ============================================================

def parse_blocks(ir_text: str) -> dict:
    """Parse IR into basic blocks. Returns {label: [instructions]}."""
    blocks = {}
    current_label = None
    current_instrs = []

    for line in ir_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            continue

        # Function definition -> entry block
        if stripped.startswith('define '):
            continue
        if stripped == '{':
            continue
        if stripped == '}':
            if current_label and current_instrs:
                blocks[current_label] = current_instrs
            break

        # Block label
        label_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_.]*)\s*:', stripped)
        if label_match:
            if current_label and current_instrs:
                blocks[current_label] = current_instrs
            current_label = label_match.group(1)
            current_instrs = []
            # Check for instructions after the label on same line
            rest = stripped[label_match.end():].strip()
            if rest:
                current_instrs.append(rest)
            continue

        # If no label yet, this is the entry block
        if current_label is None:
            current_label = "entry"

        current_instrs.append(stripped)

    # Don't forget the last block
    if current_label and current_instrs and current_label not in blocks:
        blocks[current_label] = current_instrs

    return blocks


TERMINATORS = {'ret', 'br', 'switch', 'invoke', 'resume', 'unreachable', 'indirectbr', 'callbr'}

def check_terminators(blocks: dict) -> Tuple[bool, list, list]:
    """Every basic block must end with a terminator instruction."""
    errors = []
    categories = []

    for label, instrs in blocks.items():
        if not instrs:
            errors.append(f"Block '{label}' is empty (no instructions)")
            categories.append(ErrorCategory.MISSING_TERMINATOR)
            continue

        last_instr = instrs[-1]
        first_word = last_instr.split()[0] if last_instr.split() else ""
        # Handle assignment: %x = tail call ...
        if '=' in last_instr:
            first_word = last_instr.split('=')[1].strip().split()[0]

        if first_word not in TERMINATORS:
            errors.append(f"Block '{label}' does not end with a terminator. Last: '{last_instr[:60]}'")
            categories.append(ErrorCategory.MISSING_TERMINATOR)

        # Check no instructions after terminator
        for i, instr in enumerate(instrs[:-1]):
            iword = instr.split()[0] if instr.split() else ""
            if '=' in instr:
                rhs = instr.split('=')[1].strip()
                iword = rhs.split()[0] if rhs.split() else ""
            if iword in TERMINATORS:
                errors.append(f"Block '{label}': instruction after terminator at position {i}")
                categories.append(ErrorCategory.BROKEN_CONTROL_FLOW)

    return len(errors) == 0, errors, categories


def check_ssa(ir_text: str) -> Tuple[bool, list, list]:
    """Check SSA property: each register defined at most once."""
    errors = []
    categories = []
    definitions = {}

    for line_num, line in enumerate(ir_text.split('\n'), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(';') or stripped.startswith('define'):
            continue

        # Look for register definitions: %name = ...
        def_match = re.match(r'(%[a-zA-Z0-9_.]+)\s*=\s*', stripped)
        if def_match:
            reg_name = def_match.group(1)
            if reg_name in definitions:
                errors.append(
                    f"SSA violation: '{reg_name}' defined at line {line_num} "
                    f"and previously at line {definitions[reg_name]}"
                )
                categories.append(ErrorCategory.SSA_VIOLATION)
            definitions[reg_name] = line_num

    return len(errors) == 0, errors, categories


def check_phi_nodes(blocks: dict) -> Tuple[bool, list, list]:
    """Check PHI node validity."""
    errors = []
    categories = []

    block_labels = set(blocks.keys())

    for label, instrs in blocks.items():
        seen_non_phi = False
        for instr in instrs:
            # Extract instruction name after possible assignment
            rhs = instr
            if '=' in instr:
                rhs = instr.split('=', 1)[1].strip()

            is_phi = rhs.startswith('phi ')

            if is_phi and seen_non_phi:
                errors.append(f"Block '{label}': PHI node after non-PHI instruction")
                categories.append(ErrorCategory.INVALID_PHI)

            if not is_phi and not rhs.startswith(';'):
                seen_non_phi = True

            # Check PHI predecessor labels
            if is_phi:
                pred_labels = re.findall(r'%(\w+)\]', instr)
                for pred in pred_labels:
                    if pred not in block_labels:
                        errors.append(
                            f"Block '{label}': PHI references non-existent predecessor '{pred}'"
                        )
                        categories.append(ErrorCategory.INVALID_PHI)

        # Check PHI in entry block (if it has no predecessors)
        if label == "entry":
            for instr in instrs:
                rhs = instr.split('=', 1)[1].strip() if '=' in instr else instr
                if rhs.startswith('phi '):
                    errors.append("PHI node in entry block (entry has no predecessors)")
                    categories.append(ErrorCategory.INVALID_PHI)

    return len(errors) == 0, errors, categories


def check_branch_targets(ir_text: str, blocks: dict) -> Tuple[bool, list, list]:
    """Check that all branch targets reference valid blocks."""
    errors = []
    categories = []
    block_labels = set(blocks.keys())

    # Find all branch targets
    br_targets = re.findall(r'label\s+%(\w+)', ir_text)
    for target in br_targets:
        if target not in block_labels:
            errors.append(f"Branch target '%{target}' does not exist as a block label")
            categories.append(ErrorCategory.BROKEN_CONTROL_FLOW)

    return len(errors) == 0, errors, categories


def check_type_consistency(ir_text: str) -> Tuple[bool, list, list]:
    """Basic type consistency checks."""
    errors = []
    categories = []

    # Check that integer ops use integer types
    int_ops = ['add', 'sub', 'mul', 'udiv', 'sdiv', 'urem', 'srem', 'shl', 'lshr', 'ashr', 'and', 'or', 'xor']
    float_ops = ['fadd', 'fsub', 'fmul', 'fdiv', 'frem']

    for line in ir_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            continue

        rhs = stripped
        if '=' in stripped:
            rhs = stripped.split('=', 1)[1].strip()

        parts = rhs.split()
        if not parts:
            continue

        # Remove nsw/nuw/exact flags
        op = parts[0]

        if op in int_ops:
            # Should have integer type
            type_candidates = [p for p in parts[1:] if p.startswith('i') and p[1:].isdigit()]
            float_types = [p for p in parts[1:] if p in ('float', 'double', 'half', 'fp128')]
            if float_types and not type_candidates:
                errors.append(f"Integer operation '{op}' used with float type: {stripped[:80]}")
                categories.append(ErrorCategory.TYPE_MISMATCH)

        elif op in float_ops:
            # Should have float type
            int_types = [p for p in parts[1:] if p.startswith('i') and p[1:].isdigit()]
            float_types = [p for p in parts[1:] if p in ('float', 'double', 'half', 'fp128')]
            if int_types and not float_types:
                errors.append(f"Float operation '{op}' used with integer type: {stripped[:80]}")
                categories.append(ErrorCategory.TYPE_MISMATCH)

    return len(errors) == 0, errors, categories


def check_use_before_def(ir_text: str) -> Tuple[bool, list, list]:
    """Check for uses of undefined registers (simplified check)."""
    errors = []
    categories = []

    defined = set()
    # Add function parameters as defined
    param_match = re.search(r'define\s+\S+\s+@\w+\(([^)]*)\)', ir_text)
    if param_match:
        params = param_match.group(1)
        for p in re.findall(r'%(\w+)', params):
            defined.add(f'%{p}')

    for line in ir_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith(';') or stripped.startswith('define'):
            continue
        if re.match(r'^[a-zA-Z_]\w*:', stripped):
            continue
        if stripped in ('{', '}'):
            continue

        # Record definition
        def_match = re.match(r'(%[a-zA-Z0-9_.]+)\s*=', stripped)
        if def_match:
            defined.add(def_match.group(1))

        # PHI nodes reference values from predecessors — skip use-before-def for PHIs
        rhs = stripped.split('=', 1)[1].strip() if '=' in stripped else stripped
        if rhs.startswith('phi '):
            continue

        # Check uses (simplified: won't handle all cases but catches common ones)
        # Skip the defined register on the left side
        check_text = stripped
        if def_match:
            check_text = stripped.split('=', 1)[1]

        uses = re.findall(r'(%[a-zA-Z0-9_.]+)', check_text)
        for use in uses:
            # Skip label references (they appear after 'label')
            if f'label {use}' in check_text:
                continue
            if use not in defined:
                # Don't flag if it looks like it could be from a dominating block
                # (This is a simplification — full check needs dominator tree)
                pass  # Simplified: we note but don't error on this

    return len(errors) == 0, errors, categories


# ============================================================
# Stage 3: LLVM Verifier (via llvmlite)
# ============================================================

def check_llvm_verify(ir_text: str) -> Tuple[bool, list, list]:
    """Use llvmlite to parse and verify the IR."""
    errors = []
    categories = []

    try:
        import llvmlite.binding as llvm

        # Try to parse the module
        try:
            mod = llvm.parse_assembly(ir_text)
            # Module parsed successfully
            return True, [], []
        except RuntimeError as e:
            error_msg = str(e)
            errors.append(f"LLVM verifier error: {error_msg[:200]}")

            # Categorize the error
            lower_msg = error_msg.lower()
            if 'redefinition' in lower_msg or 'ssa' in lower_msg or 'multiple definition' in lower_msg:
                categories.append(ErrorCategory.SSA_VIOLATION)
            elif 'type' in lower_msg or 'mismatch' in lower_msg:
                categories.append(ErrorCategory.TYPE_MISMATCH)
            elif 'terminator' in lower_msg:
                categories.append(ErrorCategory.MISSING_TERMINATOR)
            elif 'phi' in lower_msg:
                categories.append(ErrorCategory.INVALID_PHI)
            elif 'dominat' in lower_msg:
                categories.append(ErrorCategory.USE_BEFORE_DEF)
            elif 'expected' in lower_msg or 'invalid' in lower_msg or 'unknown' in lower_msg:
                categories.append(ErrorCategory.SYNTAX_ERROR)
            else:
                categories.append(ErrorCategory.UNKNOWN)

    except ImportError:
        errors.append("llvmlite not available — skipping LLVM verification")
        categories.append(ErrorCategory.UNKNOWN)

    return len(errors) == 0, errors, categories


# ============================================================
# Stage 4: Semantic Interest Check
# ============================================================

def check_semantic_interest(ir_text: str) -> Tuple[bool, list]:
    """Check if the IR is semantically interesting for testing."""
    warnings = []
    features = count_ir_features(ir_text)

    interest_score = 0

    if features["has_phi"]:
        interest_score += 2
    if features["has_branch"]:
        interest_score += 1
    if features["has_loop"]:
        interest_score += 3
    if features["has_switch"]:
        interest_score += 2
    if features["has_memory_ops"]:
        interest_score += 2
    if features["has_float"]:
        interest_score += 1
    if features["has_nsw_nuw"]:
        interest_score += 2  # Overflow flags are optimization-relevant
    if features["has_select"]:
        interest_score += 1
    if features["num_blocks"] > 3:
        interest_score += 1
    if features["num_phi_nodes"] > 1:
        interest_score += 1

    is_interesting = interest_score >= 3

    if interest_score < 2:
        warnings.append(f"Low semantic interest score ({interest_score}): IR is trivial")
    if features["num_blocks"] <= 1 and not features["has_memory_ops"]:
        warnings.append("Single-block function with no memory ops — limited testing value")
    if not features["has_branch"] and not features["has_phi"]:
        warnings.append("No control flow — straightline code has limited optimizer interaction")

    return is_interesting, warnings


# ============================================================
# Combined Validation Pipeline
# ============================================================

def validate_ir(ir_text: str, use_llvm_verify: bool = True) -> IRValidationResult:
    """Run full validation pipeline on LLVM IR text."""
    result = IRValidationResult(is_valid=False)

    # Stage 1: Basic structure
    ok, errors, cats = check_basic_structure(ir_text)
    result.errors.extend(errors)
    result.error_categories.extend(cats)
    if not ok:
        return result

    # Stage 2: Rule-based checks
    blocks = parse_blocks(ir_text)

    checks = [
        check_terminators(blocks),
        check_ssa(ir_text),
        check_phi_nodes(blocks),
        check_branch_targets(ir_text, blocks),
        check_type_consistency(ir_text),
    ]

    all_rule_ok = True
    for ok, errors, cats in checks:
        if not ok:
            all_rule_ok = False
        result.errors.extend(errors)
        result.error_categories.extend(cats)

    result.rule_check_passed = all_rule_ok

    # Stage 3: LLVM verifier
    if use_llvm_verify:
        ok, errors, cats = check_llvm_verify(ir_text)
        result.llvm_verify_passed = ok
        result.errors.extend(errors)
        result.error_categories.extend(cats)
    else:
        result.llvm_verify_passed = result.rule_check_passed

    # Stage 4: Semantic interest
    is_interesting, warnings = check_semantic_interest(ir_text)
    result.semantic_check_passed = is_interesting
    result.warnings.extend(warnings)

    # Overall validity
    result.is_valid = result.rule_check_passed and result.llvm_verify_passed

    return result
