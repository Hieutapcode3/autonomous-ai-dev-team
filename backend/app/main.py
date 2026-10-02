import asyncio
import uuid
import os
import shutil
import re
import httpx
from typing import Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas import (
    GlobalDAGState,
    CreateSessionRequest,
    StopSessionRequest,
    WebSocketEvent,
    ConfigSettings,
)
from app.router import DynamicModelRouter
from app.sandbox import SandboxRuntime
from app.verifier import VerifierGate
from app.planner import PlannerEngine
from app.llm import LLMClient
from app.orchestrator import TeamOrchestrator


app = FastAPI(title="Autonomous Multi-Agent Software Team API", version="1.0.0")

# Mount uploads directory for reference media
uploads_root = Path("uploads")
uploads_root.mkdir(parents=True, exist_ok=True)
(uploads_root / "references").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_root.resolve())), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active sessions and connections
sessions: Dict[str, GlobalDAGState] = {}
orchestrators: Dict[str, TeamOrchestrator] = {}
active_connections: Dict[str, List[WebSocket]] = {}
sandbox_runtime = SandboxRuntime()
planner_engine = PlannerEngine()
llm_client = LLMClient()
current_settings = ConfigSettings()


class ConnectionManager:
    @staticmethod
    async def connect(websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in active_connections:
            active_connections[session_id] = []
        active_connections[session_id].append(websocket)

    @staticmethod
    def disconnect(websocket: WebSocket, session_id: str):
        if session_id in active_connections:
            if websocket in active_connections[session_id]:
                active_connections[session_id].remove(websocket)

    @staticmethod
    async def broadcast_event(event: WebSocketEvent):
        session_id = event.session_id
        if session_id in active_connections:
            dead_connections = []
            for connection in active_connections[session_id]:
                try:
                    await connection.send_text(event.model_dump_json())
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                active_connections[session_id].remove(dead)


manager = ConnectionManager()


from app.context_loader import ProjectContextLoader


@app.post("/api/sessions", response_model=GlobalDAGState)
async def create_session(req: CreateSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    context = ProjectContextLoader.ingest(req.project_path, req.project_type)
    state = planner_engine.decompose_objective(
        session_id=session_id,
        objective=req.objective,
        project_type=context["project_type"],
        rules=context["rules"],
        skills=context["skills"],
    )
    state.project_path = context["project_path"]
    state.project_type = context["project_type"]
    state.ingested_rules = context["rules"]
    state.ingested_skills = context["skills"]
    state.context_summary = context["summary"]
    state.reference_media = req.reference_media
    state.demo_html = req.demo_html or next((m for m in req.reference_media if m.get("media_type") == "html"), None)
    state.use_simulation = req.use_simulation
    state.max_iterations = req.max_iterations
    if req.task_key:
        state.task_key = req.task_key.strip()
        state.has_task_key = True
    sessions[session_id] = state
    return state


@app.post("/api/upload-reference")
async def upload_reference_media(file: UploadFile = File(...)):
    uploads_dir = Path("uploads/references")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    file_ext = Path(file.filename or "file").suffix.lower()
    unique_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = uploads_dir / unique_name

    content = await file.read()
    save_path.write_bytes(content)

    is_video = file_ext in [".mp4", ".webm", ".mov", ".mkv", ".avi"]
    is_html = file_ext in [".html", ".htm"]

    extracted_logic = None
    if is_html:
        media_type = "html"
        try:
            text_content = content.decode("utf-8", errors="replace")
            script_blocks = re.findall(r"<script[\s\S]*?>([\s\S]*?)</script>", text_content, flags=re.IGNORECASE)
            scripts_combined = "\n".join(script_blocks) if script_blocks else text_content

            functions = re.findall(r"function\s+([a-zA-Z0-9_]+)\s*\(", scripts_combined)
            arrow_funcs = re.findall(r"(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:\([^)]*\)|[a-zA-Z0-9_]+)?\s*=>", scripts_combined)
            all_funcs = list(dict.fromkeys(functions + arrow_funcs))[:30]

            const_vars = re.findall(r"(?:const|let|var)\s+([a-zA-Z0-9_]+)", scripts_combined)
            all_vars = list(dict.fromkeys(const_vars))[:40]

            has_canvas = bool(re.search(r"<canvas[\s\S]*?>", text_content, flags=re.IGNORECASE))
            has_request_anim = "requestAnimationFrame" in scripts_combined

            extracted_logic = {
                "has_canvas": has_canvas,
                "has_game_loop": has_request_anim or "setInterval" in scripts_combined,
                "functions": all_funcs,
                "variables": all_vars,
                "code_snippet": scripts_combined[:5000],
            }
        except Exception as e:
            extracted_logic = {"error": str(e)}
    elif is_video:
        media_type = "video"
    else:
        media_type = "image"

    return {
        "name": file.filename,
        "filename": unique_name,
        "file_path": str(save_path.resolve()),
        "url": f"/uploads/references/{unique_name}",
        "media_type": media_type,
        "size_bytes": len(content),
        "extracted_logic": extracted_logic,
    }


@app.get("/api/context/inspect")
async def inspect_project_context(path: Optional[str] = None, project_type: Optional[str] = "generic"):
    return ProjectContextLoader.ingest(path, project_type)


@app.get("/api/sessions")
async def list_sessions():
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "status": s.status,
                "objective": s.objective,
                "project_type": s.project_type,
                "project_path": s.project_path,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "total_elapsed_time_sec": s.total_elapsed_time_sec,
                "total_cost_usd": s.total_cost_usd,
                "completed": len([t for t in s.tasks.values() if t.status == "completed"]),
                "total": len(s.tasks),
                "artifacts_count": len(s.artifacts_history),
                "use_simulation": s.use_simulation,
                "has_task_key": bool(getattr(s, "task_key", None)),
                "has_run": s.status in ["running", "completed", "failed", "stopped"] and (s.total_elapsed_time_sec > 0 or len(s.artifacts_history) > 0 or any(t.status == "completed" for t in s.tasks.values())),
            }
            for sid, s in reversed(list(sessions.items()))
        ]
    }


