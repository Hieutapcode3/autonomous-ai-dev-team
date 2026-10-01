import asyncio
import time
from typing import Callable, Awaitable, Optional, Dict, Any
from app.schemas import GlobalDAGState, SubTask, TaskStatus, WebSocketEvent, ModelProvider
from app.router import DynamicModelRouter
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.planner import PlannerEngine
from app.llm import LLMClient
from app.github_service import GitHubService


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
        self.state.status = "running"
        pipeline_start_time = time.time()
        await self._emit_log(
            "Orchestrator",
            f"Initiating execution pipeline for session {self.state.session_id} (Est. Total Duration: ~{self.state.total_estimated_time_sec}s)..."
        )
        await self._broadcast("SESSION_UPDATED", self.state.model_dump())

        replan_count = 0
        max_replans = self.state.max_iterations

        while True:
            superseded_ids = {t.retry_of for t in self.state.tasks.values() if t.retry_of}
            active_tasks = [t for t in self.state.tasks.values() if t.task_id not in superseded_ids]
            uncompleted = [t for t in active_tasks if t.status != TaskStatus.COMPLETED]
            if not uncompleted:
                self.state.status = "completed"
                self.state.total_elapsed_time_sec = round(time.time() - pipeline_start_time, 2)
                await self._update_fleet("IDLE", "IDLE", "IDLE")
                await self._emit_log(
                    "Orchestrator",
                    f"All DAG subtasks completed! Total Elapsed: {self.state.total_elapsed_time_sec:.1f}s (Est: ~{self.state.total_estimated_time_sec}s). Gate PASSED.",
                    "SUCCESS"
                )

                # Auto-push to GitHub if configured
                await self._try_push_github()

                await self._broadcast("RUN_FINISHED", {"status": "SUCCESS", "state": self.state.model_dump()})
                return {"status": "SUCCESS", "state": self.state.model_dump()}

            # Find pending tasks whose dependencies have completed or failed (with replan)
            ready_tasks = [
                task for task in self.state.tasks.values()
                if task.status == TaskStatus.PENDING
                and all(
                    self.state.tasks[dep_id].status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                    for dep_id in task.dependencies
                    if dep_id in self.state.tasks
                )
            ]

            if not ready_tasks:
                break

            # Execute the ready batch
            batch_tasks = ready_tasks
            replan_needed = False

            for task in batch_tasks:
                # 1. Dynamic Model Routing
                await self._update_fleet("ACTIVE", "IDLE", "IDLE")
                allocated_model, rationale = self.router.route_task(task)
                task.assigned_model = allocated_model
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

                exec_result = await self.llm.execute_task(
                    task=task,
                    model=allocated_model,
                    context={"objective": self.state.objective},
                    simulate_error=should_fail,
                    log_callback=self._emit_log,
                )

                if should_fail:
                    self._has_simulated_failure = True

                # Apply file writes to sandbox
                code_changes = exec_result.get("code_changes", {})
                for filepath, code_body in code_changes.items():
                    res = self.sandbox.fs_write(filepath, code_body)
                    await self._emit_log("Sandbox", f"Wrote file {filepath} ({res['size_bytes']} bytes). Unified diff generated.")

                # Calculate cost and latency
                in_tok = exec_result.get("input_tokens", 1000)
                out_tok = exec_result.get("output_tokens", 500)
                cost = self.router.estimate_cost(allocated_model, in_tok, out_tok)
                task.cost_usd = cost
                self.state.total_cost_usd += cost
                task.execution_time_ms = round((time.time() - start_time) * 1000, 2)

                # 3. Deterministic Verifier Gate
                await self._update_fleet("IDLE", "IDLE", "VERIFYING")
                await self._emit_log("Verifier", f"Quality Gate analyzing output of #{task.task_id} (Syntax, AST, Tests)...")

                verify_result = await self.verifier.evaluate(task, {
                    "artifacts": {"files": list(code_changes.keys())},
                    "success": True,
                })

                if verify_result.passed:
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
                else:
                    task.status = TaskStatus.FAILED
                    task.error_trace = verify_result.error_log
                    await self._emit_log("Verifier", f"Quality Gate REJECTED #{task.task_id}!\n{verify_result.error_log}", "ERROR")
                    await self._broadcast("TASK_FAILED", task.model_dump())

                    # 4. Trigger Adaptive Replanning
                    await self._update_fleet("REPLANNING", "IDLE", "IDLE")
                    await self._emit_log("Replanner", f"Triggering Adaptive Replanning to inject fix node for #{task.task_id}...")
                    fix_task = self.planner.trigger_replan(self.state, task)
                    await self._broadcast("REPLAN_TRIGGERED", {
                        "failed_task_id": task.task_id,
                        "fix_task": fix_task.model_dump(),
                        "state": self.state.model_dump(),
                    })
                    replan_count += 1
                    self.state.iteration = replan_count
                    if replan_count >= max_replans:
                        await self._emit_log("Orchestrator", f"Max replanning iterations ({max_replans}) reached.", "ERROR")
                        break
                    replan_needed = True
                    break

            await asyncio.sleep(0.5)

            if replan_needed:
                continue

        # If loop exited and tasks still uncompleted
        superseded_ids = {t.retry_of for t in self.state.tasks.values() if t.retry_of}
        active_tasks = [t for t in self.state.tasks.values() if t.task_id not in superseded_ids]
        uncompleted = [t for t in active_tasks if t.status != TaskStatus.COMPLETED]
        if uncompleted:
            self.state.status = "failed"
            await self._update_fleet("IDLE", "IDLE", "IDLE")
            await self._emit_log("Orchestrator", "DAG execution finished with uncompleted tasks.", "ERROR")
            await self._broadcast("RUN_FINISHED", {"status": "FAILED", "state": self.state.model_dump()})
            return {"status": "FAILED", "message": "DAG stopped with uncompleted tasks.", "state": self.state.model_dump()}

        self.state.status = "completed"
        return {"status": "SUCCESS", "state": self.state.model_dump()}
