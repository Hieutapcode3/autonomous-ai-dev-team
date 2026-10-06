"""
Git Workspace & Worktree Isolation Manager.
Implements Section 18 of autonomous-ai-dev-team-analysis.md:
- Isolated Branching per Session (protects main branch)
- Automatic Task Micro-Commits
- Safe Discard & Reset on Rejection / Cancellation
- Git Worktree isolation support
"""

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any


class GitWorkspaceManager:
    @staticmethod
    def is_git_repo(path: Optional[str]) -> bool:
        if not path:
            return False
        p = Path(path)
        return (p / ".git").exists() or (p / ".git").is_file()

    @staticmethod
    def _run_git(repo_path: str, args: List[str], timeout: int = 20) -> Dict[str, Any]:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "code": res.returncode,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "code": -1}

    @classmethod
    def get_current_branch(cls, repo_path: str) -> Optional[str]:
        res = cls._run_git(repo_path, ["branch", "--show-current"])
        return res["stdout"] if res["success"] and res["stdout"] else None

    @classmethod
    def create_and_checkout_feature_branch(cls, repo_path: str, branch_name: str) -> bool:
        """Create and checkout an isolated feature branch for the session."""
        if not cls.is_git_repo(repo_path):
            return False
        # Try checking out if exists, or create with -b
        res = cls._run_git(repo_path, ["checkout", "-b", branch_name])
        if not res["success"]:
            # If already exists, checkout
            res = cls._run_git(repo_path, ["checkout", branch_name])
        return res["success"]

    @classmethod
    def commit_task_changes(
        cls,
        repo_path: str,
        task_id: str,
        task_title: str,
        files: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Stage changed files and create a clean micro-commit for the completed task."""
        if not cls.is_git_repo(repo_path):
            return None

        # Stage specific files or all tracked/untracked changes
        if files:
            for f in files:
                cls._run_git(repo_path, ["add", f])
        else:
            cls._run_git(repo_path, ["add", "."])

        msg = f"feat(agent): [Task #{task_id}] {task_title}"
        res = cls._run_git(repo_path, ["commit", "-m", msg])
        if res["success"]:
            # Get latest commit sha
            sha_res = cls._run_git(repo_path, ["rev-parse", "--short", "HEAD"])
            return sha_res["stdout"] if sha_res["success"] else None
        return None

    @classmethod
    def reset_and_clean_changes(cls, repo_path: str) -> bool:
        """Discard uncommitted modifications and remove untracked files on failure."""
        if not cls.is_git_repo(repo_path):
            return False
        cls._run_git(repo_path, ["reset", "--hard", "HEAD"])
        cls._run_git(repo_path, ["clean", "-fd"])
        return True

    @classmethod
    def create_worktree(
        cls,
        repo_path: str,
        worktree_path: str,
        branch_name: str,
    ) -> bool:
        """Create a dedicated git worktree for physical file-level directory isolation."""
        if not cls.is_git_repo(repo_path):
            return False
        # git worktree add <path> -b <branch>
        res = cls._run_git(repo_path, ["worktree", "add", worktree_path, "-b", branch_name])
        return res["success"]

    @classmethod
    def remove_worktree(cls, repo_path: str, worktree_path: str) -> bool:
        """Safely prune and remove an isolated worktree."""
        if not cls.is_git_repo(repo_path):
            return False
        res = cls._run_git(repo_path, ["worktree", "remove", "--force", worktree_path])
        if not res["success"] and os.path.exists(worktree_path):
            try:
                shutil.rmtree(worktree_path)
            except Exception:
                pass
        cls._run_git(repo_path, ["worktree", "prune"])
        return True
