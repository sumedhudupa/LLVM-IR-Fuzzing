"""
app/services/analysis_service.py
Analysis services for invalid taxonomy and controlled study runs.
"""
import datetime
import json
import re
import csv
from collections import Counter
from pathlib import Path

from app.config import LOGS_DIR, SEED_DIR
from app.models.analysis import StudyRunRequest
from app.models.differential import DifferentialRunRequest
from app.services.differential_service import DifferentialService
from app.services.mutant_service import MutantService
from app.services.manifest_service import ManifestTracker
from app.models.mutants import GenerateMutantsRequest, ValidateMutantsRequest
from app.utils.fs_helpers import append_json_log

VALIDITY_LOG = LOGS_DIR / "validity_logs.json"
STUDY_RUNS_LOG = LOGS_DIR / "study_runs.jsonl"
RAW_MUTANTS_LOG = LOGS_DIR / "raw_mutants.json"
RESULTS_CSV = LOGS_DIR / "results.csv"
LLM_SUMMARY_CSV = LOGS_DIR / "llm_summary.csv"
LLM_PER_SEED_SUMMARY_CSV = LOGS_DIR / "llm_per_seed_summary.csv"


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
                        run_tag=req.run_tag if mutator == "llm" else None,
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
        Analyze validity rate vs seed size for each mutator type.
        """
        raw_mutants = AnalysisService._load_json_log(RAW_MUTANTS_LOG)
        validity_logs = AnalysisService._load_validity_logs()

        # Build validity lookup: mutant_id -> is_valid
        validity_map = {v["mutant_id"]: v.get("is_valid", False) for v in validity_logs}

        # Group by (seed_name, mutator_type)
        from collections import defaultdict
        seed_stats = defaultdict(lambda: {
            "llm": {"generated": 0, "valid": 0},
            "grammar": {"generated": 0, "valid": 0},
            "random": {"generated": 0, "valid": 0},
            "size": 0,
        })

        for m in raw_mutants:
            seed_name = m.get("seed_name", "")
            mutator_type = m.get("mutator_type", "")
            if not seed_name or mutator_type not in ("llm", "grammar", "random"):
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
            random_gen = stats["random"]["generated"]

            llm_rate = round(stats["llm"]["valid"] / llm_gen, 4) if llm_gen > 0 else 0.0
            grammar_rate = round(stats["grammar"]["valid"] / grammar_gen, 4) if grammar_gen > 0 else 0.0
            random_rate = round(stats["random"]["valid"] / random_gen, 4) if random_gen > 0 else 0.0

            results.append({
                "seed_name": seed_name,
                "seed_size_bytes": stats["size"],
                "llm_generated": llm_gen,
                "llm_valid": stats["llm"]["valid"],
                "llm_validity_rate": llm_rate,
                "grammar_generated": grammar_gen,
                "grammar_valid": stats["grammar"]["valid"],
                "grammar_validity_rate": grammar_rate,
                "random_generated": random_gen,
                "random_valid": stats["random"]["valid"],
                "random_validity_rate": random_rate,
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

    @staticmethod
    async def get_manifest() -> dict:
        """
        Generate and retrieve comprehensive manifest with all mutant metadata.
        Aggregates raw_mutants.json and validity_logs.json into structured manifest.
        """
        tracker = ManifestTracker(LOGS_DIR)
        manifest_path = tracker.save_manifest(SEED_DIR)

        # Load and return manifest
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "mutants": [],
            "summary": {
                "total_generated": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_count": 0,
                "trivial_count": 0,
                "by_mutator_type": {},
                "by_error_type": {},
            }
        }

    @staticmethod
    async def get_llm_summary() -> dict:
        """
        Aggregate per-LLM metrics across raw_mutants, validity logs, and results.csv.
        Returns a dict with per-LLM rows and per-seed rows, and writes summary CSVs.
        """
        raw_mutants = AnalysisService._load_json_log(RAW_MUTANTS_LOG)
        validity_logs = AnalysisService._load_validity_logs()

        results_rows = []
        if RESULTS_CSV.exists():
            with open(RESULTS_CSV, newline="") as f:
                results_rows = list(csv.DictReader(f))

        def _safe_int(value: object) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _safe_float(value: object) -> float | None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def _infer_llm_key(raw_entry: dict) -> tuple[str, str | None, str | None, str | None]:
            meta = raw_entry.get("metadata") or {}
            run_tag = raw_entry.get("run_tag") or meta.get("run_tag")
            provider = meta.get("provider") or raw_entry.get("provider")
            model = meta.get("model") or raw_entry.get("model")

            if run_tag:
                return run_tag, run_tag, provider, model
            if provider and model:
                return f"{provider}/{model}", None, provider, model
            if model:
                return model, None, provider, model
            if provider:
                return provider, None, provider, None
            return "unknown", None, None, None

        error_keys = ["syntax", "ssa", "type", "cfg", "undef", "other", "timeout"]

        def _init_stats(llm_key: str, run_tag: str | None, provider: str | None, model: str | None,
                        seed_name: str | None = None) -> dict:
            return {
                "llm_key": llm_key,
                "run_tag": run_tag,
                "provider": provider,
                "model": model,
                "seed_name": seed_name,
                "generated": 0,
                "duplicate_skipped": 0,
                "valid": 0,
                "invalid": 0,
                "diff_total": 0,
                "diff_mismatches": 0,
                "attempts_sum": 0,
                "attempts_count": 0,
                "gen_time_sum": 0.0,
                "gen_time_count": 0,
                "refinement_success": 0,
                "refinement_count": 0,
                "errors": {k: 0 for k in error_keys},
            }

        def _add_generation(s: dict, status: str) -> None:
            if status == "duplicate_skipped":
                s["duplicate_skipped"] += 1
            else:
                s["generated"] += 1

        def _add_meta(s: dict, meta: dict) -> None:
            attempts_made = _safe_int(meta.get("attempts_made"))
            if attempts_made is not None:
                s["attempts_sum"] += attempts_made
                s["attempts_count"] += 1

            gen_time_ms = _safe_float(meta.get("generation_time_ms"))
            if gen_time_ms is not None:
                s["gen_time_sum"] += gen_time_ms
                s["gen_time_count"] += 1

            refinement_succeeded = meta.get("refinement_succeeded")
            if refinement_succeeded is not None:
                s["refinement_count"] += 1
                if bool(refinement_succeeded):
                    s["refinement_success"] += 1

        def _add_validity(s: dict, vlog: dict) -> None:
            if vlog.get("is_valid"):
                s["valid"] += 1
            else:
                s["invalid"] += 1
                etype = (vlog.get("error_type") or "other").strip().lower()
                if etype not in error_keys:
                    etype = "other"
                s["errors"][etype] += 1

        def _add_diff(s: dict, row: dict) -> None:
            s["diff_total"] += 1
            if str(row.get("is_mismatch", "")).lower() == "true":
                s["diff_mismatches"] += 1

        def _build_row(s: dict, include_seed: bool = False) -> dict:
            generated = s["generated"]
            valid = s["valid"]
            invalid = s["invalid"]
            diff_total = s["diff_total"]
            diff_mismatches = s["diff_mismatches"]

            validity_rate = round(valid / generated, 4) if generated else 0.0
            bug_rate = round(diff_mismatches / diff_total, 4) if diff_total else 0.0
            avg_generation_ms = (
                round(s["gen_time_sum"] / s["gen_time_count"], 2)
                if s["gen_time_count"]
                else None
            )
            avg_attempts = (
                round(s["attempts_sum"] / s["attempts_count"], 2)
                if s["attempts_count"]
                else None
            )
            refinement_success_rate = (
                round(s["refinement_success"] / s["refinement_count"], 4)
                if s["refinement_count"]
                else None
            )

            row = {
                "llm_key": s["llm_key"],
                "run_tag": s["run_tag"],
                "provider": s["provider"],
                "model": s["model"],
                "generated": generated,
                "valid": valid,
                "invalid": invalid,
                "duplicate_skipped": s["duplicate_skipped"],
                "validity_rate": validity_rate,
                "diff_total": diff_total,
                "diff_mismatches": diff_mismatches,
                "bug_rate": bug_rate,
                "avg_generation_ms": avg_generation_ms,
                "avg_attempts": avg_attempts,
                "refinement_success_rate": refinement_success_rate,
                "error_syntax": s["errors"]["syntax"],
                "error_ssa": s["errors"]["ssa"],
                "error_type": s["errors"]["type"],
                "error_cfg": s["errors"]["cfg"],
                "error_undef": s["errors"]["undef"],
                "error_other": s["errors"]["other"],
                "error_timeout": s["errors"]["timeout"],
            }
            if include_seed:
                row["seed_name"] = s["seed_name"] or "unknown"
            return row

        stats: dict[str, dict] = {}
        per_seed_stats: dict[tuple[str, str], dict] = {}
        id_to_key: dict[str, str] = {}
        id_to_seed: dict[str, str] = {}

        for entry in raw_mutants:
            if entry.get("mutator_type") != "llm":
                continue

            mutant_id = entry.get("id") or entry.get("mutant_id")
            if not mutant_id:
                continue

            seed_name = entry.get("seed_name") or "unknown"
            llm_key, run_tag, provider, model = _infer_llm_key(entry)

            if llm_key not in stats:
                stats[llm_key] = _init_stats(llm_key, run_tag, provider, model)

            seed_key = (llm_key, seed_name)
            if seed_key not in per_seed_stats:
                per_seed_stats[seed_key] = _init_stats(llm_key, run_tag, provider, model, seed_name)

            id_to_key[mutant_id] = llm_key
            id_to_seed[mutant_id] = seed_name

            status = entry.get("status", "generated")
            _add_generation(stats[llm_key], status)
            _add_generation(per_seed_stats[seed_key], status)

            meta = entry.get("metadata") or {}
            _add_meta(stats[llm_key], meta)
            _add_meta(per_seed_stats[seed_key], meta)

        for vlog in validity_logs:
            mutant_id = vlog.get("mutant_id")
            llm_key = id_to_key.get(mutant_id)
            if not llm_key:
                continue

            seed_name = id_to_seed.get(mutant_id) or vlog.get("seed_name") or "unknown"
            seed_key = (llm_key, seed_name)
            if seed_key not in per_seed_stats:
                s = stats.get(llm_key)
                per_seed_stats[seed_key] = _init_stats(
                    llm_key,
                    s["run_tag"] if s else None,
                    s["provider"] if s else None,
                    s["model"] if s else None,
                    seed_name,
                )

            _add_validity(stats[llm_key], vlog)
            _add_validity(per_seed_stats[seed_key], vlog)

        for row in results_rows:
            mutant_id = row.get("mutant_id")
            llm_key = id_to_key.get(mutant_id)
            if not llm_key:
                continue

            seed_name = id_to_seed.get(mutant_id) or "unknown"
            seed_key = (llm_key, seed_name)
            if seed_key not in per_seed_stats:
                s = stats.get(llm_key)
                per_seed_stats[seed_key] = _init_stats(
                    llm_key,
                    s["run_tag"] if s else None,
                    s["provider"] if s else None,
                    s["model"] if s else None,
                    seed_name,
                )

            _add_diff(stats[llm_key], row)
            _add_diff(per_seed_stats[seed_key], row)

        rows = [_build_row(s) for s in stats.values()]
        rows.sort(key=lambda r: r["llm_key"])

        per_seed_rows = [_build_row(s, include_seed=True) for s in per_seed_stats.values()]
        per_seed_rows.sort(key=lambda r: (r["llm_key"], r["seed_name"]))

        csv_columns = [
            "llm_key",
            "run_tag",
            "provider",
            "model",
            "generated",
            "valid",
            "invalid",
            "duplicate_skipped",
            "validity_rate",
            "diff_total",
            "diff_mismatches",
            "bug_rate",
            "avg_generation_ms",
            "avg_attempts",
            "refinement_success_rate",
            "error_syntax",
            "error_ssa",
            "error_type",
            "error_cfg",
            "error_undef",
            "error_other",
            "error_timeout",
        ]

        with open(LLM_SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        per_seed_columns = ["seed_name"] + csv_columns
        with open(LLM_PER_SEED_SUMMARY_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=per_seed_columns)
            writer.writeheader()
            for row in per_seed_rows:
                writer.writerow(row)

        return {"llms": rows, "per_seed": per_seed_rows, "total": len(rows)}

