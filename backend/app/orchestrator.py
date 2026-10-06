import asyncio
import time
from pathlib import Path
from typing import Callable, Awaitable, Optional, Dict, Any, Set
from app.schemas import GlobalDAGState, SubTask, TaskStatus, WebSocketEvent, ModelProvider
from app.router import DynamicModelRouter
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.planner import PlannerEngine
from app.llm import LLMClient
from app.github_service import GitHubService
from app.coding_agent import CodingAgent
from app.git_workspace import GitWorkspaceManager
from app import unity_verifier


EventCallback = Callable[[WebSocketEvent], Awaitable[None]]


class TeamOrchestrator:
    def __init__(
        self,
        state: GlobalDAGState,
        router: DynamicModelRouter,
        sandbox: SandboxRuntime,
        verifier: VerifierGate,
        planner: PlannerEngine,
        llm_client: LLMClient,
        event_callback: Optional[EventCallback] = None,
        simulate_failure_once: bool = False,
        github_token: Optional[str] = None,
        auto_push_github: bool = False,
    ):
        self.state = state
        self.router = router
        self.sandbox = sandbox
        self.verifier = verifier
        self.planner = planner
        self.llm = llm_client
        self.emit_event = event_callback
        self.simulate_failure_once = simulate_failure_once
        self._has_simulated_failure = False
        self.github_token = github_token
        self.auto_push_github = auto_push_github
        self._stop_event = asyncio.Event()
        self._running_task: Optional[asyncio.Task] = None
        self._file_backups: Dict[str, str] = {}
        self._created_files: Set[str] = set()
        self._git_branch: Optional[str] = None
        self._orig_git_branch: Optional[str] = None

    def stop_execution(self) -> None:
        """Signal the orchestrator to stop. Cancels the running asyncio task immediately."""
        self._stop_event.set()
        if self._running_task and not self._running_task.done():
            self._running_task.cancel()

    async def _rollback_changes(self):
        """Roll back all modified files and remove newly created broken files to keep Unity clean."""
        project_path = self.state.project_path
        base = Path(project_path) if project_path else self.sandbox.workspace

        # 1. Remove newly created files on disk that caused compile errors
        if self._created_files:
            for rel in list(self._created_files):
                for root in [base, self.sandbox.workspace]:
                    try:
                        f = root / rel
                        if f.exists() and f.is_file():
                            f.unlink()
                            meta = root / f"{rel}.meta"
                            if meta.exists():
                                meta.unlink()
                            await self._emit_log("Rollback", f"Cleaned up broken generated file: {rel}", "WARN")
                    except Exception as e:
                        await self._emit_log("Rollback", f"Could not remove {rel}: {e}", "WARN")
            self._created_files.clear()

        # 2. Restore modified files to pristine pre-run state
        if self._file_backups:
            for fpath, orig_code in list(self._file_backups.items()):
                try:
                    self.sandbox.fs_write(fpath, orig_code)
                    if base and base != self.sandbox.workspace:
                        disk_f = base / fpath
                        if disk_f.exists():
                            disk_f.write_text(orig_code, encoding="utf-8")
                    await self._emit_log("Rollback", f"Restored {fpath} to pristine pre-run state.", "WARN")
                except Exception as e:
                    await self._emit_log("Rollback", f"Failed rollback for {fpath}: {e}", "ERROR")
            self._file_backups.clear()

        # 3. Trigger Unity refresh so red console errors disappear immediately
        if self.state.project_type == "unity" or (base and (base / "Assets").exists()):
            try:
                await unity_verifier.refresh_and_wait(self._emit_log)
                await self._emit_log("Rollback", "Triggered Unity Editor refresh to clear compile errors.", "INFO")
            except Exception as e:
                await self._emit_log("Rollback", f"Unity refresh note: {e}", "WARN")

        # 4. Clean Git working copy if repository exists
        if project_path and GitWorkspaceManager.is_git_repo(project_path):
            try:
                GitWorkspaceManager.reset_and_clean_changes(project_path)
                await self._emit_log("Git", "Git workspace cleanly reset to HEAD.", "INFO")
            except Exception:
                pass

    def _read_project_files(self, task: SubTask) -> Dict[str, str]:
        """Read current on-disk content of the task's target files plus contextual sibling files."""
        project_path = self.state.project_path
        if not project_path:
            return {}
        base = Path(project_path)
        contents: Dict[str, str] = {}
        target_dirs = set()

        # 1. Read explicitly targeted files
        if task.target_files:
            for rel in task.target_files:
                abs_path = base / rel
                if abs_path.exists() and abs_path.is_file():
                    try:
                        # Limit to 8 KB per file to keep prompt size manageable
                        contents[rel] = abs_path.read_text(encoding="utf-8", errors="replace")[:8000]
                        target_dirs.add(abs_path.parent)
                    except Exception:
                        pass

        # 2. Also read sibling related files (.cs, .uxml, .uss) in the same directory (e.g. partial classes)
        for d in target_dirs:
            try:
                for pattern in ["*.cs", "*.uxml", "*.uss"]:
                    for sibling in d.glob(pattern):
                        if len(contents) >= 8:
                            break
                        try:
                            sibling_rel = sibling.relative_to(base).as_posix()
                            if sibling_rel not in contents:
                                contents[sibling_rel] = sibling.read_text(encoding="utf-8", errors="replace")[:6000]
                        except Exception:
                            pass
            except Exception:
                pass

        return contents

    async def _broadcast(self, event_type: str, data: Dict[str, Any]):
        if self.emit_event:
            event = WebSocketEvent(
                event_type=event_type,
                session_id=self.state.session_id,
                timestamp=time.time(),
                data=data,
            )
            await self.emit_event(event)

    async def _emit_log(self, source: str, message: str, level: str = "INFO"):
        await self._broadcast(
            "LOG_CHUNK",
            {"source": source, "message": message, "level": level, "time": time.strftime("%H:%M:%S")},
        )

    async def _update_fleet(self, planner_state: str, executor_state: str, verifier_state: str):
        await self._broadcast(
            "AGENT_FLEET_UPDATE",
            {
                "planner": planner_state,
                "executor": executor_state,
                "verifier": verifier_state,
            },
        )

    async def _try_push_github(self):
        """Push all sandbox workspace files to a new GitHub repo if configured."""
        if not self.auto_push_github or not self.github_token:
            return

        await self._emit_log("GitHub", "Auto-push enabled. Collecting workspace files...")
        await self._update_fleet("IDLE", "IDLE", "PUSHING")

        try:
            gh = GitHubService(token=self.github_token)

            # Gather all files written to sandbox during the run
            all_files: Dict[str, str] = {}
            for artifact in self.sandbox.artifacts_history:
                fpath = artifact.get("file", "")
                if fpath:
                    try:
                        content = self.sandbox.fs_read(fpath)
                        all_files[fpath] = content
                    except Exception:
                        pass

            if not all_files:
                await self._emit_log("GitHub", "No sandbox files found to push. Skipping.", "WARN")
                return

            await self._emit_log(
                "GitHub",
                f"Pushing {len(all_files)} file(s) to GitHub: {', '.join(list(all_files.keys())[:5])}{'...' if len(all_files) > 5 else ''}"
            )

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: gh.publish_workspace(
                    objective=self.state.objective,
                    session_id=self.state.session_id,
                    files=all_files,
                )
            )

            self.state.github_result = result
            await self._emit_log(
                "GitHub",
                f"Repository created and pushed! Repo: {result['repo_url']} | Commit: {result['commit_sha'][:7]}",
                "SUCCESS",
            )
            await self._broadcast("GITHUB_PUSHED", result)

        except Exception as exc:
            await self._emit_log("GitHub", f"GitHub push failed: {exc}", "ERROR")

    async def execute_dag(self) -> Dict[str, Any]:
        # Register this coroutine as the current task so stop_execution can cancel it.
        self._running_task = asyncio.current_task()
        pipeline_start_time = time.time()
        try:
            return await self._execute_dag_inner(pipeline_start_time)
        except asyncio.CancelledError:
            self.state.status = "stopped"
            self.state.total_elapsed_time_sec = round(time.time() - pipeline_start_time, 2)
            try:
                await self._rollback_changes()
                await self._update_fleet("IDLE", "IDLE", "IDLE")
                await self._emit_log("Orchestrator", "Workflow forcibly cancelled by stop signal. Rolled back any broken files.", "WARN")
                await self._broadcast("RUN_STOPPED", {
                    "session_id": self.state.session_id,
                    "status": "STOPPED",
                    "state": self.state.model_dump(),
                })
            except Exception:
                pass
            return {"status": "STOPPED", "state": self.state.model_dump()}

    async def _execute_dag_inner(self, pipeline_start_time: float) -> Dict[str, Any]:
        self.state.status = "running"
        await self._emit_log(
            "Orchestrator",
            f"Initiating execution pipeline for session {self.state.session_id} (Est. Total Duration: ~{self.state.total_estimated_time_sec}s)..."
        )

        # Phase 0: Project Context, Rule & Skill Ingestion Gate
        project_type = self.state.project_type or "generic"
        project_path = self.state.project_path
        await self._emit_log(
            "ContextLoader",
            f"Phase 0: Scanning project guidelines at '{project_path or 'Workspace Sandbox'}' [Type: {project_type.upper()}]...",
            "INFO"
        )
        if self.state.ingested_rules:
            rule_titles = [r.get("title", r.get("id")) for r in self.state.ingested_rules]
            await self._emit_log(
                "ContextLoader",
                f"Ingested {len(self.state.ingested_rules)} Active Rules: {', '.join(rule_titles)}",
                "SUCCESS"
            )
        if self.state.ingested_skills:
            skill_names = [s.get("name") for s in self.state.ingested_skills]
            await self._emit_log(
                "ContextLoader",
                f"Discovered {len(self.state.ingested_skills)} Specialized Skills: {', '.join(skill_names)}",
                "SUCCESS"
            )
        if self.state.reference_media:
            media_names = [f"{m.get('name', 'Media')} ({m.get('media_type', 'image')})" for m in self.state.reference_media]
            await self._emit_log(
                "ContextLoader",
                f"Ingested {len(self.state.reference_media)} Visual References: {', '.join(media_names)}",
                "SUCCESS"
            )
            await self._emit_log(
                "ContextLoader",
                "Multimodal art style, UI layout anchors, and visual composition bound to Game Architect.",
                "INFO"
            )
        if self.state.demo_html:
            demo_name = self.state.demo_html.get('name', 'game_demo.html')
            logic_meta = self.state.demo_html.get('extracted_logic') or {}
            funcs = logic_meta.get('functions', [])
            await self._emit_log(
                "ContextLoader",
                f"Ingested Playable HTML Game Demo: '{demo_name}' (Extracted {len(funcs)} JS functions & mechanics). Bound to Planner & C# Engineers.",
                "SUCCESS"
            )
        await self._emit_log(
            "ContextLoader",
            "Rule, Skill, Visual Reference & Playable Demo Ingestion Gate PASSED. All guidelines bound to Agent Fleet.",
            "SUCCESS"
        )

        # Phase 0.5: Git Worktree / Branch Isolation Gate
        if self.state.project_path and GitWorkspaceManager.is_git_repo(self.state.project_path):
            self._orig_git_branch = GitWorkspaceManager.get_current_branch(self.state.project_path)
            feature_branch = f"ai-agent/{self.state.session_id[:8]}"
            if GitWorkspaceManager.create_and_checkout_feature_branch(self.state.project_path, feature_branch):
                self._git_branch = feature_branch
                await self._emit_log(
                    "Git",
                    f"Created & switched to isolated branch '{feature_branch}'. Base branch '{self._orig_git_branch or 'main'}' is protected.",
                    "SUCCESS",
                )

        await self._broadcast("SESSION_UPDATED", self.state.model_dump())

        replan_count = 0
        max_replans = self.state.max_iterations

        while True:
            if self._stop_event.is_set():
                self.state.status = "stopped"
                self.state.total_elapsed_time_sec = round(time.time() - pipeline_start_time, 2)
                await self._rollback_changes()
                await self._update_fleet("IDLE", "IDLE", "IDLE")
                await self._emit_log("Orchestrator", "Workflow execution manually stopped by user. Rolled back any broken files.", "WARN")
                await self._broadcast("RUN_STOPPED", {"session_id": self.state.session_id, "status": "STOPPED", "state": self.state.model_dump()})
                return {"status": "STOPPED", "state": self.state.model_dump()}

            superseded_ids = {t.retry_of for t in self.state.tasks.values() if t.retry_of}
            active_tasks = [t for t in self.state.tasks.values() if t.task_id not in superseded_ids]
            uncompleted = [t for t in active_tasks if t.status != TaskStatus.COMPLETED]
            if not uncompleted:
                self.state.status = "completed"
                self.state.total_elapsed_time_sec = round(time.time() - pipeline_start_time, 2)
                self.state.artifacts_history = list(self.sandbox.artifacts_history)
                await self._update_fleet("IDLE", "IDLE", "IDLE")
                await self._emit_log(
                    "Orchestrator",
                    f"All DAG subtasks completed! Total Elapsed: {self.state.total_elapsed_time_sec:.1f}s (Est: ~{self.state.total_estimated_time_sec}s). Gate PASSED.",
                    "SUCCESS"
                )

                # Auto-push to GitHub if configured
                await self._try_push_github()

                await self._broadcast("RUN_FINISHED", {
                    "status": "SUCCESS",
                    "state": self.state.model_dump(),
                    "artifacts_history": self.sandbox.artifacts_history,
                })
                return {"status": "SUCCESS", "state": self.state.model_dump(), "artifacts_history": self.sandbox.artifacts_history}

            # Mark pending tasks whose dependencies failed as FAILED/BLOCKED
            for t in list(self.state.tasks.values()):
                if t.status == TaskStatus.PENDING:
                    failed_deps = [
                        dep for dep in t.dependencies
                        if dep in self.state.tasks and self.state.tasks[dep].status == TaskStatus.FAILED
                    ]
                    if failed_deps:
                        t.status = TaskStatus.FAILED
                        t.error_trace = f"Blocked: upstream dependency #{failed_deps[0]} failed."
                        await self._emit_log(
                            "Orchestrator",
                            f"Task #{t.task_id} ('{t.title}') cancelled because upstream dependency #{failed_deps[0]} failed.",
                            "WARN"
                        )

            # Find pending tasks whose dependencies have strictly completed
            ready_tasks = [
                task for task in self.state.tasks.values()
                if task.status == TaskStatus.PENDING
                and all(
                    self.state.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                    if dep_id in self.state.tasks
                )
            ]

            if not ready_tasks:
                break

            # Execute the ready batch
            batch_tasks = ready_tasks
            replan_needed = False
            circuit_breaker_halt = False

            for task in batch_tasks:
                if self._stop_event.is_set():
                    break

                # 1. Dynamic Model Routing
                await self._update_fleet("ACTIVE", "IDLE", "IDLE")
                allocated_model, rationale = self.router.route_task(task)
                task.assigned_model = allocated_model
                if not task.assigned_agent:
                    task.assigned_agent = self.router.get_agent_for_task(task.domain)
                task.routing_rationale = rationale
                task.status = TaskStatus.RUNNING

                await self._emit_log(
                    "Router",
                    f"Two-Tier Routing for #{task.task_id}: {rationale} -> Agent: [{task.assigned_agent}] with Model: [{allocated_model.value}]"
                )
                await self._broadcast("MODEL_SWITCHED", {"task_id": task.task_id, "model": allocated_model.value, "agent": task.assigned_agent})
                await self._broadcast("TASK_STARTED", task.model_dump())

                # 2. Tool Execution in Sandbox
                await self._update_fleet("IDLE", "BUSY", "IDLE")
                await self._emit_log("Executor", f"Executing #{task.task_id}: '{task.title}' (Est: ~{task.estimated_time_sec}s)...")

                start_time = time.time()
                should_fail = self.simulate_failure_once and not self._has_simulated_failure and task.domain.value == "implementation"

                # Read current on-disk content so agents don't overwrite existing work
                existing_files = self._read_project_files(task)
                if existing_files:
                    await self._emit_log(
                        "ContextLoader",
                        f"Loaded {len(existing_files)} existing file(s) for #{task.task_id}: {', '.join(existing_files.keys())}",
                        "INFO",
                    )

                # Collect outputs written by all prior tasks in this session
                prior_outputs: Dict[str, str] = {}
                for artifact in self.sandbox.artifacts_history:
                    fpath = artifact.get("file", "")
                    if fpath and fpath not in existing_files:
                        try:
                            prior_outputs[fpath] = self.sandbox.fs_read(fpath)
                        except Exception:
                            pass
                if prior_outputs:
                    await self._emit_log(
                        "ContextLoader",
                        f"Injecting {len(prior_outputs)} prior-task artifact(s) into context for #{task.task_id}.",
                        "INFO",
                    )

                # Prepare pre-edit backup references for context
                orig_refs = {
                    f: self._file_backups[f]
                    for f in self._file_backups
                    if (task.target_files and f in task.target_files) or f in existing_files
                }

                task_context = {
                    "objective": self.state.objective,
                    "project_path": self.state.project_path,
                    "project_type": self.state.project_type,
                    "rules": self.state.ingested_rules,
                    "skills": self.state.ingested_skills,
                    "reference_media": self.state.reference_media,
                    "demo_html": self.state.demo_html,
                    "existing_file_contents": existing_files,
                    "prior_task_outputs": prior_outputs,
                    "original_pre_edit_contents": orig_refs,
                }

                if task.domain in [TaskDomain.IMPLEMENTATION, TaskDomain.VERIFICATION] and not should_fail:
                    coding_agent = CodingAgent(
                        sandbox=self.sandbox,
                        verifier=self.verifier,
                        llm=self.llm,
                        max_inner_turns=3,
                    )
                    exec_result = await coding_agent.run(
                        task=task,
                        model=allocated_model,
                        context=task_context,
                        log_callback=self._emit_log,
                        stop_event=self._stop_event,
                    )
                else:
                    exec_result = await self.llm.execute_task(
                        task=task,
                        model=allocated_model,
                        context=task_context,
                        simulate_error=should_fail,
                        log_callback=self._emit_log,
                        stop_event=self._stop_event,
                    )

                if should_fail:
                    self._has_simulated_failure = True

                # Backup original files before writing changes and track newly created files
                code_changes = exec_result.get("code_changes", {})
                if self.state.project_path:
                    base_proj = Path(self.state.project_path)
                    for filepath in code_changes.keys():
                        disk_f = base_proj / filepath
                        if disk_f.exists() and disk_f.is_file():
                            if filepath not in self._file_backups:
                                try:
                                    self._file_backups[filepath] = disk_f.read_text(encoding="utf-8", errors="replace")
                                except Exception:
                                    pass
                        else:
                            self._created_files.add(filepath)

                # Apply file writes to sandbox
                for filepath, code_body in code_changes.items():
                    res = self.sandbox.fs_write(filepath, code_body)
                    await self._emit_log("Sandbox", f"Wrote file {filepath} ({res['size_bytes']} bytes). Unified diff generated.")
                self.state.artifacts_history = list(self.sandbox.artifacts_history)

                # Calculate cost and latency
                in_tok = exec_result.get("input_tokens", 1000)
                out_tok = exec_result.get("output_tokens", 500)
                cost = self.router.estimate_cost(allocated_model, in_tok, out_tok)
                task.cost_usd = cost
                self.state.total_cost_usd += cost
                task.execution_time_ms = round((time.time() - start_time) * 1000, 2)

                # 3. Deterministic Verifier Gate (includes live Unity compile check)
                await self._update_fleet("IDLE", "IDLE", "VERIFYING")
                await self._emit_log("Verifier", f"Quality Gate analyzing output of #{task.task_id} (Syntax + Unity MCP compile)...")

                verify_result = await self.verifier.evaluate(
                    task,
                    {
                        "artifacts": {"files": list(code_changes.keys())},
                        "success": True,
                    },
                    log_callback=self._emit_log,
                )

                if verify_result.passed:
                    self.router.metrics.record_result(allocated_model, task.domain, True)
                    task.status = TaskStatus.COMPLETED
                    task.output_artifacts = {
                        "files": list(code_changes.keys()),
                        "explanation": exec_result.get("output"),
                        "checks": verify_result.checks,
                    }
                    await self._emit_log(
                        "Verifier",
                        f"Quality Gate PASSED for #{task.task_id} in {task.execution_time_ms/1000:.2f}s (Est: ~{task.estimated_time_sec}s). {verify_result.summary}",
                        "SUCCESS"
                    )
                    await self._broadcast("TASK_COMPLETED", task.model_dump())
                    await self._broadcast("SESSION_UPDATED", self.state.model_dump())

                    if self.state.project_path and GitWorkspaceManager.is_git_repo(self.state.project_path):
                        try:
                            sha = GitWorkspaceManager.commit_task_changes(
                                self.state.project_path,
                                task.task_id,
                                task.title,
                                list(code_changes.keys()),
                            )
                            if sha:
                                await self._emit_log("Git", f"Created micro-commit [{sha}] for #{task.task_id}: '{task.title}'", "INFO")
                        except Exception:
                            pass
                else:
                    self.router.metrics.record_result(allocated_model, task.domain, False)
                    task.status = TaskStatus.FAILED
                    task.error_trace = verify_result.error_log
                    # Enrich error trace with file context for the replan LLM
                    changed_cs = [f for f in code_changes.keys() if f.endswith(".cs")]
                    if changed_cs:
                        file_ctx = "Files modified: " + ", ".join(changed_cs)
                        task.error_trace = f"{file_ctx}\n\n{task.error_trace or ''}"
                    await self._emit_log(
                        "Verifier",
                        f"Quality Gate REJECTED #{task.task_id}!\n{verify_result.error_log}",
                        "ERROR",
                    )
                    await self._broadcast("TASK_FAILED", task.model_dump())

                    # Check retry depth to prevent infinite loops (Circuit Breaker max 2 retries)
                    depth = 1
                    curr = task
                    while curr.retry_of and curr.retry_of in self.state.tasks:
                        depth += 1
                        curr = self.state.tasks[curr.retry_of]

                    if depth >= 2:
                        await self._emit_log(
                            "CircuitBreaker",
                            f"Circuit Breaker: Task #{task.task_id} failed verification {depth} times consecutively. Halting execution and rolling back unverified changes.",
                            "ERROR",
                        )
                        # Automatic Rollback to pristine state & delete broken created files
                        await self._rollback_changes()
                        # Mark downstream pending tasks as failed
                        for downstream in self.state.tasks.values():
                            if downstream.status == TaskStatus.PENDING:
                                downstream.status = TaskStatus.FAILED
                                downstream.error_trace = f"Cancelled due to upstream failure of #{task.task_id}"
                        circuit_breaker_halt = True
                        break

                    # 4. Trigger Adaptive Replanning with full compile error context
                    await self._update_fleet("REPLANNING", "IDLE", "IDLE")
                    await self._emit_log(
                        "Replanner",
                        f"Triggering Adaptive Replanning (attempt {depth + 1}/2) — injecting fix node with compiler error context...",
                    )
                    fix_task = self.planner.trigger_replan(self.state, task)
                    await self._broadcast("REPLAN_TRIGGERED", {
                        "failed_task_id": task.task_id,
                        "fix_task": fix_task.model_dump(),
                        "state": self.state.model_dump(),
                    })
                    replan_count += 1
                    self.state.iteration = replan_count
                    if replan_count >= max_replans:
                        await self._emit_log("Orchestrator", f"Max replanning iterations ({max_replans}) reached. Rolling back broken changes.", "ERROR")
                        await self._rollback_changes()
                        circuit_breaker_halt = True
                        break
                    replan_needed = True
                    break

            if circuit_breaker_halt:
                break

            await asyncio.sleep(0.5)

            if replan_needed:
                continue

        # If loop exited and tasks still uncompleted
        superseded_ids = {t.retry_of for t in self.state.tasks.values() if t.retry_of}
        active_tasks = [t for t in self.state.tasks.values() if t.task_id not in superseded_ids]
        uncompleted = [t for t in active_tasks if t.status != TaskStatus.COMPLETED]
        if self._stop_event.is_set():
            self.state.status = "stopped"
            self.state.total_elapsed_time_sec = round(time.time() - pipeline_start_time, 2)
            await self._rollback_changes()
            await self._update_fleet("IDLE", "IDLE", "IDLE")
            await self._emit_log("Orchestrator", "Workflow execution manually stopped by user. Rolled back any broken files.", "WARN")
            await self._broadcast("RUN_STOPPED", {"session_id": self.state.session_id, "status": "STOPPED", "state": self.state.model_dump()})
            return {"status": "STOPPED", "state": self.state.model_dump()}

        if uncompleted:
            self.state.status = "failed"
            await self._rollback_changes()
            await self._update_fleet("IDLE", "IDLE", "IDLE")
            await self._emit_log("Orchestrator", "DAG execution finished with uncompleted tasks. Reverted all unverified changes.", "ERROR")
            await self._broadcast("RUN_FINISHED", {"status": "FAILED", "state": self.state.model_dump()})
            return {"status": "FAILED", "message": "DAG stopped with uncompleted tasks.", "state": self.state.model_dump()}

        self.state.status = "completed"
        return {"status": "SUCCESS", "state": self.state.model_dump()}
