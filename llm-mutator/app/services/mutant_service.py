"""
app/services/mutant_service.py
Service layer for mutation generation and validity filtering.
Source: CONTEXT.json → architecture.components[LLM Mutator Service]
        CONTEXT.json → architecture.components[Validity Filter]
        CONTEXT.json → architecture.data_flow steps 2 and 3
        CONTEXT.json → database.tables[raw_mutants]
        CONTEXT.json → database.tables[validity_logs]
"""
import datetime
from app.config import SEED_DIR
from app.models.mutants import (
    GenerateMutantsRequest,
    GenerateMutantsResponse,
    ValidateMutantsRequest,
    ValidateMutantsResponse,
    MutantValidationResult,
)
from app.generate_mutants import LLMMutator, GrammarMutator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MutantService:
    """
    Orchestrates the two mutation pipelines and validity filtering.

    Responsibilities (per CONTEXT.json architecture.components):
      - LLM Mutator Service : LLMMutator  → Ollama HTTP, writes to MUTANT_DIR
      - Grammar Mutator     : GrammarMutator → rule-based, writes to GRAMMAR_DIR
      - Validity Filter     : llvm-as + opt -passes=verify -disable-output (Phase 3)
    """

    # ── Generation ───────────────────────────────────────────────────────────

    @staticmethod
    async def generate(req: GenerateMutantsRequest) -> GenerateMutantsResponse:
        """
        Dispatch to the appropriate mutator based on req.mutator_type.

        LLM branch  (mutator_type='llm'):
          - Instantiates LLMMutator, calls Ollama via OLLAMA_HOST.
          - Cycles through 5 mutation strategies (arithmetic_substitution,
            constant_mutation, icmp_predicate_change, nop_insertion,
            branch_condition_flip).
          - Writes .ll files to MUTANT_DIR; logs to logs/raw_mutants.json.
          Source: CONTEXT.json → architecture.components[LLM Mutator Service]
                  CONTEXT.json → architecture.data_flow step 2

        Grammar branch (mutator_type='grammar'):
          - Instantiates GrammarMutator, applies deterministic rule-based
            transforms (arith swap, icmp flip, constant perturbation).
          - Writes .ll files to GRAMMAR_DIR; logs to logs/raw_mutants.json.
          Source: CONTEXT.json → architecture.components[LLM Mutator Service]
                  (described as IRFuzzer-style mutation)

        Raises:
            FileNotFoundError  – seed file not in SEED_DIR
            RuntimeError       – Ollama unreachable (LLM branch only)
        """
        if req.mutator_type == "llm":
            mutator  = LLMMutator()
            # LLMMutator.run() is async (uses httpx)
            written_ids = await mutator.run(req.seed_name, req.count)
        else:
            # GrammarMutator.run() is sync; wrap to keep interface uniform
            mutator     = GrammarMutator()
            written_ids = mutator.run(req.seed_name, req.count)

        status = "generated" if written_ids else "failed"
        logger.info(
            "generate: mutator=%s  seed=%s  requested=%d  written=%d",
            req.mutator_type, req.seed_name, req.count, len(written_ids),
        )

        return GenerateMutantsResponse(
            seed_name     = req.seed_name,
            mutator_type  = req.mutator_type,
            mutant_count  = len(written_ids),
            mutant_ids    = written_ids,
            status        = status,
        )

    # ── Validation ───────────────────────────────────────────────────────────

    @staticmethod
    async def validate(req: ValidateMutantsRequest) -> ValidateMutantsResponse:
        """
        Run llvm-as + opt -passes=verify -disable-output on each mutant_id in req.mutant_ids.
        Source: CONTEXT.json → architecture.components[Validity Filter]
        """
        from app.filter_valid import validate_batch
        
        logger.info("validate: starting batch for %d mutant(s)", len(req.mutant_ids))
        results = validate_batch(req.mutant_ids)
        
        # Convert dict results to MutantValidationResult models
        from app.models.mutants import MutantValidationResult
        model_results = [MutantValidationResult(**r) for r in results]
        
        return ValidateMutantsResponse(results=model_results)
