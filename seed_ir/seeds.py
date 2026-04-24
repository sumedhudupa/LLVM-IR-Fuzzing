"""
Seed LLVM IR test cases for mutation and generation experiments.
These are known-valid IR snippets covering different complexity levels.
"""

SEED_IR_CASES = {
    "simple_add": {
        "ir": """\
define i32 @simple_add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}
""",
        "description": "Simple integer addition",
        "complexity": "trivial",
        "features": ["integer_arithmetic"],
    },
    "branch_simple": {
        "ir": """\
define i32 @branch_simple(i32 %x) {
entry:
  %cmp = icmp sgt i32 %x, 0
  br i1 %cmp, label %positive, label %negative

positive:
  %add = add nsw i32 %x, 1
  br label %merge

negative:
  %sub = sub nsw i32 0, %x
  br label %merge

merge:
  %result = phi i32 [%add, %positive], [%sub, %negative]
  ret i32 %result
}
""",
        "description": "Simple branch with PHI node",
        "complexity": "basic",
        "features": ["branch", "phi", "icmp", "nsw"],
    },
    "loop_simple": {
        "ir": """\
define i32 @loop_simple(i32 %n) {
entry:
  br label %loop

loop:
  %i = phi i32 [0, %entry], [%next_i, %loop]
  %sum = phi i32 [0, %entry], [%next_sum, %loop]
  %next_sum = add i32 %sum, %i
  %next_i = add i32 %i, 1
  %cmp = icmp slt i32 %next_i, %n
  br i1 %cmp, label %loop, label %exit

exit:
  ret i32 %next_sum
}
""",
        "description": "Simple loop with accumulator",
        "complexity": "intermediate",
        "features": ["loop", "phi", "icmp", "branch_back"],
    },
    "memory_ops": {
        "ir": """\
define i32 @memory_ops(ptr %arr, i32 %idx) {
entry:
  %ptr = getelementptr i32, ptr %arr, i32 %idx
  %val = load i32, ptr %ptr, align 4
  %doubled = mul i32 %val, 2
  store i32 %doubled, ptr %ptr, align 4
  ret i32 %doubled
}
""",
        "description": "Memory load/store with GEP",
        "complexity": "intermediate",
        "features": ["gep", "load", "store", "memory"],
    },
    "nested_branch": {
        "ir": """\
define i32 @nested_branch(i32 %x, i32 %y) {
entry:
  %cmp1 = icmp sgt i32 %x, 0
  br i1 %cmp1, label %x_pos, label %x_neg

x_pos:
  %cmp2 = icmp sgt i32 %y, 0
  br i1 %cmp2, label %both_pos, label %x_pos_y_neg

x_neg:
  %neg_x = sub i32 0, %x
  br label %done

both_pos:
  %sum = add i32 %x, %y
  br label %done

x_pos_y_neg:
  %diff = sub i32 %x, %y
  br label %done

done:
  %result = phi i32 [%neg_x, %x_neg], [%sum, %both_pos], [%diff, %x_pos_y_neg]
  ret i32 %result
}
""",
        "description": "Nested branches with multi-predecessor PHI",
        "complexity": "intermediate",
        "features": ["nested_branch", "phi_multi_pred", "icmp"],
    },
    "switch_case": {
        "ir": """\
define i32 @switch_case(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %default [
    i32 0, label %case_add
    i32 1, label %case_sub
    i32 2, label %case_mul
  ]

case_add:
  %r_add = add i32 %a, %b
  br label %done

case_sub:
  %r_sub = sub i32 %a, %b
  br label %done

case_mul:
  %r_mul = mul i32 %a, %b
  br label %done

default:
  br label %done

done:
  %result = phi i32 [%r_add, %case_add], [%r_sub, %case_sub], [%r_mul, %case_mul], [0, %default]
  ret i32 %result
}
""",
        "description": "Switch statement with multiple cases",
        "complexity": "intermediate",
        "features": ["switch", "phi_multi_pred"],
    },
    "float_ops": {
        "ir": """\
define double @float_ops(double %x, double %y) {
entry:
  %sum = fadd double %x, %y
  %prod = fmul double %sum, %x
  %cmp = fcmp ogt double %prod, 0.0
  br i1 %cmp, label %positive, label %negative

positive:
  %sqrt_approx = fmul double %prod, 0.5
  br label %done

negative:
  %abs = fsub double 0.0, %prod
  br label %done

done:
  %result = phi double [%sqrt_approx, %positive], [%abs, %negative]
  ret double %result
}
""",
        "description": "Floating-point operations with comparison",
        "complexity": "intermediate",
        "features": ["float", "fadd", "fmul", "fcmp"],
    },
    "nsw_nuw_flags": {
        "ir": """\
define i32 @nsw_nuw_flags(i32 %a, i32 %b) {
entry:
  %add_nsw = add nsw i32 %a, %b
  %mul_nuw = mul nuw i32 %add_nsw, 2
  %sub_nsw = sub nsw i32 %mul_nuw, %a
  %shl = shl nuw i32 %sub_nsw, 1
  ret i32 %shl
}
""",
        "description": "Operations with nsw/nuw overflow flags",
        "complexity": "intermediate",
        "features": ["nsw", "nuw", "overflow_flags"],
    },
    "select_inst": {
        "ir": """\
define i32 @select_inst(i32 %a, i32 %b) {
entry:
  %cmp = icmp slt i32 %a, %b
  %min = select i1 %cmp, i32 %a, i32 %b
  %cmp2 = icmp sgt i32 %a, %b
  %max = select i1 %cmp2, i32 %a, i32 %b
  %range = sub i32 %max, %min
  ret i32 %range
}
""",
        "description": "Select instruction (branchless conditional)",
        "complexity": "basic",
        "features": ["select", "icmp"],
    },
    "nested_loop": {
        "ir": """\
define i32 @nested_loop(i32 %rows, i32 %cols) {
entry:
  br label %outer_header

outer_header:
  %i = phi i32 [0, %entry], [%next_i, %outer_latch]
  %total = phi i32 [0, %entry], [%inner_total, %outer_latch]
  %outer_cmp = icmp slt i32 %i, %rows
  br i1 %outer_cmp, label %inner_header, label %exit

inner_header:
  %j = phi i32 [0, %outer_header], [%next_j, %inner_header]
  %inner_sum = phi i32 [%total, %outer_header], [%next_sum, %inner_header]
  %prod = mul i32 %i, %j
  %next_sum = add i32 %inner_sum, %prod
  %next_j = add i32 %j, 1
  %inner_cmp = icmp slt i32 %next_j, %cols
  br i1 %inner_cmp, label %inner_header, label %outer_latch

outer_latch:
  %inner_total = phi i32 [%next_sum, %inner_header]
  %next_i = add i32 %i, 1
  br label %outer_header

exit:
  ret i32 %total
}
""",
        "description": "Nested loops with PHIs at multiple levels",
        "complexity": "advanced",
        "features": ["nested_loop", "phi_multi_level", "mul"],
    },
}

