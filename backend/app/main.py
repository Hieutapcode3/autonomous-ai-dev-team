import asyncio
import uuid
import os
import shutil
import httpx
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas import (
    GlobalDAGState,
    CreateSessionRequest,
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


@app.post("/api/sessions", response_model=GlobalDAGState)
async def create_session(req: CreateSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    state = planner_engine.decompose_objective(session_id=session_id, objective=req.objective)
    state.max_iterations = req.max_iterations
    sessions[session_id] = state
    return state


@app.get("/api/sessions/{session_id}", response_model=GlobalDAGState)
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


class RunOptions(BaseModel):
    simulate_failure: bool = False
    cost_constrained: bool = False


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str, opts: RunOptions = RunOptions()):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    if state.status == "running":
        return {"message": "Session is already executing.", "status": "running"}

    router = DynamicModelRouter(
        cost_constrained=opts.cost_constrained,
        force_simulator=current_settings.simulation_mode,
        use_local_provider=current_settings.use_local_provider,
        local_provider_type=current_settings.local_provider_type,
        ollama_model=current_settings.ollama_model,
    )
    verifier = VerifierGate(sandbox=sandbox_runtime)

    orchestrator = TeamOrchestrator(
        state=state,
        router=router,
        sandbox=sandbox_runtime,
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
