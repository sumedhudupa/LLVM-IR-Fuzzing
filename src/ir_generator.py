"""
LLM-based LLVM IR generation and mutation.

Uses the HuggingFace Inference API to prompt an LLM to generate or mutate LLVM IR.
Implements multiple strategies:
1. From-scratch generation with structured prompts
2. Seed-based mutation with specific mutation goals
3. Constrained generation with validity hints
4. Multi-shot refinement (generate → validate → refine)
"""

import os
import re
import time
import json
import random
from typing import Optional

try:
    from huggingface_hub import InferenceClient
    HAS_HF_CLIENT = True
except ImportError:
    HAS_HF_CLIENT = False

from .utils import GenerationResult, extract_ir_from_response, compute_ir_hash
from .ir_validator import validate_ir

# ============================================================
# LLM Prompts for IR Generation
# ============================================================

SYSTEM_PROMPT = """\
You are an expert LLVM IR code generator. You generate valid LLVM IR that follows all \
constraints of the LLVM IR specification. 

Critical rules you MUST follow:
1. SSA Form: Each %register is defined EXACTLY ONCE in the function
2. Terminators: Every basic block ends with ret, br, switch, or unreachable  
3. Types: All operands must have matching types. Integer ops (add, sub, mul) use i32/i64. \
Float ops (fadd, fsub, fmul) use float/double.
4. PHI nodes: Must appear at the START of a block, before any non-PHI instruction. \
Predecessor labels must match actual CFG predecessors.
5. Dominance: Every use of a value must be dominated by its definition.
6. Branch targets: All 'label %X' targets must reference existing block labels.

Output ONLY the LLVM IR code, no explanations. Start with 'define' and end with '}'."""

GENERATION_PROMPTS = {
    "arithmetic_chain": """\
Generate a valid LLVM IR function that performs a chain of arithmetic operations \
on i32 inputs with at least one conditional branch. Include nsw/nuw flags where \
semantically safe. The function should have 3-5 basic blocks.""",

    "loop_with_phi": """\
Generate a valid LLVM IR function with a loop that uses PHI nodes for the \
induction variable and an accumulator. The loop should compute something \
non-trivial like polynomial evaluation or array reduction.""",

    "nested_control_flow": """\
Generate a valid LLVM IR function with nested if-else branches (at least 3 levels \
of nesting). Use PHI nodes in merge blocks. Include at least one comparison each \
of icmp sgt, icmp slt, and icmp eq.""",

    "memory_access_pattern": """\
Generate a valid LLVM IR function that takes a pointer argument, performs \
getelementptr calculations, loads values, computes on them, and stores results \
back. Include at least one conditional based on a loaded value.""",

    "float_computation": """\
Generate a valid LLVM IR function that performs floating-point computations \
(fadd, fmul, fdiv) with at least one fcmp comparison and branch. Use 'double' \
type. Include fast-math flags on at least one operation.""",

    "switch_dispatch": """\
Generate a valid LLVM IR function with a switch instruction dispatching to at \
least 4 cases plus a default. Each case should perform different computations. \
Merge results with a PHI node.""",

    "mixed_types": """\
Generate a valid LLVM IR function that works with both integer (i32, i64) and \
floating-point (double) types. Include proper cast instructions (sitofp, fptosi, \
zext, trunc) for type conversions between computations.""",

    "optimizer_stress": """\
Generate a valid LLVM IR function designed to stress-test LLVM optimization passes. \
Include: dead code that could be eliminated, constant expressions that could be folded, \
redundant loads that could be CSE'd, and loop-invariant computations that could be hoisted. \
Make sure the function is still valid IR.""",
}

MUTATION_GOALS = {
    "add_branch": "add a new conditional branch that splits an existing basic block",
    "add_loop": "wrap an existing computation in a loop with a PHI node",
    "change_types": "change integer operations to use i64 instead of i32 (with proper zext/trunc)",
    "add_nsw_nuw": "add nsw and/or nuw flags to arithmetic operations where semantically valid",
    "add_memory_ops": "add memory operations (alloca, store, load) to compute intermediate results via memory",
    "add_select": "replace a branch+phi pattern with a select instruction",
    "add_dead_code": "add dead code that a good optimizer should eliminate",
    "duplicate_block": "duplicate a basic block to create a diamond control flow pattern",
    "add_overflow_check": "add an overflow check before an arithmetic operation using llvm.sadd.with.overflow",
}


