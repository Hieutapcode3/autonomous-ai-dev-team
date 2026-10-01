"use client";

import React, { useState, useRef, useEffect } from "react";
import { Terminal, Trash2, ArrowDown, Filter } from "lucide-react";

export interface LogEntry {
  source: string;
  message: string;
  level: "INFO" | "SUCCESS" | "ERROR" | "WARN";
  time: string;
}

interface TerminalLogProps {
  logs: LogEntry[];
  onClearLogs: () => void;
}

export function TerminalLog({ logs, onClearLogs }: TerminalLogProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((log) => {
    if (filter === "ALL") return true;
    return log.source.toUpperCase() === filter.toUpperCase();
  });

  const getSourceBadge = (source: string) => {
    const s = source.toUpperCase();
    if (s.includes("ROUTER")) return "text-purple-400 bg-purple-950/60 border-purple-800";
    if (s.includes("EXECUTOR")) return "text-blue-400 bg-blue-950/60 border-blue-800";
    if (s.includes("VERIFIER")) return "text-emerald-400 bg-emerald-950/60 border-emerald-800";
    if (s.includes("REPLANNER")) return "text-orange-400 bg-orange-950/60 border-orange-800";
    if (s.includes("SANDBOX")) return "text-cyan-400 bg-cyan-950/60 border-cyan-800";
    if (s.includes("OLLAMA")) return "text-teal-300 bg-teal-950/70 border-teal-700 font-semibold";
    if (s.includes("CLI")) return "text-amber-300 bg-amber-950/70 border-amber-700 font-semibold";
    if (s.includes("GITHUB")) return "text-pink-300 bg-pink-950/70 border-pink-700";
    return "text-slate-400 bg-slate-900 border-slate-700";
  };

  const getLevelStyle = (level: string) => {
    switch (level) {
      case "SUCCESS":
        return "text-emerald-300";
      case "ERROR":
        return "text-red-400";
      case "WARN":
        return "text-amber-300";
      default:
        return "text-slate-200";
    }
  };

  const filterOptions = ["ALL", "ROUTER", "EXECUTOR", "VERIFIER", "OLLAMA", "CLI", "SANDBOX"];

  return (
    <div className="bg-slate-950/90 border border-slate-800/80 rounded-2xl flex flex-col h-full shadow-2xl overflow-hidden font-mono">
      <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-semibold text-slate-300">
            Real-Time Execution Log & Terminal
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            ({filteredLogs.length} events)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-slate-950/80 p-0.5 rounded-lg border border-slate-800 text-[10px]">
            {filterOptions.map((opt) => (
              <button
                key={opt}
                onClick={() => setFilter(opt)}
                className={`px-2 py-0.5 rounded-md transition-all ${
                  filter === opt
                    ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            title="Toggle Auto Scroll"
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              autoScroll
                ? "bg-cyan-950 text-cyan-400 border-cyan-800"
                : "bg-slate-900 text-slate-400 border-slate-800"
            }`}
          >
            <ArrowDown className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClearLogs}
            title="Clear Log"
            className="p-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="flex-1 p-3.5 overflow-y-auto space-y-1.5 text-xs text-slate-300 selection:bg-cyan-500/30 selection:text-white"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-slate-600 text-center py-8 italic font-sans text-xs">
            No execution logs recorded yet. Start a session or trigger a subtask.
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div
              key={index}
              className="flex items-start gap-2.5 leading-relaxed hover:bg-slate-900/40 p-1 rounded-md transition-colors"
            >
              <span className="text-slate-500 text-[11px] shrink-0">{log.time}</span>
              <span
                className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border shrink-0 ${getSourceBadge(
                  log.source
                )}`}
              >
                [{log.source}]
              </span>
              <span className={`flex-1 break-words whitespace-pre-wrap ${getLevelStyle(log.level)}`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
