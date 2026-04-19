"""
app/utils/ir_helpers.py
Utilities for extracting and validating LLVM IR text from LLM responses.
Source: CONTEXT.json → architecture.components[LLM Mutator Service]
        CONTEXT.json → architecture.components[Validity Filter]
"""
import re

# Tokens that must appear in any plausible LLVM IR module
_REQUIRED_TOKENS = ("define ", "@", "{", "}")

# Patterns for code-fence extraction (ordered by specificity)
_FENCE_PATTERNS = [
    re.compile(r"```llvm\s*\n(.*?)```", re.DOTALL),   # ```llvm ... ```
    re.compile(r"```ir\s*\n(.*?)```",   re.DOTALL),   # ```ir   ... ```
    re.compile(r"```\s*\n(.*?)```",     re.DOTALL),   # ```     ... ```
]

# Lines that signal the start of an LLVM IR module
_IR_START_TOKENS = (
    "; ModuleID",
    "target datalayout",
    "target triple",
    "define ",
    "@",
)

# Regex to strip <think>...</think> blocks (qwen3 chain-of-thought)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def strip_thinking_tags(text: str) -> str:
    """
    Remove <think>…</think> reasoning blocks emitted by qwen3 and similar
    models before returning the actual completion text.
    """
    return _THINK_RE.sub("", text).strip()


def extract_ir(response_text: str) -> str | None:
    """
    Extract a LLVM IR module string from a raw LLM response.

    Strategy (in order):
      1. Look for a ```llvm / ```ir / ``` code fence.
      2. Fallback: find the first recognisable IR line and take all text from there.
      3. Return None if nothing plausible is found.
    """
    text = strip_thinking_tags(response_text)

    # ── 1. Code-fence extraction ──────────────────────────────────────────────
    for pattern in _FENCE_PATTERNS:
        m = pattern.search(text)
        if m:
            candidate = m.group(1).strip()
            if candidate:
                return candidate

    # ── 2. Heuristic line-search fallback ─────────────────────────────────────
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(tok) for tok in _IR_START_TOKENS):
            candidate = "\n".join(lines[i:]).strip()
            if candidate:
                return candidate

    return None


def is_plausible_ir(text: str) -> bool:
    """
    Lightweight structural check – does this text look like a LLVM IR module?
    This is NOT a full parse; llvm-as handles that.  We just gate out obvious
    garbage (empty strings, markdown prose, error messages, etc.).

    Checks:
      - Non-trivial length (≥ 30 chars)
      - Contains all of: "define ", "@", "{", "}"
      - Does NOT consist entirely of prose (heuristic: ratio of IR-ish chars)
    """
    if not text or len(text.strip()) < 30:
        return False

    for token in _REQUIRED_TOKENS:
        if token not in text:
            return False

    # Reject if the first non-blank line looks like a natural-language sentence
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if first_line.endswith(".") and not first_line.startswith(";"):
        return False

    return True


def add_module_header(ir: str, seed_name: str) -> str:
    """
    Ensure the IR starts with a ModuleID comment (cosmetic, not required by
    llvm-as, but makes tracing easier).
    """
    if not ir.startswith("; ModuleID"):
        header = f"; ModuleID = '<llm-mutant from {seed_name}>'\n"
        return header + ir
    return ir


def sanitize_ir(ir: str) -> str:
    """
    Apply heuristic fixes for common small-model hallucination errors:
      - Replace C-style comments (//) with LLVM comments (;).
      - Strip x86-style assembly suffixes (addq -> add).
      - Ensure the block ends cleanly (remove trailing prose/markdown).
    """
    if not ir:
        return ""

    # 1. Fix comments: // -> ;
    cleaned = re.sub(r"(?m)^\s*//", ";", ir)   # leading //
    cleaned = re.sub(r"//", ";", cleaned)      # inline //

    # 2. Fix assembly suffixes: addq, subq, mulq, etc. -> add, sub, mul
    # Pattern: \b(opcode)[qlb]\b  -> \b(opcode)\b
    _opcodes = ["add", "sub", "mul", "div", "rem", "or", "and", "xor", "mov"]
    for op in _opcodes:
        cleaned = re.sub(rf"\b{op}[qlbw]\b", op, cleaned)

    # 3. Strip trailing markdown/prose that might have leaked past the extractor
    # Look for the last '}' that closes a function and cut everything after it
    # if it doesn't look like IR metadata.
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        # If there's content after the last brace, check if it's prose
        # (Very simple check: if it contains words but no '!' or '@' or ';')
        trailing = cleaned[last_brace + 1 :].strip()
        if trailing and not any(c in trailing for c in ("!", "@", ";", "=")):
            cleaned = cleaned[: last_brace + 1]

    return cleaned.strip()
