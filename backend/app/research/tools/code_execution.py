"""Safe-ish Python execution tool for deterministic research calculations."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ToolSecurityError(ValueError):
    """Raised when submitted code violates the tool safety policy."""


@dataclass(frozen=True)
class CodeExecutionResult:
    """Structured result returned by the Python execution tool."""

    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool = False
    error: str = ""

    def model_dump(self) -> dict[str, object]:
        """Return a serializable payload compatible with Pydantic-style callers."""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "error": self.error,
        }


class CodeExecutionTool:
    """Run small Python snippets in a subprocess with static safety checks."""

    name = "python_code_execution"
    description = (
        "Executes small, deterministic Python snippets for calculations or data "
        "transforms during research. The tool rejects dangerous imports and calls."
    )
    default_timeout_seconds = 30
    blocked_imports = {
        "os",
        "subprocess",
        "sys",
        "socket",
        "shutil",
        "pathlib",
        "requests",
        "urllib",
        "http",
    }
    blocked_calls = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "globals",
        "input",
        "locals",
        "open",
    }
    blocked_attributes = {
        "os.system",
        "os.popen",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "os.rename",
        "os.replace",
        "os.environ",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.Popen",
        "sys.exit",
    }

    @classmethod
    def schema(cls) -> dict[str, Any]:
        """Return an OpenAI-compatible JSON tool schema."""
        return {
            "name": cls.name,
            "description": cls.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds.",
                        "minimum": 1,
                        "maximum": cls.default_timeout_seconds,
                        "default": cls.default_timeout_seconds,
                    },
                },
                "required": ["code"],
                "additionalProperties": False,
            },
        }

    def run(
        self,
        code: str,
        *,
        timeout_seconds: int | None = None,
    ) -> CodeExecutionResult:
        """Validate and execute Python code in an isolated subprocess."""
        timeout = self._normalize_timeout(timeout_seconds)
        self._validate_code(code)
        with tempfile.TemporaryDirectory(prefix="research-code-") as temp_dir:
            script_path = Path(temp_dir) / "snippet.py"
            script_path.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(script_path)],
                    cwd=temp_dir,
                    env=self._subprocess_env(),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                return CodeExecutionResult(
                    stdout=self._text_output(exc.stdout),
                    stderr=self._text_output(exc.stderr),
                    exit_code=None,
                    timed_out=True,
                    error=f"Execution timed out after {timeout} seconds.",
                )

        return CodeExecutionResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
        )

    def _normalize_timeout(self, timeout_seconds: int | None) -> int:
        """Clamp the caller timeout to the configured safety ceiling."""
        if timeout_seconds is None:
            return self.default_timeout_seconds
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")
        return min(timeout_seconds, self.default_timeout_seconds)

    def _validate_code(self, code: str) -> None:
        """Reject code that imports or calls blocked APIs."""
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ToolSecurityError(f"Invalid Python code: {exc.msg}") from exc

        for node in ast.walk(tree):
            self._check_import(node)
            self._check_call(node)
            self._check_attribute(node)

    def _check_import(self, node: ast.AST) -> None:
        """Reject imports of modules that escape the execution sandbox."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._raise_if_blocked_module(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            self._raise_if_blocked_module(node.module)

    def _check_call(self, node: ast.AST) -> None:
        """Reject direct calls to blocked builtins and process APIs."""
        if not isinstance(node, ast.Call):
            return
        if isinstance(node.func, ast.Name) and node.func.id in self.blocked_calls:
            raise ToolSecurityError(f"Blocked unsafe call: {node.func.id}")
        if isinstance(node.func, ast.Attribute):
            attribute_name = self._attribute_name(node.func)
            if attribute_name in self.blocked_attributes:
                raise ToolSecurityError(f"Blocked unsafe call: {attribute_name}")

    def _check_attribute(self, node: ast.AST) -> None:
        """Reject direct access to blocked process or filesystem attributes."""
        if not isinstance(node, ast.Attribute):
            return
        attribute_name = self._attribute_name(node)
        if attribute_name in self.blocked_attributes:
            raise ToolSecurityError(f"Blocked unsafe attribute: {attribute_name}")

    def _raise_if_blocked_module(self, module_name: str) -> None:
        """Reject a module when its root package is blocked."""
        root_name = module_name.split(".", 1)[0]
        if root_name in self.blocked_imports:
            raise ToolSecurityError(f"Blocked unsafe import: {root_name}")

    def _attribute_name(self, node: ast.Attribute) -> str:
        """Return a dotted attribute name for simple AST attribute chains."""
        parts: list[str] = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _subprocess_env(self) -> dict[str, str]:
        """Build a minimal environment for the snippet process."""
        env: dict[str, str] = {}
        for name in ("PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP"):
            value = os.environ.get(name)
            if value is not None:
                env[name] = value
        env["PYTHONPATH"] = ""
        return env

    def _text_output(self, value: str | bytes | None) -> str:
        """Normalize subprocess timeout output to text."""
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