# IR templates for LLM generation prompts
IR_GENERATION_TEMPLATES = {
    "basic_function": """\
; Generate a new LLVM IR function that {objective}
; Requirements:
; - Valid SSA form (each register defined exactly once)
; - Proper terminator at end of each basic block (ret, br, switch, unreachable)
; - Correct types (all operands must match instruction type)
; - PHI nodes only at beginning of blocks
; - All branch targets must be valid block labels

define {ret_type} @{func_name}({params}) {{
""",
    "mutation_prompt": """\
; The following is a valid LLVM IR function:
{original_ir}

; Mutate this function to {mutation_goal}
; IMPORTANT constraints to maintain:
; 1. SSA form: each %register defined exactly once
; 2. Every block ends with a terminator (ret/br/switch)
; 3. Types must match (no mixing i32 and i64 without casts)
; 4. PHI node predecessors must match actual CFG predecessors
; 5. All used values must be defined before use (domination)

; Mutated version:
""",
}

def get_seeds_by_complexity(complexity: str = None):
    """Get seed IR cases filtered by complexity."""
    if complexity is None:
        return SEED_IR_CASES
    return {k: v for k, v in SEED_IR_CASES.items() if v["complexity"] == complexity}

def get_seeds_by_feature(feature: str):
    """Get seed IR cases that use a specific feature."""
    return {k: v for k, v in SEED_IR_CASES.items() if feature in v["features"]}
