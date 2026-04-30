"""
tests/test_phase3.py – Unit tests for Phase 3 components.
Tests ManifestTracker, IR deduplication, semantic equivalence, and schema.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# These imports would be from the llm-mutator package
# For standalone test, we can mock them
from app.services.manifest_service import ManifestTracker, ManifestEntry, ManifestSummary


class TestManifestTracker:
    """Test suite for ManifestTracker service."""

    @pytest.fixture
    def temp_logs_dir(self):
        """Create temporary logs directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            # Create raw_mutants.json (newline-delimited)
            raw_mutants = [
                {
                    "id": "seed1_llm_mut_0",
                    "seed_name": "seed1.ll",
                    "mutator_type": "llm",
                    "strategy": "arithmetic_substitution",
                    "status": "generated",
                    "seed_size_bytes": 256,
                    "created_at": "2026-04-30T10:00:00Z"
                },
                {
                    "id": "seed1_llm_mut_1",
                    "seed_name": "seed1.ll",
                    "mutator_type": "llm",
                    "strategy": "constant_mutation",
                    "status": "generated",
                    "seed_size_bytes": 256,
                    "created_at": "2026-04-30T10:01:00Z"
                },
                {
                    "id": "seed1_grammar_mut_0",
                    "seed_name": "seed1.ll",
                    "mutator_type": "grammar",
                    "strategy": "arithmetic_substitution",
                    "status": "generated",
                    "seed_size_bytes": 256,
                    "created_at": "2026-04-30T10:02:00Z"
                },
            ]

            with open(logs_dir / "raw_mutants.json", "w") as f:
                for entry in raw_mutants:
                    f.write(json.dumps(entry) + "\n")

            # Create validity_logs.json (JSON array)
            validity_logs = [
                {
                    "mutant_id": "seed1_llm_mut_0",
                    "is_valid": True,
                    "error_type": None,
                    "verifier_output": "Verification successful.",
                    "trivial": False,
                    "is_duplicate": False,
                    "content_hash": "abc123",
                    "rule_check_passed": True,
                    "timeout_occurred": False,
                    "created_at": "2026-04-30T10:05:00Z"
                },
                {
                    "mutant_id": "seed1_llm_mut_1",
                    "is_valid": False,
                    "error_type": "syntax",
                    "verifier_output": "error: expected instruction opcode",
                    "trivial": False,
                    "is_duplicate": False,
                    "content_hash": None,
                    "rule_check_passed": False,
                    "timeout_occurred": False,
                    "created_at": "2026-04-30T10:06:00Z"
                },
                {
                    "mutant_id": "seed1_grammar_mut_0",
                    "is_valid": True,
                    "error_type": None,
                    "verifier_output": "Verification successful.",
                    "trivial": True,
                    "is_duplicate": False,
                    "content_hash": "def456",
                    "rule_check_passed": True,
                    "timeout_occurred": False,
                    "created_at": "2026-04-30T10:07:00Z"
                },
            ]

            with open(logs_dir / "validity_logs.json", "w") as f:
                json.dump(validity_logs, f)

            yield logs_dir

    @pytest.fixture
    def temp_seed_dir(self):
        """Create temporary seed directory with test seeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            seed_dir = Path(tmpdir)
            seed_file = seed_dir / "seed1.ll"
            seed_file.write_text("define i32 @main() { ret i32 0 }")
            yield seed_dir

    def test_load_raw_mutants_newline_delimited(self, temp_logs_dir):
        """Test loading newline-delimited raw_mutants.json."""
        tracker = ManifestTracker(temp_logs_dir)
        raw = tracker.load_raw_mutants()

        assert len(raw) == 3
        assert "seed1_llm_mut_0" in raw
        assert raw["seed1_llm_mut_0"]["mutator_type"] == "llm"
        assert raw["seed1_llm_mut_0"]["seed_size_bytes"] == 256

    def test_load_validity_logs_json_array(self, temp_logs_dir):
        """Test loading JSON array validity_logs.json."""
        tracker = ManifestTracker(temp_logs_dir)
        validity = tracker.load_validity_logs()

        assert len(validity) == 3
        assert "seed1_llm_mut_0" in validity
        assert validity["seed1_llm_mut_0"]["is_valid"] is True
        assert validity["seed1_llm_mut_0"]["trivial"] is False

    def test_generate_manifest_aggregates_data(self, temp_logs_dir, temp_seed_dir):
        """Test manifest generation aggregates raw and validity logs."""
        tracker = ManifestTracker(temp_logs_dir)
        entries, summary = tracker.generate_manifest(temp_seed_dir)

        # Check entries
        assert len(entries) == 3
        assert entries[0].mutant_id == "seed1_llm_mut_0"
        assert entries[0].source == "llm"
        assert entries[0].is_valid is True
        assert entries[0].trivial is False

        # Check trivial detection
        trivial_entry = [e for e in entries if e.trivial]
        assert len(trivial_entry) == 1
        assert trivial_entry[0].mutant_id == "seed1_grammar_mut_0"

    def test_summary_statistics(self, temp_logs_dir, temp_seed_dir):
        """Test summary statistics are computed correctly."""
        tracker = ManifestTracker(temp_logs_dir)
        entries, summary = tracker.generate_manifest(temp_seed_dir)

        assert summary.total_generated == 3
        assert summary.valid_count == 2
        assert summary.invalid_count == 1
        assert summary.duplicate_count == 0
        assert summary.trivial_count == 1

    def test_per_mutator_type_stats(self, temp_logs_dir, temp_seed_dir):
        """Test per-mutator-type statistics."""
        tracker = ManifestTracker(temp_logs_dir)
        entries, summary = tracker.generate_manifest(temp_seed_dir)

        assert "llm" in summary.by_mutator_type
        assert "grammar" in summary.by_mutator_type

        llm_stats = summary.by_mutator_type["llm"]
        assert llm_stats["generated"] == 2
        assert llm_stats["valid"] == 1
        assert llm_stats["invalid"] == 1

        grammar_stats = summary.by_mutator_type["grammar"]
        assert grammar_stats["generated"] == 1
        assert grammar_stats["valid"] == 1
        assert grammar_stats["trivial"] == 1

    def test_error_type_breakdown(self, temp_logs_dir, temp_seed_dir):
        """Test error type breakdown in summary."""
        tracker = ManifestTracker(temp_logs_dir)
        entries, summary = tracker.generate_manifest(temp_seed_dir)

        assert "syntax" in summary.by_error_type
        assert summary.by_error_type["syntax"] == 1

    def test_save_manifest_creates_file(self, temp_logs_dir, temp_seed_dir):
        """Test save_manifest creates manifest.json."""
        tracker = ManifestTracker(temp_logs_dir)
        manifest_path = tracker.save_manifest(temp_seed_dir)

        assert manifest_path.exists()
        assert manifest_path.name == "manifest.json"

        # Verify JSON structure
        data = json.loads(manifest_path.read_text())
        assert "generated_at" in data
        assert "mutants" in data
        assert "summary" in data
        assert len(data["mutants"]) == 3
        assert data["summary"]["total_generated"] == 3

    def test_filter_entries_by_source(self, temp_logs_dir, temp_seed_dir):
        """Test filtering entries by source."""
        tracker = ManifestTracker(temp_logs_dir)
        entries, _ = tracker.generate_manifest(temp_seed_dir)

        # Save and reload manifest
        tracker.save_manifest(temp_seed_dir)

        # Filter by source
        llm_entries = tracker.filter_entries(source="llm")
        assert len(llm_entries) == 2
        assert all(e.source == "llm" for e in llm_entries)

        grammar_entries = tracker.filter_entries(source="grammar")
        assert len(grammar_entries) == 1
        assert all(e.source == "grammar" for e in grammar_entries)

    def test_filter_entries_by_validity(self, temp_logs_dir, temp_seed_dir):
        """Test filtering entries by validity."""
        tracker = ManifestTracker(temp_logs_dir)
        tracker.save_manifest(temp_seed_dir)

        valid_entries = tracker.filter_entries(is_valid=True)
        assert len(valid_entries) == 2
        assert all(e.is_valid for e in valid_entries)

        invalid_entries = tracker.filter_entries(is_valid=False)
        assert len(invalid_entries) == 1
        assert all(not e.is_valid for e in invalid_entries)

    def test_filter_entries_by_trivial(self, temp_logs_dir, temp_seed_dir):
        """Test filtering entries by trivial flag."""
        tracker = ManifestTracker(temp_logs_dir)
        tracker.save_manifest(temp_seed_dir)

        trivial_entries = tracker.filter_entries(trivial=True)
        assert len(trivial_entries) == 1
        assert trivial_entries[0].mutant_id == "seed1_grammar_mut_0"

    def test_compute_seed_ir_hash(self, temp_seed_dir):
        """Test seed IR hash computation."""
        tracker = ManifestTracker(temp_seed_dir)
        seed_file = temp_seed_dir / "seed1.ll"

        hash1 = tracker.compute_seed_ir_hash(seed_file)
        assert hash1 is not None
        assert len(hash1) == 32  # MD5 hex digest length

        # Same file should produce same hash
        hash2 = tracker.compute_seed_ir_hash(seed_file)
        assert hash1 == hash2

        # Non-existent file should return None
        non_existent = temp_seed_dir / "non_existent.ll"
        assert tracker.compute_seed_ir_hash(non_existent) is None

    def test_manifest_entry_dataclass(self):
        """Test ManifestEntry dataclass initialization."""
        entry = ManifestEntry(
            mutant_id="test_mut_0",
            seed_name="test.ll",
            source="llm",
            mutation_type="arithmetic_substitution",
            seed_ir_hash="abc123",
            is_valid=True,
            trivial=False,
            is_duplicate=False,
            content_hash="def456",
            error_type=None,
            status="validated",
            timestamp="2026-04-30T10:00:00Z"
        )

        assert entry.mutant_id == "test_mut_0"
        assert entry.is_valid is True
        assert entry.trivial is False

    def test_manifest_summary_dataclass(self):
        """Test ManifestSummary dataclass initialization."""
        summary = ManifestSummary(
            total_generated=10,
            valid_count=7,
            invalid_count=3,
            duplicate_count=0,
            trivial_count=2,
            by_mutator_type={"llm": {"generated": 10, "valid": 7}},
            by_error_type={"syntax": 2, "ssa": 1}
        )

        assert summary.total_generated == 10
        assert summary.valid_count == 7
        assert summary.by_error_type["syntax"] == 2


class TestManifestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_logs_directory(self):
        """Test handling of empty logs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)
            tracker = ManifestTracker(logs_dir)

            raw = tracker.load_raw_mutants()
            validity = tracker.load_validity_logs()
            assert len(raw) == 0
            assert len(validity) == 0

    def test_malformed_json_lines_skipped(self):
        """Test that malformed JSON lines are skipped gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            # Write file with some malformed JSON
            with open(logs_dir / "raw_mutants.json", "w") as f:
                f.write('{"id": "entry1", "data": "json"}\n')
                f.write("this is not json\n")
                f.write('{"id": "entry2", "data": "entry"}\n')

            tracker = ManifestTracker(logs_dir)
            raw = tracker.load_raw_mutants()
            assert len(raw) == 2  # Only valid entries loaded
            assert "entry1" in raw
            assert "entry2" in raw

    def test_filter_no_matches(self):
        """Test filter returns empty list when no matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)
            tracker = ManifestTracker(logs_dir)

            # Create empty manifest
            with open(logs_dir / "manifest.json", "w") as f:
                json.dump({"mutants": [], "summary": {}}, f)

            results = tracker.filter_entries(source="nonexistent")
            assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
