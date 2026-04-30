"""
manifest_service.py – Comprehensive manifest tracking for generated mutants.
Aggregates data from raw_mutants.json and validity_logs.json into a structured manifest.json.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class ManifestEntry:
    """Per-mutant entry in the manifest."""
    mutant_id: str
    seed_name: str
    source: str              # "llm", "grammar", or "random"
    mutation_type: str       # strategy name
    seed_ir_hash: Optional[str] = None
    is_valid: bool = False
    trivial: bool = False    # True if valid but semantically equivalent to seed
    is_duplicate: bool = False
    content_hash: Optional[str] = None
    error_type: Optional[str] = None
    generation_time_s: Optional[float] = None
    status: str = "generated"  # "generated", "validated", "failed"
    timestamp: str = ""


@dataclass
class ManifestSummary:
    """Summary statistics across all mutants."""
    total_generated: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    trivial_count: int = 0
    by_mutator_type: dict = None  # {mutator_type: {valid, invalid, duplicate, trivial}}
    by_error_type: dict = None    # {error_type: count}

    def __post_init__(self):
        if self.by_mutator_type is None:
            self.by_mutator_type = {}
        if self.by_error_type is None:
            self.by_error_type = {}


class ManifestTracker:
    """Service for tracking and aggregating mutant metadata."""

    def __init__(self, logs_dir: Path, results_dir: Optional[Path] = None):
        self.logs_dir = logs_dir
        self.results_dir = results_dir or (logs_dir.parent / "results" / "ir")
        self.raw_mutants_log = logs_dir / "raw_mutants.json"
        self.validity_logs = logs_dir / "validity_logs.json"
        self.manifest_file = logs_dir / "manifest.json"

    def compute_seed_ir_hash(self, seed_path: Path) -> Optional[str]:
        """Compute MD5 hash of seed IR file."""
        if not seed_path.exists():
            return None
        content = seed_path.read_text(encoding="utf-8")
        return hashlib.md5(content.encode()).hexdigest()

    def load_raw_mutants(self) -> dict:
        """Load raw_mutants.json (newline-delimited JSON)."""
        mutants_by_id = {}
        if not self.raw_mutants_log.exists():
            return mutants_by_id

        with open(self.raw_mutants_log, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    mutants_by_id[entry.get("id", entry.get("mutant_id"))] = entry
                except json.JSONDecodeError:
                    pass
        return mutants_by_id

    def load_validity_logs(self) -> dict:
        """Load validity_logs.json (JSON array)."""
        validity_by_id = {}
        if not self.validity_logs.exists():
            return validity_by_id

        try:
            with open(self.validity_logs, "r") as f:
                entries = json.load(f)
                for entry in entries:
                    validity_by_id[entry.get("mutant_id")] = entry
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return validity_by_id

    def generate_manifest(self, seed_dir: Path) -> tuple[list[ManifestEntry], ManifestSummary]:
        """
        Aggregate raw_mutants.json and validity_logs.json into manifest entries.
        Returns (list of entries, summary stats).
        """
        raw_mutants = self.load_raw_mutants()
        validity_logs = self.load_validity_logs()

        manifest_entries = []
        summary = ManifestSummary()

        for mutant_id, raw_entry in raw_mutants.items():
            # Get validity info if available
            validity_entry = validity_logs.get(mutant_id, {})

            # Extract fields
            seed_name = raw_entry.get("seed_name", "")
            source = raw_entry.get("mutator_type", "llm")
            mutation_type = raw_entry.get("strategy", "unknown")
            is_valid = validity_entry.get("is_valid", False)
            trivial = validity_entry.get("trivial", False)
            is_duplicate = validity_entry.get("is_duplicate", False)
            content_hash = validity_entry.get("content_hash")
            error_type = validity_entry.get("error_type")
            created_at = raw_entry.get("created_at", "")

            # Compute seed_ir_hash
            seed_ir_hash = None
            if seed_name and seed_dir:
                seed_path = seed_dir / seed_name
                seed_ir_hash = self.compute_seed_ir_hash(seed_path)

            # Determine status
            if mutant_id in validity_logs:
                status = "validated"
            elif raw_entry.get("status") == "failed":
                status = "failed"
            else:
                status = "generated"

            # Create manifest entry
            entry = ManifestEntry(
                mutant_id=mutant_id,
                seed_name=seed_name,
                source=source,
                mutation_type=mutation_type,
                seed_ir_hash=seed_ir_hash,
                is_valid=is_valid,
                trivial=trivial,
                is_duplicate=is_duplicate,
                content_hash=content_hash,
                error_type=error_type,
                status=status,
                timestamp=created_at
            )
            manifest_entries.append(entry)

            # Update summary stats
            summary.total_generated += 1
            if is_valid:
                summary.valid_count += 1
                if trivial:
                    summary.trivial_count += 1
            else:
                summary.invalid_count += 1

            if is_duplicate:
                summary.duplicate_count += 1

            # Per-mutator-type stats
            if source not in summary.by_mutator_type:
                summary.by_mutator_type[source] = {
                    "generated": 0,
                    "valid": 0,
                    "invalid": 0,
                    "duplicate": 0,
                    "trivial": 0
                }
            summary.by_mutator_type[source]["generated"] += 1
            if is_valid:
                summary.by_mutator_type[source]["valid"] += 1
                if trivial:
                    summary.by_mutator_type[source]["trivial"] += 1
            else:
                summary.by_mutator_type[source]["invalid"] += 1
            if is_duplicate:
                summary.by_mutator_type[source]["duplicate"] += 1

            # Error type breakdown
            if error_type:
                summary.by_error_type[error_type] = summary.by_error_type.get(error_type, 0) + 1

        return manifest_entries, summary

    def save_manifest(self, seed_dir: Path) -> Path:
        """Generate and save manifest.json."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        entries, summary = self.generate_manifest(seed_dir)

        # Build output structure
        output = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mutants": [asdict(e) for e in entries],
            "summary": asdict(summary)
        }

        # Write manifest.json
        with open(self.manifest_file, "w") as f:
            json.dump(output, f, indent=2)

        return self.manifest_file

    def filter_entries(self,
                       source: Optional[str] = None,
                       mutation_type: Optional[str] = None,
                       is_valid: Optional[bool] = None,
                       trivial: Optional[bool] = None) -> list[ManifestEntry]:
        """
        Filter manifest entries by criteria.
        Returns filtered list of entries.
        """
        if not self.manifest_file.exists():
            return []

        with open(self.manifest_file, "r") as f:
            data = json.load(f)
            entries = [
                ManifestEntry(**e)
                for e in data.get("mutants", [])
            ]

        # Apply filters
        if source is not None:
            entries = [e for e in entries if e.source == source]
        if mutation_type is not None:
            entries = [e for e in entries if e.mutation_type == mutation_type]
        if is_valid is not None:
            entries = [e for e in entries if e.is_valid == is_valid]
        if trivial is not None:
            entries = [e for e in entries if e.trivial == trivial]

        return entries

    def get_summary(self) -> Optional[ManifestSummary]:
        """Retrieve summary statistics from manifest.json."""
        if not self.manifest_file.exists():
            return None

        with open(self.manifest_file, "r") as f:
            data = json.load(f)
            summary_dict = data.get("summary", {})
            return ManifestSummary(**summary_dict)
