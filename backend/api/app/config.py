"""
config.py – Centralised settings for the LLM Mutator service.
Source: CONTEXT.json → setup.environment_variables
"""
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_ROOT: Path = Path(__file__).resolve().parents[1]
BACKEND_ROOT: Path = API_ROOT.parent
DATA_ROOT: Path = BACKEND_ROOT / "data"

# ── Ollama / LLM ────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3:1.5b")

# ── LLM Provider Switch (Ollama or Groq) ─────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
if LLM_PROVIDER not in {"ollama", "groq"}:
    raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}. Expected 'ollama' or 'groq'.")

# Groq (groq.com) OpenAI-compatible API settings
_groq_key = os.getenv("GROQ_API_KEY", "").strip()
_legacy_grok_key = os.getenv("GROK_API_KEY", "").strip()
if not _groq_key and _legacy_grok_key:
    warnings.warn(
        "GROK_API_KEY is deprecated; use GROQ_API_KEY for Groq (groq.com).",
        DeprecationWarning,
        stacklevel=2,
    )
    _groq_key = _legacy_grok_key

GROQ_API_KEY: str = _groq_key
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip().rstrip("/")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "1500"))
# For reasoning models (e.g., qwen/qwen-3-32b) set to "hidden" to avoid thinking tokens in output.
GROQ_REASONING_FORMAT: str = os.getenv("GROQ_REASONING_FORMAT", "").strip()

# Groq rate-limit handling (HTTP 429)
GROQ_MAX_RETRIES: int = int(os.getenv("GROQ_MAX_RETRIES", "6"))
GROQ_RETRY_BASE_SLEEP_S: float = float(os.getenv("GROQ_RETRY_BASE_SLEEP_S", "1.0"))
GROQ_RETRY_MAX_SLEEP_S: float = float(os.getenv("GROQ_RETRY_MAX_SLEEP_S", "30.0"))

# ── Filesystem paths ────────────────────────────────────────────
SEED_DIR: Path = Path(os.getenv("SEED_DIR", str(DATA_ROOT / "seeds")))
MUTANT_DIR: Path = Path(os.getenv("MUTANT_DIR", str(DATA_ROOT / "mutants_llm")))
GRAMMAR_DIR: Path = Path(os.getenv("GRAMMAR_DIR", str(DATA_ROOT / "mutants_grammar")))
VALID_DIR: Path = Path(os.getenv("VALID_DIR", str(DATA_ROOT / "valid_mutants")))
INVALID_DIR: Path = Path(os.getenv("INVALID_DIR", str(DATA_ROOT / "invalid_mutants")))
LOGS_DIR: Path = Path(os.getenv("LOGS_DIR", str(DATA_ROOT / "logs")))
RANDOM_DIR: Path = Path(os.getenv("RANDOM_DIR", str(DATA_ROOT / "mutants_random")))

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
