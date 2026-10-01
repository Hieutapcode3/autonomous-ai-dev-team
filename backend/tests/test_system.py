import pytest
from app.schemas import SubTask, TaskDomain, ModelProvider, TaskStatus
from app.router import DynamicModelRouter
from app.planner import PlannerEngine
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate


def test_router_allocations():
    router = DynamicModelRouter(cost_constrained=False, force_simulator=False)

    high_arch_task = SubTask(
        task_id="t1",
        title="System Design",
        description="Architecture design",
        domain=TaskDomain.ARCHITECTURE,
        complexity=9,
    )
    model1, _ = router.route_task(high_arch_task)
    assert model1 == ModelProvider.CLAUDE_OPUS

    coding_task = SubTask(
        task_id="t2",
        title="Coding",
        description="Write algorithm",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=7,
    )
    model2, _ = router.route_task(coding_task)
    assert model2 == ModelProvider.CLAUDE_SONNET

    util_task = SubTask(
        task_id="t3",
        title="Log Parse",
        description="Extract metrics",
        domain=TaskDomain.UTILITY,
        complexity=2,
    )
    model3, _ = router.route_task(util_task)
    assert model3 == ModelProvider.GPT_4O_MINI


def test_planner_topological_sort():
    planner = PlannerEngine()
    state = planner.decompose_objective("test_sess", "Build Payment Service")

    assert len(state.tasks) == 4
    assert len(state.execution_order) >= 3

    # Check topological order: t1 must come before t2
    task_keys = list(state.tasks.keys())
    assert state.tasks[task_keys[1]].dependencies == [task_keys[0]]


def test_sandbox_and_verifier(tmp_path):
    sandbox = SandboxRuntime(base_workspace=str(tmp_path))
    res = sandbox.fs_write("calc.py", "def add(a, b):\n    return a + b\n")
    assert res["file"] == "calc.py"

    verifier = VerifierGate(sandbox=sandbox)
    task = SubTask(
        task_id="test_task",
        title="Calc Implementation",
        description="Create calculator",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=5,
    )

    import asyncio
    v_res = asyncio.run(
        verifier.evaluate(task, {"artifacts": {"files": ["calc.py"]}, "success": True})
    )
    assert v_res.passed is True
