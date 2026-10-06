import pytest
from app.schemas import SubTask, TaskDomain, ModelProvider
from app.router import DynamicModelRouter, MODEL_REGISTRY


def test_router_v2_model_registry():
    # Verify all models have capability profiles
    assert ModelProvider.CLAUDE_OPUS in MODEL_REGISTRY
    assert ModelProvider.GEMINI_PRO in MODEL_REGISTRY
    assert ModelProvider.CLAUDE_SONNET in MODEL_REGISTRY

    opus_profile = MODEL_REGISTRY[ModelProvider.CLAUDE_OPUS]
    assert "deep_reasoning" in opus_profile.capabilities
    assert opus_profile.quality_score >= 9.5


def test_router_v2_model_escalation_on_retry():
    # If a task is a retry of a failed task, router must escalate to a stronger model
    router = DynamicModelRouter(
        cost_constrained=False,
        has_anthropic_key=True,
    )
    failed_task = SubTask(
        task_id="t1",
        title="Implementation Task",
        description="Write C# Script",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=6,
    )
    fix_task = SubTask(
        task_id="replan_123",
        title="[FIX #1] Implementation Task",
        description="Fix compiler error",
        domain=TaskDomain.IMPLEMENTATION,
        complexity=7,
        retry_of="t1",
    )

    model, reason = router.route_task(fix_task)
    assert model == ModelProvider.CLAUDE_OPUS
    assert "Escalation" in reason


def test_router_v2_fallback_model():
    router = DynamicModelRouter()
    assert router.get_fallback_model(ModelProvider.CLAUDE_OPUS) == ModelProvider.CLAUDE_SONNET
    assert router.get_fallback_model(ModelProvider.CLAUDE_SONNET) == ModelProvider.GEMINI_PRO
    assert router.get_fallback_model(ModelProvider.GEMINI_PRO) == ModelProvider.GPT_4O_MINI


def test_router_v2_metrics_tracking():
    router = DynamicModelRouter()
    # Initial prior
    assert router.metrics.get_success_rate(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION) == 0.85

    # Record 3 successes and 1 failure
    router.metrics.record_result(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION, True)
    router.metrics.record_result(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION, True)
    router.metrics.record_result(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION, True)
    router.metrics.record_result(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION, False)

    rate = router.metrics.get_success_rate(ModelProvider.GPT_4O, TaskDomain.IMPLEMENTATION)
    assert rate == 0.75
