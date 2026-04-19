
import sys
import os
import json
import shutil
import pathlib
import traceback

# Add the app directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Environment Variables
os.environ['SEED_DIR']     = os.path.abspath('seeds_test')
os.environ['MUTANT_DIR']   = os.path.abspath('mutants_llm_test')
os.environ['GRAMMAR_DIR']  = os.path.abspath('mutants_grammar_test')
os.environ['LOGS_DIR']     = os.path.abspath('logs_test')

# Ensure directories exist
for d in ['SEED_DIR', 'MUTANT_DIR', 'GRAMMAR_DIR', 'LOGS_DIR']:
    pathlib.Path(os.environ[d]).mkdir(parents=True, exist_ok=True)

PASS = []
FAIL = []

def ok(name):
    PASS.append(name)
    print(f'PASS  {name}')

def err(name, msg):
    FAIL.append(name)
    print(f'FAIL  {name}: {msg}')

# ── 1. ir_helpers unit tests ──────────────────────────────────────────────────
from app.utils.ir_helpers import (
    strip_thinking_tags, extract_ir, is_plausible_ir, add_module_header
)

try:
    result = strip_thinking_tags('<think>hidden</think>\ndefine i64 @f() { ret i64 0 }')
    assert 'hidden' not in result and 'define' in result
    ok('ir_helpers: strip_thinking_tags')

    SAMPLE = "```llvm\ndefine i64 @f(i64 %x) { ret i64 %x }\n```"
    ir = extract_ir(SAMPLE)
    assert ir is not None and 'define' in ir
    ok('ir_helpers: extract_ir')
except Exception as e:
    err('ir_helpers', traceback.format_exc())

# ── 2. GrammarMutator ──────────────────────────────────────────────────────────
from app.generate_mutants import GrammarMutator

try:
    gm = GrammarMutator()
    seed_content = """
define i64 @test(i64 %a, i64 %b) {
entry:
  %res = add i64 %a, %b
  %c = icmp eq i64 %res, 0
  ret i64 42
}
"""
    # strategy_id = index % 3
    
    # index 0 -> arithmetic_substitution (0 % 3 = 0)
    mutated0, strat0 = gm._mutate_one(seed_content, 0)
    assert strat0 == 'arithmetic_substitution'
    assert 'sub' in mutated0 or 'mul' in mutated0 or mutated0 != seed_content
    ok(f'GrammarMutator: {strat0}')

    # index 10 -> icmp_predicate_flip (10 % 3 = 1, 10 % 10 = 0 -> eq to ne)
    mutated1, strat1 = gm._mutate_one(seed_content, 10)
    assert strat1 == 'icmp_predicate_flip'
    assert 'icmp ne' in mutated1
    ok(f'GrammarMutator: {strat1}')

    # index 2 -> constant_perturbation (2 % 3 = 2)
    mutated2, strat2 = gm._mutate_one(seed_content, 2)
    assert strat2 == 'constant_perturbation'
    assert mutated2 != seed_content
    # Depending on match order, either 0 or 42 is changed.
    ok(f'GrammarMutator: {strat2}')

except Exception as e:
    err('GrammarMutator', traceback.format_exc())

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print(f'{"="*55}')
print(f'PASSED: {len(PASS)}   FAILED: {len(FAIL)}')
if FAIL:
    sys.exit(1)
print(f'{"="*55}')
