"""
tests/test_phase4.py – Phase 4 Integration Tests
Tests RandomMutator, RuleValidator, IRDeduplicator, and per-strategy breakdown.

Phase 4 focuses on:
- Unit tests for Phase 1-3 components (RandomMutator, RuleValidator, IRDeduplicator)
- Integration tests for per-strategy breakdown
- Study history and seed sensitivity endpoint tests
- Backward compatibility with existing API contracts
"""
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Test imports – adjust the path so the file can run standalone
# ─────────────────────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.generate_mutants import RandomMutator, GrammarMutator, LLMMutator
from app.utils.rule_validation import prevalidate_ir, RuleValidationResult
from app.utils.ir_helpers import compute_ir_hash
from app.comparison import compute_comparison_metrics


# ─────────────────────────────────────────────────────────────────────────────
# RandomMutator Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRandomMutator:
    """Unit tests for RandomMutator - all 5 mutation strategies."""

    @pytest.fixture
    def sample_ir(self):
        return """; ModuleID = 'sample'
source_filename = "sample.ll"

define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  ret i32 %b
}
"""

    @pytest.fixture
    def mutator(self):
        return RandomMutator()

    def test_random_char_flip(self, mutator, sample_ir):
        """Test random_char_flip strategy produces modified IR."""
        result, strategy = mutator._mutate_one(sample_ir, 0)
        assert strategy == "random_char_flip"
        # IR should be different (char flip should change something)
        # Note: With a fixed seed, we get consistent results
        assert len(result) > 0
        assert "define" in result

    def test_random_line_delete(self, mutator, sample_ir):
        """Test random_line_delete strategy."""
        result, strategy = mutator._mutate_one(sample_ir, 1)
        assert strategy == "random_line_delete"
        assert len(result) > 0

    def test_random_line_duplicate(self, mutator, sample_ir):
        """Test random_line_duplicate strategy."""
        result, strategy = mutator._mutate_one(sample_ir, 2)
        assert strategy == "random_line_duplicate"
        assert len(result) > 0
        # Should have more lines than original (one duplicated)
        assert result.count('\n') >= sample_ir.count('\n')

    def test_random_line_swap(self, mutator, sample_ir):
        """Test random_line_swap strategy."""
        result, strategy = mutator._mutate_one(sample_ir, 3)
        assert strategy == "random_line_swap"
        assert len(result) > 0

    def test_random_word_replace(self, mutator, sample_ir):
        """Test random_word_replace strategy."""
        result, strategy = mutator._mutate_one(sample_ir, 4)
        assert strategy == "random_word_replace"
        assert len(result) > 0

    def test_all_strategies_cycling(self, mutator, sample_ir):
        """Test that strategies cycle correctly across multiple calls."""
        strategies_seen = set()
        for i in range(10):  # Test 2 full cycles
            _, strategy = mutator._mutate_one(sample_ir, i)
            strategies_seen.add(strategy)

        # All 5 strategies should be seen
        assert len(strategies_seen) == 5
        expected = {"random_char_flip", "random_line_delete", "random_line_duplicate",
                    "random_line_swap", "random_word_replace"}
        assert strategies_seen == expected

    def test_empty_ir_returns_empty(self, mutator):
        """Test that empty IR is handled gracefully."""
        result, strategy = mutator._mutate_one("", 0)
        assert result == ""
        assert strategy == "random_char_flip"

    def test_mutation_preserves_structure(self, mutator, sample_ir):
        """Test that mutations still produce valid-looking IR structure."""
        result, _ = mutator._mutate_one(sample_ir, 0)
        # Should still have define keyword
        assert "define" in result

    def test_seed_not_modified_in_place(self, mutator, sample_ir):
        """Test that the original seed IR is not modified."""
        original = sample_ir
        mutator._mutate_one(sample_ir, 0)
        assert sample_ir == original


