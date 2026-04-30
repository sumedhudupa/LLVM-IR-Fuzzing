"""
generate_mutants.py – LLM-guided and grammar-based LLVM IR mutation.
Source: CONTEXT.json → architecture.components[LLM Mutator Service]
        CONTEXT.json → architecture.data_flow steps 2–3
        CONTEXT.json → setup.environment_variables
        CONTEXT.json → database.tables[raw_mutants]

Two mutators are provided:
  LLMMutator     – calls Ollama via HTTP with targeted mutation prompts
  GrammarMutator – applies deterministic rule-based IR transforms (IRFuzzer-style)
"""
import re
import datetime
import asyncio
from pathlib import Path

import httpx

from .config import (
    OLLAMA_HOST, LLM_MODEL,
    SEED_DIR, MUTANT_DIR, GRAMMAR_DIR, LOGS_DIR, RANDOM_DIR,
    ENABLE_REFINEMENT, MAX_REFINEMENT_ATTEMPTS,
)
from .utils.rule_validation import prevalidate_ir
from .utils.fs_helpers import build_mutant_id, append_json_log
from .utils.ir_helpers import (
    extract_ir,
    is_plausible_ir,
    sanitize_ir,
    add_module_header,
    compute_ir_hash,
)
from .utils.logger import get_logger

logger = get_logger(__name__)

RAW_MUTANTS_LOG = LOGS_DIR / "raw_mutants.json"


