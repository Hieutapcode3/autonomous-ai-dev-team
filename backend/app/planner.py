import re
import uuid
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque
from app.schemas import SubTask, TaskDomain, TaskStatus, GlobalDAGState


class PlannerEngine:
    @staticmethod
    def _match_scripts(discovered_scripts: List[str], objective: str) -> List[str]:
        """
        Identify scripts explicitly or structurally referenced in the objective without hardcoded language dictionaries:
        1. Tokens with file extensions (.cs, .uxml, .uss, etc.) or @mentions
        2. PascalCase / CamelCase class identifiers (e.g. BlockHomeLevelEditorWindow, GameManager)
        3. Hyphenated / compound identifiers (e.g. level-editor, grid_manager)
        """
        if not discovered_scripts or not objective:
            return []

        # Extract tokens that structurally look like code artifacts
        file_tokens = re.findall(r"@?([\w\.-]+\.(?:cs|uxml|uss|json|shader|py|ts|js))\b", objective, re.IGNORECASE)
        pascal_tokens = re.findall(r"\b([A-Z][a-zA-Z0-9]+)\b", objective)
        compound_tokens = re.findall(r"\b([a-zA-Z0-9]+[-_][a-zA-Z0-9_-]+)\b", objective)

        candidate_identifiers = set()
        for t in file_tokens + pascal_tokens + compound_tokens:
            candidate_identifiers.add(t.lower())
            candidate_identifiers.add(Path(t).stem.lower())

        if not candidate_identifiers:
            return []

        exact_matches: List[str] = []
        partial_matches: List[str] = []

        for script in discovered_scripts:
            s_name = Path(script).name.lower()
            s_stem = Path(script).stem.lower()

            if s_name in candidate_identifiers or s_stem in candidate_identifiers:
                if script not in exact_matches:
                    exact_matches.append(script)
                continue

            for t in candidate_identifiers:
                if len(t) >= 6 and t in s_stem:
                    if script not in partial_matches and script not in exact_matches:
                        partial_matches.append(script)
                    break

        return (exact_matches + partial_matches)[:4]

    def decompose_objective(
        self,
        session_id: str,
        objective: str,
        project_type: str = "generic",
        rules: Optional[List[Dict[str, Any]]] = None,
        skills: Optional[List[Dict[str, Any]]] = None,
        discovered_scripts: Optional[List[str]] = None,
        discovered_ui: Optional[List[str]] = None,
        explicit_target_files: Optional[List[str]] = None,
    ) -> GlobalDAGState:
        tasks: Dict[str, SubTask] = {}

        t1_id = f"task_{uuid.uuid4().hex[:6]}"
        t2_id = f"task_{uuid.uuid4().hex[:6]}"
        t3_id = f"task_{uuid.uuid4().hex[:6]}"
        t4_id = f"task_{uuid.uuid4().hex[:6]}"
        t5_id = f"task_{uuid.uuid4().hex[:6]}"

        if project_type == "unity":
            scripts = discovered_scripts or []

            # Check if any rule is an explicitly mentioned primary specification (e.g. level-editor.md)
            primary_spec = next((r for r in (rules or []) if r.get("is_primary_spec")), None)
            spec_guide_text = ""
            if primary_spec:
                spec_guide_text = (
                    f"\n\n=== PRIMARY USER SPECIFICATION ({primary_spec.get('source', '')}) ===\n"
                    f"You MUST align your implementation strictly with this specification:\n"
                    f"{primary_spec.get('content')[:3500]}\n"
                    f"==========================================================\n"
                )

            is_level_editor = (
                any(
                    kw in objective.lower()
                    for kw in ["level editor", "leveleditor", "level-editor", "level_editor", "board editor", "map editor", "màn chơi", "stage editor"]
                )
                or ("level" in objective.lower() and "editor" in objective.lower())
            )
            is_editor_tool = is_level_editor or any(
                kw in objective.lower()
                for kw in ["editor", "editor window", "tool cho gd", "authoring", "editor tooling"]
            )

            # Determine base scripts directory
            base_script_dir = "Assets/BlockHome/Scripts" if any("BlockHome" in s for s in scripts) else "Assets/Scripts"
            if scripts:
                first_script = scripts[0].replace("\\", "/")
                parts = first_script.split("/")
                if len(parts) >= 3:
                    base_script_dir = "/".join(parts[:parts.index("Scripts") + 1]) if "Scripts" in parts else "/".join(parts[:-1])

            if explicit_target_files:
                code_targets = [f for f in explicit_target_files if not f.endswith((".uxml", ".uss"))]
                ui_targets = [f for f in explicit_target_files if f.endswith((".uxml", ".uss"))]
                impl_files = code_targets or explicit_target_files
                scene_files = ui_targets or [
                    f for f in (discovered_ui or []) if any(Path(c).stem in f for c in impl_files)
                ] or (discovered_ui[:2] if discovered_ui else [impl_files[0]])

                first_target = impl_files[0]
                target_stem = Path(first_target).stem

                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title=f"Core C# Implementation: {target_stem}",
                    description=(
                        f"Implement requested changes for objective: '{objective}' directly into target files.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(impl_files)}\n"
                        "MANDATORY ANTI-STUB RULES: Zero skeleton code, zero TODO comments. Write complete, working methods."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_read", "fs_write"],
                    target_files=impl_files,
                )

                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="UI Toolkit Layout & Styling Alignment",
                    description=(
                        f"Align visual layout, UXML, and USS styles for: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(scene_files)}\n"
                        "Ensure styling adheres to editor conventions and non-destructive guidelines."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=6,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=scene_files,
                )

                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="Deterministic Quality Gate & Unity Verification",
                    description="Verify C# code syntax, check rule compliance, and validate Unity editor console logs.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t2_id],
                    required_tools=["terminal_exec", "test_runner"],
                )

            elif is_level_editor:
                # Targeted 5-phase deliverables pipeline for Level Editor matching Antigravity IDE standard
                editor_script_dir = "Assets/BlockHome/Scripts/Editor/LevelEditor" if any("BlockHome" in s for s in scripts) else f"{base_script_dir}/Editor/LevelEditor"
                editor_ui_dir = "Assets/BlockHome/Editor" if any("BlockHome" in s for s in scripts) else "Assets/Editor/LevelEditor"

                data_files = [
                    f"{editor_script_dir}/EditorLevelData.cs",
                    f"{editor_script_dir}/EditorSerialization.cs",
                ]
                ui_files = [
                    f"{editor_ui_dir}/UXML/BlockHomeLevelEditorWindow.uxml",
                    f"{editor_ui_dir}/USS/BlockHomeLevelEditorWindow.uss",
                ]
                window_files = [
                    f"{editor_script_dir}/BlockHomeLevelEditorWindow.cs",
                    f"{editor_script_dir}/BlockHomeLevelEditorWindow.Toolbar.cs",
                ]
                validation_files = [
                    f"{editor_script_dir}/BlockHomeLevelEditorWindow.Validation.cs",
                    f"{editor_script_dir}/LevelEditorPlayTest.cs",
                ]

                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title="Level Editor Data Models & Serialization Engine",
                    description=(
                        f"Implement complete C# data structures and serialization for the Level Editor objective: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(data_files)}\n\n"
                        "DELIVERABLES & REQUIREMENTS:\n"
                        "- Grid cell model (2D/3D matrix), layer definitions (Floor, Walls, Furniture/Obstacles, Characters/Spawns, Doors).\n"
                        "- Level metadata (ID, LevelNumber, GridWidth, GridHeight, MoveLimit, ParTime, ThemeConfig).\n"
                        "- Serialization methods: LoadFromJson, SaveToJson, ScriptableObject export, and Undo/Redo state snapshot structs.\n"
                        "- STRICT MANDATE: Full production C# code (> 200 lines). Zero empty methods, zero TODOs."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_read", "fs_write"],
                    target_files=data_files,
                )

                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="UI Toolkit Visual Hierarchy & USS Styling (UXML/USS)",
                    description=(
                        f"Implement the complete UI Toolkit structure and stylesheet for the Level Editor: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(ui_files)}\n\n"
                        "DELIVERABLES & REQUIREMENTS:\n"
                        "- Multi-column responsive layout: Header toolbar (New/Open/Save/Validate/PlayTest buttons), "
                        "Left sidebar (Level list scroll view), Center viewport (Canvas container with pan/zoom scroll view), "
                        "and Right sidebar (Tool palette buttons + Inspector property fields).\n"
                        "- Comprehensive USS styles: Unity dark theme variables (--unity-colors-*), hover/active states for tools, "
                        "grid cell borders, badge pills, and clean margins/padding."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=7,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=ui_files,
                )

                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="EditorWindow Controller & Interactive Tool Modes",
                    description=(
                        f"Implement the main EditorWindow C# controller and interactive tool state machine: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(window_files)}\n\n"
                        "DELIVERABLES & REQUIREMENTS:\n"
                        "- Inherit from EditorWindow with [MenuItem('Tools/BlockHome/Level Editor')].\n"
                        "- CreateGUI(): Load and clone UXML, bind button ClickEvents, setup slider/field ChangeEvents.\n"
                        "- Tool State Machine: Paint mode (place blocks), Erase mode (clear cells), Pick mode (sample cell data), Select mode (inspect properties).\n"
                        "- Grid pointer interactions: PointerDown, PointerMove, PointerUp drag painting.\n"
                        "- Visual redraw loop: Draw grid cells with appropriate color coding and preview highlights.\n"
                        "- STRICT MANDATE: Minimum 250+ lines of robust, working C# logic. Zero skeleton stubs."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=8,
                    dependencies=[t2_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=window_files,
                )

                tasks[t4_id] = SubTask(
                    task_id=t4_id,
                    title="Level Validation Engine & PlayTest Bridge",
                    description=(
                        f"Implement the validation rules and PlayTest launcher bridge for: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(validation_files)}\n\n"
                        "DELIVERABLES & REQUIREMENTS:\n"
                        "- Validation engine: Check perimeter wall boundary closure, verify at least one spawn point and goal exist, check furniture path clearance.\n"
                        "- Error visualizer: Return list of ValidationError(type, message, cellCoord) and highlight erroneous cells on the canvas.\n"
                        "- PlayTest bridge: Save temporary level state, switch to Unity Play Mode (EditorApplication.isPlaying = true), and instruct LevelLoader to load active test data."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=7,
                    dependencies=[t3_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=validation_files,
                )

                tasks[t5_id] = SubTask(
                    task_id=t5_id,
                    title="Deterministic Quality Gate & Unity Verification",
                    description=(
                        "Verify C# code syntax across all editor scripts, enforce anti-stub rule compliance (no empty bodies or TODOs), "
                        "and validate Unity Editor compilation via Unity MCP / console logs."
                    ),
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t4_id],
                    required_tools=["terminal_exec", "test_runner"],
                )

            elif is_editor_tool:
                # Other editor tooling (general tools, custom inspectors)
                feature_name = "CustomTool"
                editor_script_dir = f"{base_script_dir}/Editor/{feature_name}"
                impl_files = [f"{editor_script_dir}/{feature_name}Window.cs", f"{editor_script_dir}/{feature_name}Data.cs"]
                ui_files = [f"{editor_script_dir}/{feature_name}Window.uxml", f"{editor_script_dir}/{feature_name}Window.uss"]

                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title=f"Editor Tool Logic Implementation ({feature_name})",
                    description=(
                        f"Implement editor tooling logic and data models for: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(impl_files)}\n"
                        "STRICT ANTI-STUB MANDATE: Write fully implemented classes and methods. Zero TODOs."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_read", "fs_write"],
                    target_files=impl_files,
                )

                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="UI Toolkit Visual Layout & Styling",
                    description=(
                        f"Implement UI Toolkit UXML layout and USS styles for: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(ui_files)}"
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=6,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=ui_files,
                )

                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="Deterministic Quality Gate & Unity Verification",
                    description="Verify C# code syntax, check rule compliance, and validate Unity editor console logs.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t2_id],
                    required_tools=["terminal_exec", "test_runner"],
                )

            else:
                # General Gameplay / System Implementation
                feature_name = "GameplayFeature"
                impl_files = [f"{base_script_dir}/{feature_name}Controller.cs", f"{base_script_dir}/{feature_name}Data.cs"]

                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title=f"Gameplay C# Logic Implementation ({feature_name})",
                    description=(
                        f"Implement core gameplay logic and data models for: '{objective}'.\n"
                        f"{spec_guide_text}\n"
                        f"TARGET FILES: {', '.join(impl_files)}\n"
                        "STRICT ANTI-STUB MANDATE: Write complete working code. Zero stubs."
                    ),
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_read", "fs_write"],
                    target_files=impl_files,
                )

                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="Deterministic Quality Gate & Unity Verification",
                    description="Verify C# syntax, check rule compliance, and validate Unity editor console logs.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t1_id],
                    required_tools=["terminal_exec", "test_runner"],
                )
        else:
            obj_lower = objective.lower()
            is_game_proto = any(k in obj_lower for k in ["html", "canvas", "game", "playable", "three.js", "prototype", "2d", "3d", "arcade", "puzzle"])
            is_web_app = any(k in obj_lower for k in ["react", "next", "vue", "frontend", "ui", "web app", "dashboard", "tailwind"])

            if is_game_proto:
                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title="Playable Game Architecture & Tech Stack Selection",
                    description=f"Analyze mechanics for '{objective}'. Select rendering context (Canvas 2D vs Three.js/WebGL), establish entity state machine and loop contracts.",
                    domain=TaskDomain.ARCHITECTURE,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_write"],
                    target_files=["GameArchitectureSpec.md"],
                )
                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="Playable Game Engine & Core Mechanics Implementation",
                    description="Implement single-file HTML5/JS game loop (requestAnimationFrame), player input controller, scoring formulas, and entity physics.",
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=7,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write", "terminal_exec"],
                    target_files=["index.html"],
                )
                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="Juice, Visual Polish & Web Audio Synthesizer",
                    description="Integrate particle systems, screen shake, floating combo text popups, and Web Audio API synthesizer for zero-asset audio.",
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=6,
                    dependencies=[t2_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=["index.html"],
                )
                tasks[t4_id] = SubTask(
                    task_id=t4_id,
                    title="Deterministic Playability & Quality Gate Verification",
                    description="Verify HTML structure, check JavaScript execution without syntax errors, validate zero external dependencies, and confirm responsive touch/mouse inputs.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t3_id],
                    required_tools=["terminal_exec", "test_runner"],
                    target_files=["index.html"],
                )
            elif is_web_app:
                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title="Web Application Architecture & Framework Blueprint",
                    description=f"Analyze requirements for '{objective}'. Select framework (Next.js/React/Vite), design component hierarchy, state flow, and styling tokens.",
                    domain=TaskDomain.ARCHITECTURE,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_write"],
                    target_files=["ArchitectureSpec.md"],
                )
                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="UI Components & Responsive Layout Construction",
                    description="Build UI components with modern aesthetics, accessible forms, state hooks, and client-side validation.",
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=7,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write", "terminal_exec"],
                    target_files=["src/App.tsx", "package.json"],
                )
                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="Business Logic & State Management Integration",
                    description="Implement business handlers, API communications, caching, and reactive data store.",
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=6,
                    dependencies=[t2_id],
                    required_tools=["fs_read", "fs_write"],
                    target_files=["src/store.ts"],
                )
                tasks[t4_id] = SubTask(
                    task_id=t4_id,
                    title="Automated Quality Gate & Build Verification",
                    description="Execute TypeScript type checks, bundle compilation, and automated test suite.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=5,
                    dependencies=[t3_id],
                    required_tools=["terminal_exec", "test_runner"],
                )
            else:
                tasks[t1_id] = SubTask(
                    task_id=t1_id,
                    title="System Architecture & Technology Selection",
                    description=f"Analyze requirements for: '{objective}'. Determine optimal tech stack, interface contracts, and module boundaries.",
                    domain=TaskDomain.ARCHITECTURE,
                    complexity=8,
                    dependencies=[],
                    required_tools=["fs_write"],
                    target_files=["ArchitectureSpec.md"],
                )
                tasks[t2_id] = SubTask(
                    task_id=t2_id,
                    title="Core Domain & Service Logic Implementation",
                    description="Implement business calculation engine, data structures, and main algorithmic methods.",
                    domain=TaskDomain.IMPLEMENTATION,
                    complexity=7,
                    dependencies=[t1_id],
                    required_tools=["fs_read", "fs_write", "terminal_exec"],
                    target_files=["src/service.py"],
                )
                tasks[t3_id] = SubTask(
                    task_id=t3_id,
                    title="Unit Tests & Automated Test Harness",
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
                    description="Execute full linter, syntax analysis, and test runner across the workspace.",
                    domain=TaskDomain.VERIFICATION,
                    complexity=4,
                    dependencies=[t3_id],
                    required_tools=["terminal_exec", "test_runner"],
                )

        from app.router import DynamicModelRouter
        router = DynamicModelRouter()

        for task_id, task in tasks.items():
            task.estimated_time_sec = self.estimate_task_duration(task.domain, task.complexity)
            if project_type == "unity":
                agent_names = {
                    TaskDomain.ARCHITECTURE: "Game Architect",
                    TaskDomain.IMPLEMENTATION: "Gameplay C# Programmer",
                    TaskDomain.VERIFICATION: "Unity QA Verifier",
                    TaskDomain.ANALYSIS: "Game Systems Analyst",
                    TaskDomain.UTILITY: "Unity Asset Tool Specialist",
                }
                task.assigned_agent = agent_names.get(task.domain, "Unity Specialist")
            elif any(k in objective.lower() for k in ["html", "canvas", "game", "playable", "three.js", "prototype"]):
                agent_names = {
                    TaskDomain.ARCHITECTURE: "Creative Game Architect",
                    TaskDomain.IMPLEMENTATION: "Senior Game Developer",
                    TaskDomain.VERIFICATION: "Game QA Verifier",
                }
                task.assigned_agent = agent_names.get(task.domain, "Game Engineer")
            elif any(k in objective.lower() for k in ["react", "next", "vue", "frontend", "ui", "web app"]):
                agent_names = {
                    TaskDomain.ARCHITECTURE: "Full-Stack Architect",
                    TaskDomain.IMPLEMENTATION: "Frontend Engineer",
                    TaskDomain.VERIFICATION: "Web QA Specialist",
                }
                task.assigned_agent = agent_names.get(task.domain, "Web Developer")
            else:
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
            max_iterations=15,
            total_cost_usd=0.0,
            total_estimated_time_sec=total_est,
            total_elapsed_time_sec=0.0,
            status="ready",
            project_type=project_type,
            ingested_rules=rules or [],
            ingested_skills=skills or [],
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

        error_trace = failed_task.error_trace or "Verification gate rejection — no error detail."

        # Compute retry depth to avoid title explosion like "[FIX] [FIX] [FIX]..."
        clean_title = re.sub(r"^(\[FIX(?:\s*#\d+)?\]\s*)+", "", failed_task.title).strip()
        depth = 1
        curr = failed_task
        while curr.retry_of and curr.retry_of in state.tasks:
            depth += 1
            curr = state.tasks[curr.retry_of]
        replan_title = f"[FIX #{depth}] {clean_title}"

        # Extract any source files mentioned in the compiler error trace (e.g. Assets\...\LevelLoader.cs)
        discovered_error_files = re.findall(r"(?:Assets|assets)[\\/][^\s\(\):;,]+\.cs", error_trace)
        normalized_error_files = [f.replace("\\", "/") for f in discovered_error_files]
        all_targets = list(dict.fromkeys((failed_task.target_files or []) + normalized_error_files))

        fix_description = (
            f"CRITICAL FIX REQUIRED: Fix compiler / quality gate errors for: '{clean_title}'.\n\n"
            f"MANDATORY NON-DESTRUCTIVE FIX RULES:\n"
            f"1. MINIMAL SURGICAL FIXES ONLY: Do NOT rewrite entire unrelated systems. Fix ONLY the compile errors.\n"
            f"2. RESTORE MISSING METHODS: If errors mention missing methods (e.g. 'ReloadCurrentLevel', 'LoadNextLevel'), you MUST restore or declare them. NEVER delete methods that other scripts depend on.\n"
            f"3. STRICT SIGNATURE CHECK: Fix type mismatches (e.g. Vector2 vs Vector2Int) and method argument counts.\n"
            f"4. PRESERVE 100% OF EXISTING WORKING CODE: Keep all other methods, fields, and classes intact.\n\n"
            f"=== ERROR TRACE ===\n{error_trace}\n===================\n\n"
            f"Target files that must be fixed: {', '.join(all_targets) if all_targets else 'same as failed task'}."
        )

        fix_task = SubTask(
            task_id=replan_id,
            title=replan_title,
            description=fix_description,
            domain=failed_task.domain,
            complexity=min(10, failed_task.complexity + 1),
            dependencies=[failed_task.task_id],
            required_tools=failed_task.required_tools,
            status=TaskStatus.PENDING,
            retry_of=failed_task.task_id,
            target_files=all_targets,
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
