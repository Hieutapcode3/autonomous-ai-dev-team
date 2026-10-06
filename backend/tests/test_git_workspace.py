import pytest
import subprocess
import tempfile
from pathlib import Path
from app.git_workspace import GitWorkspaceManager


def test_git_workspace_not_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert not GitWorkspaceManager.is_git_repo(tmpdir)
        assert GitWorkspaceManager.commit_task_changes(tmpdir, "1", "Test") is None


def test_git_workspace_branch_commit_reset():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a temporary git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmpdir, check=True)

        # Initial commit so HEAD exists
        readme = Path(tmpdir) / "README.md"
        readme.write_text("# Initial", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=tmpdir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, check=True)

        assert GitWorkspaceManager.is_git_repo(tmpdir)

        # Create feature branch
        branch_ok = GitWorkspaceManager.create_and_checkout_feature_branch(tmpdir, "ai-feature/test1234")
        assert branch_ok
        assert GitWorkspaceManager.get_current_branch(tmpdir) == "ai-feature/test1234"

        # Commit task changes
        new_file = Path(tmpdir) / "feature.txt"
        new_file.write_text("hello world", encoding="utf-8")

        sha = GitWorkspaceManager.commit_task_changes(tmpdir, "task_1", "Feature Implement", ["feature.txt"])
        assert sha is not None

        # Modify and test reset
        new_file.write_text("broken code", encoding="utf-8")
        untracked = Path(tmpdir) / "untracked.tmp"
        untracked.write_text("garbage", encoding="utf-8")

        reset_ok = GitWorkspaceManager.reset_and_clean_changes(tmpdir)
        assert reset_ok
        assert new_file.read_text(encoding="utf-8") == "hello world"
        assert not untracked.exists()
