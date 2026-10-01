from typing import Dict, Tuple
from app.schemas import SubTask, TaskDomain, ModelProvider


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


class DynamicModelRouter:
    def __init__(
        self,
        cost_constrained: bool = False,
        force_simulator: bool = False,
        use_local_provider: bool = False,
        local_provider_type: str = "ollama",
        ollama_model: str = "qwen2.5-coder:7b",
    ):
        self.cost_constrained = cost_constrained
        self.force_simulator = force_simulator
        self.use_local_provider = use_local_provider
        self.local_provider_type = local_provider_type
        self.ollama_model = ollama_model

    @staticmethod
    def get_agent_for_task(domain: TaskDomain) -> str:
        if domain in [TaskDomain.ARCHITECTURE, TaskDomain.ANALYSIS]:
            return "Architect Agent (Planner)"
        elif domain == TaskDomain.IMPLEMENTATION:
            return "Coding Engineer Agent (Executor)"
        elif domain == TaskDomain.VERIFICATION:
            return "Quality Assurance Agent (Verifier Gate)"
        return "DevOps & Utility Agent"

    def route_task(self, task: SubTask, override: ModelProvider | None = None) -> Tuple[ModelProvider, str]:
        if override:
            return override, "Manual override by user"

        if self.use_local_provider:
            if self.local_provider_type == "claude-cli":
                return ModelProvider.CLAUDE_CLI, "Direct Terminal CLI: Claude Code CLI (No API Key)"
            if self.local_provider_type == "gemini-cli":
                return ModelProvider.GEMINI_CLI, "Direct Terminal CLI: Google Gemini CLI (No API Key)"
            if "deepseek" in self.ollama_model.lower():
                return ModelProvider.OLLAMA_DEEPSEEK, f"Local AI: Ollama ({self.ollama_model}) - 100% Free & Offline"
            return ModelProvider.OLLAMA_QWEN, f"Local AI: Ollama ({self.ollama_model}) - 100% Free & Offline"

        # Tier 1 & 2: Big-context tasks
        if "big_log_analysis" in task.required_tools or "large_repo_search" in task.required_tools:
            return ModelProvider.GEMINI_PRO, "Tier 1: Big-Log/Repo search -> Tier 2: Large 2M token window (Gemini Pro)"

        # Tier 1: Analysis & Architecture
        if task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
            if task.complexity >= 8 and not self.cost_constrained:
                return ModelProvider.CLAUDE_OPUS, f"Tier 1: Deep Reasoning (Lv.{task.complexity}/10) -> Tier 2: High-Tier Model (Claude 3 Opus)"
            return ModelProvider.CLAUDE_SONNET, f"Tier 1: Architecture Blueprint (Lv.{task.complexity}/10) -> Tier 2: Mid-Tier Model (Claude 3.5 Sonnet)"

        # Tier 1: Core Implementation & Refactoring
        if task.domain == TaskDomain.IMPLEMENTATION:
            if self.cost_constrained:
                if task.complexity <= 6:
                    return ModelProvider.DEEPSEEK_CODER, f"Tier 1: Coding (Lv.{task.complexity}/10) + Cost Constrained -> Tier 2: DeepSeek Coder"
                return ModelProvider.GPT_4O_MINI, f"Tier 1: Coding (Lv.{task.complexity}/10) + Cost Constrained -> Tier 2: GPT-4o-mini"
            if task.complexity >= 7:
                return ModelProvider.CLAUDE_SONNET, f"Tier 1: High-Complexity Implementation (Lv.{task.complexity}/10) -> Tier 2: Claude 3.5 Sonnet"
            if task.complexity >= 4:
                return ModelProvider.GPT_4O, f"Tier 1: Core Service Implementation (Lv.{task.complexity}/10) -> Tier 2: GPT-4o"
            return ModelProvider.GPT_4O_MINI, f"Tier 1: Minor Code/Scripting (Lv.{task.complexity}/10) -> Tier 2: Fast Model (GPT-4o-mini)"

        # Tier 1: Verification & Testing
        if task.domain == TaskDomain.VERIFICATION:
            if task.complexity >= 7 and not self.cost_constrained:
                return ModelProvider.CLAUDE_SONNET, f"Tier 1: Complex Verification & Test Harness (Lv.{task.complexity}/10) -> Tier 2: Claude 3.5 Sonnet"
            return ModelProvider.GPT_4O, f"Tier 1: Automated Test Generation & Gate (Lv.{task.complexity}/10) -> Tier 2: GPT-4o"

        # Tier 1: Utility, Command execution, Log parsing
        if task.domain == TaskDomain.UTILITY or task.complexity <= 3:
            return ModelProvider.GPT_4O_MINI, f"Tier 1: Utility Ops (Lv.{task.complexity}/10) -> Tier 2: Cost-Tier Model (GPT-4o-mini)"

        return ModelProvider.CLAUDE_SONNET, "Tier 1: General software task -> Tier 2: Claude 3.5 Sonnet"

    @staticmethod
    def estimate_cost(model: ModelProvider, input_tokens: int, output_tokens: int) -> float:
        input_rate, output_rate = MODEL_PRICING.get(model, (0.0, 0.0))
        return round((input_tokens * input_rate) + (output_tokens * output_rate), 6)