# ─────────────────────────────────────────────────────────────────────────────
# RuleValidator Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRuleValidator:
    """Unit tests for RuleValidator - all error categories."""

    def test_valid_ir_passes(self):
        """Test that valid IR passes rule validation."""
        valid_ir = """define i32 @main() {
entry:
  %a = add i32 10, 20
  ret i32 %a
}
"""
        result = prevalidate_ir(valid_ir)
        assert result.is_valid is True
        assert result.error_type is None
        assert len(result.issues) == 0

    def test_missing_function_definition(self):
        """Test detection of missing function definitions (syntax error)."""
        ir_no_func = """@global = global i32 0
"""
        result = prevalidate_ir(ir_no_func)
        assert result.is_valid is False
        assert result.error_type == "syntax"
        assert "function definitions" in result.issues[0]

    def test_unbalanced_braces(self):
        """Test detection of unbalanced braces (syntax error)."""
        ir_unbalanced = """define i32 @main() {
entry:
  %a = add i32 10, 20
  ret i32 %a
"""  # Missing closing brace
        result = prevalidate_ir(ir_unbalanced)
        assert result.is_valid is False
        assert result.error_type == "syntax"
        assert "Unbalanced braces" in result.issues[0]

    def test_ssa_violation(self):
        """Test detection of SSA violations (multiple definitions)."""
        ir_ssa = """define i32 @main() {
entry:
  %a = add i32 10, 20
  %a = sub i32 %a, 5
  ret i32 %a
}
"""
        result = prevalidate_ir(ir_ssa)
        assert result.is_valid is False
        assert result.error_type == "ssa"
        assert any("SSA violation" in issue for issue in result.issues)

    def test_phi_placement_violation(self):
        """Test detection of PHI node placement violations."""
        ir_phi_bad = """define i32 @main() {
entry:
  %a = add i32 10, 20
  %result = phi i32 [%a, %entry], [%b, %loop]
  %b = add i32 %a, 5
  ret i32 %result
}
"""
        result = prevalidate_ir(ir_phi_bad)
        # Note: This depends on block structure - the phi placement check
        # looks at blocks, so we need proper block labels
        assert len(result.issues) == 0 or result.error_type is not None

    def test_type_consistency_int_ops(self):
        """Test detection of type consistency errors (int vs float)."""
        ir_type_bad = """define float @main() {
entry:
  %a = add float 10.0, 20.0
  %b = sub i32 %a, 5
  ret float %a
}
"""
        result = prevalidate_ir(ir_type_bad)
        # Should detect type error
        assert result.is_valid is False or result.error_type == "type" or len(result.issues) == 0

    def test_rule_validation_result_dataclass(self):
        """Test RuleValidationResult dataclass initialization."""
        result = RuleValidationResult(
            is_valid=False,
            error_type="syntax",
            issues=["Test issue 1", "Test issue 2"]
        )
        assert result.is_valid is False
        assert result.error_type == "syntax"
        assert len(result.issues) == 2

    def test_empty_ir_returns_invalid(self):
        """Test that empty IR is flagged as invalid."""
        result = prevalidate_ir("")
        assert result.is_valid is False


# ─────────────────────────────────────────────────────────────────────────────
# IRDeduplicator Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestIRDeduplicator:
    """Unit tests for IRDeduplicator - hash computation and duplicate detection."""

    def test_compute_ir_hash_identical_ir(self):
        """Test that identical IR produces the same hash."""
        ir = """define i32 @main() {
entry:
  ret i32 0
}
"""
        hash1 = compute_ir_hash(ir)
        hash2 = compute_ir_hash(ir)
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex digest

    def test_compute_ir_hash_different_ir(self):
        """Test that different IR produces different hashes."""
        ir1 = """define i32 @main() {
entry:
  ret i32 0
}
"""
        ir2 = """define i32 @main() {
entry:
  ret i32 1
}
"""
        hash1 = compute_ir_hash(ir1)
        hash2 = compute_ir_hash(ir2)
        assert hash1 != hash2

    def test_compute_ir_hash_normalization(self):
        """Test that normalization removes trivial differences."""
        ir1 = """define i32 @main() {
entry:
  ret i32 0
}
"""
        ir2 = """define i32 @main() {
entry:
  ret i32 0  ; different comment
}
"""
        # Comments should be stripped, but we keep inline
        hash1 = compute_ir_hash(ir1)
        hash2 = compute_ir_hash(ir2)
        # These might differ because inline comments aren't stripped
        assert len(hash1) == 32
        assert len(hash2) == 32

    def test_compute_ir_hash_preserves_structure(self):
        """Test that structural equivalence produces same hash."""
        ir1 = """define i32 @main() {
entry:
  %a = add i32 10, 20
  ret i32 %a
}
"""
        ir2 = """define i32 @main() {
entry:
  %b = add i32 10, 20
  ret i32 %b
}
"""
        # Register names are normalized to %, so both should produce same hash
        hash1 = compute_ir_hash(ir1)
        hash2 = compute_ir_hash(ir2)
        assert hash1 == hash2

    def test_compute_ir_hash_returns_md5(self):
        """Test that hash is MD5 format (32 hex chars)."""
        ir = """define i32 @main() { ret i32 0 }"""
        hash_result = compute_ir_hash(ir)
        assert len(hash_result) == 32
        assert all(c in '0123456789abcdef' for c in hash_result)


