"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Play,
  Sparkles,
  Settings as SettingsIcon,
  RefreshCw,
  Terminal,
  FileCode,
  ShieldCheck,
  Radio,
  Cpu,
  Layers,
  Bug,
  Info,
  GripHorizontal,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

import { DAGCanvas } from "@/components/DAGCanvas";
import { SessionStats } from "@/components/SessionStats";
import { AgentFleet } from "@/components/AgentFleet";
import { TerminalLog, LogEntry } from "@/components/TerminalLog";
import { CodeArtifactViewer } from "@/components/CodeArtifactViewer";
import { TaskModal } from "@/components/TaskModal";
import { SettingsModal } from "@/components/SettingsModal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";

export default function ControlCenterPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [sessionState, setSessionState] = useState<any>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeBottomTab, setActiveBottomTab] = useState<"logs" | "artifacts" | "verifier">("logs");
  const [isTaskModalOpen, setIsTaskModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [githubResult, setGithubResult] = useState<{ repo_url: string; commit_sha: string; repo_name: string } | null>(null);

  // Resizable panels state
  const [bottomPanelHeight, setBottomPanelHeight] = useState<number>(270);
  const [isDraggingSplitter, setIsDraggingSplitter] = useState<boolean>(false);
  const [isBottomCollapsed, setIsBottomCollapsed] = useState<boolean>(false);
  const [isLeftCollapsed, setIsLeftCollapsed] = useState<boolean>(false);

  // Dragging logic for horizontal splitter between DAG canvas and bottom tabs
  useEffect(() => {
    if (!isDraggingSplitter) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY - 12;
      const clamped = Math.max(110, Math.min(newHeight, window.innerHeight - 240));
      setBottomPanelHeight(clamped);
      if (isBottomCollapsed) {
        setIsBottomCollapsed(false);
      }
    };

    const handleMouseUp = () => {
      setIsDraggingSplitter(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDraggingSplitter, isBottomCollapsed]);

  const [fleetState, setFleetState] = useState({
    planner: "IDLE",
    executor: "IDLE",
    verifier: "IDLE",
  });

  const [logs, setLogs] = useState<LogEntry[]>([
    {
      source: "System",
      message: "Autonomous Multi-Agent Software Team initialized. Ready for objective input.",
      level: "INFO",
      time: "INIT",
    },
  ]);

  const socketRef = useRef<WebSocket | null>(null);

  const appendLog = useCallback((source: string, message: string, level: "INFO" | "SUCCESS" | "ERROR" | "WARN" = "INFO") => {
    setLogs((prev) => [
      ...prev,
      {
        source,
        message,
        level,
        time: new Date().toLocaleTimeString(),
      },
    ]);
  }, []);

  // Initialize or fetch first session
  const initDefaultSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          objective: "Implement a Block actor scoring system with ScriptableObject event channel.",
          project_type: "unity",
          project_path: "d:\\Unity\\Project\\ls004-block-home",
          max_iterations: 15,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setSessionState(data);
        appendLog(
          "ContextLoader",
          `Phase 0 Ingested: ${data.ingested_rules?.length || 0} Rules, ${data.ingested_skills?.length || 0} Skills for ${data.project_type?.toUpperCase()} [${data.project_path || "Sandbox"}]`,
          "SUCCESS"
        );
        appendLog("Planner", `Generated initial DAG for session #${data.session_id} with ${Object.keys(data.tasks || {}).length} subtasks.`);
      }
    } catch {
      appendLog("System", "Could not reach backend server at " + API_BASE + ". Ensure python backend is running.", "WARN");
    }
  }, [appendLog]);

  useEffect(() => {
    initDefaultSession();
  }, [initDefaultSession]);

  const [reconnectKey, setReconnectKey] = useState(0);

  // Connect WebSocket when sessionId or reconnectKey changes
  useEffect(() => {
    if (!sessionId) return;

    let isSubscribed = true;
    let reconnectTimeout: NodeJS.Timeout;

    if (socketRef.current) {
      socketRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`);
    socketRef.current = ws;

    ws.onopen = () => {
      if (!isSubscribed) return;
      setIsConnected(true);
      appendLog("WebSocket", `Live link established for session #${sessionId}.`, "SUCCESS");
    };

    ws.onclose = () => {
      if (!isSubscribed) return;
      setIsConnected(false);
      appendLog("WebSocket", "Session stream disconnected. Reconnecting in 2s...", "WARN");
      reconnectTimeout = setTimeout(() => {
        if (isSubscribed) {
          setReconnectKey((prev) => prev + 1);
        }
      }, 2000);
    };

    ws.onerror = () => {
      if (!isSubscribed) return;
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      if (!isSubscribed) return;
      try {
        const payload = JSON.parse(event.data);
        const { event_type, data } = payload;

        switch (event_type) {
          case "INIT_STATE":
          case "SESSION_UPDATED":
            setSessionState(data);
            break;

          case "TASK_STARTED":
            setSessionState((prev: any) => {
              if (!prev) return prev;
              return {
                ...prev,
                status: "running",
                tasks: { ...prev.tasks, [data.task_id]: data },
              };
            });
            break;

          case "TASK_COMPLETED":
          case "TASK_FAILED":
            setSessionState((prev: any) => {
              if (!prev) return prev;
              return {
                ...prev,
                tasks: { ...prev.tasks, [data.task_id]: data },
              };
            });
            break;

          case "REPLAN_TRIGGERED":
            setSessionState((prev: any) => {
              if (!prev) return prev;
              return data.state;
            });
            appendLog(
              "Replanner",
              `Adaptive Replanning added fix node #${data.fix_task.task_id} for failed node #${data.failed_task_id}.`,
              "WARN"
            );
            break;

          case "MODEL_SWITCHED":
            appendLog("Router", `Assigned model ${data.model} to subtask #${data.task_id}.`);
            break;

          case "AGENT_FLEET_UPDATE":
            setFleetState(data);
            break;

          case "LOG_CHUNK":
            appendLog(data.source, data.message, data.level);
            break;

          case "RUN_FINISHED":
            setSessionState(data.state);
            appendLog("Orchestrator", `Execution finished with status: ${data.status}`, data.status === "SUCCESS" ? "SUCCESS" : "ERROR");
            break;

          case "GITHUB_PUSHED":
            setGithubResult(data);
            appendLog("GitHub", `Pushed to GitHub: ${data.repo_url}`, "SUCCESS");
            break;

          default:
            break;
        }
      } catch (err) {
        console.error("WS error parsing message:", err);
      }
    };

    return () => {
      isSubscribed = false;
      clearTimeout(reconnectTimeout);
      ws.close();
    };
  }, [sessionId, reconnectKey, appendLog]);

  // Active fallback polling while running to guarantee UI progress sync
  useEffect(() => {
    if (!sessionId || sessionState?.status !== "running") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
        if (res.ok) {
          const freshState = await res.json();
          setSessionState(freshState);
        }
      } catch {
        // Ignore background polling errors
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [sessionId, sessionState?.status]);

  // Handle Run
  const handleRunWorkflow = async (simulateFailure: boolean = false) => {
    if (!sessionId) return;
    try {
      appendLog("Orchestrator", `Triggering execution run (Simulate Failure: ${simulateFailure})...`);
      let activeSid = sessionId;
      let res = await fetch(`${API_BASE}/api/sessions/${activeSid}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulate_failure: simulateFailure, cost_constrained: false }),
      });

      // If backend restarted or session expired, auto-recreate and rerun
      if (res.status === 404) {
        appendLog("Orchestrator", "Session not found on backend (reloaded). Auto-recreating plan...", "WARN");
        const createRes = await fetch(`${API_BASE}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            objective: sessionState?.objective || "Implement a Block actor scoring system with ScriptableObject event channel.",
            cost_constrained: false,
            project_type: sessionState?.project_type || "unity",
            project_path: sessionState?.project_path || "d:\\Unity\\Project\\ls004-block-home",
            max_iterations: 15,
          }),
        });
        if (createRes.ok) {
          const freshData = await createRes.json();
          activeSid = freshData.session_id;
          setSessionId(activeSid);
          setSessionState(freshData);
          res = await fetch(`${API_BASE}/api/sessions/${activeSid}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ simulate_failure: simulateFailure, cost_constrained: false }),
          });
        }
      }

      if (res.ok) {
        setSessionState((prev: any) => ({ ...prev, status: "running" }));
      } else {
        const errData = await res.json().catch(() => ({}));
        appendLog("Orchestrator", `Failed to start run: ${errData.detail || res.statusText}`, "ERROR");
      }
    } catch {
      appendLog("System", "Failed to start workflow execution. Backend unreachable.", "ERROR");
    }
  };

  // Handle New Task Modal submission
  const handleCreateObjective = async (
    objective: string,
    costConstrained: boolean,
    simulateFailure: boolean,
    projectType: string = "unity",
    projectPath: string = "",
    referenceMedia: any[] = []
  ) => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          objective,
          cost_constrained: costConstrained,
          project_type: projectType,
          project_path: projectPath || null,
          max_iterations: 15,
          reference_media: referenceMedia,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setSessionState(data);
        appendLog(
          "ContextLoader",
          `Phase 0 Ingested: ${data.ingested_rules?.length || 0} Rules, ${data.ingested_skills?.length || 0} Skills for ${data.project_type?.toUpperCase()} [${data.project_path || "Sandbox"}]`,
          "SUCCESS"
        );
        appendLog("Planner", `Created session #${data.session_id} with ${Object.keys(data.tasks || {}).length} subtasks.`);

        // If user wanted immediate run with simulation
        if (simulateFailure) {
          setTimeout(() => handleRunWorkflow(true), 500);
        }
      }
    } catch {
      appendLog("System", "Error creating session.", "ERROR");
    }
  };

  // Derive model allocation counts
  const modelCounts: Record<string, number> = {};
  let completedTasksCount = 0;
  let totalTasksCount = 0;

  if (sessionState?.tasks) {
    const tasksArray = Object.values(sessionState.tasks) as any[];
    const superseded = new Set(tasksArray.filter((t) => t.retry_of).map((t) => t.retry_of));
    const activeTasks = tasksArray.filter((t) => !superseded.has(t.task_id));
    totalTasksCount = activeTasks.length;
    completedTasksCount = activeTasks.filter((t) => t.status === "completed").length;
    tasksArray.forEach((t) => {
      if (t.assigned_model) {
        modelCounts[t.assigned_model] = (modelCounts[t.assigned_model] || 0) + 1;
      }
    });
  }

  const selectedTask = selectedTaskId && sessionState?.tasks ? sessionState.tasks[selectedTaskId] : null;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#070b14] text-slate-100 overflow-hidden select-none">
      {/* HEADER BAR */}
      <header className="h-14 border-b border-slate-800/90 bg-slate-950/80 px-5 flex items-center justify-between backdrop-blur-md shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 via-indigo-600 to-purple-600 p-[1.5px] shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Cpu className="w-4 h-4 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-extrabold tracking-wider text-sm bg-gradient-to-r from-cyan-400 via-slate-100 to-purple-400 bg-clip-text text-transparent">
                AUTONOMOUS SOFTWARE TEAM
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-500/40">
                CONTROL CENTER
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-sans">
              Two-Tier Dynamic Routing • Closed-Loop Quality Gate • Adaptive DAG
            </p>
          </div>
        </div>

        {/* Live link status & action controls */}
        <div className="flex items-center gap-3">
          {sessionState && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono">
              <span className={`w-2 h-2 rounded-full ${sessionState.project_type === "unity" ? "bg-purple-400" : "bg-cyan-400"}`} />
              <span className="text-slate-300 font-bold uppercase">{sessionState.project_type || "GENERIC"}</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400 font-semibold" title={sessionState.context_summary || ""}>
                {sessionState.ingested_rules?.length || 0} Rules / {sessionState.ingested_skills?.length || 0} Skills
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400" : "bg-red-500"
              }`}
            />
            <span className="text-slate-400 text-[11px]">
              {isConnected ? "WS Connected" : "Connecting..."}
            </span>
          </div>

          <button
            onClick={() => setIsTaskModalOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-all shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            New Objective
          </button>

          <button
            onClick={() => handleRunWorkflow(false)}
            disabled={sessionState?.status === "running"}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-lg ${
              sessionState?.status === "running"
                ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                : "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/20"
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Run Workflow
          </button>

          <button
            onClick={() => handleRunWorkflow(true)}
            disabled={sessionState?.status === "running"}
            title="Demonstrates how an AST/Compiler error triggers the Adaptive Replanner to inject a fix node into the DAG"
            className="px-3 py-1.5 rounded-xl bg-orange-950/60 hover:bg-orange-900/60 border border-orange-500/50 text-orange-200 text-xs font-semibold flex items-center gap-1.5 transition-all"
          >
            <Bug className="w-3.5 h-3.5 text-orange-400" />
            Test Re-Plan Loop
          </button>

          <button
            onClick={() => setIsSettingsModalOpen(true)}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <SettingsIcon className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* GitHub Push Success Banner */}
      {githubResult && (
        <div className="flex items-center gap-3 px-4 py-2 bg-emerald-950/60 border-b border-emerald-500/30 text-xs font-mono animate-in slide-in-from-top duration-300">
          <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
          </svg>
          <span className="text-emerald-300 font-semibold">Pushed to GitHub:</span>
          <a
            href={githubResult.repo_url}
            target="_blank"
            rel="noreferrer"
            className="text-cyan-400 hover:text-cyan-300 underline truncate max-w-xs"
          >
            {githubResult.repo_name}
          </a>
          <span className="text-slate-500">·</span>
          <span className="text-slate-400">commit <span className="text-slate-200">{githubResult.commit_sha.slice(0, 7)}</span></span>
          <a
            href={githubResult.repo_url}
            target="_blank"
            rel="noreferrer"
            className="ml-auto px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-[11px] font-semibold transition-colors"
          >
            Open on GitHub →
          </a>
          <button
            onClick={() => setGithubResult(null)}
            className="text-slate-500 hover:text-slate-300 transition-colors ml-1"
          >✕</button>
        </div>
      )}

      {/* WORKSPACE MAIN BODY */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Floating Sidebar Toggle Button */}
        <button
          onClick={() => setIsLeftCollapsed(!isLeftCollapsed)}
          className={`absolute top-3 z-30 p-1.5 rounded-r-xl bg-slate-900/90 border border-l-0 border-slate-700 hover:border-cyan-400 text-slate-300 hover:text-cyan-300 flex items-center justify-center shadow-2xl transition-all duration-300 ${
            isLeftCollapsed ? "left-0" : "left-80"
          }`}
          title={isLeftCollapsed ? "Expand side panel" : "Collapse side panel"}
        >
          {isLeftCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>

        {/* LEFT CONTROL PANEL (Section 5.1 & 5.2) */}
        <aside
          className={`border-r border-slate-800/80 bg-slate-950/60 flex flex-col gap-3.5 overflow-y-auto shrink-0 backdrop-blur-sm transition-all duration-300 ${
            isLeftCollapsed ? "w-0 p-0 border-r-0 opacity-0 overflow-hidden pointer-events-none" : "w-80 p-3.5 opacity-100"
          }`}
        >
          <SessionStats
            objective={sessionState?.objective || ""}
            iteration={sessionState?.iteration || 0}
            maxIterations={sessionState?.max_iterations || 15}
            totalCostUsd={sessionState?.total_cost_usd || 0.0}
            totalEstimatedTimeSec={sessionState?.total_estimated_time_sec || 0}
            totalElapsedTimeSec={sessionState?.total_elapsed_time_sec || 0}
            status={sessionState?.status || "ready"}
            completedTasks={completedTasksCount}
            totalTasks={totalTasksCount}
            projectType={sessionState?.project_type || "generic"}
            projectPath={sessionState?.project_path}
            ingestedRulesCount={sessionState?.ingested_rules?.length || 0}
            ingestedSkillsCount={sessionState?.ingested_skills?.length || 0}
            referenceMedia={sessionState?.reference_media || []}
          />

          <AgentFleet fleetState={fleetState} modelCounts={modelCounts} />

          {/* Subtask Inspector Drawer */}
          {selectedTask && (
            <div className="bg-slate-900/90 border border-cyan-500/40 rounded-2xl p-3.5 backdrop-blur-md shadow-xl flex flex-col gap-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-cyan-300 font-mono flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" />
                  Subtask #{selectedTask.task_id}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                  {selectedTask.status}
                </span>
              </div>

              <div className="text-xs font-semibold text-slate-100">{selectedTask.title}</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{selectedTask.description}</p>

              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-1 text-slate-400">
                <div className="col-span-2 text-indigo-300 font-semibold bg-indigo-950/40 p-1.5 rounded border border-indigo-500/30">
                  Agent: {selectedTask.assigned_agent || "Autonomous Agent"}
                </div>
                <div>Model: <span className="text-cyan-300">{selectedTask.assigned_model || "N/A"}</span></div>
                <div>Domain: <span className="text-purple-300 capitalize">{selectedTask.domain}</span></div>
                <div>Complexity: <span className="text-amber-300">Lv.{selectedTask.complexity}</span></div>
                <div>Cost: <span className="text-emerald-400">${(selectedTask.cost_usd || 0).toFixed(4)}</span></div>
                <div>Est. Time: <span className="text-amber-300">~{selectedTask.estimated_time_sec || 0}s</span></div>
                <div>Actual: <span className="text-cyan-300">{selectedTask.execution_time_ms ? `${(selectedTask.execution_time_ms / 1000).toFixed(1)}s` : "Pending"}</span></div>
              </div>

              {selectedTask.routing_rationale && (
                <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-[10px] font-mono text-slate-400">
                  <span className="text-cyan-400 font-bold block mb-0.5">Two-Tier Routing Rationale:</span>
                  {selectedTask.routing_rationale}
                </div>
              )}

              {selectedTask.error_trace && (
                <div className="mt-2 p-2 rounded-lg bg-red-950/40 border border-red-500/50 text-[10px] font-mono text-red-300 max-h-28 overflow-y-auto whitespace-pre-wrap">
                  {selectedTask.error_trace}
                </div>
              )}
            </div>
          )}
        </aside>

        {/* RIGHT WORKSPACE (DAG Canvas + Bottom Panels) */}
        <main className="flex-1 flex flex-col overflow-hidden p-3 gap-2">
          {/* SECTION 3: LIVE DAG WORKFLOW CANVAS */}
          <div className="flex-1 min-h-[160px] overflow-hidden">
            <DAGCanvas
              tasks={sessionState?.tasks || {}}
              executionOrder={sessionState?.execution_order || []}
              onSelectTask={(id) => setSelectedTaskId(id)}
            />
          </div>

          {/* DRAGGABLE HORIZONTAL SPLITTER BAR */}
          <div
            onMouseDown={() => setIsDraggingSplitter(true)}
            className="group relative h-4 -my-0.5 flex items-center justify-center cursor-row-resize select-none z-20"
            title="Drag up or down to resize bottom panel / DAG canvas. Double-click to toggle collapse."
            onDoubleClick={() => setIsBottomCollapsed((prev) => !prev)}
          >
            <div
              className={`w-full h-[2px] transition-all ${
                isDraggingSplitter
                  ? "bg-cyan-400 shadow-md shadow-cyan-400/80"
                  : "bg-slate-800 group-hover:bg-cyan-500/70"
              }`}
            />

            <div
              className={`absolute px-3 py-0.5 rounded-full border text-[10px] font-mono flex items-center gap-1.5 transition-all backdrop-blur-md ${
                isDraggingSplitter
                  ? "bg-cyan-950 border-cyan-400 text-cyan-200 shadow-xl shadow-cyan-950/80 ring-2 ring-cyan-400/30"
                  : "bg-slate-900 border-slate-700 text-slate-400 group-hover:border-cyan-500 group-hover:text-cyan-300 shadow-lg"
              }`}
            >
              <GripHorizontal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline text-[9px] uppercase font-bold tracking-wider">
                {isBottomCollapsed ? "Collapsed (42px)" : `${Math.round(bottomPanelHeight)}px`}
              </span>
            </div>

            <div className="absolute right-2 flex items-center gap-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsBottomCollapsed((prev) => !prev);
                }}
                className="px-1.5 py-0.5 rounded bg-slate-900/90 border border-slate-700 hover:border-cyan-400 hover:text-cyan-300 text-slate-400 text-[10px] flex items-center gap-1 transition-colors"
                title={isBottomCollapsed ? "Expand bottom panel" : "Collapse bottom panel"}
              >
                {isBottomCollapsed ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                <span className="text-[9px]">{isBottomCollapsed ? "Expand" : "Collapse"}</span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsBottomCollapsed(false);
                  setBottomPanelHeight((prev) => (prev > 420 ? 270 : 540));
                }}
                className="p-1 rounded bg-slate-900/90 border border-slate-700 hover:border-cyan-400 hover:text-cyan-300 text-slate-400 transition-colors"
                title="Toggle Maximize/Default height"
              >
                {bottomPanelHeight > 420 ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
              </button>
            </div>
          </div>

          {/* SECTION 4: REAL-TIME LOG STREAM, DIFF & VERIFIER TABS */}
          <div
            style={{ height: isBottomCollapsed ? "42px" : `${bottomPanelHeight}px` }}
            className="flex flex-col shrink-0 overflow-hidden transition-[height] duration-100"
          >
            {/* Tab Header */}
            <div className="flex items-center gap-2 mb-2 shrink-0">
              <button
                onClick={() => {
                  setActiveBottomTab("logs");
                  if (isBottomCollapsed) setIsBottomCollapsed(false);
                }}
                className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  activeBottomTab === "logs"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <Terminal className="w-3.5 h-3.5" />
                Live Log Stream ({logs.length})
              </button>

              <button
                onClick={() => {
                  setActiveBottomTab("artifacts");
                  if (isBottomCollapsed) setIsBottomCollapsed(false);
                }}
                className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  activeBottomTab === "artifacts"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                Sandbox Diff & Code Viewer
              </button>

              <button
                onClick={() => {
                  setActiveBottomTab("verifier");
                  if (isBottomCollapsed) setIsBottomCollapsed(false);
                }}
                className={`px-3 py-1 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  activeBottomTab === "verifier"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Deterministic Quality Gate
              </button>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-hidden">
              {activeBottomTab === "logs" && (
                <TerminalLog logs={logs} onClearLogs={() => setLogs([])} />
              )}

              {activeBottomTab === "artifacts" && (
                <CodeArtifactViewer apiUrl={API_BASE} />
              )}

              {activeBottomTab === "verifier" && (
                <div className="bg-slate-950/90 border border-slate-800/80 rounded-2xl p-4 h-full overflow-y-auto font-mono text-xs flex flex-col gap-2 shadow-2xl">
                  <div className="text-slate-300 font-bold text-xs border-b border-slate-800 pb-2 flex items-center justify-between">
                    <span>Quality Gate Inspection Log</span>
                    <span className="text-[11px] text-slate-500 font-normal">Deterministic Verification Status</span>
                  </div>
                  {sessionState?.tasks &&
                    (Object.values(sessionState.tasks) as any[]).map((task) => (
                      <div
                        key={task.task_id}
                        className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              task.status === "completed"
                                ? "bg-emerald-400"
                                : task.status === "failed"
                                ? "bg-red-400"
                                : "bg-slate-600"
                            }`}
                          />
                          <span className="font-semibold text-slate-200">#{task.task_id}: {task.title}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-400">Model: {task.assigned_model || "None"}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              task.status === "completed"
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : task.status === "failed"
                                ? "bg-red-950 text-red-300 border border-red-800"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {task.status}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* MODALS */}
      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        onSubmit={handleCreateObjective}
        initialObjective={sessionState?.objective || ""}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        apiUrl={API_BASE}
      />
    </div>
  );
}
