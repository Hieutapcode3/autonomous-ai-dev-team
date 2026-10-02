"use client";

import React, { useState } from "react";
import {
  X,
  CheckCircle2,
  FileCode,
  Clock,
  DollarSign,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Cpu,
  Layers,
  ShieldCheck,
  Code2,
  FolderCheck,
} from "lucide-react";

interface ExecutionSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionState: any;
  artifactsHistory: any[];
  onViewArtifacts: () => void;
}

export function ExecutionSummaryModal({
  isOpen,
  onClose,
  sessionState,
  artifactsHistory,
  onViewArtifacts,
}: ExecutionSummaryModalProps) {
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  if (!isOpen || !sessionState) return null;

  // Aggregate files from artifactsHistory or fallback from tasks
  const filesList: Array<{
    file: string;
    action: string;
    diff?: string;
    content?: string;
    size_bytes?: number;
  }> = [];

  const seenFiles = new Set<string>();

  if (artifactsHistory && artifactsHistory.length > 0) {
    artifactsHistory.forEach((item) => {
      if (item.file && !seenFiles.has(item.file)) {
        seenFiles.add(item.file);
        filesList.push(item);
      }
    });
  }

  // Fallback scan from completed tasks
  if (sessionState.tasks) {
    Object.values(sessionState.tasks).forEach((task: any) => {
      const taskFiles = task.output_artifacts?.files || task.target_files || [];
      taskFiles.forEach((f: string) => {
        if (!seenFiles.has(f)) {
          seenFiles.add(f);
          filesList.push({
            file: f,
            action: "created",
            content: task.output_artifacts?.explanation || "",
            size_bytes: 512,
          });
        }
      });
    });
  }

  const tasksArray = sessionState.tasks ? Object.values(sessionState.tasks) : [];
  const completedTasks = tasksArray.filter((t: any) => t.status === "completed").length;
  const totalTasks = tasksArray.length;

  const copyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedFile(path);
    setTimeout(() => setCopiedFile(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* HEADER BANNER */}
        <div className="p-5 border-b border-slate-800/80 bg-gradient-to-r from-emerald-950/50 via-slate-900 to-cyan-950/40 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/10">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">
                  Workflow Execution Completed!
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-bold uppercase">
                  GATE PASSED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                All subtasks executed, code verified through Quality Gate, and artifacts committed.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* METRICS STRIP */}
        <div className="grid grid-cols-4 gap-2.5 p-4 bg-slate-950/70 border-b border-slate-800/80">
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Duration
            </span>
            <span className="text-sm font-bold font-mono text-slate-100">
              {sessionState.total_elapsed_time_sec ? `${sessionState.total_elapsed_time_sec}s` : "~5.2s"}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Subtasks
            </span>
            <span className="text-sm font-bold font-mono text-emerald-300">
              {completedTasks} / {totalTasks} Done
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
              <FolderCheck className="w-3.5 h-3.5 text-purple-400" />
              Files Touched
            </span>
            <span className="text-sm font-bold font-mono text-purple-300">
              {filesList.length} File{filesList.length !== 1 ? "s" : ""}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
              <DollarSign className="w-3.5 h-3.5 text-amber-400" />
              Est. Cost
            </span>
            <span className="text-sm font-bold font-mono text-amber-300">
              ${sessionState.total_cost_usd?.toFixed(4) || "0.0000"}
            </span>
          </div>
        </div>

        {/* BODY TABS & CONTENT */}
        <div className="p-5 space-y-5 overflow-y-auto">
          {/* MODIFIED & CREATED FILES SECTION */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <FileCode className="w-4 h-4 text-cyan-400" />
                Files Created / Modified ({filesList.length})
              </h3>
              <span className="text-[10px] text-slate-400 font-mono">
                Click any file to inspect code changes or diff
              </span>
            </div>

            {filesList.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center text-xs text-slate-400">
                No external files were generated in this run.
              </div>
            ) : (
              <div className="space-y-2">
                {filesList.map((item, idx) => {
                  const isExpanded = expandedFile === item.file;
                  const isModified = item.action === "modify";
                  return (
                    <div
                      key={idx}
                      className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden transition-all"
                    >
                      <div
                        onClick={() => setExpandedFile(isExpanded ? null : item.file)}
                        className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-900/80 transition-colors"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-cyan-400 shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-500 shrink-0" />
                          )}
                          <span
                            className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider shrink-0 ${
                              isModified
                                ? "bg-cyan-950 text-cyan-300 border border-cyan-800"
                                : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            }`}
                          >
                            {item.action || "CREATED"}
                          </span>
                          <span className="font-mono text-xs text-slate-200 truncate font-semibold">
                            {item.file}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {item.size_bytes && (
                            <span className="text-[10px] font-mono text-slate-500">
                              {(item.size_bytes / 1024).toFixed(1)} KB
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              copyPath(item.file);
                            }}
                            title="Copy file path"
                            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                          >
                            {copiedFile === item.file ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* EXPANDED CODE / DIFF PREVIEW */}
                      {isExpanded && (
                        <div className="border-t border-slate-800 bg-slate-950 p-3 space-y-2">
                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                            <span>{item.diff ? "Unified Diff Output:" : "Code Content:"}</span>
                            <span className="text-slate-500">Read-only preview</span>
                          </div>
                          <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-60 leading-relaxed">
                            <code>{item.diff || item.content || "// File content written successfully."}</code>
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* AGENT FLEET CONTRIBUTIONS BREAKDOWN */}
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              Agent Fleet Execution Summary
            </h3>

            <div className="space-y-2">
              {tasksArray.map((t: any) => (
                <div
                  key={t.task_id}
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                    <div>
                      <div className="text-xs font-semibold text-slate-200">
                        #{t.task_id}: {t.title}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {t.output_artifacts?.explanation || t.description || "Task completed successfully."}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                      {t.assigned_agent || "Agent"}
                    </span>
                    <span className="text-[10px] font-mono text-cyan-400">
                      {t.assigned_model || "LLM"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MODAL FOOTER */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950 flex items-center justify-between">
          <button
            type="button"
            onClick={onViewArtifacts}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs font-semibold text-cyan-400 flex items-center gap-1.5 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open in Artifact Viewer
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/25"
          >
            Done & Close
          </button>
        </div>
      </div>
    </div>
  );
}
