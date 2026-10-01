"use client";

import React from "react";
import { Users, BrainCircuit, Play, ShieldCheck, PieChart } from "lucide-react";

interface FleetState {
  planner: string;
  executor: string;
  verifier: string;
}

interface AgentFleetProps {
  fleetState: FleetState;
  modelCounts: Record<string, number>;
}

export function AgentFleet({ fleetState, modelCounts }: AgentFleetProps) {
  const totalModelAllocations = Object.values(modelCounts).reduce((a, b) => a + b, 0);

  const getStatusColor = (state: string) => {
    const s = state.toUpperCase();
    if (s === "BUSY" || s === "ACTIVE" || s === "VERIFYING") {
      return "text-cyan-400 bg-cyan-950/70 border-cyan-500/50 animate-pulse";
    }
    if (s === "REPLANNING") {
      return "text-orange-400 bg-orange-950/70 border-orange-500/50 animate-pulse";
    }
    if (s === "PASSED") {
      return "text-emerald-400 bg-emerald-950/70 border-emerald-500/50";
    }
    return "text-slate-400 bg-slate-950/40 border-slate-800";
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md shadow-lg flex flex-col gap-3.5">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Users className="w-4 h-4 text-purple-400" />
          Autonomous Agent Fleet
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <BrainCircuit className="w-4 h-4 text-purple-400" />
            <span>Team Leader (Planner)</span>
          </div>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${getStatusColor(
              fleetState.planner
            )}`}
          >
            {fleetState.planner}
          </span>
        </div>

        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Play className="w-4 h-4 text-blue-400" />
            <span>Tool Executor (Sandbox)</span>
          </div>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${getStatusColor(
              fleetState.executor
            )}`}
          >
            {fleetState.executor}
          </span>
        </div>

        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/60">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Deterministic Verifier Gate</span>
          </div>
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${getStatusColor(
              fleetState.verifier
            )}`}
          >
            {fleetState.verifier}
          </span>
        </div>
      </div>

      <div className="border-t border-slate-800/80 pt-3">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-medium">
          <span className="flex items-center gap-1.5">
            <PieChart className="w-3.5 h-3.5 text-cyan-400" />
            Dynamic Model Allocation
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            {totalModelAllocations} Tasks
          </span>
        </div>

        <div className="flex flex-col gap-1.5 text-xs">
          {Object.entries(modelCounts).map(([model, count]) => {
            const percent =
              totalModelAllocations > 0 ? Math.round((count / totalModelAllocations) * 100) : 0;
            return (
              <div key={model} className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px]">
                  <span className="font-mono text-slate-300">{model}</span>
                  <span className="font-mono text-slate-400">{percent}%</span>
                </div>
                <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800/50">
                  <div
                    className="bg-cyan-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
            );
          })}
          {Object.keys(modelCounts).length === 0 && (
            <div className="text-[11px] text-slate-500 italic text-center py-1">
              Awaiting model routing...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
