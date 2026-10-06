import os
import subprocess
import difflib
import re
from typing import Dict, Any, List, Optional
from pathlib import Path


class SandboxRuntime:
    def __init__(self, base_workspace: Optional[str] = None):
        if base_workspace:
            self.workspace = Path(base_workspace).resolve()
        else:
            self.workspace = (Path(__file__).parent.parent.parent / "workspace_sandbox").resolve()

        self.workspace.mkdir(parents=True, exist_ok=True)
        self.artifacts_history: List[Dict[str, Any]] = []

    def _resolve_safe_path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if not str(target).startswith(str(self.workspace)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    def fs_read(self, file_path: str) -> str:
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return safe_path.read_text(encoding="utf-8")

    def fs_write(self, file_path: str, content: str) -> Dict[str, Any]:
        safe_path = self._resolve_safe_path(file_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        old_content = ""
        is_new = not safe_path.exists()
        if not is_new:
            try:
                old_content = safe_path.read_text(encoding="utf-8")
            except Exception:
                old_content = ""

        safe_path.write_text(content, encoding="utf-8")

        # Ensure package directory has __init__.py
        if safe_path.suffix == ".py" and safe_path.parent != self.workspace:
            init_file = safe_path.parent / "__init__.py"
            if not init_file.exists():
                init_file.write_text("", encoding="utf-8")

        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )

        artifact_record = {
            "file": file_path,
            "action": "create" if is_new else "modify",
            "content": content,
            "diff": diff,
            "size_bytes": len(content.encode("utf-8")),
        }
        self.artifacts_history.append(artifact_record)
        return artifact_record

    def fs_patch(self, file_path: str, target_block: str, replacement_block: str) -> Dict[str, Any]:
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        current_content = safe_path.read_text(encoding="utf-8")
        if target_block not in current_content:
            raise ValueError(f"Target block to patch was not found in {file_path}")

        new_content = current_content.replace(target_block, replacement_block, 1)
        return self.fs_write(file_path, new_content)

    def fs_list(self, sub_dir: str = ".") -> List[Dict[str, Any]]:
        safe_dir = self._resolve_safe_path(sub_dir)
        if not safe_dir.exists() or not safe_dir.is_dir():
            return []

        results = []
        for root, dirs, files in os.walk(safe_dir):
            rel_root = Path(root).relative_to(self.workspace)
            for f in files:
                rel_file = str(rel_root / f).replace("\\", "/")
                p = Path(root) / f
                results.append({
                    "path": rel_file,
                    "size_bytes": p.stat().st_size,
                    "is_dir": False
                })
        return results

    def fs_search(self, pattern: str, sub_dir: str = ".", max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for pattern across text files in workspace (case-insensitive regex)."""
        safe_dir = self._resolve_safe_path(sub_dir)
        if not safe_dir.exists() or not safe_dir.is_dir():
            return []

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except Exception:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        results = []
        skip_exts = {".meta", ".dll", ".png", ".jpg", ".jpeg", ".asset", ".prefab", ".mat", ".unity", ".fbx"}
        for root, dirs, files in os.walk(safe_dir):
            rel_root = Path(root).relative_to(self.workspace)
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in skip_exts:
                    continue
                p = Path(root) / f
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    for line_num, line in enumerate(text.splitlines(), start=1):
                        if regex.search(line):
                            rel_file = str(rel_root / f).replace("\\", "/")
                            results.append({
                                "file": rel_file,
                                "line": line_num,
                                "content": line.strip()[:200],
                            })
                            if len(results) >= max_results:
                                return results
                except Exception:
                    continue
        return results

    def terminal_exec(self, command: str, timeout_sec: int = 30) -> Dict[str, Any]:
        try:
            exec_env = os.environ.copy()
            exec_env["PYTHONPATH"] = str(self.workspace) + os.pathsep + exec_env.get("PYTHONPATH", "")
            result = subprocess.run(
                command,
                cwd=str(self.workspace),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=exec_env,
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout_sec} seconds.",
                "success": False,
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }

    def test_runner(self, command: str) -> Dict[str, Any]:
        return self.terminal_exec(command, timeout_sec=60)
