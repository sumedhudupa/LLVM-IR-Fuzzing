"""
Grammar-based and random mutation baseline for LLVM IR.

Implements traditional mutation strategies:
1. Random instruction replacement
2. Random operand swapping
3. Block duplication
4. Type widening/narrowing
5. Flag addition/removal (nsw, nuw, fast)
6. Dead code insertion
7. Random constant mutation
"""

import re
import random
import time
import copy
from typing import Optional

from .utils import GenerationResult
from .ir_validator import validate_ir, parse_blocks


# ============================================================
# Grammar-Aware Mutations
# ============================================================

INT_TYPES = ['i1', 'i8', 'i16', 'i32', 'i64']
FLOAT_TYPES = ['float', 'double']
INT_BINOPS = ['add', 'sub', 'mul', 'udiv', 'sdiv', 'urem', 'srem']
INT_BITOPS = ['and', 'or', 'xor', 'shl', 'lshr', 'ashr']
FLOAT_BINOPS = ['fadd', 'fsub', 'fmul', 'fdiv', 'frem']
ICMP_PREDS = ['eq', 'ne', 'sgt', 'sge', 'slt', 'sle', 'ugt', 'uge', 'ult', 'ule']
FCMP_PREDS = ['oeq', 'one', 'ogt', 'oge', 'olt', 'ole', 'ord', 'uno',
              'ueq', 'une', 'ugt', 'uge', 'ult', 'ule']
OVERFLOW_FLAGS = ['nsw', 'nuw']