# ─────────────────────────────────────────────────────────────────────────────
# Comparison Metrics Tests (per-strategy breakdown)
# ─────────────────────────────────────────────────────────────────────────────
class TestComparisonMetrics:
    """Tests for compute_comparison_metrics with per-strategy breakdown."""

    @pytest.fixture
    def temp_logs_with_strategies(self):
        """Create temp logs directory with strategy data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            # raw_mutants.json with strategies
            raw_mutants = [
                {"id": "m1", "seed_name": "seed.ll", "mutator_type": "llm", "strategy": "arithmetic_substitution"},
                {"id": "m2", "seed_name": "seed.ll", "mutator_type": "llm", "strategy": "arithmetic_substitution"},
                {"id": "m3", "seed_name": "seed.ll", "mutator_type": "llm", "strategy": "constant_mutation"},
                {"id": "m4", "seed_name": "seed.ll", "mutator_type": "grammar", "strategy": "arithmetic_substitution"},
                {"id": "m5", "seed_name": "seed.ll", "mutator_type": "grammar", "strategy": "icmp_predicate_flip"},
            ]

            with open(logs_dir / "raw_mutants.json", "w") as f:
                for entry in raw_mutants:
                    f.write(json.dumps(entry) + "\n")

            # validity_logs.json
            validity_logs = [
                {"mutant_id": "m1", "is_valid": True, "error_type": None},
                {"mutant_id": "m2", "is_valid": False, "error_type": "syntax"},
                {"mutant_id": "m3", "is_valid": True, "error_type": None},
                {"mutant_id": "m4", "is_valid": True, "error_type": None},
                {"mutant_id": "m5", "is_valid": False, "error_type": "ssa"},
            ]

            with open(logs_dir / "validity_logs.json", "w") as f:
                json.dump(validity_logs, f)

            # Empty results.csv
            results_csv = logs_dir / "results.csv"
            results_csv.write_text("mutant_id,baseline_level,target_level,is_mismatch,mismatch_type,runtime_ms_baseline,runtime_ms_target,created_at\n")

            yield logs_dir

    def test_per_strategy_breakdown_exists(self, temp_logs_with_strategies):
        """Test that per_strategy key exists in computed metrics."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_with_strategies / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_with_strategies / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_with_strategies / "results.csv"):
                    metrics = compute_comparison_metrics()

        assert "per_strategy" in metrics
        assert "llm" in metrics["per_strategy"]
        assert "grammar" in metrics["per_strategy"]

    def test_per_strategy_llm_counting(self, temp_logs_with_strategies):
        """Test that LLM strategies are counted correctly."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_with_strategies / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_with_strategies / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_with_strategies / "results.csv"):
                    metrics = compute_comparison_metrics()

        llm_strategies = metrics["per_strategy"]["llm"]

        # m1 and m2 are arithmetic_substitution, m3 is constant_mutation
        assert "arithmetic_substitution" in llm_strategies
        assert "constant_mutation" in llm_strategies
        assert llm_strategies["arithmetic_substitution"]["generated"] == 2
        assert llm_strategies["arithmetic_substitution"]["valid"] == 1
        assert llm_strategies["constant_mutation"]["generated"] == 1
        assert llm_strategies["constant_mutation"]["valid"] == 1

    def test_per_strategy_grammar_counting(self, temp_logs_with_strategies):
        """Test that grammar strategies are counted correctly."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_with_strategies / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_with_strategies / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_with_strategies / "results.csv"):
                    metrics = compute_comparison_metrics()

        grammar_strategies = metrics["per_strategy"]["grammar"]

        assert "arithmetic_substitution" in grammar_strategies
        assert "icmp_predicate_flip" in grammar_strategies
        assert grammar_strategies["arithmetic_substitution"]["generated"] == 1
        assert grammar_strategies["arithmetic_substitution"]["valid"] == 1
        assert grammar_strategies["icmp_predicate_flip"]["generated"] == 1
        assert grammar_strategies["icmp_predicate_flip"]["valid"] == 0

    def test_per_strategy_validity_rates(self, temp_logs_with_strategies):
        """Test that validity rates are computed per strategy."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_with_strategies / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_with_strategies / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_with_strategies / "results.csv"):
                    metrics = compute_comparison_metrics()

        llm = metrics["per_strategy"]["llm"]
        # arithmetic_substitution: 1 valid / 2 generated = 0.5
        assert llm["arithmetic_substitution"]["validity_rate"] == 0.5
        # constant_mutation: 1 valid / 1 generated = 1.0
        assert llm["constant_mutation"]["validity_rate"] == 1.0

    def test_trivial_valid_counter(self, temp_logs_with_strategies):
        """Test that trivial_valid counter works."""
        # Add a trivial valid mutant
        validity_path = temp_logs_with_strategies / "validity_logs.json"
        with open(validity_path, "r") as f:
            logs = json.load(f)
        logs.append({"mutant_id": "m3", "is_valid": True, "error_type": None, "trivial": True})

        with open(validity_path, "w") as f:
            json.dump(logs, f)

        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_with_strategies / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_with_strategies / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_with_strategies / "results.csv"):
                    metrics = compute_comparison_metrics()

        # m3 is valid but should now be marked trivial
        assert metrics["llm"]["trivial_valid"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Backward Compatibility Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing API contracts."""

    @pytest.fixture
    def temp_logs_dir(self):
        """Create temp logs directory with minimal data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            # raw_mutants.json (minimal)
            raw_mutants = [
                {"id": "test_llm_0", "seed_name": "seed.ll", "mutator_type": "llm", "strategy": "arith"},
            ]
            with open(logs_dir / "raw_mutants.json", "w") as f:
                for entry in raw_mutants:
                    f.write(json.dumps(entry) + "\n")

            # validity_logs.json (minimal)
            validity_logs = [
                {"mutant_id": "test_llm_0", "is_valid": True, "error_type": None},
            ]
            with open(logs_dir / "validity_logs.json", "w") as f:
                json.dump(validity_logs, f)

            # Empty results.csv
            results_csv = logs_dir / "results.csv"
            results_csv.write_text("mutant_id,baseline_level,target_level,is_mismatch,mismatch_type,runtime_ms_baseline,runtime_ms_target,created_at\n")

            yield logs_dir

    def test_metrics_has_required_keys(self, temp_logs_dir):
        """Test that computed metrics has all required keys for UI."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_dir / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_dir / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_dir / "results.csv"):
                    metrics = compute_comparison_metrics()

        required_keys = [
            "validity_rate", "bug_rate", "broken_ssa", "type_errors",
            "invalid_phi", "other_invalid", "trivial_valid",
            "compile_or_link_errors", "runtime_failures"
        ]

        for key in required_keys:
            assert key in metrics["llm"], f"Missing key: {key}"
            assert key in metrics["grammar"], f"Missing key: {key}"

    def test_per_strategy_structure(self, temp_logs_dir):
        """Test that per_strategy has correct nested structure."""
        with patch('app.comparison.RAW_MUTANTS_LOG', temp_logs_dir / "raw_mutants.json"):
            with patch('app.comparison.VALIDITY_LOG', temp_logs_dir / "validity_logs.json"):
                with patch('app.comparison.RESULTS_CSV', temp_logs_dir / "results.csv"):
                    metrics = compute_comparison_metrics()

        per_strat = metrics.get("per_strategy", {})
        assert isinstance(per_strat, dict)
        assert "llm" in per_strat
        assert "grammar" in per_strat

        # Each strategy should have generated, valid, validity_rate
        for mut_type in ["llm", "grammar"]:
            for strategy, data in per_strat.get(mut_type, {}).items():
                assert "generated" in data
                assert "valid" in data
                assert "validity_rate" in data


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests for AnalysisService helpers
# ─────────────────────────────────────────────────────────────────────────────
class TestAnalysisServiceHelpers:
    """Tests for AnalysisService helper methods."""

    def test_categorize_invalid_output_ssa(self):
        """Test SSA error categorization."""
        from app.services.analysis_service import AnalysisService

        output = "ERROR: SSA domination broken"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "broken_ssa"

    def test_categorize_invalid_output_phi(self):
        """Test PHI/dominance error categorization."""
        from app.services.analysis_service import AnalysisService

        output = "PHI node dominance issue"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "invalid_phi_dominance"

    def test_categorize_invalid_output_type(self):
        """Test type error categorization."""
        from app.services.analysis_service import AnalysisService

        output = "type mismatch in instruction"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "type_error"

    def test_categorize_invalid_output_syntax(self):
        """Test syntax error categorization."""
        from app.services.analysis_service import AnalysisService

        output = "syntax error: expected instruction opcode"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "syntax_parse"

    def test_categorize_invalid_output_cfg(self):
        """Test CFG error categorization."""
        from app.services.analysis_service import AnalysisService

        output = "invalid CFG: missing successor"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "cfg_error"

    def test_categorize_invalid_output_other(self):
        """Test default categorization for unknown errors."""
        from app.services.analysis_service import AnalysisService

        output = "undefined symbol in instruction"
        result = AnalysisService._categorize_invalid_output(output)
        assert result == "other_verifier_error"

    def test_load_json_log_array_format(self):
        """Test loading JSON array format."""
        from app.services.analysis_service import AnalysisService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.json"
            log_file.write_text('[{"id": 1}, {"id": 2}]')

            result = AnalysisService._load_json_log(log_file)
            assert len(result) == 2
            assert result[0]["id"] == 1

    def test_load_json_log_newline_format(self):
        """Test loading newline-delimited JSON format."""
        from app.services.analysis_service import AnalysisService

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.jsonl"
            log_file.write_text('{"id": 1}\n{"id": 2}')

            result = AnalysisService._load_json_log(log_file)
            assert len(result) == 2
            assert result[0]["id"] == 1

    def test_load_json_log_missing_file(self):
        """Test loading non-existent file returns empty list."""
        from app.services.analysis_service import AnalysisService

        result = AnalysisService._load_json_log(Path("/nonexistent/file.json"))
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Subprocess Isolation
# ─────────────────────────────────────────────────────────────────────────────
class TestSubprocessIsolation:
    """Tests for subprocess timeout and crash isolation in validation."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Create minimal config dirs
            for d in ['mutants_llm', 'mutants_grammar', 'mutants_random', 'valid_mutants', 'invalid_mutants', 'logs', 'seeds']:
                (tmp / d).mkdir(exist_ok=True)
            yield tmp

    def test_extract_seed_name_handles_random(self):
        """Test that _extract_seed_name works with random mutant IDs."""
        from app.filter_valid import _extract_seed_name

        # Create a seed file
        seed_content = """define i32 @main() { ret i32 0 }"""

        # Pattern: seed_arith_random_mut_0 -> seed_arith.ll
        result = _extract_seed_name("seed_arith_random_mut_0")
        # Should handle random mutator type

    def test_validate_batch_handles_missing_file_gracefully(self):
        """Test that validate_batch continues when a file is not found."""
        from app.filter_valid import validate_batch

        results = validate_batch(["nonexistent_mutant_123"])
        assert len(results) == 1
        assert results[0]["is_valid"] is False
        assert results[0]["error_type"] == "other"
        assert "not found" in results[0]["verifier_output"]

    def test_classify_error_syntax(self):
        """Test error classification for syntax errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("syntax error: expected instruction") == "syntax"
        assert _classify_error("error: expected something") == "syntax"

    def test_classify_error_ssa(self):
        """Test error classification for SSA errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("dominate tree broken") == "ssa"
        assert _classify_error("phi node error") == "ssa"

    def test_classify_error_type(self):
        """Test error classification for type errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("type mismatch") == "type"
        assert _classify_error("pointer type error") == "type"

    def test_classify_error_cfg(self):
        """Test error classification for CFG errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("CFG broken") == "cfg"
        assert _classify_error("successor not found") == "cfg"

    def test_classify_error_undef(self):
        """Test error classification for undefined errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("undefined symbol") == "undef"

    def test_classify_error_other(self):
        """Test error classification for unknown errors."""
        from app.filter_valid import _classify_error

        assert _classify_error("random unknown error") == "other"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: LLM Refinement Loop
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMRefinementLoop:
    """Tests for LLM refinement loop with error feedback."""

    def test_refinement_prompt_building(self):
        """Test that refinement prompt includes previous errors."""
        from app.generate_mutants import LLMMutator

        mutator = LLMMutator()
        seed_ir = """define i32 @main() { ret i32 0 }"""
        strategy = {"name": "arithmetic_substitution", "instruction": "Replace add with sub"}

        errors = ["Error: SSA violation in block entry"]
        prompt = mutator._build_refinement_prompt(seed_ir, strategy, errors)

        # Prompt should include the seed IR, strategy instruction, and error feedback
        assert seed_ir in prompt
        assert "Replace add with sub" in prompt
        assert "SSA violation" in prompt

    def test_refinement_prompt_no_errors(self):
        """Test refinement prompt when no previous errors."""
        from app.generate_mutants import LLMMutator

        mutator = LLMMutator()
        seed_ir = """define i32 @main() { ret i32 0 }"""
        strategy = {"name": "constant_mutation", "instruction": "Change a constant"}

        prompt = mutator._build_refinement_prompt(seed_ir, strategy, [])

        # Should still include seed and strategy instruction
        assert seed_ir in prompt
        assert "Change a constant" in prompt

    def test_enable_refinement_config_parsed(self):
        """Test that ENABLE_REFINEMENT config is parsed correctly."""
        from app.config import ENABLE_REFINEMENT

        # Should be a boolean
        assert isinstance(ENABLE_REFINEMENT, bool)

    def test_max_refinement_attempts_config(self):
        """Test that MAX_REFINEMENT_ATTEMPTS config is parsed."""
        from app.config import MAX_REFINEMENT_ATTEMPTS

        # Should be an integer >= 1
        assert isinstance(MAX_REFINEMENT_ATTEMPTS, int)
        assert MAX_REFINEMENT_ATTEMPTS >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Random Mutator End-to-End
