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
    mutator_type: str
    mutation_strategy: str
    timestamp: str
    is_valid: bool = False
    error_type: Optional[str] = None
    content_hash: Optional[str] = None
    seed_ir_hash: Optional[str] = None
    status: str = "generated"  # "generated", "validated", "failed", "duplicate_skipped"
    path: str = ""
    trivial: bool = False    # True if valid but semantically equivalent to seed
    is_duplicate: bool = False
    generation_time_s: Optional[float] = None
    source: Optional[str] = None
    mutation_type: Optional[str] = None


@dataclass
class ManifestSummary:
    """Summary statistics across all mutants."""
    total_generated: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    trivial_count: int = 0
    skipped_duplicate_count: int = 0
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
        """Load validity logs (JSON array or newline-delimited JSON)."""
        validity_by_id = {}
        if not self.validity_logs.exists():
            return validity_by_id

        try:
            raw = self.validity_logs.read_text(encoding="utf-8").strip()
            if not raw:
                return validity_by_id
            if raw.startswith("["):
                entries = json.loads(raw)
            else:
                entries = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

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
            mutator_type = raw_entry.get("mutator_type", "llm")
            mutation_strategy = raw_entry.get("strategy", "unknown")
            is_valid = validity_entry.get("is_valid", False)
            trivial = validity_entry.get("trivial", False)
            is_duplicate = validity_entry.get("is_duplicate", False)
            content_hash = validity_entry.get("content_hash") or raw_entry.get("content_hash")
            error_type = validity_entry.get("error_type")
            created_at = validity_entry.get("timestamp") or validity_entry.get("created_at") or raw_entry.get("created_at", "")
            path = raw_entry.get("path", "")
            raw_status = raw_entry.get("status", "generated")

            # Compute seed_ir_hash
            seed_ir_hash = None
            if seed_name and seed_dir:
                seed_path = seed_dir / seed_name
                seed_ir_hash = self.compute_seed_ir_hash(seed_path)

            # Determine status
            if mutant_id in validity_logs:
                status = "validated"
            else:
                status = raw_status

            # Create manifest entry
            entry = ManifestEntry(
                mutant_id=mutant_id,
                seed_name=seed_name,
                mutator_type=mutator_type,
                mutation_strategy=mutation_strategy,
                timestamp=created_at,
                is_valid=is_valid,
                error_type=error_type,
                content_hash=content_hash,
                seed_ir_hash=seed_ir_hash,
                status=status,
                path=path,
                trivial=trivial,
                is_duplicate=is_duplicate,
                source=mutator_type,
                mutation_type=mutation_strategy,
            )
            manifest_entries.append(entry)

            # Update summary stats
            if status != "duplicate_skipped":
                summary.total_generated += 1
            else:
                summary.skipped_duplicate_count += 1

            if is_valid:
                summary.valid_count += 1
                if trivial:
                    summary.trivial_count += 1
            elif status != "duplicate_skipped":
                summary.invalid_count += 1

            if is_duplicate or status == "duplicate_skipped":
                summary.duplicate_count += 1

            # Per-mutator-type stats
            if mutator_type not in summary.by_mutator_type:
                summary.by_mutator_type[mutator_type] = {
                    "generated": 0,
                    "valid": 0,
                    "invalid": 0,
                    "duplicate": 0,
                    "trivial": 0,
                    "duplicate_skipped": 0,
                }
            if status != "duplicate_skipped":
                summary.by_mutator_type[mutator_type]["generated"] += 1
            else:
                summary.by_mutator_type[mutator_type]["duplicate_skipped"] += 1
            if is_valid:
                summary.by_mutator_type[mutator_type]["valid"] += 1
                if trivial:
                    summary.by_mutator_type[mutator_type]["trivial"] += 1
            elif status != "duplicate_skipped":
                summary.by_mutator_type[mutator_type]["invalid"] += 1
            if is_duplicate or status == "duplicate_skipped":
                summary.by_mutator_type[mutator_type]["duplicate"] += 1

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
