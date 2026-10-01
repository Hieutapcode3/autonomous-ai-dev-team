import ast
import json
from pathlib import Path
from typing import Dict, Any, List
from app.schemas import SubTask, VerifierResult, TaskDomain
from app.sandbox import SandboxRuntime


class VerifierGate:
    def __init__(self, sandbox: SandboxRuntime):
        self.sandbox = sandbox

    async def evaluate(self, task: SubTask, exec_result: Dict[str, Any]) -> VerifierResult:
        # Non-code utility tasks check tool exit codes
        if task.domain == TaskDomain.UTILITY:
            tool_success = exec_result.get("success", False)
            return VerifierResult(
                passed=tool_success,
                status_code=0 if tool_success else 1,
                summary="Utility command passed" if tool_success else "Utility execution failed",
                error_log=exec_result.get("error") or exec_result.get("stderr"),
            )

        checks: List[Dict[str, Any]] = []
        all_passed = True
        error_logs: List[str] = []

        # 1. Syntax Verification on generated files
        artifacts = exec_result.get("artifacts", {})
        created_files = artifacts.get("files", [])

        for file_path in created_files:
            syntax_check = self._verify_syntax(file_path)
            checks.append(syntax_check)
            if not syntax_check["passed"]:
                all_passed = False
                error_logs.append(f"Syntax Error in {file_path}: {syntax_check['error']}")

        # 2. Automated Test / Verification execution
        if all_passed and (task.domain in [TaskDomain.IMPLEMENTATION, TaskDomain.VERIFICATION]):
            test_files = [
                f for f in created_files
                if "test" in f.lower() or f.endswith(("_test.py", "_spec.ts", ".test.js"))
            ]
            has_existing_tests = any(
                "test" in f["path"].lower() for f in self.sandbox.fs_list()
            )

            if test_files or has_existing_tests:
                # Run python test suite if python files exist
                has_python = any(f.endswith(".py") for f in created_files) or any(
                    f["path"].endswith(".py") for f in self.sandbox.fs_list()
                )
                if has_python:
                    venv_pytest = Path(__file__).resolve().parent.parent / "venv" / "Scripts" / "pytest.exe"
                    if venv_pytest.exists():
                        run_cmd = f'"{venv_pytest}" -o pythonpath=. -q'
                    else:
                        import sys
                        run_cmd = f'"{sys.executable}" -m pytest -o pythonpath=. -q'
                    res = self.sandbox.terminal_exec(run_cmd, timeout_sec=20)
                    test_passed = res["exit_code"] == 0
                    checks.append({
                        "check": "pytest_suite",
                        "command": run_cmd,
                        "passed": test_passed,
                        "output": res["stdout"] or res["stderr"],
                    })
                    if not test_passed:
                        all_passed = False
                        error_logs.append(f"Test Suite Failed:\n{res['stdout']}\n{res['stderr']}")

        summary = "All quality gate checks passed." if all_passed else f"{len(error_logs)} verification checks failed."
        full_error_log = "\n---\n".join(error_logs) if error_logs else None

        return VerifierResult(
            passed=all_passed,
            status_code=0 if all_passed else 1,
            summary=summary,
            error_log=full_error_log,
            checks=checks,
        )

    def _verify_syntax(self, rel_path: str) -> Dict[str, Any]:
        full_path = self.sandbox.workspace / rel_path
        if not full_path.exists():
            return {
                "file": rel_path,
                "check": "file_existence",
                "passed": False,
                "error": "File was declared created but does not exist on disk",
            }

        ext = full_path.suffix.lower()

        if ext == ".py":
            try:
                content = full_path.read_text(encoding="utf-8")
                ast.parse(content, filename=rel_path)
                return {"file": rel_path, "check": "python_ast", "passed": True}
            except SyntaxError as e:
                return {
                    "file": rel_path,
                    "check": "python_ast",
                    "passed": False,
                    "error": f"Line {e.lineno}: {e.msg}",
                }

        if ext == ".json":
            try:
                content = full_path.read_text(encoding="utf-8")
                json.loads(content)
                return {"file": rel_path, "check": "json_parse", "passed": True}
            except json.JSONDecodeError as e:
                return {
                    "file": rel_path,
                    "check": "json_parse",
                    "passed": False,
                    "error": f"JSON syntax error at line {e.lineno}: {e.msg}",
                }

        return {"file": rel_path, "check": "generic_text", "passed": True}