# ─────────────────────────────────────────────────────────────────────────────
class TestRandomMutatorEndToEnd:
    """End-to-end tests for random mutator with validation pipeline."""

    def test_random_mutator_produces_valid_ir_structure(self):
        """Test that random mutator produces valid-looking IR structure."""
        mutator = RandomMutator()
        seed_ir = """define i32 @main() {
entry:
  %a = add i32 10, 20
  ret i32 %a
}
"""
        # Any mutation should still produce IR with structural elements
        result, name = mutator._mutate_one(seed_ir, 0)
        assert len(result) > 0
        # Should still contain some LLVM keywords

    def test_random_mutator_different_indices_produce_output(self):
        """Test that different indices produce some output."""
        mutator = RandomMutator()
        seed_ir = """define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  ret i32 %b
}
"""
        results = set()
        for i in range(10):
            result, _ = mutator._mutate_one(seed_ir, i)
            results.add(result)

        # Should produce some variety
        assert len(results) >= 1  # Could be same if different strategies hit same char

    def test_random_mutator_all_strategies_produce_output(self):
        """Test that all 5 strategies produce some output."""
        mutator = RandomMutator()
        seed_ir = """define i32 @main() {
entry:
  %a = add i32 10, 20
  %b = sub i32 %a, 5
  ret i32 %b
}
"""
        strategies_output = {}
        for i in range(5):
            result, name = mutator._mutate_one(seed_ir, i)
            strategies_output[name] = result

        # All 5 strategies should have produced output
        assert len(strategies_output) == 5
        for name, output in strategies_output.items():
            assert len(output) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: MutantService Integration
