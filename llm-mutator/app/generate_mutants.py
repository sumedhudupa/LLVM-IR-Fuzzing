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
    SEED_DIR, MUTANT_DIR, GRAMMAR_DIR, LOGS_DIR,
)
from .utils.fs_helpers import build_mutant_id, append_json_log
from .utils.ir_helpers import extract_ir, is_plausible_ir, sanitize_ir, add_module_header
from .utils.logger import get_logger

logger = get_logger(__name__)

RAW_MUTANTS_LOG = LOGS_DIR / "raw_mutants.json"

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

    # ── Single mutant generation ─────────────────────────────────────────────

    async def _generate_one(
        self,
        seed_ir:    str,
        seed_name:  str,
        mutant_id:  str,
        strategy:   dict,
        temperature: float,
    ) -> tuple[str, bool]:
        """
        Attempt to generate one mutant via Ollama.

        Returns:
            (ir_text, True)       on success  – ir_text is the mutated IR
            (error_msg, False)    on failure  – error_msg is a diagnostic string
        """
        prompt = self._build_prompt(seed_ir, strategy)

        try:
            logger.info(
                "Ollama call | mutant=%s  strategy=%s  model=%s  temp=%.2f",
                mutant_id, strategy["name"], self.client.model, temperature,
            )
            raw = await self.client.generate(prompt, temperature=temperature)
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP %s for %s: %s",
                         exc.response.status_code, mutant_id, exc)
            return f"HTTP error {exc.response.status_code}", False
        except httpx.RequestError as exc:
            logger.error("Ollama connection error for %s: %s", mutant_id, exc)
            return f"Connection error: {exc}", False

        # ── Extract and Sanitize IR ──────────────────────────────────────────
        ir = extract_ir(raw)
        if ir is None:
            logger.warning("No IR extracted from Ollama response for %s", mutant_id)
            logger.debug("Raw response snippet: %.300s", raw)
            return "IR extraction failed", False

        ir = sanitize_ir(ir)

        # ── Basic plausibility gate (full parse is done later by llvm-as) ────
        if not is_plausible_ir(ir):
            logger.warning("Plausibility check failed for %s", mutant_id)
            logger.debug("Extracted candidate: %.300s", ir)
            return "IR plausibility check failed", False

        ir = add_module_header(ir, seed_name)
        return ir, True

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

        for i in range(count):
            strategy    = MUTATION_STRATEGIES[i % len(MUTATION_STRATEGIES)]
            mutant_id   = build_mutant_id(seed_name, "llm", i)
            # Gradually raise temperature for more diverse outputs
            temperature = round(min(0.60 + i * 0.05, 0.90), 2)

            ir_text, ok = await self._generate_one(
                seed_ir, seed_name, mutant_id, strategy, temperature
            )

            created_at = datetime.datetime.utcnow().isoformat() + "Z"

            if ok:
                out_path = MUTANT_DIR / f"{mutant_id}.ll"
                out_path.write_text(ir_text, encoding="utf-8")
                logger.info("Written: %s  (%d bytes)", out_path, len(ir_text))
                written_ids.append(mutant_id)
            else:
                failed_count += 1
                logger.warning("Failed mutant %s: %s", mutant_id, ir_text)

            # ── Log per CONTEXT.json database.tables[raw_mutants] schema ───────
            append_json_log(
                RAW_MUTANTS_LOG,
                {
                    "id":           mutant_id,
                    "seed_name":    seed_name,
                    "mutator_type": "llm",
                    "path": str(MUTANT_DIR / f"{mutant_id}.ll") if ok else "",
                    "strategy":     strategy["name"],
                    "status":       "generated" if ok else "failed",
                    "created_at":   created_at,
                },
            )

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

        for i in range(count):
            mutant_id       = build_mutant_id(seed_name, "grammar", i)
            mutant_ir, strat = self._mutate_one(seed_ir, i)
            mutant_ir       = add_module_header(mutant_ir, seed_name)

            out_path = GRAMMAR_DIR / f"{mutant_id}.ll"
            out_path.write_text(mutant_ir, encoding="utf-8")
            logger.info("Grammar mutant written: %s  strategy=%s", out_path, strat)
            written_ids.append(mutant_id)

            # ── Log per CONTEXT.json database.tables[raw_mutants] schema ───
            append_json_log(
                RAW_MUTANTS_LOG,
                {
                    "id":           mutant_id,
                    "seed_name":    seed_name,
                    "mutator_type": "grammar",
                    "path":         str(out_path),
                    "strategy":     strat,
                    "status":       "generated",
                    "created_at":   datetime.datetime.utcnow().isoformat() + "Z",
                },
            )

        logger.info("GrammarMutator done: %d mutants for seed '%s'",
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
