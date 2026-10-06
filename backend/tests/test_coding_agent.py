import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile
from app.schemas import SubTask, TaskDomain, ModelProvider, TaskStatus
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.llm import LLMClient
from app.coding_agent import CodingAgent


@pytest.mark.anyio
async def test_coding_agent_self_correction_on_syntax_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = SandboxRuntime(base_workspace=tmpdir)
        verifier = VerifierGate(sandbox)
        llm = LLMClient()

        task = SubTask(
            task_id="t_code",
            title="Implement Test Script",
            description="Implement a clean C# test script",
            domain=TaskDomain.IMPLEMENTATION,
            complexity=6,
            dependencies=[],
            target_files=["Assets/TestScript.cs"]
        )

        agent = CodingAgent(sandbox=sandbox, verifier=verifier, llm=llm, max_inner_turns=2)

        # Mock LLM to return broken C# on turn 1 (mismatched braces), and valid C# on turn 2
        broken_code = "namespace Test { public class TestScript { void Run() { } "  # Missing 2 close braces
        fixed_code = "namespace Test { public class TestScript { void Run() { } } }"

        call_count = 0

        async def mock_execute(task, model, context, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "output": "Turn 1 attempt",
                    "files": ["Assets/TestScript.cs"],
                    "code_changes": {"Assets/TestScript.cs": broken_code},
                }
            else:
                # Assert that turn 2 received the self_correction_error in context
                assert "self_correction_error" in context
                assert "Mismatched braces" in context["self_correction_error"]
                return {
                    "output": "Turn 2 fixed",
                    "files": ["Assets/TestScript.cs"],
                    "code_changes": {"Assets/TestScript.cs": fixed_code},
                }

        with patch.object(llm, "execute_task", side_effect=mock_execute):
            result = await agent.run(task, ModelProvider.GEMINI_PRO, {})

            assert call_count == 2
            assert result["code_changes"]["Assets/TestScript.cs"] == fixed_code
