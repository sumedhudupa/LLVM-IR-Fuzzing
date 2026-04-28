"""
app/services/analysis_service.py
Analysis services for invalid taxonomy and controlled study runs.
"""
import datetime
import json
import re
from collections import Counter
from pathlib import Path

from app.config import LOGS_DIR
from app.models.analysis import StudyRunRequest
from app.models.differential import DifferentialRunRequest
from app.services.differential_service import DifferentialService
from app.services.mutant_service import MutantService
from app.models.mutants import GenerateMutantsRequest, ValidateMutantsRequest
from app.utils.fs_helpers import append_json_log

VALIDITY_LOG = LOGS_DIR / "validity_logs.json"
STUDY_RUNS_LOG = LOGS_DIR / "study_runs.jsonl"
RAW_MUTANTS_LOG = LOGS_DIR / "raw_mutants.json"


class AnalysisService:
    @staticmethod
    def _load_json_log(path: Path) -> list[dict]:
        """Load a JSON log file (array format or newline-delimited)."""
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return []
        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    @staticmethod
    def _load_validity_logs() -> list[dict]:
        return AnalysisService._load_json_log(VALIDITY_LOG)

    @staticmethod
    def _categorize_invalid_output(verifier_output: str) -> str:
        s = (verifier_output or "").lower()
        if "ssa" in s or "dominate" in s:
            return "broken_ssa"
        if "phi" in s or "dominance" in s:
            return "invalid_phi_dominance"
        if "type" in s or "mismatch" in s or "pointer" in s:
            return "type_error"
        if "syntax error" in s or "expected" in s or "invalid token" in s:
            return "syntax_parse"
        if "cfg" in s or "successor" in s or "terminator" in s:
            return "cfg_error"
        return "other_verifier_error"

    @staticmethod
    async def get_invalid_taxonomy() -> dict:
        logs = AnalysisService._load_validity_logs()
        invalid = [r for r in logs if not r.get("is_valid", False)]
        category_counts: Counter = Counter()
        error_counts: Counter = Counter()

        for row in invalid:
            output = row.get("verifier_output", "")
            category = AnalysisService._categorize_invalid_output(output)
            category_counts[category] += 1
            normalized = re.sub(r"\s+", " ", output.strip())[:160]
            if normalized:
                error_counts[normalized] += 1

        top_errors = [
            {"error": msg, "count": count}
            for msg, count in error_counts.most_common(8)
        ]

        return {
            "total_invalid": len(invalid),
            "categories": dict(category_counts),
            "top_errors": top_errors,
        }

    @staticmethod
    async def run_controlled_study(req: StudyRunRequest) -> dict:
        started_at = datetime.datetime.utcnow().isoformat() + "Z"
        run_id = f"study_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
        per_config: list[dict] = []
        aggregate = {
            "generated": 0,
            "valid": 0,
            "invalid": 0,
            "differential_mismatches": 0,
            "configs": 0,
        }

        for mutator in req.mutators:
            for seed_name in req.seed_names:
                gen = await MutantService.generate(
                    GenerateMutantsRequest(
                        seed_name=seed_name,
                        mutator_type=mutator,
                        count=req.count_per_seed,
                    )
                )

                validate = await MutantService.validate(
                    ValidateMutantsRequest(mutant_ids=gen.mutant_ids)
                )
                valid_ids = [r.mutant_id for r in validate.results if r.is_valid]
                invalid_count = len(validate.results) - len(valid_ids)

                diff_summary = {
                    "total_valid": 0,
                    "total_mismatches": 0,
                    "mismatch_rate": 0.0,
                }
                if valid_ids:
                    diff = await DifferentialService.run(
                        DifferentialRunRequest(
                            baseline_opt=req.baseline_opt,
                            target_opt=req.target_opt,
                            mutant_ids=valid_ids,
                            run_id=run_id,
                        )
                    )
                    diff_summary = {
                        "total_valid": diff.total_valid,
                        "total_mismatches": diff.total_mismatches,
                        "mismatch_rate": diff.mismatch_rate,
                    }

                config_result = {
                    "mutator": mutator,
                    "seed_name": seed_name,
                    "requested_count": req.count_per_seed,
                    "generated_count": gen.mutant_count,
                    "valid_count": len(valid_ids),
                    "invalid_count": invalid_count,
                    "differential": diff_summary,
                }
                per_config.append(config_result)

                aggregate["generated"] += gen.mutant_count
                aggregate["valid"] += len(valid_ids)
                aggregate["invalid"] += invalid_count
                aggregate["differential_mismatches"] += diff_summary["total_mismatches"]
                aggregate["configs"] += 1

        aggregate["validity_rate"] = round(
            aggregate["valid"] / aggregate["generated"], 4
        ) if aggregate["generated"] else 0.0
        aggregate["mismatch_rate_over_valid"] = round(
            aggregate["differential_mismatches"] / aggregate["valid"], 4
        ) if aggregate["valid"] else 0.0

        completed_at = datetime.datetime.utcnow().isoformat() + "Z"
        payload = {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "settings": req.model_dump(),
            "per_config": per_config,
            "aggregate": aggregate,
        }
        append_json_log(Path(STUDY_RUNS_LOG), payload)
        return payload

    @staticmethod
    async def get_seed_sensitivity() -> list[dict]:
        """
        Analyze validity rate vs seed size for both mutator types.
        Returns list of {seed_name, seed_size_bytes, llm_validity_rate, grammar_validity_rate}
        """
        raw_mutants = AnalysisService._load_json_log(RAW_MUTANTS_LOG)
        validity_logs = AnalysisService._load_validity_logs()

        # Build validity lookup: mutant_id -> is_valid
        validity_map = {v["mutant_id"]: v.get("is_valid", False) for v in validity_logs}

        # Group by (seed_name, mutator_type)
        from collections import defaultdict
        seed_stats = defaultdict(lambda: {"llm": {"generated": 0, "valid": 0}, "grammar": {"generated": 0, "valid": 0}, "size": 0})

        for m in raw_mutants:
            seed_name = m.get("seed_name", "")
            mutator_type = m.get("mutator_type", "")
            if not seed_name or mutator_type not in ("llm", "grammar"):
                continue

            # Track seed size
            size = m.get("seed_size_bytes", 0)
            if size > 0:
                seed_stats[seed_name]["size"] = size

            # Track generation and validity
            seed_stats[seed_name][mutator_type]["generated"] += 1
            mutant_id = m.get("id", "")
            if validity_map.get(mutant_id, False):
                seed_stats[seed_name][mutator_type]["valid"] += 1

        # Build result list
        results = []
        for seed_name, stats in seed_stats.items():
            llm_gen = stats["llm"]["generated"]
            grammar_gen = stats["grammar"]["generated"]

            llm_rate = round(stats["llm"]["valid"] / llm_gen, 4) if llm_gen > 0 else 0.0
            grammar_rate = round(stats["grammar"]["valid"] / grammar_gen, 4) if grammar_gen > 0 else 0.0

            results.append({
                "seed_name": seed_name,
                "seed_size_bytes": stats["size"],
                "llm_generated": llm_gen,
                "llm_valid": stats["llm"]["valid"],
                "llm_validity_rate": llm_rate,
                "grammar_generated": grammar_gen,
                "grammar_valid": stats["grammar"]["valid"],
                "grammar_validity_rate": grammar_rate,
            })

        # Sort by seed size
        results.sort(key=lambda x: x["seed_size_bytes"])
        return results

    @staticmethod
    async def get_study_history(limit: int = 20) -> list[dict]:
        """
        Read study_runs.jsonl and return the last N runs, newest first.
        """
        if not STUDY_RUNS_LOG.exists():
            return []

        runs = []
        content = STUDY_RUNS_LOG.read_text(encoding="utf-8").strip()
        if not content:
            return []

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        # Return last N runs, newest first
        return runs[-limit:][::-1]
