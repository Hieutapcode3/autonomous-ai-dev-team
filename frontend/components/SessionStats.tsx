import React from "react";
import { Target, RotateCcw, DollarSign, Activity, CheckCircle, AlertTriangle, Clock, Timer, ShieldCheck, Gamepad2, Globe, Image as ImageIcon, Video, ExternalLink } from "lucide-react";

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
  projectType?: string;
  projectPath?: string;
  ingestedRulesCount?: number;
  ingestedSkillsCount?: number;
  referenceMedia?: Array<{
    name: string;
    filename?: string;
    file_path?: string;
    url: string;
    media_type: string;
    size_bytes?: number;
  }>;
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
  projectType = "generic",
  projectPath,
  ingestedRulesCount = 0,
  ingestedSkillsCount = 0,
  referenceMedia = [],
}: SessionStatsProps) {
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
  const isUnity = projectType === "unity";

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
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md shadow-lg flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          Objective & Session Stats
        </span>
        {getStatusBadge()}
      </div>

      {/* Target Project & Phase 0 Ingested Badge */}
      <div className={`p-2.5 rounded-xl border flex items-center justify-between text-xs font-mono ${
        isUnity
          ? "bg-purple-950/40 border-purple-500/40 text-purple-300"
          : "bg-cyan-950/40 border-cyan-500/40 text-cyan-300"
      }`}>
        <div className="flex items-center gap-2 truncate">
          {isUnity ? <Gamepad2 className="w-4 h-4 text-purple-400 shrink-0" /> : <Globe className="w-4 h-4 text-cyan-400 shrink-0" />}
          <span className="font-bold uppercase tracking-wider">{isUnity ? "Unity Game" : "Sandbox Web"}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-semibold shrink-0">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>{ingestedRulesCount} Rules • {ingestedSkillsCount} Skills</span>
        </div>
      </div>

      <div className="text-sm font-medium text-slate-200 line-clamp-2 leading-relaxed bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
        {objective || "No active objective set"}
      </div>

      {/* Visual Reference Previews */}
      {referenceMedia && referenceMedia.length > 0 && (
        <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60 flex flex-col gap-2">
          <div className="flex items-center justify-between text-[11px] font-semibold text-slate-300">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <ImageIcon className="w-3.5 h-3.5" />
              Visual Ref Inputs ({referenceMedia.length})
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Art & Layout</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {referenceMedia.map((m, idx) => {
              const mediaUrl = m.url?.startsWith("http") ? m.url : `http://localhost:8000${m.url}`;
              return (
                <a
                  key={idx}
                  href={mediaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="relative group shrink-0 rounded-lg overflow-hidden border border-slate-700/80 hover:border-cyan-400 transition-all"
                  title={`${m.name} (${m.media_type}) - Click to preview`}
                >
                  {m.media_type === "image" ? (
                    <img
                      src={mediaUrl}
                      alt={m.name}
                      className="w-11 h-11 object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-11 h-11 bg-purple-950 flex flex-col items-center justify-center text-purple-300">
                      <Video className="w-4 h-4" />
                      <span className="text-[7px] font-bold mt-0.5">VIDEO</span>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    <ExternalLink className="w-3 h-3 text-white" />
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      )}

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
