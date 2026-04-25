# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the core pipeline: IR generation, validation, mutation baselines, differential testing, failure analysis, and experiment orchestration. Use `src/experiment_runner.py` as the main entry point. `seed_ir/` stores reusable LLVM IR seed cases in `seeds.py`. `scripts/` contains one-off utilities such as `generate_paper_figures.py`. Generated artifacts belong in `results/`, including `experiment_results.json`, `analysis_output.md`, and `results/figures/`. Top-level documentation lives in `README.md`, `report.md`, and `constraints_catalog.md`.

## Build, Test, and Development Commands
Create and activate a virtual environment before running anything:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install llvmlite matplotlib huggingface_hub
```

Run the full experiment workflow:

```bash
python -m src.experiment_runner
```

Generate figures from saved results:

```bash
python scripts/generate_paper_figures.py
python scripts/generate_paper_figures.py --input results/experiment_results.json --output results/figures
```

Set `HF_TOKEN` to enable live Hugging Face inference; otherwise the generator falls back to mock mode.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, module-level docstrings, type hints where useful, and small focused functions. Use `snake_case` for files, functions, variables, and CLI flags. Keep constants uppercase, for example `GENERATION_PROMPTS` and `MUTATION_GOALS`. New code should stay consistent with the current standard-library-first approach and avoid introducing heavy dependencies without a clear need.

## Testing Guidelines
There is no standalone `tests/` package yet. Validate changes by running `python -m src.experiment_runner` and confirming regenerated outputs in `results/` are sensible. For plotting or reporting changes, also run `python scripts/generate_paper_figures.py`. If you add formal tests, place them under `tests/` and name files `test_*.py`.

## Commit & Pull Request Guidelines
Recent history uses short imperative subjects such as `Add src/experiment_runner.py`. Keep commits focused and descriptive, preferably under 72 characters. Pull requests should include:
- a brief summary of the research or workflow impact
- the commands run for validation
- any changed output files under `results/`
- screenshots only when visual outputs in `results/figures/` materially change

## Security & Configuration Tips
Do not commit secrets. Store API credentials in environment variables such as `HF_TOKEN`. Treat generated result files as reproducible artifacts: regenerate them from code changes instead of hand-editing JSON, Markdown, or figures.
