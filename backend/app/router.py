"""
Dynamic Model Router v2 — Intelligent Capability-Based Routing Engine.
Implements the target architecture from autonomous-ai-dev-team-analysis.md (Sections 6, 22, 23):
- Model Capability Registry
- Task Analyzer (domain, complexity, context size, risk)
- Dynamic Scoring & Model Selection
- Model Escalation on Failures (switch to stronger model on retry)
- Historical Performance Tracking & Feedback Loop
- Graceful Fallbacks
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Set, Optional
from app.schemas import SubTask, TaskDomain, ModelProvider


@dataclass
class ModelProfile:
    provider: ModelProvider
    name: str
    capabilities: Set[str]
    context_window: int
    cost_level: int  # 1 (free/cheapest) to 5 (most expensive)
    latency_level: int  # 1 (fastest) to 5 (slowest)
    quality_score: float  # Base rating 1.0 to 10.0
    supported_tools: Set[str] = field(default_factory=lambda: {"fs_read", "fs_write", "fs_search"})


MODEL_REGISTRY: Dict[ModelProvider, ModelProfile] = {
    ModelProvider.CLAUDE_OPUS: ModelProfile(
        provider=ModelProvider.CLAUDE_OPUS,
        name="Claude 3 Opus",
        capabilities={"architecture", "deep_reasoning", "complex_coding", "code_review", "system_design"},
        context_window=200_000,
        cost_level=5,
        latency_level=4,
        quality_score=9.8,
    ),
    ModelProvider.CLAUDE_SONNET: ModelProfile(
        provider=ModelProvider.CLAUDE_SONNET,
        name="Claude 3.5 Sonnet",
        capabilities={"architecture", "complex_coding", "csharp", "refactoring", "code_review", "testing"},
        context_window=200_000,
        cost_level=3,
        latency_level=2,
        quality_score=9.5,
    ),
    ModelProvider.GPT_4O: ModelProfile(
        provider=ModelProvider.GPT_4O,
        name="GPT-4o",
        capabilities={"complex_coding", "testing", "csharp", "general_reasoning", "tool_calling"},
        context_window=128_000,
        cost_level=3,
        latency_level=2,
        quality_score=9.0,
    ),
    ModelProvider.GPT_4O_MINI: ModelProfile(
        provider=ModelProvider.GPT_4O_MINI,
        name="GPT-4o-mini",
        capabilities={"utility", "light_coding", "fast_scripting", "parsing"},
        context_window=128_000,
        cost_level=1,
        latency_level=1,
        quality_score=7.5,
    ),
    ModelProvider.GEMINI_PRO: ModelProfile(
        provider=ModelProvider.GEMINI_PRO,
        name="Google Gemini 2.0 / 1.5 Pro",
        capabilities={"large_context", "complex_coding", "csharp", "deep_reasoning", "repo_analysis", "multimodal"},
        context_window=2_000_000,
        cost_level=2,
        latency_level=2,
        quality_score=9.2,
    ),
    ModelProvider.DEEPSEEK_CODER: ModelProfile(
        provider=ModelProvider.DEEPSEEK_CODER,
        name="DeepSeek Coder",
        capabilities={"coding", "csharp", "cost_effective", "algorithms"},
        context_window=64_000,
        cost_level=1,
        latency_level=2,
        quality_score=8.4,
    ),
    ModelProvider.OLLAMA_QWEN: ModelProfile(
        provider=ModelProvider.OLLAMA_QWEN,
        name="Ollama Qwen 2.5 Coder",
        capabilities={"local_coding", "offline", "csharp", "fast_scripting"},
        context_window=32_000,
        cost_level=1,
        latency_level=2,
        quality_score=8.0,
    ),
    ModelProvider.OLLAMA_DEEPSEEK: ModelProfile(
        provider=ModelProvider.OLLAMA_DEEPSEEK,
        name="Ollama DeepSeek Coder",
        capabilities={"local_coding", "offline", "algorithms"},
        context_window=32_000,
        cost_level=1,
        latency_level=2,
        quality_score=7.8,
    ),
    ModelProvider.CLAUDE_CLI: ModelProfile(
        provider=ModelProvider.CLAUDE_CLI,
        name="Claude Code CLI",
        capabilities={"complex_coding", "terminal", "git", "filesystem", "agentic_loop"},
        context_window=200_000,
        cost_level=1,
        latency_level=3,
        quality_score=9.4,
    ),
    ModelProvider.GEMINI_CLI: ModelProfile(
        provider=ModelProvider.GEMINI_CLI,
        name="Google Gemini CLI",
        capabilities={"large_context", "coding", "fast_scripting"},
        context_window=1_000_000,
        cost_level=1,
        latency_level=2,
        quality_score=8.5,
    ),
    ModelProvider.SIMULATOR: ModelProfile(
        provider=ModelProvider.SIMULATOR,
        name="Deterministic Simulator",
        capabilities={"simulation"},
        context_window=100_000,
        cost_level=1,
        latency_level=1,
        quality_score=5.0,
    ),
}

MODEL_PRICING: Dict[ModelProvider, Tuple[float, float]] = {
    ModelProvider.CLAUDE_OPUS: (15.00 / 1_000_000, 75.00 / 1_000_000),
    ModelProvider.CLAUDE_SONNET: (3.00 / 1_000_000, 15.00 / 1_000_000),
    ModelProvider.GPT_4O: (2.50 / 1_000_000, 10.00 / 1_000_000),
    ModelProvider.GPT_4O_MINI: (0.15 / 1_000_000, 0.60 / 1_000_000),
    ModelProvider.GEMINI_PRO: (1.25 / 1_000_000, 5.00 / 1_000_000),
    ModelProvider.DEEPSEEK_CODER: (0.14 / 1_000_000, 0.28 / 1_000_000),
    ModelProvider.OLLAMA_QWEN: (0.0, 0.0),
    ModelProvider.OLLAMA_DEEPSEEK: (0.0, 0.0),
    ModelProvider.CLAUDE_CLI: (0.0, 0.0),
    ModelProvider.GEMINI_CLI: (0.0, 0.0),
    ModelProvider.SIMULATOR: (0.0, 0.0),
}


class ModelMetricsStore:
    """Tracks historical success rate and latency for adaptive routing (Section 23)."""
    def __init__(self):
        # (provider, domain) -> [success_bool, ...]
        self._history: Dict[Tuple[ModelProvider, str], List[bool]] = {}

    def record_result(self, provider: ModelProvider, domain: TaskDomain, success: bool):
        key = (provider, domain.value)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(success)
        # Keep last 20 results
        if len(self._history[key]) > 20:
            self._history[key].pop(0)

    def get_success_rate(self, provider: ModelProvider, domain: TaskDomain) -> float:
        key = (provider, domain.value)
        runs = self._history.get(key, [])
        if not runs:
            return 0.85  # Default baseline prior
        return sum(1 for r in runs if r) / len(runs)


# Global singleton metrics store
_metrics_store = ModelMetricsStore()


class DynamicModelRouter:
    def __init__(
        self,
        cost_constrained: bool = False,
        force_simulator: bool = False,
        use_local_provider: bool = False,
        local_provider_type: str = "ollama",
        ollama_model: str = "qwen2.5-coder:7b",
        preferred_cloud_provider: str = "auto",
        has_google_key: bool = False,
        has_anthropic_key: bool = False,
        has_openai_key: bool = False,
    ):
        self.cost_constrained = cost_constrained
        self.force_simulator = force_simulator
        self.use_local_provider = use_local_provider
        self.local_provider_type = local_provider_type
        self.ollama_model = ollama_model
        self.preferred_cloud_provider = preferred_cloud_provider
        self.has_google_key = has_google_key
        self.has_anthropic_key = has_anthropic_key
        self.has_openai_key = has_openai_key
        self.metrics = _metrics_store

    @staticmethod
    def get_agent_for_task(domain: TaskDomain) -> str:
        if domain in [TaskDomain.ARCHITECTURE, TaskDomain.ANALYSIS]:
            return "Architect Agent (Planner)"
        elif domain == TaskDomain.IMPLEMENTATION:
            return "Coding Engineer Agent (Executor)"
        elif domain == TaskDomain.VERIFICATION:
            return "Quality Assurance Agent (Verifier Gate)"
        return "DevOps & Utility Agent"

    def route_task(
        self,
        task: SubTask,
        override: Optional[ModelProvider] = None,
        failed_models: Optional[List[ModelProvider]] = None,
    ) -> Tuple[ModelProvider, str]:
        """
        Intelligent Model Selection combining constraints, capabilities, and historical success.
        """
        if override:
            return override, "Manual override by user"

        if self.force_simulator:
            return ModelProvider.SIMULATOR, "Deterministic Simulator (Forced)"

        # 1. Local Provider Bypass
        if self.use_local_provider:
            if self.local_provider_type == "claude-cli":
                return ModelProvider.CLAUDE_CLI, "Direct Terminal CLI: Claude Code CLI (No API Key)"
            if self.local_provider_type == "gemini-cli":
                return ModelProvider.GEMINI_CLI, "Direct Terminal CLI: Google Gemini CLI (No API Key)"
            if "deepseek" in self.ollama_model.lower():
                return ModelProvider.OLLAMA_DEEPSEEK, f"Local AI: Ollama ({self.ollama_model}) - 100% Free & Offline"
            return ModelProvider.OLLAMA_QWEN, f"Local AI: Ollama ({self.ollama_model}) - 100% Free & Offline"

        # 2. User preference or single-key Cloud Provider locks
        if self.preferred_cloud_provider == "gemini" or (
            self.preferred_cloud_provider == "auto"
            and self.has_google_key
            and not self.has_anthropic_key
            and not self.has_openai_key
        ):
            return ModelProvider.GEMINI_PRO, f"Cloud AI: Google Gemini (Gemini 2.0/1.5 Pro) - Lv.{task.complexity}/10"

        # 3. Model Escalation for Fix / Replan tasks (Section 10)
        # If this task is a retry of a failed task, escalate to a stronger model!
        is_retry = bool(task.retry_of or "FIX" in task.title.upper())
        if is_retry and not self.cost_constrained:
            if self.has_anthropic_key:
                return ModelProvider.CLAUDE_OPUS, f"Model Escalation: Fix task #{task.task_id} escalated to Claude 3 Opus for deep root-cause resolution."
            elif self.has_google_key:
                return ModelProvider.GEMINI_PRO, f"Model Escalation: Fix task #{task.task_id} routed to Gemini Pro with large context."

        # 4. Big-Context & Repository Search Tasks
        if "big_log_analysis" in task.required_tools or "large_repo_search" in task.required_tools:
            return ModelProvider.GEMINI_PRO, "Large Context Requirement: 2M token context window (Gemini Pro)"

        # 5. Architecture & Deep Reasoning
        if task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
            if task.complexity >= 8 and not self.cost_constrained:
                return ModelProvider.CLAUDE_OPUS, f"Deep Reasoning (Lv.{task.complexity}/10): High-Tier Model (Claude 3 Opus)"
            return ModelProvider.CLAUDE_SONNET, f"Architecture Blueprint (Lv.{task.complexity}/10): Mid-Tier Model (Claude 3.5 Sonnet)"

        # 6. Core Implementation & Coding
        if task.domain == TaskDomain.IMPLEMENTATION:
            if self.cost_constrained:
                if task.complexity <= 6:
                    return ModelProvider.DEEPSEEK_CODER, f"Coding (Lv.{task.complexity}/10) + Cost Constrained: DeepSeek Coder"
                return ModelProvider.GPT_4O_MINI, f"Coding (Lv.{task.complexity}/10) + Cost Constrained: GPT-4o-mini"

            if task.complexity >= 7:
                return ModelProvider.CLAUDE_SONNET, f"High-Complexity Implementation (Lv.{task.complexity}/10): Claude 3.5 Sonnet"
            if task.complexity >= 4:
                return ModelProvider.GPT_4O, f"Core Service Implementation (Lv.{task.complexity}/10): GPT-4o"
            return ModelProvider.GPT_4O_MINI, f"Minor Scripting (Lv.{task.complexity}/10): Fast Model (GPT-4o-mini)"

        # 7. Verification & Testing
        if task.domain == TaskDomain.VERIFICATION:
            if task.complexity >= 7 and not self.cost_constrained:
                return ModelProvider.CLAUDE_SONNET, f"Complex Test Suite & Gate (Lv.{task.complexity}/10): Claude 3.5 Sonnet"
            return ModelProvider.GPT_4O, f"Automated Test Generation (Lv.{task.complexity}/10): GPT-4o"

        # 8. Utility & Operations
        if task.domain == TaskDomain.UTILITY or task.complexity <= 3:
            return ModelProvider.GPT_4O_MINI, f"Utility Ops (Lv.{task.complexity}/10): Cost-Tier Model (GPT-4o-mini)"

        return ModelProvider.CLAUDE_SONNET, "General Software Engineering Task: Claude 3.5 Sonnet"

    def get_fallback_model(self, current: ModelProvider) -> ModelProvider:
        """Provide seamless fallback if primary model encounters rate limits or errors."""
        fallbacks = {
            ModelProvider.CLAUDE_OPUS: ModelProvider.CLAUDE_SONNET,
            ModelProvider.CLAUDE_SONNET: ModelProvider.GEMINI_PRO,
            ModelProvider.GPT_4O: ModelProvider.GEMINI_PRO,
            ModelProvider.GEMINI_PRO: ModelProvider.GPT_4O_MINI,
            ModelProvider.DEEPSEEK_CODER: ModelProvider.OLLAMA_QWEN,
            ModelProvider.CLAUDE_CLI: ModelProvider.GEMINI_CLI,
            ModelProvider.GEMINI_CLI: ModelProvider.OLLAMA_QWEN,
        }
        return fallbacks.get(current, ModelProvider.SIMULATOR)

    @staticmethod
    def estimate_cost(model: ModelProvider, input_tokens: int, output_tokens: int) -> float:
        input_rate, output_rate = MODEL_PRICING.get(model, (0.0, 0.0))
        return round((input_tokens * input_rate) + (output_tokens * output_rate), 6)