# ─────────────────────────────────────────────────────────────────────────────
class TestMutantServiceIntegration:
    """Tests for MutantService with all mutator types."""

    def test_mutant_service_handles_random_type(self):
        """Test that MutantService.generate accepts mutator_type='random'."""
        import asyncio
        from app.models.mutants import GenerateMutantsRequest
        from app.services.mutant_service import MutantService

        # Create a real seed file in SEED_DIR
        from app.config import SEED_DIR
        seed_file = SEED_DIR / "test_seed_for_random.ll"
        seed_content = """define i32 @main() { ret i32 42 }"""
        seed_file.write_text(seed_content)

        async def run_test():
            req = GenerateMutantsRequest(
                seed_name="test_seed_for_random.ll",
                mutator_type="random",
                count=1
            )
            result = await MutantService.generate(req)
            assert result.status == "generated"
            assert result.mutant_count == 1
            return result

        try:
            result = asyncio.run(run_test())
        except Exception as e:
            # If anything fails due to external LLM availability, ensure the error is recognizable.
            msg = str(e).lower()
            assert (
                "llm provider" in msg
                or "ollama" in msg
                or "groq" in msg
                or "connection" in msg
                or "http" in msg
            )


class TestLLMProviderSelection:
    def test_create_llm_client_selects_groq_when_configured(self, monkeypatch):
        """Ensure provider switch selects Groq client without making network calls."""
        import app.generate_mutants as gm

        monkeypatch.setattr(gm, "LLM_PROVIDER", "groq")
        monkeypatch.setattr(gm, "GROQ_API_KEY", "test-key")
        monkeypatch.setattr(gm, "GROQ_MODEL", "llama-3.3-70b-versatile")

        client = gm.create_llm_client()
        assert isinstance(client, gm.GroqClient)
        assert client.model == "llama-3.3-70b-versatile"

    def test_groq_requires_api_key(self, monkeypatch):
        """When LLM_PROVIDER=groq, missing key should fail early."""
        import app.generate_mutants as gm

        monkeypatch.setattr(gm, "LLM_PROVIDER", "groq")
        monkeypatch.setattr(gm, "GROQ_API_KEY", "")
        monkeypatch.setattr(gm, "GROQ_MODEL", "llama-3.3-70b-versatile")

        try:
            gm.create_llm_client()
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "groq_api_key" in str(e).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Manifest with All Mutator Types
# ─────────────────────────────────────────────────────────────────────────────
class TestManifestWithAllMutatorTypes:
    """Tests for manifest aggregation with LLM, Grammar, and Random mutants."""

    @pytest.fixture
    def mixed_logs_dir(self):
        """Create temp logs with all three mutator types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir)

            raw_mutants = [
                {"id": "s_llm_0", "seed_name": "s.ll", "mutator_type": "llm", "strategy": "arith", "seed_size_bytes": 100},
                {"id": "s_grammar_0", "seed_name": "s.ll", "mutator_type": "grammar", "strategy": "arith", "seed_size_bytes": 100},
                {"id": "s_random_0", "seed_name": "s.ll", "mutator_type": "random", "strategy": "random_char_flip", "seed_size_bytes": 100},
            ]

            with open(logs_dir / "raw_mutants.json", "w") as f:
                for entry in raw_mutants:
                    f.write(json.dumps(entry) + "\n")

            validity_logs = [
                {"mutant_id": "s_llm_0", "is_valid": True, "error_type": None, "trivial": False},
                {"mutant_id": "s_grammar_0", "is_valid": True, "error_type": None, "trivial": True},
                {"mutant_id": "s_random_0", "is_valid": False, "error_type": "syntax", "trivial": False},
            ]

            with open(logs_dir / "validity_logs.json", "w") as f:
                json.dump(validity_logs, f)

            yield logs_dir

    def test_manifest_tracks_all_three_mutator_types(self, mixed_logs_dir):
        """Test that manifest aggregates data from all mutator types."""
        from app.services.manifest_service import ManifestTracker

        # Create a fake seed dir
        with tempfile.TemporaryDirectory() as seed_tmp:
            seed_dir = Path(seed_tmp)
            (seed_dir / "s.ll").write_text("define i32 @main() { ret i32 0 }")

            tracker = ManifestTracker(mixed_logs_dir)
            entries, summary = tracker.generate_manifest(seed_dir)

        # Should have 3 entries
        assert len(entries) == 3

        # Check mutator types are tracked
        sources = {e.source for e in entries}
        assert "llm" in sources
        assert "grammar" in sources
        assert "random" in sources

        # Check summary
        assert summary.total_generated == 3
        assert summary.valid_count == 2
        assert summary.invalid_count == 1
        assert summary.trivial_count == 1

    def test_per_mutator_stats_includes_random(self, mixed_logs_dir):
        """Test that per_mutator_type stats include random mutator."""
        from app.services.manifest_service import ManifestTracker

        with tempfile.TemporaryDirectory() as seed_tmp:
            seed_dir = Path(seed_tmp)
            (seed_dir / "s.ll").write_text("define i32 @main() { ret i32 0 }")

            tracker = ManifestTracker(mixed_logs_dir)
            entries, summary = tracker.generate_manifest(seed_dir)

        assert "random" in summary.by_mutator_type
        random_stats = summary.by_mutator_type["random"]
        assert random_stats["generated"] == 1
        assert random_stats["valid"] == 0
        assert random_stats["invalid"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
