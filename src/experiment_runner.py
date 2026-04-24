"""
Main experiment runner for the LLVM IR generation study.

Orchestrates:
1. LLM-based IR generation (from scratch, mutation, refinement)
2. Grammar-based mutation baseline
3. Random mutation baseline
4. Validation and differential testing
5. Failure analysis and comparison
"""

import json
import time
import sys
import os
import random

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ir_generator import LLMIRGenerator, GENERATION_PROMPTS, MUTATION_GOALS
from src.grammar_mutator import GrammarMutator, RandomMutator
from src.ir_validator import validate_ir
from src.differential_tester import differential_test
from src.failure_analyzer import FailureAnalyzer
from src.utils import GenerationResult, format_ir_stats, count_ir_features
from seed_ir.seeds import SEED_IR_CASES


def run_llm_experiment(generator, n_per_strategy=10):
    """Run LLM-based generation experiments."""
    print("\n" + "="*60)
    print("PHASE 1: LLM-Based IR Generation")
    print("="*60)

    results = []

    # Strategy 1: From-scratch generation
    print(f"\n--- From-Scratch Generation ({n_per_strategy} samples) ---")
    prompt_keys = list(GENERATION_PROMPTS.keys())
    for i in range(n_per_strategy):
        key = prompt_keys[i % len(prompt_keys)]
        result = generator.generate_from_scratch(prompt_key=key)
        status = "VALID" if result.validation.is_valid else "INVALID"
        print(f"  [{i+1}/{n_per_strategy}] {key}: {status} "
              f"({result.generation_time_s:.2f}s)")
        if not result.validation.is_valid and result.validation.errors:
            print(f"    Errors: {result.validation.errors[0][:80]}")
        results.append(result)

    # Strategy 2: Seed mutation
    print(f"\n--- Seed Mutation ({n_per_strategy} samples) ---")
    seeds = list(SEED_IR_CASES.values())
    goals = list(MUTATION_GOALS.values())
    for i in range(n_per_strategy):
        seed = seeds[i % len(seeds)]
        goal = goals[i % len(goals)]
        result = generator.mutate_seed(seed["ir"], mutation_goal=goal)
        status = "VALID" if result.validation.is_valid else "INVALID"
        print(f"  [{i+1}/{n_per_strategy}] mutate({seed['description'][:30]}): {status} "
              f"({result.generation_time_s:.2f}s)")
        results.append(result)

    # Strategy 3: Generation with refinement
    print(f"\n--- Refinement-Based Generation ({n_per_strategy} samples) ---")
    for i in range(n_per_strategy):
        key = prompt_keys[i % len(prompt_keys)]
        result = generator.generate_with_refinement(prompt_key=key, max_attempts=3)
        status = "VALID" if result.validation.is_valid else "INVALID"
        print(f"  [{i+1}/{n_per_strategy}] {key}: {status} "
              f"({result.generation_time_s:.2f}s)")
        results.append(result)

    return results


def run_grammar_experiment(n_per_seed=5):
    """Run grammar-based mutation baseline."""
    print("\n" + "="*60)
    print("PHASE 2: Grammar-Based Mutation Baseline")
    print("="*60)

    mutator = GrammarMutator(seed=42)
    seed_irs = [case["ir"] for case in SEED_IR_CASES.values()]

    results = []
    total = len(seed_irs) * n_per_seed
    count = 0

    for seed_name, case in SEED_IR_CASES.items():
        for j in range(n_per_seed):
            count += 1
            result = mutator.mutate(case["ir"])
            status = "VALID" if result.validation.is_valid else "INVALID"
            print(f"  [{count}/{total}] grammar_mutate({seed_name}): {status} "
                  f"[{result.mutation_type}]")
            results.append(result)

    return results


def run_random_experiment(n_per_seed=5):
    """Run random mutation baseline."""
    print("\n" + "="*60)
    print("PHASE 3: Random Mutation Baseline")
    print("="*60)

    mutator = RandomMutator(seed=42)
    results = []
    total = len(SEED_IR_CASES) * n_per_seed
    count = 0

    for seed_name, case in SEED_IR_CASES.items():
        for j in range(n_per_seed):
            count += 1
            result = mutator.mutate(case["ir"])
            status = "VALID" if result.validation.is_valid else "INVALID"
            print(f"  [{count}/{total}] random_mutate({seed_name}): {status} "
                  f"[{result.mutation_type}]")
            results.append(result)

    return results


