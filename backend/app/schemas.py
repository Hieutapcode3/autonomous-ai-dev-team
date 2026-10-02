from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time


class TaskDomain(str, Enum):
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    UTILITY = "utility"


class ModelProvider(str, Enum):
    CLAUDE_OPUS = "claude-3-opus"
    CLAUDE_SONNET = "claude-3-5-sonnet"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GEMINI_PRO = "gemini-1.5-pro"
    DEEPSEEK_CODER = "deepseek-coder"
    OLLAMA_QWEN = "ollama:qwen2.5-coder:7b"
    OLLAMA_DEEPSEEK = "ollama:deepseek-coder:6.7b"
    CLAUDE_CLI = "claude-cli"
    GEMINI_CLI = "gemini-cli"
    SIMULATOR = "mock-simulator"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubTask(BaseModel):
    task_id: str
    title: str
    description: str
    domain: TaskDomain
    complexity: int = Field(ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    assigned_model: Optional[ModelProvider] = None
    assigned_agent: Optional[str] = None
    routing_rationale: Optional[str] = None
    required_tools: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    output_artifacts: Optional[Dict[str, Any]] = None
    error_trace: Optional[str] = None
    retry_of: Optional[str] = None
    cost_usd: float = 0.0
    execution_time_ms: float = 0.0
    estimated_time_sec: int = 0
    target_files: List[str] = Field(default_factory=list)


class GlobalDAGState(BaseModel):
    session_id: str
    objective: str
    tasks: Dict[str, SubTask] = Field(default_factory=dict)
    execution_order: List[List[str]] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 15
    total_cost_usd: float = 0.0
    total_estimated_time_sec: int = 0
    total_elapsed_time_sec: float = 0.0
    status: str = "idle"
    active_agent: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    github_result: Optional[Dict[str, str]] = None
    project_path: Optional[str] = None
    project_type: str = "generic"
    ingested_rules: List[Dict[str, Any]] = Field(default_factory=list)
    ingested_skills: List[Dict[str, Any]] = Field(default_factory=list)
    context_summary: Optional[str] = None
    reference_media: List[Dict[str, Any]] = Field(default_factory=list)
    demo_html: Optional[Dict[str, Any]] = None
    use_simulation: bool = True
    artifacts_history: List[Dict[str, Any]] = Field(default_factory=list)


class VerifierResult(BaseModel):
    passed: bool
    status_code: int = 0
    summary: str
    error_log: Optional[str] = None
    checks: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool
    output: str
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0


class WebSocketEvent(BaseModel):
    event_type: str
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any] = Field(default_factory=dict)


class CreateSessionRequest(BaseModel):
    objective: str
    cost_constrained: bool = False
    sandbox_path: Optional[str] = None
    project_path: Optional[str] = None
    project_type: Optional[str] = "generic"
    use_simulation: bool = True
    max_iterations: int = 15
    selected_provider_override: Optional[ModelProvider] = None
    reference_media: List[Dict[str, Any]] = Field(default_factory=list)
    demo_html: Optional[Dict[str, Any]] = None


class ConfigSettings(BaseModel):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    github_token: Optional[str] = None
    simulation_mode: bool = True
    default_cost_constrained: bool = False
    auto_push_github: bool = False
    use_local_provider: bool = False
    local_provider_type: str = "ollama"  # "ollama", "claude-cli", or "gemini-cli"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_base_url: str = "http://localhost:11434"
    gemini_cli_command: str = "gemini"
