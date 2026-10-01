"use client";

import React from "react";
import { Target, RotateCcw, DollarSign, Activity, CheckCircle, AlertTriangle, Clock, Timer } from "lucide-react";

interface SessionStatsProps {
  objective: string;
  iteration: number;
  maxIterations: number;
  totalCostUsd: number;
  totalEstimatedTimeSec?: number;
  totalElapsedTimeSec?: number;
  status: string;
  completedTasks: number;
  totalTasks: number;
}

export function SessionStats({
  objective,
  iteration,
  maxIterations,
  totalCostUsd,
  totalEstimatedTimeSec = 0,
  totalElapsedTimeSec = 0,
  status,
  completedTasks,
  totalTasks,
}: SessionStatsProps) {
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const getStatusBadge = () => {
    switch (status.toLowerCase()) {
      case "running":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-500/60 flex items-center gap-1.5 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            RUNNING
          </span>
        );
      case "completed":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5" />
            COMPLETED
          </span>
        );
      case "failed":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-300 border border-red-500/60 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            FAILED
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            READY
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md shadow-lg flex flex-col gap-3.5">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          Objective & Session Stats
        </span>
        {getStatusBadge()}
      </div>

      <div className="text-sm font-medium text-slate-200 line-clamp-2 leading-relaxed bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
        {objective || "No active objective set"}
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
            <span>Iteration</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-200">
            {iteration} / {maxIterations}
          </span>
        </div>

        <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>Cost</span>
          </div>
          <span className="text-xs font-mono font-bold text-emerald-400">
            ${totalCostUsd.toFixed(4)}
          </span>
        </div>

        <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Est. Time</span>
          </div>
          <span className="text-xs font-mono font-bold text-amber-300">
            ~{totalEstimatedTimeSec}s
          </span>
        </div>

        <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Timer className="w-3.5 h-3.5 text-cyan-400" />
            <span>Elapsed</span>
          </div>
          <span className="text-xs font-mono font-bold text-cyan-400">
            {totalElapsedTimeSec > 0 ? `${totalElapsedTimeSec.toFixed(1)}s` : "0.0s"}
          </span>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-slate-400">DAG Execution Progress</span>
          <span className="font-mono text-cyan-400 font-bold">
            {completedTasks}/{totalTasks} ({progressPercent}%)
          </span>
        </div>
        <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800/80">
          <div
            className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-500 shadow-sm shadow-cyan-500/50"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
