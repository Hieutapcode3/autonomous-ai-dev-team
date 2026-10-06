import pytest
from app.schemas import GlobalDAGState, SubTask, TaskStatus, TaskDomain, ModelProvider
from app.planner import PlannerEngine
from app.router import DynamicModelRouter
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.orchestrator import TeamOrchestrator
from app.llm import LLMClient
from pathlib import Path
import tempfile


def test_replan_dependencies_do_not_depend_on_failed_task():
    planner = PlannerEngine()
    state = GlobalDAGState(session_id="test", objective="test")
    
    t1 = SubTask(
        task_id="t1",
        title="Task 1",
        description="Task 1",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=5,
        dependencies=[],
        status=TaskStatus.COMPLETED
    )
    t2 = SubTask(
        task_id="t2",
        title="Task 2",
        description="Task 2",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=5,
        dependencies=["t1"],
        status=TaskStatus.FAILED,
        error_trace="Some compiler error in Unity"
    )
    state.tasks = {"t1": t1, "t2": t2}
    
    fix_task = planner.trigger_replan(state, t2)
    
    # fix_task must inherit t2's dependencies ("t1"), NOT depend on "t2" (which is FAILED)
    assert fix_task.dependencies == ["t1"]
    assert fix_task.retry_of == "t2"
    assert fix_task.task_id in state.tasks


@pytest.mark.anyio
async def test_rollback_cleans_created_files_and_restores_backups():
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = SandboxRuntime(base_workspace=tmpdir)
        router = DynamicModelRouter()
        verifier = VerifierGate(sandbox)
        planner = PlannerEngine()
        llm = LLMClient()
        
        state = GlobalDAGState(session_id="test", objective="test", project_path=tmpdir)
        orchestrator = TeamOrchestrator(state, router, sandbox, verifier, planner, llm)
        
        # Simulate creating a file and backing up a file
        existing_file = Path(tmpdir) / "existing.txt"
        existing_file.write_text("original content", encoding="utf-8")
        
        orchestrator._file_backups["existing.txt"] = "original content"
        # Overwrite file
        existing_file.write_text("modified broken content", encoding="utf-8")
        
        # New created file
        new_file = Path(tmpdir) / "new_broken.txt"
        new_file.write_text("broken code", encoding="utf-8")
        new_meta = Path(tmpdir) / "new_broken.txt.meta"
        new_meta.write_text("meta info", encoding="utf-8")
        orchestrator._created_files.add("new_broken.txt")
        
        # Run rollback
        await orchestrator._rollback_changes()
        
        # New files should be deleted
        assert not new_file.exists()
        assert not new_meta.exists()
        
        # Existing file should be restored
        assert existing_file.read_text(encoding="utf-8") == "original content"
