"""
Coding Agent with Autonomous Multi-Turn Execution & Self-Correction Loop.
Channels an agentic developer loop (inspired by Antigravity IDE / Claude Code):
1. Repository & Symbol Inspection (read files, search symbols, inspect siblings)
2. Targeted Code Generation (strict anti-stub mandate, namespace alignment)
3. Immediate Pre-Verification (syntax, completeness, rules, Unity compilation)
4. In-Turn Self-Correction (surgically fix compile errors before yielding result)
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Awaitable

from app.schemas import SubTask, TaskDomain, ModelProvider
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.llm import LLMClient


class CodingAgent:
    def __init__(
        self,
        sandbox: SandboxRuntime,
        verifier: VerifierGate,
        llm: LLMClient,
        max_inner_turns: int = 3,
    ):
        self.sandbox = sandbox
        self.verifier = verifier
        self.llm = llm
        self.max_inner_turns = max_inner_turns

    async def run(
        self,
        task: SubTask,
        model: ModelProvider,
        context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """
        Execute an agentic coding loop with automated pre-verification and self-correction.
        """
        if stop_event and stop_event.is_set():
            raise asyncio.CancelledError("CodingAgent cancelled by stop signal.")

        if log_callback:
            await log_callback(
                "CodingAgent",
                f"Starting agentic coding loop for #{task.task_id} ('{task.title}')...",
                "INFO",
            )

        # 1. Inspect repository & discover relevant symbols
        enriched_context = await self._gather_repo_context(task, context, log_callback)

        turn = 1
        last_error: Optional[str] = None
        current_code_changes: Dict[str, str] = {}
        last_exec_result: Dict[str, Any] = {}

        while turn <= self.max_inner_turns:
            if stop_event and stop_event.is_set():
                raise asyncio.CancelledError("CodingAgent cancelled by stop signal.")

            if turn > 1:
                if log_callback:
                    await log_callback(
                        "CodingAgent",
                        f"Self-Correction Turn {turn}/{self.max_inner_turns}: repairing compiler/verification issues...",
                        "WARN",
                    )
                # Inject self-correction prompt into context
                enriched_context["self_correction_error"] = last_error
                enriched_context["previous_code_changes"] = current_code_changes

            # Call LLM
            exec_result = await self.llm.execute_task(
                task=task,
                model=model,
                context=enriched_context,
                log_callback=log_callback,
                stop_event=stop_event,
            )
            last_exec_result = exec_result
            code_changes = exec_result.get("code_changes", {})

            if not code_changes:
                # If no code was returned for an implementation task, try next turn with explicit prompt
                last_error = "No code_changes were returned. You MUST output full, working code files in JSON."
                turn += 1
                continue

            current_code_changes = code_changes

            # 2. Pre-Verification Gate: Fast local syntax, rules, and completeness check
            issues: List[str] = []

            for fpath, code in code_changes.items():
                # Write to sandbox to test
                self.sandbox.fs_write(fpath, code)

                syntax_res = self.verifier._verify_syntax(fpath)
                if not syntax_res.get("passed", True):
                    issues.append(f"Syntax Error in {fpath}: {syntax_res.get('error')}")

                rules_res = self.verifier._verify_rules(fpath)
                if not rules_res.get("passed", True):
                    issues.append(f"Rule Violation in {fpath}: {rules_res.get('error')}")

                comp_res = self.verifier._verify_completeness(fpath)
                if not comp_res.get("passed", True):
                    issues.append(f"Completeness Failure in {fpath}: {comp_res.get('error')}")

            if not issues:
                # Fast checks passed! Check Unity compilation if applicable
                is_unity = (
                    any(f.endswith(".cs") for f in code_changes.keys())
                    or (self.sandbox.workspace / "Assets").exists()
                )
                if is_unity and any(f.endswith(".cs") for f in code_changes.keys()):
                    from app import unity_verifier
                    if await unity_verifier.is_unity_reachable():
                        if log_callback:
                            await log_callback(
                                "CodingAgent",
                                "Pre-verifying compilation directly in Unity Editor...",
                                "INFO",
                            )
                        u_res = await unity_verifier.verify_unity_compilation(
                            changed_files=list(code_changes.keys()),
                            log=log_callback,
                        )
                        if not u_res.get("compile_passed", False):
                            u_summary = u_res.get("error_summary", "Unity compilation error.")
                            issues.append(f"Unity Compile Error:\n{u_summary}")

            if not issues:
                # Clean pass!
                if log_callback:
                    await log_callback(
                        "CodingAgent",
                        f"Pre-verification PASSED on Turn {turn} (0 errors). Ready for Quality Gate.",
                        "SUCCESS",
                    )
                return exec_result

            # Compile issues found: prepare for self-correction in next turn
            last_error = "\n".join(issues)
            if log_callback:
                await log_callback(
                    "CodingAgent",
                    f"Turn {turn} Pre-verification found {len(issues)} issue(s):\n{last_error[:250]}...",
                    "WARN",
                )
            turn += 1

        # Turns exhausted: return the latest result (main verifier/replanner will handle fallback)
        if log_callback:
            await log_callback(
                "CodingAgent",
                f"Agent self-correction turns exhausted ({self.max_inner_turns}). Proceeding to main Verifier Gate.",
                "INFO",
            )
        return last_exec_result

    async def _gather_repo_context(
        self,
        task: SubTask,
        base_context: Dict[str, Any],
        log_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Scan workspace for relevant symbols, sibling scripts, and shared data models.
        """
        ctx = dict(base_context)
        discovered_symbols: List[str] = []

        # 1. Search for keywords mentioned in the subtask title / description
        title_words = re.findall(r"[A-Z][a-zA-Z0-9]+", task.title + " " + (task.description or ""))
        keywords = set(w for w in title_words if len(w) >= 4 and w not in ["Task", "Create", "Implement", "Build", "Level", "Editor"])

        for kw in list(keywords)[:4]:
            results = self.sandbox.fs_search(kw, max_results=8)
            for r in results:
                discovered_symbols.append(f"[{r['file']}:{r['line']}] {r['content']}")

        if discovered_symbols and log_callback:
            await log_callback(
                "CodingAgent",
                f"Discovered {len(discovered_symbols)} relevant symbol references in workspace: {', '.join(list(keywords)[:3])}",
                "INFO",
            )

        if discovered_symbols:
            ctx["discovered_symbol_references"] = "\n".join(discovered_symbols[:15])

        # 2. Inject explicit Level Editor contracts if this is a Level Editor task
        obj_lower = (ctx.get("objective", "") + " " + task.title).lower()
        if any(kw in obj_lower for kw in ["level editor", "editorwindow", "leveleditor"]):
            ctx["level_editor_contracts"] = (
                "MANDATORY ARCHITECTURE & NAMESPACE CONTRACT FOR LEVEL EDITOR:\n"
                "- Unified Namespace: 'BlockHome.Editor.LevelEditor'\n"
                "- Core Data Model: 'EditorLevelData' (CellType, EditorCellData, EditorBlockPlacementData, EditorHumanPlacementData)\n"
                "- Runtime Serialization: Bi-directional conversion with 'BlockHome.Core.LevelData' and storage in 'Assets/Resources/Levels/Level_{N}.json'\n"
                "- Window Class: 'BlockHomeLevelEditorWindow : EditorWindow' with [MenuItem('Tools/BlockHome/Level Editor')]\n"
                "- Zero namespace divergence: All partial classes and tools MUST use namespace 'BlockHome.Editor.LevelEditor'."
            )

        return ctx