class LLMIRGenerator:
    """LLM-based LLVM IR generator using HuggingFace Inference API."""

    def __init__(self, model_id: str = "Qwen/Qwen2.5-Coder-32B-Instruct", use_api: bool = True):
        self.model_id = model_id
        self.use_api = use_api
        self.generated_hashes = set()  # For dedup
        self.client = None

        if use_api and HAS_HF_CLIENT:
            token = os.environ.get("HF_TOKEN")
            if token:
                self.client = InferenceClient(model=model_id, token=token)
            else:
                print("Warning: HF_TOKEN not set — LLM generation will use mock mode")
                self.use_api = False

    def _call_llm(self, prompt: str, system: str = SYSTEM_PROMPT,
                  max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Call the LLM and return the response text."""
        if not self.use_api or self.client is None:
            return self._mock_generate(prompt)

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM API error: {e}")
            return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """Generate mock IR for testing without API access."""
        # Produce plausible but varied IR based on prompt keywords
        templates = [
            self._mock_arithmetic,
            self._mock_branch,
            self._mock_loop,
            self._mock_memory,
            self._mock_float,
            self._mock_switch,
        ]
        return random.choice(templates)()

    def _mock_arithmetic(self) -> str:
        fname = f"arith_{random.randint(0, 999)}"
        return f"""\
define i32 @{fname}(i32 %a, i32 %b) {{
entry:
  %sum = add nsw i32 %a, %b
  %prod = mul nsw i32 %sum, %a
  %diff = sub i32 %prod, %b
  %cmp = icmp sgt i32 %diff, 0
  br i1 %cmp, label %pos, label %neg

pos:
  %r1 = add i32 %diff, 1
  br label %done

neg:
  %r2 = sub i32 0, %diff
  br label %done

done:
  %result = phi i32 [%r1, %pos], [%r2, %neg]
  ret i32 %result
}}
"""

    def _mock_branch(self) -> str:
        fname = f"branch_{random.randint(0, 999)}"
        return f"""\
define i32 @{fname}(i32 %x, i32 %y) {{
entry:
  %cmp1 = icmp sgt i32 %x, %y
  br i1 %cmp1, label %then1, label %else1

then1:
  %a = add i32 %x, %y
  %cmp2 = icmp eq i32 %a, 0
  br i1 %cmp2, label %inner_then, label %merge

else1:
  %b = sub i32 %y, %x
  br label %merge

inner_then:
  %c = mul i32 %x, 2
  br label %merge

merge:
  %res = phi i32 [%a, %then1], [%b, %else1], [%c, %inner_then]
  ret i32 %res
}}
"""

    def _mock_loop(self) -> str:
        fname = f"loop_{random.randint(0, 999)}"
        return f"""\
define i32 @{fname}(i32 %n) {{
entry:
  %cmp_entry = icmp sgt i32 %n, 0
  br i1 %cmp_entry, label %loop, label %exit_zero

loop:
  %i = phi i32 [0, %entry], [%next_i, %loop]
  %acc = phi i32 [1, %entry], [%next_acc, %loop]
  %next_acc = mul i32 %acc, %i
  %next_acc2 = add i32 %next_acc, 1
  %next_i = add nsw i32 %i, 1
  %cmp = icmp slt i32 %next_i, %n
  br i1 %cmp, label %loop, label %exit

exit_zero:
  br label %exit

exit:
  %result = phi i32 [%next_acc2, %loop], [0, %exit_zero]
  ret i32 %result
}}
"""

    def _mock_memory(self) -> str:
        fname = f"mem_{random.randint(0, 999)}"
        return f"""\
define i32 @{fname}(ptr %arr, i32 %idx, i32 %val) {{
entry:
  %ptr = getelementptr i32, ptr %arr, i32 %idx
  %old = load i32, ptr %ptr, align 4
  %sum = add i32 %old, %val
  %cmp = icmp sgt i32 %sum, 100
  br i1 %cmp, label %cap, label %store

cap:
  br label %store

store:
  %to_store = phi i32 [100, %cap], [%sum, %entry]
  store i32 %to_store, ptr %ptr, align 4
  ret i32 %to_store
}}
"""

    def _mock_float(self) -> str:
        fname = f"float_{random.randint(0, 999)}"
        return f"""\
define double @{fname}(double %x, double %y) {{
entry:
  %sum = fadd double %x, %y
  %prod = fmul fast double %sum, %x
  %cmp = fcmp ogt double %prod, 0.0
  br i1 %cmp, label %pos, label %neg

pos:
  %half = fmul double %prod, 0.5
  br label %done

neg:
  %abs_val = fsub double 0.0, %prod
  br label %done

done:
  %result = phi double [%half, %pos], [%abs_val, %neg]
  ret double %result
}}
"""

    def _mock_switch(self) -> str:
        fname = f"switch_{random.randint(0, 999)}"
        return f"""\
define i32 @{fname}(i32 %op, i32 %a, i32 %b) {{
entry:
  switch i32 %op, label %default [
    i32 0, label %add_case
    i32 1, label %sub_case
    i32 2, label %mul_case
    i32 3, label %div_case
  ]

add_case:
  %r0 = add i32 %a, %b
  br label %done

sub_case:
  %r1 = sub i32 %a, %b
  br label %done

mul_case:
  %r2 = mul i32 %a, %b
  br label %done

div_case:
  %cmp = icmp eq i32 %b, 0
  br i1 %cmp, label %default, label %safe_div

safe_div:
  %r3 = sdiv i32 %a, %b
  br label %done

default:
  br label %done

done:
  %result = phi i32 [%r0, %add_case], [%r1, %sub_case], [%r2, %mul_case], [%r3, %safe_div], [0, %default]
  ret i32 %result
}}
"""

    def generate_from_scratch(self, prompt_key: str = None) -> GenerationResult:
        """Generate IR from scratch using a generation prompt."""
        if prompt_key is None:
            prompt_key = random.choice(list(GENERATION_PROMPTS.keys()))

        prompt = GENERATION_PROMPTS[prompt_key]

        start = time.time()
        response = self._call_llm(prompt)
        gen_time = time.time() - start

        ir_text = extract_ir_from_response(response)
        validation = validate_ir(ir_text)

        result = GenerationResult(
            source="llm",
            ir_text=ir_text,
            validation=validation,
            generation_time_s=gen_time,
            prompt_used=prompt_key,
            mutation_type="from_scratch",
            is_interesting=validation.semantic_check_passed,
        )

        # Track hash for dedup
        h = compute_ir_hash(ir_text)
        if h in self.generated_hashes:
            result.is_interesting = False  # Duplicate
        self.generated_hashes.add(h)

        return result

    def mutate_seed(self, seed_ir: str, mutation_goal: str = None) -> GenerationResult:
        """Mutate a seed IR using the LLM."""
        if mutation_goal is None:
            mutation_goal = random.choice(list(MUTATION_GOALS.values()))

        prompt = f"""\
The following is a valid LLVM IR function:

{seed_ir}

Mutate this function to {mutation_goal}.

IMPORTANT constraints to maintain:
1. SSA form: each %register defined exactly once
2. Every block ends with a terminator (ret/br/switch)
3. Types must match (no mixing i32 and i64 without casts)
4. PHI node predecessors must match actual CFG predecessors
5. All used values must be defined before use (domination)

Output ONLY the mutated LLVM IR function. Start with 'define' and end with '}}'. No explanations."""

        start = time.time()
        response = self._call_llm(prompt, temperature=0.8)
        gen_time = time.time() - start

        ir_text = extract_ir_from_response(response)
        validation = validate_ir(ir_text)

        return GenerationResult(
            source="llm",
            ir_text=ir_text,
            validation=validation,
            generation_time_s=gen_time,
            prompt_used=f"mutation: {mutation_goal[:50]}",
            seed_ir=seed_ir,
            mutation_type="mutation",
            is_interesting=validation.semantic_check_passed,
        )

    def generate_with_refinement(self, prompt_key: str = None, max_attempts: int = 3) -> GenerationResult:
        """Generate IR with iterative refinement based on validation feedback."""
        if prompt_key is None:
            prompt_key = random.choice(list(GENERATION_PROMPTS.keys()))

        prompt = GENERATION_PROMPTS[prompt_key]
        best_result = None

        for attempt in range(max_attempts):
            if attempt == 0:
                current_prompt = prompt
            else:
                # Add validation feedback
                error_summary = "; ".join(best_result.validation.errors[:3])
                current_prompt = f"""\
{prompt}

Previous attempt had these errors: {error_summary}

Fix these issues and generate valid LLVM IR. Remember:
- Each %register defined EXACTLY ONCE (SSA)
- Every block ends with ret/br/switch
- Types must match
- PHI predecessors must match CFG"""

            start = time.time()
            response = self._call_llm(current_prompt, temperature=max(0.3, 0.7 - attempt * 0.15))
            gen_time = time.time() - start

            ir_text = extract_ir_from_response(response)
            validation = validate_ir(ir_text)

            result = GenerationResult(
                source="llm",
                ir_text=ir_text,
                validation=validation,
                generation_time_s=gen_time,
                prompt_used=f"{prompt_key}_attempt{attempt}",
                mutation_type="refinement",
                is_interesting=validation.semantic_check_passed,
            )

            if best_result is None or validation.is_valid:
                best_result = result

            if validation.is_valid:
                break

        return best_result

    def generate_batch(self, n: int = 10, strategy: str = "mixed") -> list:
        """Generate a batch of IR test cases."""
        results = []

        for i in range(n):
            if strategy == "from_scratch":
                result = self.generate_from_scratch()
            elif strategy == "mutation":
                from ..seed_ir.seeds import SEED_IR_CASES
                seed = random.choice(list(SEED_IR_CASES.values()))
                result = self.mutate_seed(seed["ir"])
            elif strategy == "refinement":
                result = self.generate_with_refinement()
            elif strategy == "mixed":
                # Alternate strategies
                strategies = ["from_scratch", "mutation", "refinement"]
                chosen = strategies[i % len(strategies)]
                if chosen == "from_scratch":
                    result = self.generate_from_scratch()
                elif chosen == "mutation":
                    from ..seed_ir.seeds import SEED_IR_CASES
                    seed = random.choice(list(SEED_IR_CASES.values()))
                    result = self.mutate_seed(seed["ir"])
                else:
                    result = self.generate_with_refinement()
            else:
                result = self.generate_from_scratch()

            results.append(result)

        return results
