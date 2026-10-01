import uuid
from typing import Dict, List, Set
from collections import defaultdict, deque
from app.schemas import SubTask, TaskDomain, TaskStatus, GlobalDAGState


class PlannerEngine:
    def decompose_objective(self, session_id: str, objective: str) -> GlobalDAGState:
        # Default structured decomposition based on software engineering lifecycle
        tasks: Dict[str, SubTask] = {}

        t1_id = f"task_{uuid.uuid4().hex[:6]}"
        t2_id = f"task_{uuid.uuid4().hex[:6]}"
        t3_id = f"task_{uuid.uuid4().hex[:6]}"
        t4_id = f"task_{uuid.uuid4().hex[:6]}"

        tasks[t1_id] = SubTask(
            task_id=t1_id,
            title="System Architecture & Interface Blueprint",
            description=f"Analyze requirements for: '{objective}'. Define models, API signatures, and boundary specs.",
            domain=TaskDomain.ARCHITECTURE,
            complexity=8,
            dependencies=[],
            required_tools=["fs_write"],
        )

        tasks[t2_id] = SubTask(
            task_id=t2_id,
            title="Core Domain & Service Logic Implementation",
            description="Implement business calculation engine, data structures, and main algorithmic methods.",
            domain=TaskDomain.IMPLEMENTATION,
            complexity=6,
            dependencies=[t1_id],
            required_tools=["fs_read", "fs_write", "terminal_exec"],
            target_files=["src/service.py"],
        )

        tasks[t3_id] = SubTask(
            task_id=t3_id,
            title="Unit Tests & Automated Harness",
            description="Create test fixtures, edge cases, and automated validation suite matching domain specifications.",
            domain=TaskDomain.VERIFICATION,
            complexity=5,
            dependencies=[t2_id],
            required_tools=["fs_write", "terminal_exec", "test_runner"],
            target_files=["tests/test_service.py"],
        )

        tasks[t4_id] = SubTask(
            task_id=t4_id,
            title="Deterministic Quality Gate & Build Verification",
            description="Execute full linter, AST syntax analysis, and pytest runner across the workspace.",
            domain=TaskDomain.VERIFICATION,
            complexity=4,
            dependencies=[t3_id],
            required_tools=["terminal_exec", "test_runner"],
        )

        from app.router import DynamicModelRouter
        router = DynamicModelRouter()

        for task_id, task in tasks.items():
            task.estimated_time_sec = self.estimate_task_duration(task.domain, task.complexity)
            task.assigned_agent = router.get_agent_for_task(task.domain)
            model, rationale = router.route_task(task)
            task.assigned_model = model
            task.routing_rationale = rationale

        execution_order = self.compute_topological_batches(tasks)
        total_est = self.compute_pipeline_estimated_time(tasks, execution_order)

        return GlobalDAGState(
            session_id=session_id,
            objective=objective,
            tasks=tasks,
            execution_order=execution_order,
            iteration=0,
            max_iterations=5,
            total_cost_usd=0.0,
            total_estimated_time_sec=total_est,
            total_elapsed_time_sec=0.0,
            status="ready",
        )

    @staticmethod
    def estimate_task_duration(domain: TaskDomain, complexity: int) -> int:
        if domain in [TaskDomain.ARCHITECTURE, TaskDomain.ANALYSIS]:
            return complexity * 3 + 10
        elif domain == TaskDomain.IMPLEMENTATION:
            return complexity * 5 + 15
        elif domain == TaskDomain.VERIFICATION:
            return complexity * 2 + 10
        return complexity * 2 + 5

    def compute_pipeline_estimated_time(self, tasks: Dict[str, SubTask], batches: List[List[str]]) -> int:
        total = 0
        for batch in batches:
            batch_durations = [tasks[tid].estimated_time_sec for tid in batch if tid in tasks]
            total += max(batch_durations) if batch_durations else 0
        return total

    def compute_topological_batches(self, tasks: Dict[str, SubTask]) -> List[List[str]]:
        in_degree: Dict[str, int] = {tid: 0 for tid in tasks}
        adj_list: Dict[str, List[str]] = defaultdict(list)

        for tid, task in tasks.items():
            for dep_id in task.dependencies:
                if dep_id in tasks:
                    adj_list[dep_id].append(tid)
                    in_degree[tid] += 1

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        batches: List[List[str]] = []
        visited_count = 0

        while queue:
            batch_size = len(queue)
            current_batch: List[str] = []

            for _ in range(batch_size):
                curr = queue.popleft()
                current_batch.append(curr)
                visited_count += 1

                for neighbor in adj_list[curr]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if current_batch:
                batches.append(current_batch)

        # Fallback if circular dependency or remaining tasks
        if visited_count < len(tasks):
            remaining = [tid for tid in tasks if not any(tid in b for b in batches)]
            if remaining:
                batches.append(remaining)

        return batches

    def trigger_replan(self, state: GlobalDAGState, failed_task: SubTask) -> SubTask:
        replan_id = f"replan_{uuid.uuid4().hex[:6]}"

        fix_task = SubTask(
            task_id=replan_id,
            title=f"Fix & Refine: {failed_task.title}",
            description=(
                f"Resolved regression or verification failure in {failed_task.title}.\n"
                f"Error diagnosis: {failed_task.error_trace or 'Verification gate rejection'}"
            ),
            domain=failed_task.domain,
            complexity=min(10, failed_task.complexity + 1),
            dependencies=[failed_task.task_id],
            required_tools=failed_task.required_tools,
            status=TaskStatus.PENDING,
            retry_of=failed_task.task_id,
            target_files=failed_task.target_files,
            estimated_time_sec=self.estimate_task_duration(failed_task.domain, min(10, failed_task.complexity + 1)),
        )

        from app.router import DynamicModelRouter
        router = DynamicModelRouter()
        fix_task.assigned_agent = router.get_agent_for_task(fix_task.domain)
        model, rationale = router.route_task(fix_task)
        fix_task.assigned_model = model
        fix_task.routing_rationale = rationale

        state.tasks[replan_id] = fix_task

        # Downstream tasks that depended on the failed task must now depend on the fix task
        for tid, t in state.tasks.items():
            if tid != replan_id and failed_task.task_id in t.dependencies:
                t.dependencies = [dep if dep != failed_task.task_id else replan_id for dep in t.dependencies]

        # Recompute execution order to include the new fix task
        state.execution_order = self.compute_topological_batches(state.tasks)
        state.total_estimated_time_sec = self.compute_pipeline_estimated_time(state.tasks, state.execution_order)
        return fix_task