@app.delete("/api/sessions/unexecuted")
async def clear_unexecuted_sessions():
    """Delete all sessions that were never executed (no completed tasks and no elapsed time)."""
    to_delete = [
        sid for sid, s in list(sessions.items())
        if s.status in ["idle", "active"] and not any(t.status == "completed" for t in s.tasks.values()) and s.total_elapsed_time_sec == 0
    ]
    for sid in to_delete:
        del sessions[sid]
        if sid in orchestrators:
            del orchestrators[sid]
    return {"deleted_count": len(to_delete), "deleted_sessions": to_delete}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        if session_id in orchestrators:
            del orchestrators[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str, req: StopSessionRequest = StopSessionRequest()):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]

    # Verify task key if configured
    if getattr(state, "task_key", None):
        submitted_key = (req.task_key or "").strip()
        expected_key = state.task_key.strip()
        if submitted_key != expected_key:
            raise HTTPException(
                status_code=403,
                detail="Mã Task Key không chính xác. Không thể dừng quy trình đang chạy!",
            )

    orch = orchestrators.get(session_id)
    if orch:
        orch.stop_execution()

    state.status = "stopped"
    await manager.broadcast_event(
        WebSocketEvent(
            event_type="RUN_STOPPED",
            session_id=session_id,
            timestamp=time.time(),
            data={
                "session_id": session_id,
                "status": "stopped",
                "message": "Workflow stopped by user request.",
            },
        )
    )
    return {"status": "stopped", "session_id": session_id}


@app.get("/api/sessions/{session_id}", response_model=GlobalDAGState)
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


class RunOptions(BaseModel):
    simulate_failure: bool = False
    cost_constrained: bool = False
    use_simulation: Optional[bool] = None
    task_key: Optional[str] = None


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str, opts: RunOptions = RunOptions()):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    if state.status == "running":
        return {"message": "Session is already executing.", "status": "running"}

    if opts.task_key:
        state.task_key = opts.task_key.strip()
        state.has_task_key = True

    sim_mode = (
        opts.use_simulation
        if opts.use_simulation is not None
        else getattr(state, "use_simulation", current_settings.simulation_mode)
    )
    llm_client.simulation_mode = sim_mode

    has_cloud_keys = bool(
        llm_client.anthropic_key
        or llm_client.openai_key
        or llm_client.google_key
        or llm_client.openrouter_key
    )
    use_local = current_settings.use_local_provider or (not sim_mode and not has_cloud_keys)

    router = DynamicModelRouter(
        cost_constrained=opts.cost_constrained,
        force_simulator=sim_mode,
        use_local_provider=use_local,
        local_provider_type=current_settings.local_provider_type,
        ollama_model=current_settings.ollama_model,
    )
    active_sandbox = (
        SandboxRuntime(base_workspace=state.project_path)
        if state.project_path and os.path.exists(state.project_path)
        else sandbox_runtime
    )
    verifier = VerifierGate(sandbox=active_sandbox)

    orchestrator = TeamOrchestrator(
        state=state,
        router=router,
        sandbox=active_sandbox,
        verifier=verifier,
        planner=planner_engine,
        llm_client=llm_client,
        event_callback=manager.broadcast_event,
        simulate_failure_once=opts.simulate_failure,
        github_token=current_settings.github_token or None,
        auto_push_github=current_settings.auto_push_github,
    )
    orchestrators[session_id] = orchestrator

    # Launch DAG execution asynchronously
    asyncio.create_task(orchestrator.execute_dag())
    return {"status": "started", "session_id": session_id}


