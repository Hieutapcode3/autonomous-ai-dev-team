import os
import json
import re
import shutil
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Callable, Awaitable
from app.schemas import ModelProvider, SubTask, TaskDomain


def _parse_model_json_output(raw_text: str) -> Dict[str, Any]:
    """Parse JSON output from LLM/CLI response with fallback regex extraction."""
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract JSON fenced inside markdown code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Extract outermost JSON object
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except Exception:
            pass

    return {"explanation": raw_text, "files": [], "code_changes": {}, "commands": []}


# Ordered list of current Gemini models to try, newest first.
# Update this list whenever Google releases or deprecates models.
GEMINI_MODELS_PRIORITY = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.0-ultra-5",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash-latest",
]

NON_DESTRUCTIVE_RULES = (
    "=== MANDATORY PRE-EXECUTION NECESSITY (YAGNI) & NON-DESTRUCTIVE EDITING RULES ===\n"
    "1. NECESSITY CHECK (YAGNI):\n"
    "   Before touching ANY file, ask: 'Is modifying this existing file strictly necessary to achieve the objective?'\n"
    "   'Can this feature be created as a NEW standalone script/component instead?'\n"
    "   PREFER creating NEW files over modifying existing working scripts.\n\n"
    "2. STRICT PROHIBITION ON DELETING OR TRUNCATING EXISTING CODE:\n"
    "   - You are STRICTLY FORBIDDEN from deleting, removing, renaming, or commenting out ANY existing methods, properties, fields, or logic.\n"
    "   - Never omit code with placeholders like '// ... existing code ...'.\n"
    "   - NEVER delete public methods (like ReloadCurrentLevel, LoadNextLevel, ContainsCell, etc.) that other scripts in the project depend on.\n"
    "   - If modifying an existing file: PRESERVE ALL ORIGINAL CODE intact. You may ONLY append new methods or surgically insert minimal hooks.\n\n"
    "3. MINIMAL SURGICAL EDITS:\n"
    "   - Do NOT rewrite a 500+ line file from scratch if you only need to add 1 method.\n"
    "   - Do NOT refactor, reformat, or reorganize existing working code.\n\n"
    "4. MANDATORY FULL IMPLEMENTATION — ZERO SKELETON STUBS ALLOWED:\n"
    "   - You are STRICTLY FORBIDDEN from generating skeletal stubs, dummy templates, or placeholder comments (e.g. '// TODO', '// implement logic here', '/* ... */').\n"
    "   - Every class, method, event callback, and algorithm MUST be fully and concretely implemented in complete, working C#.\n"
    "   - Do NOT output 40-50 line minimal stubs that merely open an empty window or log a message. Fully implement the data structures, UI element bindings, toolbar tools, and serialization.\n"
    "   - Any skeletal stub will be IMMEDIATELY REJECTED by the Quality Gate Verifier.\n"
)


