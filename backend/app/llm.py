import os
import json
import httpx
from typing import Dict, Any, List, Optional
from app.schemas import ModelProvider, SubTask, TaskDomain


class LLMClient:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

    async def execute_task(
        self,
        task: SubTask,
        model: ModelProvider,
        context: Dict[str, Any],
        simulate_error: bool = False,
    ) -> Dict[str, Any]:
        has_real_key = bool(
            (model in [ModelProvider.CLAUDE_SONNET, ModelProvider.CLAUDE_OPUS] and self.anthropic_key)
            or (model in [ModelProvider.GPT_4O, ModelProvider.GPT_4O_MINI] and self.openai_key)
            or (model == ModelProvider.GEMINI_PRO and self.google_key)
            or (self.openrouter_key)
        )

        # Fall back to simulation if no API keys are provided or simulation is enforced
        if not has_real_key or model == ModelProvider.SIMULATOR:
            return await self._simulate_execution(task, model, context, simulate_error)

        try:
            return await self._call_real_provider(task, model, context)
        except Exception as e:
            # Fallback gracefully with error explanation
            res = await self._simulate_execution(task, model, context, simulate_error)
            res["output"] = f"[Live API Call Error: {str(e)} - Fell back to simulated output]\n\n" + res["output"]
            return res

    async def _call_real_provider(
        self, task: SubTask, model: ModelProvider, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an autonomous senior software engineer agent in a multi-agent team. "
            "You must return your output strictly in JSON format with keys:\n"
            "- 'files': list of file paths created or modified (e.g. ['src/service.py'])\n"
            "- 'code_changes': dict mapping file_path to complete code content\n"
            "- 'explanation': markdown text explanation of decisions made\n"
            "- 'commands': list of shell commands to execute"
        )
        user_prompt = (
            f"Subtask: {task.title}\n"
            f"Description: {task.description}\n"
            f"Domain: {task.domain.value}\n"
            f"Complexity Level: {task.complexity}/10\n"
            f"Context: {json.dumps(context)}"
        )

        # 1. Anthropic Claude API
        if model in [ModelProvider.CLAUDE_SONNET, ModelProvider.CLAUDE_OPUS] and self.anthropic_key:
            claude_model = (
                "claude-3-5-sonnet-20241022"
                if model == ModelProvider.CLAUDE_SONNET
                else "claude-3-opus-20240229"
            )
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": claude_model,
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                data = res.json()
                raw_text = data["content"][0]["text"]
                parsed = json.loads(raw_text) if raw_text.strip().startswith("{") else {"explanation": raw_text, "files": [], "code_changes": {}}
                usage = data.get("usage", {})
                return {
                    "output": parsed.get("explanation", raw_text),
                    "files": parsed.get("files", []),
                    "code_changes": parsed.get("code_changes", {}),
                    "commands": parsed.get("commands", []),
                    "input_tokens": usage.get("input_tokens", 1000),
                    "output_tokens": usage.get("output_tokens", 500),
                }

        # 2. OpenAI API
        if model in [ModelProvider.GPT_4O, ModelProvider.GPT_4O_MINI] and self.openai_key:
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o" if model == ModelProvider.GPT_4O else "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                usage = data.get("usage", {})
                return {
                    "output": parsed.get("explanation", "Task executed."),
                    "files": parsed.get("files", []),
                    "code_changes": parsed.get("code_changes", {}),
                    "commands": parsed.get("commands", []),
                    "input_tokens": usage.get("prompt_tokens", 1000),
                    "output_tokens": usage.get("completion_tokens", 500),
                }

        # 3. OpenRouter API
        if self.openrouter_key:
            model_map = {
                ModelProvider.CLAUDE_SONNET: "anthropic/claude-3.5-sonnet",
                ModelProvider.CLAUDE_OPUS: "anthropic/claude-3-opus",
                ModelProvider.GPT_4O: "openai/gpt-4o",
                ModelProvider.GPT_4O_MINI: "openai/gpt-4o-mini",
                ModelProvider.GEMINI_PRO: "google/gemini-pro-1.5",
                ModelProvider.DEEPSEEK_CODER: "deepseek/deepseek-chat",
            }
            target_model = model_map.get(model, "openai/gpt-4o-mini")
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": target_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content) if content.strip().startswith("{") else {"explanation": content, "files": [], "code_changes": {}}
                usage = data.get("usage", {})
                return {
                    "output": parsed.get("explanation", content),
                    "files": parsed.get("files", []),
                    "code_changes": parsed.get("code_changes", {}),
                    "commands": parsed.get("commands", []),
                    "input_tokens": usage.get("prompt_tokens", 1000),
                    "output_tokens": usage.get("completion_tokens", 500),
                }

        # Fallback simulation
        return await self._simulate_execution(task, model, context, simulate_error=False)

    async def _simulate_execution(
        self,
        task: SubTask,
        model: ModelProvider,
        context: Dict[str, Any],
        simulate_error: bool,
    ) -> Dict[str, Any]:
        files: List[str] = []
        code_changes: Dict[str, str] = {}
        commands: List[str] = []

        # If deliberate error simulation is requested (e.g. testing replanning loop)
        if simulate_error and task.domain == TaskDomain.IMPLEMENTATION and not task.retry_of:
            files.append("src/service.py")
            code_changes["src/service.py"] = (
                "def calculate_total(items):\n"
                "    total = 0\n"
                "    for item in items\n"  # Missing colon creates deterministic syntax error
                "        total += item.price\n"
                "    return total\n"
            )
            return {
                "output": f"Implemented service module (Intentional test flaw in task {task.task_id} to demonstrate replanning loop).",
                "files": files,
                "code_changes": code_changes,
                "commands": commands,
                "input_tokens": 850,
                "output_tokens": 420,
            }

        # Successful implementations
        if task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
            files.append("docs/architecture_spec.md")
            code_changes["docs/architecture_spec.md"] = (
                f"# Architecture Specification\n\n"
                f"## Objective\n{task.description}\n\n"
                f"## Domain\n{task.domain.value}\n\n"
                f"## Components\n- Core Processor Module\n- API Ingestion Gateway\n- Verification Engine\n"
            )
            explanation = f"Completed architectural blueprint and structural requirements for {task.title}."

        elif task.domain == TaskDomain.IMPLEMENTATION:
            if "service" in task.title.lower() or "core" in task.title.lower() or task.retry_of:
                files.append("src/service.py")
                code_changes["src/service.py"] = (
                    "class OrderService:\n"
                    "    def __init__(self, tax_rate: float = 0.08):\n"
                    "        self.tax_rate = tax_rate\n\n"
                    "    def calculate_subtotal(self, prices: list[float]) -> float:\n"
                    "        return round(sum(prices), 2)\n\n"
                    "    def calculate_total(self, prices: list[float]) -> float:\n"
                    "        subtotal = self.calculate_subtotal(prices)\n"
                    "        return round(subtotal * (1 + self.tax_rate), 2)\n"
                )
            else:
                files.append("src/utils.py")
                code_changes["src/utils.py"] = (
                    "import re\n\n"
                    "def sanitize_identifier(name: str) -> str:\n"
                    "    return re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())\n"
                )
            explanation = f"Implemented clean type-safe implementation for {task.title} with complete error handling."

        elif task.domain == TaskDomain.VERIFICATION:
            files.append("tests/test_service.py")
            code_changes["tests/test_service.py"] = (
                "from src.service import OrderService\n\n"
                "def test_order_subtotal():\n"
                "    svc = OrderService(tax_rate=0.10)\n"
                "    assert svc.calculate_subtotal([10.0, 20.0, 5.0]) == 35.0\n\n"
                "def test_order_total_with_tax():\n"
                "    svc = OrderService(tax_rate=0.10)\n"
                "    assert svc.calculate_total([100.0]) == 110.0\n"
            )
            commands.append("pytest -q tests/test_service.py")
            explanation = f"Generated unit tests and automated verification harness for {task.title}."

        else:
            files.append("config.json")
            code_changes["config.json"] = json.dumps(
                {"env": "development", "task_id": task.task_id, "active": True},
                indent=2,
            )
            explanation = f"Configured workspace environment for {task.title}."

        return {
            "output": explanation,
            "files": files,
            "code_changes": code_changes,
            "commands": commands,
            "input_tokens": 1200 + (task.complexity * 250),
            "output_tokens": 600 + (task.complexity * 120),
        }
