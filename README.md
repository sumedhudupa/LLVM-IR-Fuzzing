# Assignment 18: Can LLMs Generate Valid LLVM IR Test Cases for Differential Compiler Testing?

## Overview
This project explores whether Large Language Models can generate or mutate semantically valid LLVM IR test cases for compiler differential testing. We build a complete workflow that generates IR via LLM prompting, validates it through multiple verification stages, compares it against traditional fuzzing baselines, and analyzes where LLM-based generation helps, fails, or adds no value.

## Project Structure
```
├── README.md                          # This file
├── report.md                          # Full research report (main deliverable)
├── constraints_catalog.md             # LLVM IR validity constraints catalog
├── src/
│   ├── ir_generator.py                # LLM-based LLVM IR generation/mutation
│   ├── ir_validator.py                # Multi-stage IR validation pipeline
│   ├── grammar_mutator.py             # Grammar-based random mutation baseline
│   ├── differential_tester.py         # Differential testing across opt levels
│   ├── failure_analyzer.py            # Categorize and analyze failure cases
│   ├── experiment_runner.py           # Main experiment orchestration
│   └── utils.py                       # Shared utilities
├── seed_ir/
│   └── seeds.py                       # 10 seed LLVM IR test cases
└── results/
    ├── experiment_results.json        # Raw experiment data
    └── analysis_output.md             # Generated analysis report
```

## Key Results

| Approach | Total | Valid | Valid% | Interesting | Int% |
|---|---|---|---|---|---|
| **LLM-based** | 45 | 39 | **86.7%** | 45 | **100.0%** |
| Grammar-based | 50 | 45 | **90.0%** | 27 | 54.0% |
| Random mutation | 50 | 8 | **16.0%** | 7 | 14.0% |

## How to Run

```bash
pip install llvmlite
cd project
python -m src.experiment_runner
```

Set `HF_TOKEN` environment variable to use real LLM generation via HuggingFace Inference API. Without it, the system uses mock templates that demonstrate the workflow.

## Key Findings
See `report.md` for the complete analysis including:
- Survey of compiler fuzzing methods (Csmith, YARPGen, Fuzz4All, LLM-Compiler)
- Catalog of 30+ LLVM IR validity constraints
- Prototype workflow for LLM-guided IR mutation and filtering
- Failure case study (SSA violations, type errors, PHI issues)
- Comparison of LLM vs grammar-based vs random mutation
- Conclusions and recommendations
