"""
config.py – Centralised settings for the LLM Mutator service.
Source: CONTEXT.json → setup.environment_variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Ollama / LLM ────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3:1.5b")

# ── Filesystem paths ────────────────────────────────────────────
SEED_DIR: Path = Path(os.getenv("SEED_DIR", "./seeds"))
MUTANT_DIR: Path = Path(os.getenv("MUTANT_DIR", "./mutants_llm"))
GRAMMAR_DIR: Path = Path(os.getenv("GRAMMAR_DIR", "./mutants_grammar"))
VALID_DIR: Path = Path(os.getenv("VALID_DIR", "./valid_mutants"))
INVALID_DIR: Path = Path(os.getenv("INVALID_DIR", "./invalid_mutants"))
LOGS_DIR: Path = Path(os.getenv("LOGS_DIR", "./logs"))
RANDOM_DIR: Path = Path(os.getenv("RANDOM_DIR", "./mutants_random"))

# Ensure runtime directories exist
for _d in (SEED_DIR, MUTANT_DIR, GRAMMAR_DIR, VALID_DIR, INVALID_DIR, LOGS_DIR, RANDOM_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Feature Flags ────────────────────────────────────────────────
ENABLE_DEDUPLICATION: bool = os.getenv("ENABLE_DEDUPLICATION", "true").lower() == "true"
ENABLE_RULE_VALIDATION: bool = os.getenv("ENABLE_RULE_VALIDATION", "true").lower() == "true"
ENABLE_REFINEMENT: bool = os.getenv("ENABLE_REFINEMENT", "false").lower() == "true"

# ── Refinement Loop Settings ─────────────────────────────────────
MAX_REFINEMENT_ATTEMPTS: int = int(os.getenv("MAX_REFINEMENT_ATTEMPTS", "3"))

# ── Subprocess Timeout Settings ──────────────────────────────────
VALIDATION_TIMEOUT: int = int(os.getenv("VALIDATION_TIMEOUT", "30"))