def _log_raw_mutant(
    *,
    mutant_id: str,
    seed_name: str,
    mutator_type: str,
    strategy: str,
    seed_ir: str,
    status: str,
    path: str = "",
    content_hash: str | None = None,
    metadata: dict | None = None,
) -> None:
    entry = {
        "id": mutant_id,
        "seed_name": seed_name,
        "mutator_type": mutator_type,
        "path": path,
        "strategy": strategy,
        "seed_size_bytes": len(seed_ir.encode("utf-8")),
        "status": status,
        "content_hash": content_hash,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if metadata:
        entry["metadata"] = metadata
    append_json_log(RAW_MUTANTS_LOG, entry)


def _deduplicate_candidate(ir_text: str, seen_hashes: set[str]) -> tuple[bool, str]:
    content_hash = compute_ir_hash(ir_text)
    if content_hash in seen_hashes:
        return True, content_hash
    seen_hashes.add(content_hash)
    return False, content_hash

# ─────────────────────────────────────────────────────────────────────────────
# Mutation Strategy Definitions
# Each entry drives exactly one LLM call with a distinct instruction.
# Strategies cycle across the `count` mutants requested so each gets variety.
# ─────────────────────────────────────────────────────────────────────────────
MUTATION_STRATEGIES: list[dict] = [
    {
        "name": "arithmetic_substitution",
        "instruction": (
            "Replace exactly ONE arithmetic instruction "
            "(add, sub, mul, sdiv, udiv, srem, urem, and, or, xor) "
            "with a DIFFERENT arithmetic instruction of the same operand types. "
            "Keep all SSA value names, types, and function signatures unchanged."
        ),
    },
    {
        "name": "constant_mutation",
        "instruction": (
            "Change exactly ONE integer constant literal to a different integer value. "
            "Do not change variable names, types, or any instruction opcode. "
            "Keep the module structurally identical."
        ),
    },
    {
        "name": "icmp_predicate_change",
        "instruction": (
            "Find exactly ONE 'icmp' instruction and change its predicate to a different one "
            "(e.g. eq→ne, slt→sgt, ule→uge, sle→sge). "
            "Keep the operands and SSA result name unchanged."
        ),
    },
    {
        "name": "nop_insertion",
        "instruction": (
            "Insert exactly ONE no-op instruction into an existing basic block. "
            "A safe no-op example: '%unused_val = or i64 0, 0' (result unused). "
            "Do NOT use the inserted value as an operand anywhere. "
            "Keep all existing instructions, types, and SSA names unchanged."
        ),
    },
    {
        "name": "branch_condition_flip",
        "instruction": (
            "If the IR has a conditional branch (br i1 %cond, ...), flip the condition "
            "by negating the icmp predicate that produces %cond (eq↔ne, slt↔sgt, etc.). "
            "If there is no conditional branch, change one integer constant instead. "
            "Keep all other instructions unchanged."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# OllamaClient
# ─────────────────────────────────────────────────────────────────────────────
class OllamaClient:
    """
    Async HTTP wrapper for the Ollama /api/generate endpoint.
    Source: CONTEXT.json → setup.environment_variables[OLLAMA_HOST, LLM_MODEL]
    """

    GENERATE_PATH = "/api/generate"
    TAGS_PATH     = "/api/tags"

    def __init__(self, host: str = OLLAMA_HOST, model: str = LLM_MODEL):
        self.host  = host.rstrip("/")
        self.model = model
        self._generate_url = self.host + self.GENERATE_PATH
        self._tags_url     = self.host + self.TAGS_PATH

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        POST to /api/generate with stream=false.
        Returns the raw 'response' string from Ollama.
        Raises httpx.HTTPStatusError / httpx.RequestError on failure.
        """
        payload = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1500,   # increased to prevent truncation of main()
                "top_p":       0.90,
                "repeat_penalty": 1.1,
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.debug("POST %s  model=%s  temp=%.2f",
                         self._generate_url, self.model, temperature)
            resp = await client.post(self._generate_url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def check_alive(self) -> bool:
        """Return True if Ollama is reachable and responding."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(self._tags_url)
                return r.status_code == 200
        except Exception:
            return False

    async def model_available(self) -> bool:
        """Return True if LLM_MODEL is pulled and listed by Ollama."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(self._tags_url)
                r.raise_for_status()
                names = [m["name"] for m in r.json().get("models", [])]
                return any(self.model in n for n in names)
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# LLMMutator
# ─────────────────────────────────────────────────────────────────────────────
class LLMMutator:
    """
    Orchestrates LLM-guided LLVM IR mutation using Ollama.
    Source: CONTEXT.json → architecture.components[LLM Mutator Service]
            CONTEXT.json → architecture.data_flow step 2
    """

    def __init__(self):
        self.client = OllamaClient()

    # ── Prompt construction ──────────────────────────────────────────────────

    def _build_prompt(self, seed_ir: str, strategy: dict) -> str:
        """
        Build a tightly scoped mutation prompt for a small LLM
        (qwen3:1.5b or gemma3:1b as specified in CONTEXT.json).
        The prompt is intentionally concise to fit small context windows.
        """
        return (
            "You are an LLVM IR expert and mutation tool.\n"
            "Task: Apply exactly ONE mutation to the provided LLVM IR module.\n\n"
            "CONSTRAINTS (CRITICAL):\n"
            "- Output ONLY the complete mutated LLVM IR module.\n"
            "- No explanations, no markdown prose, no headers outside the code fence.\n"
            "- Use ONLY ';' for comments. DO NOT use '//'.\n"
            "- Use ONLY standard LLVM opcodes (e.g. 'add', NOT 'addq' or 'addl').\n"
            "- DO NOT use inline arithmetic in operands (e.g. '%b+1' is INVALID). Use a new instruction instead.\n"
            "- All basic block references in 'phi' or 'br' instructions MUST start with '%' (e.g. '[ %val, %entry ]', NOT '[ %val, entry ]').\n"
            "- Ensure newly created variables have unique names and are correctly used.\n"
            "- Maintain valid SSA form (every %value defined before use).\n"
            "- Do NOT truncate the output; provide the FULL module even if only one line changed.\n\n"
            "EXAMPLE MUTATION (Arithmetic Substitution):\n"
            "Input: %res = add i64 %a, 1\n"
            "Mutation: %res = sub i64 %a, 1\n\n"
            f"MUTATION TO APPLY:\n{strategy['instruction']}\n\n"
            "ORIGINAL LLVM IR:\n"
            "```llvm\n"
            f"{seed_ir}\n"
            "```\n\n"
            "MUTATED LLVM IR:"
        )

    # ── Prompt construction with error feedback ──────────────────────────────

    def _build_refinement_prompt(self, seed_ir: str, strategy: dict,
                                  error_messages: list[str]) -> str:
        """
        Build a refinement prompt that includes previous error messages to guide correction.
        Source: requirements.md → Requirement 2, Criterion 3
        """
        error_context = "\n".join(f"  - {err}" for err in error_messages)
        return (
            "You are an LLVM IR expert and mutation tool.\n"
            "Task: Apply exactly ONE mutation to the provided LLVM IR module.\n\n"
            "PREVIOUS ATTEMPT ERRORS (fix these issues):\n"
            f"{error_context}\n\n"
            "CONSTRAINTS (CRITICAL):\n"
            "- Output ONLY the complete mutated LLVM IR module.\n"
            "- No explanations, no markdown prose, no headers outside the code fence.\n"
            "- Use ONLY ';' for comments. DO NOT use '//'.\n"
            "- Use ONLY standard LLVM opcodes (e.g. 'add', NOT 'addq' or 'addl').\n"
            "- DO NOT use inline arithmetic in operands (e.g. '%b+1' is INVALID). Use a new instruction instead.\n"
            "- All basic block references in 'phi' or 'br' instructions MUST start with '%' (e.g. '[ %val, %entry ]', NOT '[ %val, entry ]').\n"
            "- Ensure newly created variables have unique names and are correctly used.\n"
            "- Maintain valid SSA form (every %value defined before use).\n"
            "- Do NOT truncate the output; provide the FULL module even if only one line changed.\n\n"
            "EXAMPLE MUTATION (Arithmetic Substitution):\n"
            "Input: %res = add i64 %a, 1\n"
            "Mutation: %res = sub i64 %a, 1\n\n"
            f"MUTATION TO APPLY:\n{strategy['instruction']}\n\n"
            "ORIGINAL LLVM IR:\n"
            "```llvm\n"
            f"{seed_ir}\n"
            "```\n\n"
            "MUTATED LLVM IR:"
        )

    # ── Single mutant generation ─────────────────────────────────────────────

    async def _generate_one(
        self,
        seed_ir:    str,
        seed_name:  str,
        mutant_id:  str,
        strategy:   dict,
        temperature: float,
        enable_refinement: bool = False,
        max_attempts: int = 3,
    ) -> tuple[str, bool, dict]:
        """
        Attempt to generate one mutant via Ollama with optional refinement loop.

        Args:
            enable_refinement: If True, retry failed generations with error feedback
            max_attempts: Maximum number of refinement attempts

        Returns:
            (ir_text, True, metadata)       on success
            (error_msg, False, metadata)    on failure
        """
        errors: list[str] = []
        attempt_metadata = []
        base_temperature = temperature

        for attempt in range(1, max_attempts + 1 if enable_refinement else 1):
            # Increase temperature on retries for more diversity
            current_temp = base_temperature + (0.1 * (attempt - 1)) if attempt > 1 else base_temperature

            # Build prompt with or without error feedback
            if attempt == 1:
                prompt = self._build_prompt(seed_ir, strategy)
            else:
                prompt = self._build_refinement_prompt(seed_ir, strategy, errors)

            try:
                logger.info(
                    "Ollama call | mutant=%s  strategy=%s  model=%s  temp=%.2f  attempt=%d/%d",
                    mutant_id, strategy["name"], self.client.model, current_temp,
                    attempt, max_attempts if enable_refinement else 1,
                )
                raw = await self.client.generate(prompt, temperature=current_temp)
            except httpx.HTTPStatusError as exc:
                logger.error("Ollama HTTP %s for %s: %s",
                             exc.response.status_code, mutant_id, exc)
                error_msg = f"HTTP error {exc.response.status_code}"
                errors.append(error_msg)
                attempt_metadata.append({
                    "attempt_number": attempt,
                    "validation_result": "failed",
                    "error": error_msg,
                })
                continue
            except httpx.RequestError as exc:
                logger.error("Ollama connection error for %s: %s", mutant_id, exc)
                error_msg = f"Connection error: {exc}"
                errors.append(error_msg)
                attempt_metadata.append({
                    "attempt_number": attempt,
                    "validation_result": "failed",
                    "error": error_msg,
                })
                continue

            # ── Extract and Sanitize IR ──────────────────────────────────────
            ir = extract_ir(raw)
            if ir is None:
                logger.warning("No IR extracted from Ollama response for %s", mutant_id)
                logger.debug("Raw response snippet: %.300s", raw)
                error_msg = "IR extraction failed"
                errors.append(error_msg)
                attempt_metadata.append({
                    "attempt_number": attempt,
                    "validation_result": "failed",
                    "error": error_msg,
                })
                continue

            ir = sanitize_ir(ir)

            # ── Basic plausibility gate ──────────────────────────────────────
            if not is_plausible_ir(ir):
                logger.warning("Plausibility check failed for %s", mutant_id)
                logger.debug("Extracted candidate: %.300s", ir)
                error_msg = "IR plausibility check failed"
                errors.append(error_msg)
                attempt_metadata.append({
                    "attempt_number": attempt,
                    "validation_result": "failed",
                    "error": error_msg,
                })
                continue

            # ── Rule-based pre-validation (if refinement enabled) ────────────
            if enable_refinement:
                rule_result = prevalidate_ir(ir)
                if not rule_result.is_valid:
                    error_msg = "; ".join(rule_result.issues)
                    errors.append(error_msg)
                    attempt_metadata.append({
                        "attempt_number": attempt,
                        "validation_result": "failed",
                        "error": error_msg,
                        "error_type": rule_result.error_type,
                    })
                    logger.warning("Refinement attempt %d failed for %s: %s",
                                   attempt, mutant_id, error_msg)
                    continue  # Retry with error feedback

            ir = add_module_header(ir, seed_name)

            # Record success metadata
            attempt_metadata.append({
                "attempt_number": attempt,
                "validation_result": "success",
            })

            refinement_metadata = {
                "attempts_made": attempt,
                "refinement_succeeded": attempt > 1,
                "attempt_details": attempt_metadata,
            }
            return ir, True, refinement_metadata

        # All attempts failed
        refinement_metadata = {
            "attempts_made": max_attempts if enable_refinement else 1,
            "refinement_succeeded": False,
            "attempt_details": attempt_metadata,
        }
        return errors[-1] if errors else "All attempts failed", False, refinement_metadata

    # ── Main pipeline ────────────────────────────────────────────────────────

    async def run(self, seed_name: str, count: int) -> list[str]:
        """
        Full LLM mutation pipeline for one seed file.

        Steps (per CONTEXT.json architecture.data_flow step 2):
          1. Read seed_name from SEED_DIR.
          2. Verify Ollama is reachable.
          3. For each of `count` mutants:
             a. Pick a mutation strategy (round-robin through MUTATION_STRATEGIES).
             b. Vary temperature for output diversity.
             c. Call Ollama, extract IR, check plausibility.
             d. Write mutant to MUTANT_DIR/{mutant_id}.ll.
             e. Log entry to logs/raw_mutants.json per CONTEXT.json schema.
          4. Return list of successfully written mutant IDs.

        Raises:
            FileNotFoundError  – seed file missing
            RuntimeError       – Ollama unreachable
        """
        seed_path = SEED_DIR / seed_name
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_path}")

        seed_ir = seed_path.read_text(encoding="utf-8")
        logger.info("Seed loaded: '%s'  (%d bytes)", seed_name, len(seed_ir))

        # ── Ollama reachability check ─────────────────────────────────────────
        if not await self.client.check_alive():
            raise RuntimeError(
                f"Ollama not reachable at {self.client.host}. "
                "Ensure Ollama is running (ollama serve) and OLLAMA_HOST is correct."
            )
        if not await self.client.model_available():
            logger.warning(
                "Model '%s' not found in Ollama – it may need to be pulled first: "
                "ollama pull %s", self.client.model, self.client.model,
            )

        written_ids: list[str] = []
        failed_count = 0
        seen_hashes: set[str] = set()

        for i in range(count):
            strategy    = MUTATION_STRATEGIES[i % len(MUTATION_STRATEGIES)]
            mutant_id   = build_mutant_id(seed_name, "llm", i)
            # Gradually raise temperature for more diverse outputs
            temperature = round(min(0.60 + i * 0.05, 0.90), 2)

            ir_text, ok, metadata = await self._generate_one(
                seed_ir,
                seed_name,
                mutant_id,
                strategy,
                temperature,
                enable_refinement=ENABLE_REFINEMENT,
                max_attempts=MAX_REFINEMENT_ATTEMPTS,
            )
            if ok:
                is_duplicate, content_hash = _deduplicate_candidate(ir_text, seen_hashes)
                if is_duplicate:
                    logger.info("Skipping duplicate LLM mutant %s (hash=%s)", mutant_id, content_hash)
                    _log_raw_mutant(
                        mutant_id=mutant_id,
                        seed_name=seed_name,
                        mutator_type="llm",
                        strategy=strategy["name"],
                        seed_ir=seed_ir,
                        status="duplicate_skipped",
                        content_hash=content_hash,
                        metadata=metadata,
                    )
                    continue
                out_path = MUTANT_DIR / f"{mutant_id}.ll"
                out_path.write_text(ir_text, encoding="utf-8")
                logger.info("Written: %s  (%d bytes)", out_path, len(ir_text))
                written_ids.append(mutant_id)
                _log_raw_mutant(
                    mutant_id=mutant_id,
                    seed_name=seed_name,
                    mutator_type="llm",
                    strategy=strategy["name"],
                    seed_ir=seed_ir,
                    status="generated",
                    path=str(out_path),
                    content_hash=content_hash,
                    metadata=metadata,
                )
            else:
                failed_count += 1
                logger.warning("Failed mutant %s: %s", mutant_id, ir_text)
                _log_raw_mutant(
                    mutant_id=mutant_id,
                    seed_name=seed_name,
                    mutator_type="llm",
                    strategy=strategy["name"],
                    seed_ir=seed_ir,
                    status="failed",
                    metadata=metadata,
                )

            # ── Log per CONTEXT.json database.tables[raw_mutants] schema ───────

        logger.info(
            "LLMMutator done: %d/%d succeeded for seed '%s'",
            len(written_ids), count, seed_name,
        )
        return written_ids


# ─────────────────────────────────────────────────────────────────────────────
# GrammarMutator  (IRFuzzer-style deterministic rule-based transforms)
# ─────────────────────────────────────────────────────────────────────────────
class GrammarMutator:
    """
    Deterministic rule-based LLVM IR mutator.
    Source: CONTEXT.json → architecture.components[LLM Mutator Service]
            (described as "IRFuzzer-style" grammar-based mutation)
            CONTEXT.json → setup.environment_variables[GRAMMAR_DIR]

    Applies three families of transforms, selected by (index % 3):
      0 → arithmetic_substitution  (opcode swap)
      1 → icmp_predicate_flip
      2 → constant_perturbation
    """

    # ── Arithmetic opcode swap tables ────────────────────────────────────────
    # Pairs are: (regex_to_match_in_IR, replacement_opcode)
    # Only opcodes with identical operand-type constraints are swapped.
    _ARITH_SWAPS: list[tuple[str, str]] = [
        (r"\badd\b",  "sub"),
        (r"\bsub\b",  "add"),
        (r"\bmul\b",  "sdiv"),
        (r"\bsdiv\b", "mul"),
        (r"\budiv\b", "urem"),
        (r"\burem\b", "udiv"),
        (r"\bsrem\b", "sdiv"),
        (r"\band\b",  "or"),
        (r"\bor\b",   "and"),
        (r"\bxor\b",  "or"),
    ]

    # ── icmp predicate flip pairs ─────────────────────────────────────────────
    _ICMP_FLIPS: list[tuple[str, str]] = [
        ("eq",  "ne"),  ("ne",  "eq"),
        ("slt", "sgt"), ("sgt", "slt"),
        ("sle", "sge"), ("sge", "sle"),
        ("ult", "ugt"), ("ugt", "ult"),
        ("ule", "uge"), ("uge", "ule"),
    ]

    # ── Integer constant regex ────────────────────────────────────────────────
    # Matches bare integers that appear as instruction operands.
    # Avoids matching integers inside '%' names or inside type declarations.
    _CONST_RE = re.compile(r"(?<![%\w])(\b\d+\b)(?![\w*\[\]])")

    # ── Strategy dispatch ─────────────────────────────────────────────────────

    def _arith_swap(self, ir: str, index: int) -> str:
        """Replace the first occurrence of one arithmetic opcode with another."""
        pattern, replacement = self._ARITH_SWAPS[index % len(self._ARITH_SWAPS)]
        return re.sub(pattern, replacement, ir, count=1)

    def _icmp_flip(self, ir: str, index: int) -> str:
        """Flip the predicate of the first icmp instruction found."""
        src, dst = self._ICMP_FLIPS[index % len(self._ICMP_FLIPS)]
        return re.sub(rf"\bicmp {re.escape(src)}\b", f"icmp {dst}", ir, count=1)

    def _const_perturb(self, ir: str, index: int) -> str:
        """
        Increment one integer constant by a small offset (1–3).
        Skips constants in metadata lines (starting with '!').
        """
        # Filter out metadata lines to avoid perturbing debug info
        lines = ir.splitlines()
        non_meta = [
            (i, l) for i, l in enumerate(lines)
            if not l.strip().startswith("!")
        ]
        matches: list[tuple[int, re.Match]] = []
        for line_i, line in non_meta:
            for m in self._CONST_RE.finditer(line):
                matches.append((line_i, m))

        if not matches:
            return ir  # nothing to perturb; return unchanged

        target_line_i, target_match = matches[index % len(matches)]
        original_val = int(target_match.group())
        delta        = (index % 3) + 1      # delta ∈ {1, 2, 3}
        new_val      = str(original_val + delta)

        line      = lines[target_line_i]
        new_line  = (
            line[:target_match.start()]
            + new_val
            + line[target_match.end():]
        )
        lines[target_line_i] = new_line
        return "\n".join(lines)

    def _mutate_one(self, seed_ir: str, index: int) -> tuple[str, str]:
        """
        Apply one grammar rule keyed by index.
        Returns (mutated_ir, strategy_name).
        """
        strategy_id = index % 3
        if strategy_id == 0:
            return self._arith_swap(seed_ir, index),    "arithmetic_substitution"
        elif strategy_id == 1:
            return self._icmp_flip(seed_ir, index),     "icmp_predicate_flip"
        else:
            return self._const_perturb(seed_ir, index), "constant_perturbation"

    # ── Main pipeline ────────────────────────────────────────────────────────

    def run(self, seed_name: str, count: int) -> list[str]:
        """
        Apply grammar mutations to one seed and write results to GRAMMAR_DIR.

        Steps (per CONTEXT.json architecture.data_flow step 2, grammar branch):
          1. Read seed_name from SEED_DIR.
          2. For each of `count` indices, apply a deterministic rule.
          3. Write mutant to GRAMMAR_DIR/{mutant_id}.ll.
          4. Log to logs/raw_mutants.json per CONTEXT.json schema.
          5. Return list of mutant IDs.

        Raises:
            FileNotFoundError – seed file missing
        """
        seed_path = SEED_DIR / seed_name
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_path}")

        seed_ir   = seed_path.read_text(encoding="utf-8")
        logger.info("GrammarMutator: seed='%s'  count=%d", seed_name, count)

        written_ids: list[str] = []
        seen_hashes: set[str] = set()

        for i in range(count):
            mutant_id       = build_mutant_id(seed_name, "grammar", i)
            mutant_ir, strat = self._mutate_one(seed_ir, i)
            mutant_ir       = add_module_header(mutant_ir, seed_name)
            is_duplicate, content_hash = _deduplicate_candidate(mutant_ir, seen_hashes)
            if is_duplicate:
                logger.info("Skipping duplicate grammar mutant %s (hash=%s)", mutant_id, content_hash)
                _log_raw_mutant(
                    mutant_id=mutant_id,
                    seed_name=seed_name,
                    mutator_type="grammar",
                    strategy=strat,
                    seed_ir=seed_ir,
                    status="duplicate_skipped",
                    content_hash=content_hash,
                )
                continue

            out_path = GRAMMAR_DIR / f"{mutant_id}.ll"
            out_path.write_text(mutant_ir, encoding="utf-8")
            logger.info("Grammar mutant written: %s  strategy=%s", out_path, strat)
            written_ids.append(mutant_id)
            _log_raw_mutant(
                mutant_id=mutant_id,
                seed_name=seed_name,
                mutator_type="grammar",
                strategy=strat,
                seed_ir=seed_ir,
                status="generated",
                path=str(out_path),
                content_hash=content_hash,
            )

            # ── Log per CONTEXT.json database.tables[raw_mutants] schema ───

        logger.info("GrammarMutator done: %d mutants for seed '%s'",
                    len(written_ids), seed_name)
        return written_ids


# ─────────────────────────────────────────────────────────────────────────────
# RandomMutator – Non-grammar-aware random mutations
# ─────────────────────────────────────────────────────────────────────────────
class RandomMutator:
    """
    Random (non-grammar-aware) LLVM IR mutator for baseline comparison.
    Source: requirements.md → Requirement 1: Random Mutation Baseline

    Implements five mutation strategies:
      1. random_char_flip – flips a single character to another
      2. random_line_delete – deletes one line
      3. random_line_duplicate – duplicates one line
      4. random_line_swap – swaps two adjacent lines
      5. random_word_replace – replaces a word with a similar one
    """

    RANDOM_STRATEGIES: list[dict] = [
        {"name": "random_char_flip"},
        {"name": "random_line_delete"},
        {"name": "random_line_duplicate"},
        {"name": "random_line_swap"},
        {"name": "random_word_replace"},
    ]

    def __init__(self):
        self.rng = __import__('random').Random()

    def _random_char_flip(self, ir: str, index: int) -> str:
        """Flip one character to a different character."""
        if not ir:
            return ir
        lines = ir.splitlines()
        # Filter non-empty lines
        non_empty = [(i, line) for i, line in enumerate(lines) if line.strip()]
        if not non_empty:
            return ir
        line_idx, line = non_empty[index % len(non_empty)]
        if not line:
            return ir
        char_idx = index % len(line)
        # Flip to a different character
        original = line[char_idx]
        replacements = [c for c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' if c != original]
        if not replacements:
            return ir
        new_char = self.rng.choice(replacements)
        lines[line_idx] = line[:char_idx] + new_char + line[char_idx + 1:]
        return '\n'.join(lines)

    def _random_line_delete(self, ir: str, index: int) -> str:
        """Delete one line from the IR."""
        lines = ir.splitlines()
        # Don't delete metadata lines or empty lines
        deletable = [i for i, line in enumerate(lines)
                     if line.strip() and not line.strip().startswith('!') and not line.strip().startswith(';')]
        if not deletable:
            return ir
        line_idx = deletable[index % len(deletable)]
        return '\n'.join(lines[:line_idx] + lines[line_idx + 1:])

    def _random_line_duplicate(self, ir: str, index: int) -> str:
        """Duplicate one line in the IR."""
        lines = ir.splitlines()
        # Only duplicate non-metadata, non-empty lines
        duplicable = [i for i, line in enumerate(lines)
                      if line.strip() and not line.strip().startswith('!') and not line.strip().startswith(';')]
        if not duplicable:
            return ir
        line_idx = duplicable[index % len(duplicable)]
        return '\n'.join(lines[:line_idx + 1] + [lines[line_idx]] + lines[line_idx + 1:])

    def _random_line_swap(self, ir: str, index: int) -> str:
        """Swap two adjacent lines in the IR."""
        lines = ir.splitlines()
        if len(lines) < 2:
            return ir
        # Find swappable pairs (both non-empty, non-metadata)
        swappable_pairs = []
        for i in range(len(lines) - 1):
            if (lines[i].strip() and lines[i + 1].strip() and
                not lines[i].strip().startswith('!') and not lines[i + 1].strip().startswith('!')):
                swappable_pairs.append(i)
        if not swappable_pairs:
            return ir
        line_idx = swappable_pairs[index % len(swappable_pairs)]
        lines[line_idx], lines[line_idx + 1] = lines[line_idx + 1], lines[line_idx]
        return '\n'.join(lines)

    def _random_word_replace(self, ir: str, index: int) -> str:
        """Replace one word with a similar-looking word."""
        # Common LLVM keywords that can be swapped
        replacements = {
            'add': 'sub', 'sub': 'add', 'mul': 'div', 'div': 'mul',
            'eq': 'ne', 'ne': 'eq', 'slt': 'sgt', 'sgt': 'slt',
            'and': 'or', 'or': 'and', 'xor': 'and',
            'load': 'store', 'store': 'load',
            'icmp': 'fcmp', 'fcmp': 'icmp',
            'alloca': 'malloc', 'malloc': 'alloca',
        }
        for old_word, new_word in replacements.items():
            if old_word in ir:
                return ir.replace(old_word, new_word, 1)
        # Fallback: just return original if no replacements found
        return ir

    def _mutate_one(self, seed_ir: str, index: int) -> tuple[str, str]:
        """
        Apply one random mutation strategy.
        Returns (mutated_ir, strategy_name).
        """
        strategy_id = index % 5
        strategy = self.RANDOM_STRATEGIES[strategy_id]

        if strategy["name"] == "random_char_flip":
            return self._random_char_flip(seed_ir, index), strategy["name"]
        elif strategy["name"] == "random_line_delete":
            return self._random_line_delete(seed_ir, index), strategy["name"]
        elif strategy["name"] == "random_line_duplicate":
            return self._random_line_duplicate(seed_ir, index), strategy["name"]
        elif strategy["name"] == "random_line_swap":
            return self._random_line_swap(seed_ir, index), strategy["name"]
        else:  # random_word_replace
            return self._random_word_replace(seed_ir, index), strategy["name"]

    def run(self, seed_name: str, count: int) -> list[str]:
        """
        Apply random mutations to one seed and write results to RANDOM_DIR.

        Steps:
          1. Read seed_name from SEED_DIR.
          2. For each of `count` indices, apply a random mutation.
          3. Write mutant to RANDOM_DIR/{mutant_id}.ll.
          4. Log to logs/raw_mutants.json per schema.
          5. Return list of mutant IDs.

        Raises:
            FileNotFoundError – seed file missing
        """
        seed_path = SEED_DIR / seed_name
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_path}")

        seed_ir = seed_path.read_text(encoding="utf-8")
        logger.info("RandomMutator: seed='%s'  count=%d", seed_name, count)

        written_ids: list[str] = []
        seen_hashes: set[str] = set()

        for i in range(count):
            mutant_id = build_mutant_id(seed_name, "random", i)
            mutant_ir, strategy = self._mutate_one(seed_ir, i)
            mutant_ir = add_module_header(mutant_ir, seed_name)
            is_duplicate, content_hash = _deduplicate_candidate(mutant_ir, seen_hashes)
            if is_duplicate:
                logger.info("Skipping duplicate random mutant %s (hash=%s)", mutant_id, content_hash)
                _log_raw_mutant(
                    mutant_id=mutant_id,
                    seed_name=seed_name,
                    mutator_type="random",
                    strategy=strategy,
                    seed_ir=seed_ir,
                    status="duplicate_skipped",
                    content_hash=content_hash,
                )
                continue

            out_path = RANDOM_DIR / f"{mutant_id}.ll"
            out_path.write_text(mutant_ir, encoding="utf-8")
            logger.info("Random mutant written: %s  strategy=%s", out_path, strategy)
            written_ids.append(mutant_id)
            _log_raw_mutant(
                mutant_id=mutant_id,
                seed_name=seed_name,
                mutator_type="random",
                strategy=strategy,
                seed_ir=seed_ir,
                status="generated",
                path=str(out_path),
                content_hash=content_hash,
            )

            # Log per schema

        logger.info("RandomMutator done: %d mutants for seed '%s'",
                    len(written_ids), seed_name)
        return written_ids


# ─────────────────────────────────────────────────────────────────────────────
# Convenience wrappers (kept for backward compatibility with existing callers)
# ─────────────────────────────────────────────────────────────────────────────

async def generate_llm_mutants(seed_name: str, count: int = 5) -> list[str]:
    """Async wrapper around LLMMutator.run()."""
    return await LLMMutator().run(seed_name, count)


def generate_grammar_mutants(seed_name: str, count: int = 5) -> list[str]:
    """Sync wrapper around GrammarMutator.run()."""
    return GrammarMutator().run(seed_name, count)


def generate_random_mutants(seed_name: str, count: int = 5) -> list[str]:
    """Sync wrapper around RandomMutator.run()."""
    return RandomMutator().run(seed_name, count)
