"""app/utils/clang_helpers.py

Helpers to compile C source into LLVM IR using clang.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class CCompilationError(RuntimeError):
    def __init__(self, message: str, stderr: str | None = None):
        super().__init__(message)
        self.stderr = stderr


def compile_c_to_ll(c_source: bytes, *, timeout_s: int = 10) -> bytes:
    """Compile C source bytes to textual LLVM IR (.ll).

    Uses clang inside the backend container.
    """
    with tempfile.TemporaryDirectory(prefix="c2ll_") as tmpdir:
        tmp = Path(tmpdir)
        c_path = tmp / "input.c"
        ll_path = tmp / "output.ll"

        c_path.write_bytes(c_source)

        cmd = [
            "clang",
            "-S",
            "-emit-llvm",
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
            str(c_path),
            "-o",
            str(ll_path),
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise CCompilationError("clang compilation timed out") from exc
        except OSError as exc:
            raise CCompilationError("clang is not available in this environment") from exc

        if proc.returncode != 0 or not ll_path.exists():
            stderr = (proc.stderr or "").strip()
            if len(stderr) > 4000:
                stderr = stderr[:4000] + "\n... (truncated)"
            msg = "clang failed to compile C to LLVM IR"
            if stderr:
                msg = f"{msg}: {stderr.splitlines()[-1]}"
            raise CCompilationError(msg, stderr=stderr)

        return ll_path.read_bytes()
