"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  History,
  Folder,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Trash2,
  ExternalLink,
  Search,
  Layers,
  Zap,
  Bot,
  Play,
  ArrowRight,
  RefreshCw,
  KeyRound,
} from "lucide-react";

export interface SessionHistoryItem {
  session_id: string;
  status: string;
  objective: string;
  project_type: string;
  project_path?: string | null;
  created_at: number;
  updated_at: number;
  total_elapsed_time_sec?: number;
  total_cost_usd?: number;
  completed: number;
  total: number;
  artifacts_count?: number;
  use_simulation?: boolean;
  has_task_key?: boolean;
  has_run?: boolean;
}

interface SessionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onViewSummaryForSession: (sessionData: any) => void;
  apiUrl: string;
}

export function SessionHistoryModal({
  isOpen,
  onClose,
  currentSessionId,
  onSelectSession,
  onViewSummaryForSession,
  apiUrl,
}: SessionHistoryModalProps) {
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch {
      // Ignore background network error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSessions();
    }
  }, [isOpen, apiUrl]);

  if (!isOpen) return null;

  const handleDelete = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    if (!confirm(`Delete history for session #${sid}?`)) return;
    setDeletingId(sid);
    try {
      const res = await fetch(`${apiUrl}/api/sessions/${sid}`, { method: "DELETE" });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.session_id !== sid));
      }
    } catch {
      // Delete error
    } finally {
      setDeletingId(null);
    }
  };

  const [clearingDrafts, setClearingDrafts] = useState(false);

  const handleClearDrafts = async () => {
    if (!confirm("Clear all unexecuted / draft sessions from history?")) return;
    setClearingDrafts(true);
    try {
      const res = await fetch(`${apiUrl}/api/sessions/unexecuted`, { method: "DELETE" });
      if (res.ok) {
        await fetchSessions();
      }
    } catch {
      // Ignore background delete error
    } finally {
      setClearingDrafts(false);
    }
  };

  const handleOpenReport = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${apiUrl}/api/sessions/${sid}`);
      if (res.ok) {
        const fullData = await res.json();
        onViewSummaryForSession(fullData);
        onClose();
      }
    } catch {
      // Failed to load
    }
  };

  const filteredSessions = sessions.filter((s) => {
    const q = searchQuery.toLowerCase();
    return (
      s.objective.toLowerCase().includes(q) ||
      s.session_id.toLowerCase().includes(q) ||
      (s.project_path && s.project_path.toLowerCase().includes(q)) ||
      s.project_type.toLowerCase().includes(q)
    );
  });

  const formatTime = (ts?: number) => {
    if (!ts) return "Just now";
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " • " + d.toLocaleDateString();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* MODAL HEADER */}
        <div className="p-5 border-b border-slate-800/80 bg-slate-950/70 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-500/20">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">Workflow Run History</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-500/30 font-bold">
                  {sessions.length} RUNS
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Browse previously executed objectives, inspect modified files, and switch active sessions.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleClearDrafts}
              disabled={clearingDrafts || isLoading}
              title="Delete all sessions that were never executed"
              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-amber-300 hover:bg-amber-950/40 border border-slate-800 hover:border-amber-500/40 transition-colors flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5 text-amber-400" />
              Clear Drafts
            </button>
            <button
              onClick={fetchSessions}
              disabled={isLoading}
              title="Refresh session list"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* SEARCH BAR */}
        <div className="p-4 bg-slate-950/50 border-b border-slate-800/80">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by objective keyword, project path, or session ID..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs font-sans text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/60"
            />
          </div>
        </div>

        {/* SESSIONS LIST */}
        <div className="p-4 space-y-3 overflow-y-auto flex-1">
          {filteredSessions.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
              <History className="w-8 h-8 text-slate-600" />
              <span>No past workflow sessions found.</span>
            </div>
          ) : (
            filteredSessions.map((s) => {
              const isCurrent = s.session_id === currentSessionId;
              const isCompleted = s.status === "completed";
              const isRunning = s.status === "running";

              return (
                <div
                  key={s.session_id}
                  onClick={() => {
                    onSelectSession(s.session_id);
                    onClose();
                  }}
                  className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col gap-2.5 ${
                    isCurrent
                      ? "bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-950/30 ring-1 ring-cyan-500/30"
                      : "bg-slate-950/60 border-slate-800/80 hover:bg-slate-900/80 hover:border-slate-700"
                  }`}
                >
                  {/* TOP ROW: ID, STATUS, TIME */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-300">
                        #{s.session_id}
                      </span>
                      {isCurrent && (
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/40 font-bold uppercase">
                          CURRENT
                        </span>
                      )}
                      {s.has_task_key && (
                        <span className="flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/40 font-bold" title="Protected by Task Key">
                          <KeyRound className="w-2.5 h-2.5 text-indigo-400" />
                          KEY
                        </span>
                      )}
                      <span
                        className={`text-[9px] font-mono px-2 py-0.5 rounded-full font-bold uppercase ${
                          s.has_run === false
                            ? "bg-slate-800 text-slate-400 border border-slate-700"
                            : isCompleted
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : isRunning
                            ? "bg-blue-950 text-blue-300 border border-blue-800 animate-pulse"
                            : s.status === "stopped"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-rose-950 text-rose-300 border border-rose-800"
                        }`}
                      >
                        {s.has_run === false ? "DRAFT (NOT RUN)" : s.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{formatTime(s.created_at)}</span>
                    </div>
                  </div>

                  {/* OBJECTIVE TEXT */}
                  <p className="text-xs font-semibold text-slate-100 line-clamp-2 leading-relaxed">
                    "{s.objective}"
                  </p>

                  {/* PROJECT PATH & METRICS ROW */}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[11px] text-slate-400">
                    <div className="flex items-center gap-2 truncate max-w-[65%]">
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase font-bold shrink-0 ${
                          s.project_type === "unity"
                            ? "bg-purple-950 text-purple-300 border border-purple-800"
                            : "bg-cyan-950 text-cyan-300 border border-cyan-800"
                        }`}
                      >
                        {s.project_type}
                      </span>
                      <span className="truncate font-mono text-slate-300 text-[10px]" title={s.project_path || ""}>
                        {s.project_path || "Default Sandbox"}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 font-mono text-[10px]">
                      <span className="text-slate-300">
                        {s.completed}/{s.total} Tasks
                      </span>

                      {s.use_simulation !== false ? (
                        <span className="text-amber-400 flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          Sim
                        </span>
                      ) : (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <Bot className="w-3 h-3" />
                          AI
                        </span>
                      )}

                      {/* ACTIONS */}
                      <button
                        type="button"
                        onClick={(e) => handleOpenReport(e, s.session_id)}
                        title="View Full Completion Report & Diff"
                        className="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-400 text-[10px] flex items-center gap-1 transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Report
                      </button>

                      <button
                        type="button"
                        onClick={(e) => handleDelete(e, s.session_id)}
                        disabled={deletingId === s.session_id}
                        title="Delete session"
                        className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* MODAL FOOTER */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 font-mono">
            Click any session row to switch active view in DAG Canvas
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