@app.get("/api/workspace/files")
async def list_workspace_files():
    files = sandbox_runtime.fs_list()
    return {"files": files, "artifacts": sandbox_runtime.artifacts_history}


@app.get("/api/workspace/file")
async def get_workspace_file(path: str = Query(...)):
    try:
        content = sandbox_runtime.fs_read(path)
        matching_artifacts = [
            a for a in sandbox_runtime.artifacts_history if a.get("file") == path
        ]
        diff = matching_artifacts[-1].get("diff", "") if matching_artifacts else ""
        return {"path": path, "content": content, "diff": diff}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/local-status")
async def get_local_status():
    """Detect presence and health of local Ollama server and Claude Code CLI."""
    ollama_online = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{current_settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_online = True
                data = resp.json()
                ollama_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        pass

    claude_cli_path = shutil.which("claude")
    if not claude_cli_path:
        local_p = os.path.expanduser("~/.local/bin/claude.exe")
        if os.path.exists(local_p):
            claude_cli_path = local_p

    gemini_cli_path = (
        shutil.which("gemini-cli")
        or shutil.which("gemini")
        or shutil.which("gemini-cli.exe")
        or shutil.which("gemini.exe")
    )
    if not gemini_cli_path:
        candidate_dirs = [
            os.path.expanduser("~\\AppData\\Local\\Programs\\Python\\Python312\\Scripts"),
            os.path.expanduser("~\\AppData\\Roaming\\Python\\Python312\\Scripts"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "venv", "Scripts"),
        ]
        for d in candidate_dirs:
            for fname in ["gemini-cli.exe", "gemini.exe", "gemini-cli.cmd", "gemini.cmd"]:
                full_path = os.path.join(d, fname)
                if os.path.exists(full_path):
                    gemini_cli_path = full_path
                    break
            if gemini_cli_path:
                break

    return {
        "ollama": {
            "online": ollama_online,
            "base_url": current_settings.ollama_base_url,
            "models": ollama_models,
        },
        "claude_cli": {
            "found": bool(claude_cli_path),
            "path": claude_cli_path,
        },
        "gemini_cli": {
            "found": bool(gemini_cli_path),
            "path": gemini_cli_path,
        },
    }


@app.get("/api/settings")
async def get_settings():
    return {
        "simulation_mode": current_settings.simulation_mode,
        "default_cost_constrained": current_settings.default_cost_constrained,
        "has_anthropic_key": bool(llm_client.anthropic_key),
        "has_openai_key": bool(llm_client.openai_key),
        "has_google_key": bool(llm_client.google_key),
        "auto_push_github": current_settings.auto_push_github,
        "has_github_token": bool(current_settings.github_token),
        "use_local_provider": current_settings.use_local_provider,
        "local_provider_type": current_settings.local_provider_type,
        "ollama_model": current_settings.ollama_model,
        "ollama_base_url": current_settings.ollama_base_url,
        "gemini_cli_command": current_settings.gemini_cli_command,
    }


@app.post("/api/settings")
async def update_settings(cfg: ConfigSettings):
    global current_settings
    current_settings = cfg
    if cfg.anthropic_api_key:
        llm_client.anthropic_key = cfg.anthropic_api_key
    if cfg.openai_api_key:
        llm_client.openai_key = cfg.openai_api_key
    if cfg.google_api_key:
        llm_client.google_key = cfg.google_api_key
    if cfg.openrouter_api_key:
        llm_client.openrouter_key = cfg.openrouter_api_key
    if cfg.ollama_base_url:
        llm_client.ollama_base_url = cfg.ollama_base_url
    return {"status": "updated"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    # Send current state immediately on connect
    if session_id in sessions:
        await websocket.send_text(
            WebSocketEvent(
                event_type="INIT_STATE",
                session_id=session_id,
                data=sessions[session_id].model_dump(),
            ).model_dump_json()
        )
    try:
        while True:
            # Keep socket alive and receive any client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
