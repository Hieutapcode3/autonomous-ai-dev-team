import pytest
import json
from unittest.mock import AsyncMock, patch
from app.schemas import SubTask, TaskDomain, ModelProvider, TaskStatus
from app.planner import PlannerEngine
from app.llm import LLMClient


@pytest.mark.anyio
async def test_planner_fallback_when_no_llm():
    planner = PlannerEngine()
    state = await planner.decompose_objective_intelligent(
        session_id="test_sess",
        objective="Create payment processing gateway",
        project_type="generic",
        llm_client=None,
    )
    assert len(state.tasks) >= 3
    assert state.status == "ready"


@pytest.mark.anyio
async def test_planner_dynamic_llm_decomposition():
    planner = PlannerEngine()
    llm = LLMClient()

    mock_tasks = [
        {
            "task_id": "auth_db",
            "title": "OAuth & DB Schema Design",
            "description": "Design PostgreSQL schemas and OAuth2 contracts",
            "domain": "architecture",
            "complexity": 8,
            "dependencies": [],
            "target_files": ["models/user.py"],
            "required_tools": ["fs_write"],
        },
        {
            "task_id": "auth_api",
            "title": "Google OAuth API Route",
            "description": "Implement OAuth callback and JWT issuance",
            "domain": "implementation",
            "complexity": 7,
            "dependencies": ["auth_db"],
            "target_files": ["routes/auth.py"],
            "required_tools": ["fs_read", "fs_write"],
        },
        {
            "task_id": "auth_qa",
            "title": "Automated Auth Security Test Suite",
            "description": "Run pytest with expired and valid JWT tokens",
            "domain": "verification",
            "complexity": 6,
            "dependencies": ["auth_api"],
            "target_files": ["tests/test_auth.py"],
            "required_tools": ["terminal_exec"],
        },
    ]

    async def mock_execute(task, model, context, **kwargs):
        return {"output": json.dumps(mock_tasks)}

    with patch.object(llm, "execute_task", side_effect=mock_execute):
        state = await planner_engine_run(planner, llm)
        assert len(state.tasks) == 3
        assert "auth_db" in state.tasks
        assert "auth_api" in state.tasks
        assert "auth_qa" in state.tasks
        # Check dependency ordering
        assert state.tasks["auth_api"].dependencies == ["auth_db"]
        assert state.tasks["auth_qa"].dependencies == ["auth_api"]


async def planner_engine_run(planner, llm):
    return await planner.decompose_objective_intelligent(
        session_id="dynamic_sess",
        objective="Create Google OAuth login with PostgreSQL and FastAPI",
        project_type="generic",
        llm_client=llm,
    )
