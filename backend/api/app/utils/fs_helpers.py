"""
app/utils/fs_helpers.py
Filesystem utility functions shared across services.
Source: CONTEXT.json → database.tables[raw_mutants] (id field format)
        CONTEXT.json → setup.environment_variables
"""
import json
import datetime
from pathlib import Path


def build_mutant_id(seed_name: str, mutator_type: str, index: int) -> str:
    """
    Build a mutant ID following the format defined in CONTEXT.json:
        database.tables[raw_mutants].fields[id]: "seed_name_mut_idx"
    Example: "add_llvm_mut_0", "loop_grammar_mut_3"
    """
    stem = Path(seed_name).stem
    return f"{stem}_{mutator_type}_mut_{index}"


def append_json_log(log_path: Path, entry: dict) -> None:
    """
    Append a JSON object to a newline-delimited JSON log file.
    Creates the file (and parent dirs) if it does not exist.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry.setdefault("created_at", datetime.datetime.utcnow().isoformat() + "Z")
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def safe_read_text(path: Path) -> str:
    """Read a file as text, returning an empty string if it doesn't exist."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
