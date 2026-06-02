"""
app/utils/fs_helpers.py
Filesystem utility functions shared across services.
Source: CONTEXT.json → database.tables[raw_mutants] (id field format)
        CONTEXT.json → setup.environment_variables
"""
import json
import datetime
import re
from pathlib import Path


def normalize_run_tag(run_tag: str) -> str:
    tag = re.sub(r"[^A-Za-z0-9-]+", "-", run_tag.strip().lower())
    tag = re.sub(r"-+", "-", tag).strip("-")
    return tag


def build_mutant_id(seed_name: str, mutator_type: str, index: int, run_tag: str | None = None) -> str:
    """
    Build a mutant ID following the format defined in CONTEXT.json:
        database.tables[raw_mutants].fields[id]: "seed_name_mut_idx"
    Example: "add_llvm_mut_0", "loop_grammar_mut_3"
    If run_tag is provided, it is inserted before the "_mut_" suffix.
    """
    stem = Path(seed_name).stem
    if run_tag:
        safe_tag = normalize_run_tag(run_tag)
        if safe_tag:
            return f"{stem}_{mutator_type}_{safe_tag}_mut_{index}"
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