def run_differential_testing(valid_results):
    """Run differential testing on valid IR."""
    print("\n" + "="*60)
    print("PHASE 4: Differential Testing")
    print("="*60)

    diff_results = []
    for i, result in enumerate(valid_results):
        print(f"  [{i+1}/{len(valid_results)}] Testing {result.source}/{result.mutation_type}...")
        diff = differential_test(result.ir_text)
        result.opt_differential = diff

        if diff["is_interesting"]:
            print(f"    → INTERESTING: Found optimization discrepancy!")
        if diff["discrepancies"]:
            for d in diff["discrepancies"]:
                print(f"    → Discrepancy: {d['detail']}")

        diff_results.append(diff)

    return diff_results


def validate_seeds():
    """Validate all seed IR cases to ensure they're valid baselines."""
    print("\n" + "="*60)
    print("PHASE 0: Seed IR Validation")
    print("="*60)

    all_valid = True
    for name, case in SEED_IR_CASES.items():
        validation = validate_ir(case["ir"])
        status = "VALID" if validation.is_valid else "INVALID"
        print(f"  {name}: {status}")
        if not validation.is_valid:
            print(f"    Errors: {validation.errors}")
            all_valid = False
        elif validation.warnings:
            print(f"    Warnings: {validation.warnings}")

    return all_valid


def main():
    """Run the complete experiment suite."""
    start_time = time.time()
    print("="*60)
    print("LLVM IR Generation Study: LLM vs Traditional Approaches")
    print("="*60)

    # Phase 0: Validate seeds
    seeds_valid = validate_seeds()
    if not seeds_valid:
        print("\nWARNING: Some seed IR cases are invalid!")

    # Phase 1: LLM generation
    # Uses mock mode if HF_TOKEN not available
    llm_gen = LLMIRGenerator(use_api=bool(os.environ.get("HF_TOKEN")))
    n_per_strategy = 15  # 15 per strategy × 3 strategies = 45 LLM samples

    llm_results = run_llm_experiment(llm_gen, n_per_strategy=n_per_strategy)

    # Phase 2: Grammar-based baseline
    grammar_results = run_grammar_experiment(n_per_seed=5)  # 10 seeds × 5 = 50

    # Phase 3: Random baseline
    random_results = run_random_experiment(n_per_seed=5)  # 10 seeds × 5 = 50

    # Phase 4: Differential testing on all valid IR
    all_results = llm_results + grammar_results + random_results
    valid_results = [r for r in all_results if r.validation and r.validation.is_valid]

    print(f"\n{len(valid_results)} valid IR samples for differential testing")
    diff_results = run_differential_testing(valid_results)

    # Phase 5: Analysis
    print("\n" + "="*60)
    print("PHASE 5: Failure Analysis")
    print("="*60)

    analyzer = FailureAnalyzer()
    analyzer.add_results(all_results)

    report = analyzer.generate_report()
    print(report)

    # Save results
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(results_dir, exist_ok=True)

    # Save analysis report
    with open(os.path.join(results_dir, "analysis_output.md"), 'w') as f:
        f.write(report)

    # Save raw results
    raw_results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_samples": len(all_results),
            "llm_samples": len(llm_results),
            "grammar_samples": len(grammar_results),
            "random_samples": len(random_results),
            "valid_total": len(valid_results),
            "runtime_s": time.time() - start_time,
        },
        "validity_by_source": analyzer.get_validity_by_source(),
        "error_distribution": {k: {kk: vv for kk, vv in v.items() if kk != "example"}
                               for k, v in analyzer.get_error_distribution().items()},
        "mutation_effectiveness": analyzer.get_mutation_effectiveness(),
        "semantic_interest": analyzer.get_semantic_interest_analysis(),
        "summary_stats": {
            "llm_stats": format_ir_stats(llm_results),
            "grammar_stats": format_ir_stats(grammar_results),
            "random_stats": format_ir_stats(random_results),
        },
    }

    with open(os.path.join(results_dir, "experiment_results.json"), 'w') as f:
        json.dump(raw_results, f, indent=2, default=str)

    # Print summary comparison table
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    print(f"\n{'Approach':<25} {'Total':<8} {'Valid':<8} {'Valid%':<10} {'Interesting':<12} {'Int%':<10}")
    print("-" * 73)

    for source, stats in analyzer.get_validity_by_source().items():
        print(f"{source:<25} {stats['total']:<8} {stats['valid']:<8} "
              f"{stats['valid_pct']:<10.1f} {stats['interesting']:<12} "
              f"{stats['interesting_pct']:<10.1f}")

    total_time = time.time() - start_time
    print(f"\nTotal runtime: {total_time:.1f}s")
    print(f"Results saved to: {results_dir}/")


if __name__ == "__main__":
    main()