class GrammarMutator:
    """Grammar-aware LLVM IR mutator for baseline comparison."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def mutate(self, ir_text: str, mutation_type: str = None) -> GenerationResult:
        """Apply a random grammar-aware mutation."""
        mutations = {
            "replace_binop": self._mutate_replace_binop,
            "swap_operands": self._mutate_swap_operands,
            "change_icmp_pred": self._mutate_icmp_pred,
            "toggle_overflow_flag": self._mutate_toggle_overflow_flag,
            "change_constant": self._mutate_change_constant,
            "insert_dead_code": self._mutate_insert_dead_code,
            "duplicate_instruction": self._mutate_duplicate_instruction,
            "remove_nsw_nuw": self._mutate_remove_flags,
            "add_nsw_nuw": self._mutate_add_flags,
            "swap_branch_targets": self._mutate_swap_branch_targets,
        }

        if mutation_type is None:
            mutation_type = self.rng.choice(list(mutations.keys()))

        mutator_fn = mutations.get(mutation_type, self._mutate_replace_binop)

        start = time.time()
        mutated = mutator_fn(ir_text)
        gen_time = time.time() - start

        validation = validate_ir(mutated)

        return GenerationResult(
            source="grammar",
            ir_text=mutated,
            validation=validation,
            generation_time_s=gen_time,
            seed_ir=ir_text,
            mutation_type=f"grammar_{mutation_type}",
            is_interesting=validation.semantic_check_passed if validation.is_valid else False,
        )

    def _mutate_replace_binop(self, ir_text: str) -> str:
        """Replace an integer binary operation with another."""
        lines = ir_text.split('\n')
        candidates = []
        for i, line in enumerate(lines):
            for op in INT_BINOPS:
                pattern = rf'=\s+{op}\s+'
                if re.search(pattern, line):
                    candidates.append((i, op))

        if not candidates:
            return ir_text

        idx, old_op = self.rng.choice(candidates)
        new_op = self.rng.choice([o for o in INT_BINOPS if o != old_op])
        lines[idx] = re.sub(rf'=\s+{old_op}\s+', f'= {new_op} ', lines[idx], count=1)
        return '\n'.join(lines)

    def _mutate_swap_operands(self, ir_text: str) -> str:
        """Swap the two operands of a binary operation."""
        lines = ir_text.split('\n')
        all_binops = INT_BINOPS + FLOAT_BINOPS + INT_BITOPS
        candidates = []

        for i, line in enumerate(lines):
            for op in all_binops:
                # Match: %result = op type %a, %b
                pattern = rf'=\s+(?:nsw\s+|nuw\s+|fast\s+)*{op}\s+(\S+)\s+(%\w+),\s*(%\w+)'
                m = re.search(pattern, line)
                if m:
                    candidates.append((i, m))

        if not candidates:
            return ir_text

        idx, match = self.rng.choice(candidates)
        type_str = match.group(1)
        op1 = match.group(2)
        op2 = match.group(3)
        # Swap operands
        lines[idx] = lines[idx][:match.start(2)] + op2 + ', ' + op1 + lines[idx][match.end(3):]
        return '\n'.join(lines)

    def _mutate_icmp_pred(self, ir_text: str) -> str:
        """Change an icmp predicate."""
        lines = ir_text.split('\n')
        candidates = []

        for i, line in enumerate(lines):
            m = re.search(r'icmp\s+(\w+)\s+', line)
            if m:
                candidates.append((i, m))

        if not candidates:
            return ir_text

        idx, match = self.rng.choice(candidates)
        old_pred = match.group(1)
        new_pred = self.rng.choice([p for p in ICMP_PREDS if p != old_pred])
        lines[idx] = lines[idx][:match.start(1)] + new_pred + lines[idx][match.end(1):]
        return '\n'.join(lines)

    def _mutate_toggle_overflow_flag(self, ir_text: str) -> str:
        """Add or remove nsw/nuw flags."""
        lines = ir_text.split('\n')
        candidates = []

        for i, line in enumerate(lines):
            for op in ['add', 'sub', 'mul', 'shl']:
                if f'= {op} ' in line or f'= {op} nsw' in line or f'= {op} nuw' in line:
                    candidates.append((i, op))

        if not candidates:
            return ir_text

        idx, op = self.rng.choice(candidates)
        line = lines[idx]

        if 'nsw' in line:
            line = line.replace(' nsw', '', 1)
        elif 'nuw' in line:
            line = line.replace(' nuw', '', 1)
        else:
            flag = self.rng.choice(['nsw', 'nuw'])
            line = line.replace(f'= {op} ', f'= {op} {flag} ', 1)

        lines[idx] = line
        return '\n'.join(lines)

    def _mutate_change_constant(self, ir_text: str) -> str:
        """Change an integer constant value."""
        lines = ir_text.split('\n')
        candidates = []

        for i, line in enumerate(lines):
            # Find integer constants (not in type positions)
            constants = re.finditer(r'(?<=,\s)(-?\d+)(?!\s*x\s)', line)
            for m in constants:
                candidates.append((i, m))

        if not candidates:
            return ir_text

        idx, match = self.rng.choice(candidates)
        old_val = int(match.group(1))
        # Mutate: add/subtract small values, or use edge cases
        mutations = [
            old_val + 1, old_val - 1, old_val * 2, 0, 1, -1,
            2147483647, -2147483648,  # INT_MAX, INT_MIN
            old_val ^ 0xFF,
        ]
        new_val = self.rng.choice(mutations)
        lines[idx] = lines[idx][:match.start(1)] + str(new_val) + lines[idx][match.end(1):]
        return '\n'.join(lines)

    def _mutate_insert_dead_code(self, ir_text: str) -> str:
        """Insert dead code (computation whose result is unused)."""
        lines = ir_text.split('\n')
        # Find lines that are inside a function and not terminators
        candidates = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and '=' in stripped and not stripped.startswith('define')
                and not stripped.startswith(';') and 'phi' not in stripped):
                candidates.append(i)

        if not candidates:
            return ir_text

        insert_after = self.rng.choice(candidates)
        dead_name = f"%dead_{self.rng.randint(0, 9999)}"
        dead_ops = [
            f"  {dead_name} = add i32 42, 0",
            f"  {dead_name} = mul i32 1, 1",
            f"  {dead_name} = xor i32 0, 0",
            f"  {dead_name} = sub i32 100, 100",
        ]
        dead_code = self.rng.choice(dead_ops)
        lines.insert(insert_after + 1, dead_code)
        return '\n'.join(lines)

    def _mutate_duplicate_instruction(self, ir_text: str) -> str:
        """Duplicate an instruction with a new register name."""
        lines = ir_text.split('\n')
        candidates = []

        for i, line in enumerate(lines):
            m = re.match(r'(\s*)(%\w+)\s*=\s*(.*)', line)
            if m and 'phi' not in line and 'ret' not in line:
                candidates.append((i, m))

        if not candidates:
            return ir_text

        idx, match = self.rng.choice(candidates)
        indent = match.group(1)
        old_reg = match.group(2)
        rhs = match.group(3)
        new_reg = f"{old_reg}_dup{self.rng.randint(0, 99)}"
        new_line = f"{indent}{new_reg} = {rhs}"
        lines.insert(idx + 1, new_line)
        return '\n'.join(lines)

    def _mutate_remove_flags(self, ir_text: str) -> str:
        """Remove all nsw/nuw flags."""
        result = ir_text.replace(' nsw ', ' ').replace(' nuw ', ' ')
        result = result.replace(' nsw\n', '\n').replace(' nuw\n', '\n')
        return result

    def _mutate_add_flags(self, ir_text: str) -> str:
        """Add nsw/nuw flags to operations that support them."""
        lines = ir_text.split('\n')
        for i, line in enumerate(lines):
            for op in ['add', 'sub', 'mul', 'shl']:
                pattern = f'= {op} i'
                if pattern in line and 'nsw' not in line and 'nuw' not in line:
                    flag = self.rng.choice(['nsw', 'nuw'])
                    lines[i] = line.replace(f'= {op} ', f'= {op} {flag} ', 1)
                    break
        return '\n'.join(lines)

    def _mutate_swap_branch_targets(self, ir_text: str) -> str:
        """Swap the true/false targets of a conditional branch."""
        lines = ir_text.split('\n')
        for i, line in enumerate(lines):
            m = re.match(r'(\s*br\s+i1\s+%\w+,\s+label\s+)(%\w+)(,\s+label\s+)(%\w+)', line)
            if m:
                lines[i] = m.group(1) + m.group(4) + m.group(3) + m.group(2)
                break
        return '\n'.join(lines)

    def generate_batch(self, seed_irs: list, n_per_seed: int = 5) -> list:
        """Generate mutated IR for each seed."""
        results = []
        for seed_ir in seed_irs:
            for _ in range(n_per_seed):
                result = self.mutate(seed_ir)
                results.append(result)
        return results


class RandomMutator:
    """Purely random (non-grammar-aware) mutator for comparison."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def mutate(self, ir_text: str, mutation_type: str = None) -> GenerationResult:
        """Apply a random character/line-level mutation."""
        mutations = {
            "random_char_flip": self._mutate_char_flip,
            "random_line_delete": self._mutate_line_delete,
            "random_line_duplicate": self._mutate_line_duplicate,
            "random_line_swap": self._mutate_line_swap,
            "random_word_replace": self._mutate_word_replace,
        }

        if mutation_type is None:
            mutation_type = self.rng.choice(list(mutations.keys()))

        mutator_fn = mutations.get(mutation_type, self._mutate_char_flip)

        start = time.time()
        mutated = mutator_fn(ir_text)
        gen_time = time.time() - start

        validation = validate_ir(mutated)

        return GenerationResult(
            source="random",
            ir_text=mutated,
            validation=validation,
            generation_time_s=gen_time,
            seed_ir=ir_text,
            mutation_type=f"random_{mutation_type}",
            is_interesting=validation.semantic_check_passed if validation.is_valid else False,
        )

    def _mutate_char_flip(self, ir_text: str) -> str:
        """Flip a random character."""
        if not ir_text:
            return ir_text
        chars = list(ir_text)
        idx = self.rng.randint(0, len(chars) - 1)
        chars[idx] = chr(self.rng.randint(32, 126))
        return ''.join(chars)

    def _mutate_line_delete(self, ir_text: str) -> str:
        """Delete a random line."""
        lines = ir_text.split('\n')
        if len(lines) <= 3:
            return ir_text
        idx = self.rng.randint(1, len(lines) - 2)  # Don't delete first/last
        del lines[idx]
        return '\n'.join(lines)

    def _mutate_line_duplicate(self, ir_text: str) -> str:
        """Duplicate a random line."""
        lines = ir_text.split('\n')
        idx = self.rng.randint(0, len(lines) - 1)
        lines.insert(idx + 1, lines[idx])
        return '\n'.join(lines)

    def _mutate_line_swap(self, ir_text: str) -> str:
        """Swap two random lines."""
        lines = ir_text.split('\n')
        if len(lines) < 4:
            return ir_text
        i, j = self.rng.sample(range(1, len(lines) - 1), 2)
        lines[i], lines[j] = lines[j], lines[i]
        return '\n'.join(lines)

    def _mutate_word_replace(self, ir_text: str) -> str:
        """Replace a random word with another."""
        words_pool = ['i32', 'i64', 'add', 'sub', 'mul', 'ret', 'br', 'label',
                      'define', 'void', 'i1', 'icmp', 'phi', '0', '1', '%x']
        lines = ir_text.split('\n')
        idx = self.rng.randint(1, max(1, len(lines) - 2))
        words = lines[idx].split()
        if words:
            w_idx = self.rng.randint(0, len(words) - 1)
            words[w_idx] = self.rng.choice(words_pool)
            lines[idx] = ' '.join(words)
        return '\n'.join(lines)

    def generate_batch(self, seed_irs: list, n_per_seed: int = 5) -> list:
        """Generate randomly mutated IR for each seed."""
        results = []
        for seed_ir in seed_irs:
            for _ in range(n_per_seed):
                result = self.mutate(seed_ir)
                results.append(result)
        return results
