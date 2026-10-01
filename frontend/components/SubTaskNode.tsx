"use client";

import React from "react";
import { Handle, Position } from "@xyflow/react";
import { CheckCircle2, XCircle, Loader2, Sparkles, RefreshCw, Cpu, Layers, Clock, Timer, Bot } from "lucide-react";

export interface SubTaskNodeData extends Record<string, unknown> {
  id: string;
  title: string;
  description: string;
  domain: string;
  complexity: number;
  assignedModel?: string;
  assignedAgent?: string;
  routingRationale?: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  retryOf?: string;
  costUsd?: number;
  executionTimeMs?: number;
  estimatedTimeSec?: number;
}

export function SubTaskNode({ data }: { data: SubTaskNodeData }) {
  const getBadgeColor = (model?: string) => {
    if (!model) return "bg-slate-800 text-slate-300 border-slate-700";
    const m = model.toLowerCase();
    if (m.includes("opus")) return "bg-purple-950/90 text-purple-200 border-purple-500/80";
    if (m.includes("sonnet")) return "bg-blue-950/90 text-blue-200 border-blue-500/80";
    if (m.includes("4o-mini")) return "bg-emerald-950/90 text-emerald-200 border-emerald-500/80";
    if (m.includes("4o")) return "bg-amber-950/90 text-amber-200 border-amber-500/80";
    if (m.includes("gemini")) return "bg-teal-950/90 text-teal-200 border-teal-500/80";
    if (m.includes("deepseek")) return "bg-indigo-950/90 text-indigo-200 border-indigo-500/80";
    return "bg-slate-800 text-slate-300 border-slate-600";
  };

  const getStatusBorder = () => {
    switch (data.status) {
      case "running":
        return "border-cyan-400 animate-glow-cyan ring-1 ring-cyan-400";
      case "completed":
        return "border-emerald-500/80 shadow-emerald-950/30";
      case "failed":
        return "border-red-500/90 shadow-red-950/30";
      default:
        return "border-slate-800 hover:border-slate-700";
    }
  };

  return (
    <div
      className={`p-4 rounded-xl border-2 shadow-2xl w-72 backdrop-blur-md transition-all duration-300 ${
        data.status === "running"
          ? "bg-slate-900/95"
          : data.status === "failed"
          ? "bg-red-950/20"
          : "bg-slate-900/80"
      } ${getStatusBorder()}`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 !bg-cyan-400 !border-2 !border-slate-900"
      />

      {data.retryOf && (
        <div className="mb-2 flex items-center gap-1.5 px-2 py-0.5 rounded bg-orange-950/60 border border-orange-500/50 text-[10px] text-orange-300 font-mono">
          <RefreshCw className="w-3 h-3 animate-spin text-orange-400" />
          <span>REPLAN FIX NODE (Fixes #{data.retryOf})</span>
        </div>
      )}

      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-mono font-semibold text-slate-400 flex items-center gap-1">
          <Layers className="w-3 h-3 text-cyan-400" />
          #{data.id.substring(0, 10)}
        </span>
        <span
          className={`text-[11px] font-mono px-2 py-0.5 rounded-full border flex items-center gap-1 ${getBadgeColor(
            data.assignedModel
          )}`}
        >
          <Cpu className="w-3 h-3" />
          {data.assignedModel || "Auto Route"}
        </span>
      </div>

      {data.assignedAgent && (
        <div className="mb-2 flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-indigo-950/60 border border-indigo-500/40 text-[10px] text-indigo-300 font-medium">
          <Bot className="w-3 h-3 text-indigo-400" />
          <span>{data.assignedAgent}</span>
        </div>
      )}

      <div className="font-semibold text-sm text-slate-100 mb-1 leading-snug line-clamp-2">
        {data.title}
      </div>
      <div className="text-xs text-slate-400 line-clamp-2 mb-3 leading-relaxed">
        {data.description}
      </div>

      <div className="flex justify-between items-center text-[11px] pt-2 border-t border-slate-800/80">
        <span className="capitalize text-slate-300 font-medium flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          {data.domain}
        </span>
        <div className="flex items-center gap-2">
          {data.estimatedTimeSec !== undefined && data.estimatedTimeSec > 0 && (
            <span className="text-[10px] text-amber-400/90 font-mono flex items-center gap-1 bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-500/30">
              <Clock className="w-2.5 h-2.5" />
              ~{data.estimatedTimeSec}s
            </span>
          )}
          <span className="font-semibold text-cyan-400 font-mono">
            Diff: Lv.{data.complexity}
          </span>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
        <div className="flex items-center gap-1.5">
          {data.status === "running" && (
            <span className="flex items-center gap-1 text-cyan-400 font-mono font-medium">
              <Loader2 className="w-3 h-3 animate-spin" /> RUNNING (~{data.estimatedTimeSec}s)
            </span>
          )}
          {data.status === "completed" && (
            <div className="flex items-center gap-1 text-emerald-400 font-medium">
              <CheckCircle2 className="w-3 h-3" />
              <span>PASSED</span>
              {data.executionTimeMs !== undefined && data.executionTimeMs > 0 && (
                <span className="text-[9px] text-emerald-300 font-mono bg-emerald-950/70 px-1 rounded ml-1">
                  {(data.executionTimeMs / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          )}
          {data.status === "failed" && (
            <span className="flex items-center gap-1 text-red-400 font-medium">
              <XCircle className="w-3 h-3" /> REJECTED
            </span>
          )}
          {data.status === "pending" && (
            <span className="text-slate-500 flex items-center gap-1">
              <Timer className="w-2.5 h-2.5" /> QUEUED (Est: ~{data.estimatedTimeSec}s)
            </span>
          )}
        </div>

        {data.costUsd !== undefined && data.costUsd > 0 && (
          <span className="font-mono text-slate-300">
            ${data.costUsd.toFixed(4)}
          </span>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 !bg-cyan-400 !border-2 !border-slate-900"
      />
    </div>
  );
}