class LLMClient:
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.ollama_base_url = ollama_base_url

    async def execute_task(
        self,
        task: SubTask,
        model: ModelProvider,
        context: Dict[str, Any],
        simulate_error: bool = False,
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        # Guard: check stop signal before doing any work
        if stop_event and stop_event.is_set():
            raise asyncio.CancelledError("Task cancelled by stop signal before execution.")

        # 1. Local Ollama execution (Free, local AI)
        if model in [ModelProvider.OLLAMA_QWEN, ModelProvider.OLLAMA_DEEPSEEK]:
            ollama_model_name = (
                "qwen2.5-coder:7b"
                if model == ModelProvider.OLLAMA_QWEN
                else "deepseek-coder:6.7b"
            )
            try:
                return await self._call_ollama(task, ollama_model_name, context, log_callback, stop_event=stop_event)
            except Exception as e:
                if log_callback:
                    await log_callback("Ollama", f"Ollama error: {str(e)} - falling back to simulation", "WARN")
                res = await self._simulate_execution(task, model, context, simulate_error)
                res["output"] = f"[Local Ollama Error: {str(e)} - Fell back to simulated output]\n\n" + res["output"]
                return res

        # 2. Local Claude Code CLI execution
        if model == ModelProvider.CLAUDE_CLI:
            try:
                return await self._call_claude_cli(task, context, log_callback)
            except Exception as e:
                try:
                    if log_callback:
                        await log_callback("CLI", f"Claude CLI error ({str(e)}). Redirecting to Local Ollama...", "WARN")
                    return await self._call_ollama(task, "qwen2.5-coder:7b", context, log_callback)
                except Exception:
                    pass
                if log_callback:
                    await log_callback("CLI", f"Claude CLI error: {str(e)} - falling back to simulation", "WARN")
                res = await self._simulate_execution(task, model, context, simulate_error)
                res["output"] = f"[Claude CLI Error: {str(e)} - Fell back to simulated output]\n\n" + res["output"]
                return res

        # 3. Google Gemini - always call Direct REST API first (CLI is too old)
        if model == ModelProvider.GEMINI_CLI:
            google_tok = self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if google_tok:
                try:
                    return await self._call_gemini_api(task, context, log_callback, stop_event=stop_event)
                except asyncio.CancelledError:
                    raise
                except Exception as api_err:
                    clean_api_err = str(api_err).replace("\n", " ").strip()
                    if log_callback:
                        await log_callback("GEMINI", f"All Gemini REST models failed ({clean_api_err[:120]}). Trying CLI fallback...", "WARN")
            try:
                return await self._call_gemini_cli(task, context, log_callback)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                clean_err = str(e).replace("\n", " ").strip()
                try:
                    if log_callback:
                        await log_callback("GEMINI", f"Gemini CLI also failed ({clean_err[:80]}). Redirecting to Local Ollama...", "WARN")
                    return await self._call_ollama(task, "qwen2.5-coder:7b", context, log_callback, stop_event=stop_event)
                except Exception:
                    pass
                if log_callback:
                    await log_callback("GEMINI", f"All Gemini paths failed. Falling back to simulation.", "WARN")
                res = await self._simulate_execution(task, model, context, simulate_error)
                res["output"] = f"[Gemini Error: {clean_err} - Fell back to simulated output]\n\n" + res["output"]
                return res

        has_real_key = bool(
            (model in [ModelProvider.CLAUDE_SONNET, ModelProvider.CLAUDE_OPUS] and self.anthropic_key)
            or (model in [ModelProvider.GPT_4O, ModelProvider.GPT_4O_MINI] and self.openai_key)
            or (model == ModelProvider.GEMINI_PRO and (self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")))
            or (self.openrouter_key)
            or (self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        )

        # Fall back to simulation if no API keys are provided or simulation is enforced
        if not has_real_key or model == ModelProvider.SIMULATOR:
            return await self._simulate_execution(task, model, context, simulate_error)

        try:
            return await self._call_real_provider(task, model, context, log_callback)
        except Exception as e:
            res = await self._simulate_execution(task, model, context, simulate_error)
            res["output"] = f"[Live API Call Error: {str(e)} - Fell back to simulated output]\n\n" + res["output"]
            return res

    async def _call_real_provider(
        self,
        task: SubTask,
        model: ModelProvider,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        rules_list = context.get("rules", [])
        rules_text = "\n".join([f"- {r.get('title')}: {r.get('content')}" for r in rules_list]) if rules_list else "Standard clean code."
        skills_list = context.get("skills", [])
        skills_text = "\n".join([f"- {s.get('name')}: {s.get('description')}" for s in skills_list]) if skills_list else "None."

        media_list = context.get("reference_media", [])
        media_text = (
            "\n".join([f"- {m.get('name')} ({m.get('media_type')}): {m.get('file_path')}" for m in media_list])
            if media_list
            else "None."
        )

        demo_html = context.get("demo_html")
        demo_text = "None."
        if demo_html:
            extracted = demo_html.get("extracted_logic") or {}
            funcs_str = ", ".join(extracted.get("functions", []))
            vars_str = ", ".join(extracted.get("variables", []))
            code_snippet = extracted.get("code_snippet", "")
            demo_text = (
                f"- Playable Demo: {demo_html.get('name')} ({demo_html.get('file_path')})\n"
                f"  Extracted Functions: {funcs_str}\n"
                f"  Variables/Constants: {vars_str}\n"
                f"  Code/Logic Excerpt:\n```javascript\n{code_snippet[:2000]}\n```"
            )

        system_prompt = (
            "You are an autonomous senior software engineer agent in a multi-agent team.\n\n"
            f"MANDATORY PROJECT RULES (NON-NEGOTIABLE):\n{rules_text}\n\n"
            f"AVAILABLE WORKFLOW SKILLS:\n{skills_text}\n\n"
            f"VISUAL & ART REFERENCES:\n{media_text}\n"
            "Analyze and adhere to the visual composition, UI anchors, spatial hierarchy, and art style conveyed in the reference media.\n\n"
            f"PLAYABLE HTML GAME DEMO & MECHANICS:\n{demo_text}\n"
            "If a playable HTML demo is provided, extract its core game loop, event handlers, math formulas, collision detection, and scoring mechanics, and port them faithfully into clean, idiomatic Unity C# scripts.\n\n"
            "You must return your output strictly in JSON format with keys:\n"
            "- 'files': list of file paths created or modified\n"
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
                        "max_tokens": 8192,
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

        # 4. Google Gemini API
        gemini_token = self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if (model == ModelProvider.GEMINI_PRO or (gemini_token and not self.anthropic_key and not self.openai_key and not self.openrouter_key)) and gemini_token:
            return await self._call_gemini_api(task, context, log_callback, stop_event=stop_event)

        # Fallback simulation
        return await self._simulate_execution(task, model, context, simulate_error=False)

    async def _call_gemini_api(
        self,
        task: SubTask,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        model_name: Optional[str] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """Execute task using official Google Gemini REST API with JSON response format."""
        api_token = self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_token:
            raise RuntimeError("Google Gemini API Key is required but not configured.")

        rules_list = context.get("rules", [])
        rules_text = "\n".join([f"- {r.get('title')}: {r.get('content')}" for r in rules_list]) if rules_list else "Standard clean code."
        skills_list = context.get("skills", [])
        skills_text = "\n".join([f"- {s.get('name')}: {s.get('description')}" for s in skills_list]) if skills_list else "None."

        media_list = context.get("reference_media", [])
        media_text = (
            "\n".join([f"- {m.get('name')} ({m.get('media_type')}): {m.get('file_path')}" for m in media_list])
            if media_list
            else "None."
        )

        demo_html = context.get("demo_html")
        demo_text = "None."
        if demo_html:
            extracted = demo_html.get("extracted_logic") or {}
            funcs_str = ", ".join(extracted.get("functions", []))
            vars_str = ", ".join(extracted.get("variables", []))
            code_snippet = extracted.get("code_snippet", "")
            demo_text = (
                f"- Playable Demo: {demo_html.get('name')} ({demo_html.get('file_path')})\n"
                f"  Extracted Functions: {funcs_str}\n"
                f"  Variables/Constants: {vars_str}\n"
                f"  Code/Logic Excerpt:\n```javascript\n{code_snippet[:2000]}\n```"
            )

        system_instruction = (
            "You are an autonomous senior software engineer and game developer agent in a multi-agent team.\n"
            f"{NON_DESTRUCTIVE_RULES}\n"
            "CRITICAL MANDATORY INSTRUCTION: You MUST generate actual, concrete code changes.\n"
            "You must return your output strictly in JSON format with keys:\n"
            "- 'files': list of relative file paths created or modified (e.g. ['Assets/BlockHome/Scripts/CoreScript/GamePlay/_Human/HumanActor.cs'])\n"
            "- 'code_changes': dict mapping file_path to complete code content containing the implementation\n"
            "- 'explanation': markdown text explanation of decisions made and code changes\n"
            "- 'commands': list of shell commands to execute (optional)\n\n"
            f"MANDATORY PROJECT RULES:\n{rules_text}\n\n"
            f"AVAILABLE WORKFLOW SKILLS:\n{skills_text}\n\n"
            f"VISUAL & ART REFERENCES:\n{media_text}\n\n"
            f"PLAYABLE DEMO LOGIC:\n{demo_text}\n"
        )

        target_files_hint = ", ".join(task.target_files) if task.target_files else "determine based on objective"

        existing_files = context.get("existing_file_contents", {})
        existing_files_text = "None."
        if existing_files:
            parts = []
            for path, content in existing_files.items():
                parts.append(f"### {path}\n```\n{content}\n```")
            existing_files_text = "\n\n".join(parts)

        orig_backups = context.get("original_pre_edit_contents", {})
        orig_text = ""
        if orig_backups:
            parts = []
            for path, content in orig_backups.items():
                parts.append(f"### ORIGINAL UNMODIFIED {path} (RESTORE MISSING METHODS FROM THIS):\n```\n{content[:4000]}\n```")
            orig_text = f"\n\nORIGINAL CODE BEFORE TASK (CRITICAL REFERENCE — PRESERVE ALL ITS METHODS):\n" + "\n\n".join(parts)

        prior_outputs = context.get("prior_task_outputs", {})
        prior_outputs_text = "None."
        if prior_outputs:
            parts = []
            for path, content in prior_outputs.items():
                parts.append(f"### {path}\n```\n{content[:3000]}\n```")
            prior_outputs_text = "\n\n".join(parts)

        user_content = (
            f"Overall Objective: {context.get('objective', '')}\n"
            f"Project Directory: {context.get('project_path', 'Sandbox')}\n"
            f"Subtask: {task.title}\n"
            f"Description: {task.description}\n"
            f"Domain: {task.domain.value}\n"
            f"Target Files: {target_files_hint}\n"
            f"Complexity Level: {task.complexity}/10\n\n"
            f"{NON_DESTRUCTIVE_RULES}\n\n"
            f"EXISTING FILE CONTENTS (read these carefully — modify them, do NOT rewrite from scratch):\n{existing_files_text}\n"
            f"{orig_text}\n\n"
            f"PRIOR TASK OUTPUTS IN THIS SESSION (already written by earlier tasks — do not duplicate):\n{prior_outputs_text}\n"
        )

        # Build the candidate list: if caller specified a model, try it first; then walk the priority list.
        if model_name:
            models_to_try = [model_name] + [m for m in GEMINI_MODELS_PRIORITY if m != model_name]
        else:
            models_to_try = list(GEMINI_MODELS_PRIORITY)

        last_error = None
        for candidate_model in models_to_try:
            # Honour stop signal between model attempts
            if stop_event and stop_event.is_set():
                raise asyncio.CancelledError("Gemini API call cancelled by stop signal.")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={api_token}"
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_content}]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                    "maxOutputTokens": 8192,
                }
            }

            if log_callback:
                await log_callback("GEMINI", f"Calling Google Gemini API model [{candidate_model}]...", "INFO")

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise RuntimeError("Gemini API returned no candidates.")

                        candidate = candidates[0]
                        parts = candidate.get("content", {}).get("parts", [])
                        raw_text = "".join([p.get("text", "") for p in parts])
                        parsed = _parse_model_json_output(raw_text)

                        usage = data.get("usageMetadata", {})
                        in_toks = usage.get("promptTokenCount", 1200)
                        out_toks = usage.get("candidatesTokenCount", 600)

                        if log_callback:
                            await log_callback(
                                "GEMINI",
                                f"Gemini [{candidate_model}] generated response ({in_toks} in / {out_toks} out tokens).",
                                "SUCCESS",
                            )

                        return {
                            "output": parsed.get("explanation", raw_text[:300] + "..."),
                            "files": parsed.get("files", []),
                            "code_changes": parsed.get("code_changes", {}),
                            "commands": parsed.get("commands", []),
                            "input_tokens": in_toks,
                            "output_tokens": out_toks,
                        }
                    else:
                        err_body = resp.text
                        last_error = f"HTTP {resp.status_code}: {err_body[:200]}"
                        if log_callback:
                            await log_callback(
                                "GEMINI",
                                f"Gemini [{candidate_model}] returned HTTP {resp.status_code}. Trying next model...",
                                "WARN",
                            )
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                last_error = str(ex)
                if log_callback:
                    await log_callback("GEMINI", f"Error with [{candidate_model}]: {str(ex)[:150]}", "WARN")

        raise RuntimeError(f"All Google Gemini models failed. Last error: {last_error}")

    async def _call_ollama(
        self,
        task: SubTask,
        model_name: str,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """Execute task using local Ollama instance with streaming logs."""
        if stop_event and stop_event.is_set():
            raise asyncio.CancelledError("Ollama call cancelled by stop signal.")
        if log_callback:
            await log_callback("Ollama", f"Connected to local Ollama on {self.ollama_base_url}", "INFO")
            await log_callback("Ollama", f"Running model: [{model_name}] for subtask #{task.task_id}...", "INFO")

        system_prompt = (
            "You are an autonomous senior software engineer and game developer agent in a multi-agent team.\n"
            f"{NON_DESTRUCTIVE_RULES}\n"
            "CRITICAL MANDATORY INSTRUCTION: You MUST generate actual, concrete code changes.\n"
            "You must return your output strictly in JSON format with keys:\n"
            "- 'files': list of relative file paths created or modified (e.g. ['Assets/BlockHome/Scripts/CoreScript/GamePlay/_Human/HumanActor.cs'])\n"
            "- 'code_changes': dict mapping file_path to complete code content containing the implementation\n"
            "- 'explanation': markdown text explanation of decisions made and code changes\n"
            "- 'commands': list of shell commands to execute (optional)\n"
            "Do NOT return empty 'code_changes' or empty 'files' for implementation tasks!"
        )

        project_type = context.get("project_type", "generic")
        target_files_hint = ", ".join(task.target_files) if task.target_files else "determine based on objective"
        rules_str = "\n".join([f"- {r.get('title')}: {r.get('content')}" for r in context.get("rules", [])[:4]])

        existing_files = context.get("existing_file_contents", {})
        existing_files_text = "None."
        if existing_files:
            parts = []
            for path, content in existing_files.items():
                parts.append(f"### {path}\n```\n{content}\n```")
            existing_files_text = "\n\n".join(parts)

        orig_backups = context.get("original_pre_edit_contents", {})
        orig_text = ""
        if orig_backups:
            parts = []
            for path, content in orig_backups.items():
                parts.append(f"### ORIGINAL UNMODIFIED {path} (RESTORE MISSING METHODS FROM THIS):\n```\n{content[:4000]}\n```")
            orig_text = f"\n\nORIGINAL CODE BEFORE TASK (CRITICAL REFERENCE — PRESERVE ALL ITS METHODS):\n" + "\n\n".join(parts)

        prior_outputs = context.get("prior_task_outputs", {})
        prior_outputs_text = "None."
        if prior_outputs:
            parts = []
            for path, content in prior_outputs.items():
                parts.append(f"### {path}\n```\n{content[:3000]}\n```")
            prior_outputs_text = "\n\n".join(parts)

        user_prompt = (
            f"Overall Objective: {context.get('objective', '')}\n"
            f"Project Directory: {context.get('project_path', 'Sandbox')}\n"
            f"Project Type: {project_type.upper()}\n"
            f"Subtask #{task.task_id}: {task.title}\n"
            f"Description: {task.description}\n"
            f"Domain: {task.domain.value}\n"
            f"Target Files: {target_files_hint}\n\n"
            f"{NON_DESTRUCTIVE_RULES}\n\n"
            f"Project Guidelines:\n{rules_str}\n\n"
            f"EXISTING FILE CONTENTS (read carefully — modify them, do NOT rewrite from scratch):\n{existing_files_text}\n"
            f"{orig_text}\n\n"
            f"PRIOR TASK OUTPUTS IN THIS SESSION (already written — do not duplicate):\n{prior_outputs_text}\n\n"
            "Please output JSON with 'files' and 'code_changes' containing the concrete code."
        )

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": True,
            "options": {
                "num_predict": 8192,
                "temperature": 0.2,
            },
        }

        accumulated_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        line_buffer = ""

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{self.ollama_base_url}/api/chat", json=payload) as response:
                async for chunk_bytes in response.aiter_lines():
                    if not chunk_bytes:
                        continue
                    try:
                        chunk = json.loads(chunk_bytes)
                        content_piece = chunk.get("message", {}).get("content", "")
                        accumulated_text += content_piece
                        line_buffer += content_piece

                        if "\n" in line_buffer and log_callback:
                            lines = line_buffer.split("\n")
                            line_buffer = lines[-1]
                            for l in lines[:-1]:
                                stripped = l.strip()
                                if stripped and (stripped.startswith('"') or stripped.startswith("{") or "def " in stripped or "class " in stripped):
                                    await log_callback("Ollama", stripped[:120], "INFO")

                        if chunk.get("done"):
                            prompt_tokens = chunk.get("prompt_eval_count", 0)
                            completion_tokens = chunk.get("eval_count", 0)
                    except Exception:
                        continue

        if log_callback:
            await log_callback(
                "Ollama",
                f"Generation finished ({completion_tokens} tokens). Parsing output structure...",
                "SUCCESS",
            )

        parsed = _parse_model_json_output(accumulated_text)
        files = parsed.get("files", [])
        code_changes = parsed.get("code_changes", {})

        # Fallback if model put code in explanation without separating files
        has_code_keywords = any(kw in accumulated_text for kw in ["class ", "def ", "using UnityEngine", "MonoBehaviour", "namespace "])
        if not code_changes and has_code_keywords:
            if project_type == "unity":
                default_file = task.target_files[0] if task.target_files else "Assets/Scripts/Gameplay/GameController.cs"
            else:
                default_file = task.target_files[0] if task.target_files else f"src/{task.domain.value}_module.py"
            files.append(default_file)
            code_changes[default_file] = accumulated_text

        return {
            "output": parsed.get("explanation", accumulated_text[:300] + "..."),
            "files": files,
            "code_changes": code_changes,
            "commands": parsed.get("commands", []),
            "input_tokens": prompt_tokens or 1000,
            "output_tokens": completion_tokens or 500,
        }

    async def _call_claude_cli(
        self,
        task: SubTask,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Execute task by spawning local Claude Code CLI subprocess and streaming output."""
        claude_bin = shutil.which("claude")
        if not claude_bin:
            local_bin = os.path.expanduser("~/.local/bin/claude.exe")
            if os.path.exists(local_bin):
                claude_bin = local_bin
            else:
                raise RuntimeError("Claude Code CLI executable not found on system PATH or ~/.local/bin/claude.exe")

        prompt = (
            f"You are an autonomous senior software engineer. Output strictly valid JSON with keys: "
            f"'files', 'code_changes', 'explanation', 'commands'.\n"
            f"Subtask: {task.title}\n"
            f"Description: {task.description}\n"
            f"Domain: {task.domain.value}\n"
            f"Context: {json.dumps(context)}"
        )

        if log_callback:
            await log_callback("CLI", f"Spawning: {claude_bin} --print (Streaming stdout/stderr)...", "INFO")

        proc = await asyncio.create_subprocess_exec(
            claude_bin,
            "--print",
            prompt,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_lines = []
        # Stream stdout line by line
        async def read_stdout():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                stdout_lines.append(decoded)
                if log_callback and decoded:
                    await log_callback("CLI", decoded[:140], "INFO")

        async def read_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                if log_callback and decoded:
                    await log_callback("CLI", f"[stderr] {decoded}", "WARN")

        # Feed empty stdin immediately to prevent CLI hanging on Windows
        if proc.stdin:
            proc.stdin.close()

        try:
            await asyncio.wait_for(asyncio.gather(read_stdout(), read_stderr()), timeout=60.0)
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            raise RuntimeError("Claude CLI process timed out after 60s")

        full_stdout = "\n".join(stdout_lines)

        if proc.returncode != 0:
            if "Not logged in" in full_stdout or "Please run /login" in full_stdout:
                raise RuntimeError("Claude CLI is not authenticated. Please run 'claude auth login' in your terminal.")
            raise RuntimeError(f"Claude CLI exited with code {proc.returncode}")

        if log_callback:
            await log_callback("CLI", "Claude CLI execution succeeded. Parsing response...", "SUCCESS")

        parsed = _parse_model_json_output(full_stdout)
        return {
            "output": parsed.get("explanation", full_stdout[:300] + "..."),
            "files": parsed.get("files", []),
            "code_changes": parsed.get("code_changes", {}),
            "commands": parsed.get("commands", []),
            "input_tokens": 1200,
            "output_tokens": 600,
        }

    async def _call_gemini_cli(
        self,
        task: SubTask,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Execute task by spawning local Google Gemini CLI subprocess and streaming output."""
        gemini_bin = (
            shutil.which("gemini-cli")
            or shutil.which("gemini")
            or shutil.which("gemini-cli.exe")
            or shutil.which("gemini.exe")
        )
        if not gemini_bin:
            candidate_dirs = [
                os.path.expanduser("~\\AppData\\Local\\Programs\\Python\\Python312\\Scripts"),
                os.path.expanduser("~\\AppData\\Roaming\\Python\\Python312\\Scripts"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts"),
            ]
            for d in candidate_dirs:
                for fname in ["gemini-cli.exe", "gemini.exe", "gemini-cli.cmd", "gemini.cmd"]:
                    full_p = os.path.join(d, fname)
                    if os.path.exists(full_p):
                        gemini_bin = full_p
                        break
                if gemini_bin:
                    break

        if not gemini_bin:
            if log_callback:
                await log_callback(
                    "GEMINI",
                    "Gemini CLI ('gemini') not found on PATH. Run: pip install gemini-cli",
                    "ERROR",
                )
            raise RuntimeError("Gemini CLI ('gemini') executable not found. Install via 'pip install gemini-cli'")

        existing_files = context.get("existing_file_contents", {})
        existing_files_text = "None."
        if existing_files:
            parts = []
            for path, content in existing_files.items():
                parts.append(f"### {path}\n```\n{content[:4000]}\n```")
            existing_files_text = "\n\n".join(parts)

        orig_backups = context.get("original_pre_edit_contents", {})
        orig_text = ""
        if orig_backups:
            parts = []
            for path, content in orig_backups.items():
                parts.append(f"### ORIGINAL UNMODIFIED {path} (RESTORE MISSING METHODS FROM THIS):\n```\n{content[:4000]}\n```")
            orig_text = f"\n\nORIGINAL CODE BEFORE TASK (CRITICAL REFERENCE — PRESERVE ALL ITS METHODS):\n" + "\n\n".join(parts)

        prior_outputs = context.get("prior_task_outputs", {})
        prior_outputs_text = "None."
        if prior_outputs:
            parts = []
            for path, content in prior_outputs.items():
                parts.append(f"### {path}\n```\n{content[:2000]}\n```")
            prior_outputs_text = "\n\n".join(parts)

        prompt = (
            f"You are an autonomous senior software engineer. Output strictly valid JSON with keys: "
            f"'files', 'code_changes', 'explanation', 'commands'.\n\n"
            f"{NON_DESTRUCTIVE_RULES}\n\n"
            f"Overall Objective: {context.get('objective', '')}\n"
            f"Project Directory: {context.get('project_path', 'Sandbox')}\n"
            f"Subtask: {task.title}\n"
            f"Description: {task.description}\n"
            f"Domain: {task.domain.value}\n"
            f"Target Files: {', '.join(task.target_files) if task.target_files else 'None'}\n\n"
            f"EXISTING FILE CONTENTS:\n{existing_files_text}\n"
            f"{orig_text}\n\n"
            f"PRIOR TASK OUTPUTS:\n{prior_outputs_text}\n\n"
            f"Output strictly valid JSON with keys: 'files', 'code_changes', 'explanation', 'commands'."
        )

        api_token = self.google_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        token_file = os.path.expanduser("~/.config/gemini-cli.toml")
        if not api_token and not os.path.exists(token_file):
            raise RuntimeError(
                "Gemini CLI requires Google API Token. Configure Google API Key in Settings or set GOOGLE_API_KEY."
            )

        if log_callback:
            await log_callback("GEMINI", f"Spawning: {gemini_bin}...", "INFO")

        cmd_args = [gemini_bin]
        if api_token:
            cmd_args.extend(["-t", api_token])
        cmd_args.append(prompt)

        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_lines = []
        stderr_lines = []

        async def read_stdout():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                stdout_lines.append(decoded)
                if log_callback and decoded:
                    await log_callback("GEMINI", decoded[:140], "INFO")

        async def read_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                stderr_lines.append(decoded)
                if log_callback and decoded:
                    await log_callback("GEMINI", f"[stderr] {decoded}", "WARN")

        if proc.stdin:
            proc.stdin.close()

        try:
            await asyncio.wait_for(asyncio.gather(read_stdout(), read_stderr()), timeout=60.0)
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            raise RuntimeError("Gemini CLI process timed out after 60s")

        full_stdout = "\n".join(stdout_lines)
        full_stderr = "\n".join(stderr_lines)

        if proc.returncode != 0:
            error_detail = full_stderr.strip() or full_stdout.strip() or f"Process exited with code {proc.returncode}"
            raise RuntimeError(f"{error_detail}")

        if log_callback:
            await log_callback("GEMINI", "Gemini CLI execution succeeded. Parsing response...", "SUCCESS")

        parsed = _parse_model_json_output(full_stdout)
        return {
            "output": parsed.get("explanation", full_stdout[:300] + "..."),
            "files": parsed.get("files", []),
            "code_changes": parsed.get("code_changes", {}),
            "commands": parsed.get("commands", []),
            "input_tokens": 1200,
            "output_tokens": 600,
        }

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
        is_unity = context.get("project_type") == "unity"

        if is_unity:
            if task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
                target = "Assets/Scripts/Architecture/GameArchitectureSpec.md"
                files.append(target)
                ref_media = context.get("reference_media", [])
                demo_html = context.get("demo_html")
                ref_section = ""
                if ref_media:
                    ref_section = "\n## Visual & Art References Analyzed\n"
                    for m in ref_media:
                        ref_section += f"- **{m.get('name')}** ({m.get('media_type', 'image')})\n  - Path: `{m.get('file_path')}`\n  - Art & Composition Directives: UI anchor alignment, color theme mapping, and visual hierarchy integrated into hierarchy planning.\n"

                demo_section = ""
                if demo_html:
                    extracted = demo_html.get("extracted_logic") or {}
                    funcs = extracted.get("functions", [])
                    funcs_desc = ", ".join(funcs[:8]) if funcs else "Core game loop & scoring"
                    demo_section = (
                        f"\n## Playable HTML Game Demo Mechanics Ported\n"
                        f"- Prototype File: `{demo_html.get('name')}`\n"
                        f"- Ported Mechanics: Canvas game loop translated to Unity MonoBehaviour Update() & FixedUpdate().\n"
                        f"- Extracted Logic & Functions: {funcs_desc}\n"
                        f"- Formula Translation: Converted JavaScript gameplay constants and loop mechanics into C# fields & events.\n"
                    )

                code_changes[target] = (
                    f"# Unity Game Architecture Specification\n\n"
                    f"## Objective\n{task.description}\n\n"
                    f"## Architecture Guidelines\n"
                    f"- Zero Vietnamese comments in codebase (Enforcing RULE_NO_VIETNAMESE_IN_CODE)\n"
                    f"- ScriptableObject event channels for decoupled communication\n"
                    f"- Cached component references in Awake()\n"
                    f"{ref_section}"
                    f"{demo_section}\n"
                    f"## Core Components\n"
                    f"- GameController.cs (Manager & game loop coordinator)\n"
                    f"- PrefabConfig.cs (ScriptableObject data definition)\n"
                )
                addons = []
                if ref_media:
                    addons.append(f"{len(ref_media)} visual reference(s)")
                if demo_html:
                    addons.append(f"playable HTML demo '{demo_html.get('name')}'")
                addon_suffix = f" (incorporated {', '.join(addons)})" if addons else ""
                explanation = f"Generated Unity architecture blueprint and component contracts for {task.title}{addon_suffix}."

            elif task.domain == TaskDomain.IMPLEMENTATION:
                if "prefab" in task.title.lower() or "tool" in task.title.lower():
                    target = "Assets/Scripts/Gameplay/PrefabConfig.cs"
                    files.append(target)
                    code_changes[target] = (
                        "using UnityEngine;\n\n"
                        "namespace GamePlay.Core\n"
                        "{\n"
                        "    [CreateAssetMenu(fileName = \"PrefabConfig\", menuName = \"Game/PrefabConfig\")]\n"
                        "    public class PrefabConfig : ScriptableObject\n"
                        "    {\n"
                        "        [SerializeField] private string prefabName = \"BlockEntity\";\n"
                        "        [SerializeField] private Vector3 spawnPosition = Vector3.zero;\n\n"
                        "        public string PrefabName => prefabName;\n"
                        "        public Vector3 SpawnPosition => spawnPosition;\n"
                        "    }\n"
                        "}\n"
                    )
                    explanation = f"Created Unity ScriptableObject configuration class {target}."
                else:
                    target = "Assets/Scripts/Gameplay/GameController.cs"
                    files.append(target)
                    code_changes[target] = (
                        "using System;\n"
                        "using UnityEngine;\n\n"
                        "namespace GamePlay.Core\n"
                        "{\n"
                        "    public class GameController : MonoBehaviour\n"
                        "    {\n"
                        "        [SerializeField] private int score = 0;\n"
                        "        [SerializeField] private float gameSpeed = 1.0f;\n\n"
                        "        public event Action<int> OnScoreChanged;\n\n"
                        "        private void Awake()\n"
                        "        {\n"
                        "            score = 0;\n"
                        "        }\n\n"
                        "        public void AddScore(int amount)\n"
                        "        {\n"
                        "            if (amount <= 0) return;\n"
                        "            score += amount;\n"
                        "            OnScoreChanged?.Invoke(score);\n"
                        "        }\n\n"
                        "        public int GetCurrentScore() => score;\n"
                        "    }\n"
                        "}\n"
                    )
                    explanation = f"Implemented clean Unity C# MonoBehaviour component {target} respecting project rules."

            elif task.domain == TaskDomain.VERIFICATION:
                explanation = f"Quality Gate verified C# syntax, verified zero Vietnamese comments, and validated Unity rules."

            else:
                files.append("Assets/Scripts/Config.json")
                code_changes["Assets/Scripts/Config.json"] = json.dumps({"engine": "unity", "task_id": task.task_id}, indent=2)
                explanation = f"Configured Unity runtime settings for {task.title}."

        elif task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
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
