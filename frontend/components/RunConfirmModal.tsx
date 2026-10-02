"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Play,
  AlertTriangle,
  Folder,
  Layers,
  Cpu,
  ShieldCheck,
  Zap,
  Bot,
  Settings,
  HelpCircle,
  FileCode,
} from "lucide-react";

interface RunConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (simulateFailure: boolean, useSimulation: boolean) => void;
  sessionState: any;
  currentSimulationMode: boolean;
  onToggleSimulationMode: (val: boolean) => void;
  apiUrl: string;
}

export function RunConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  sessionState,
  currentSimulationMode,
  onToggleSimulationMode,
  apiUrl,
}: RunConfirmModalProps) {
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [providerInfo, setProviderInfo] = useState<{
    ollamaOnline: boolean;
    ollamaModel: string;
    hasCloudKey: boolean;
  }>({
    ollamaOnline: false,
    ollamaModel: "qwen2.5-coder:7b",
    hasCloudKey: false,
  });

  useEffect(() => {
    if (!isOpen) return;

    // Check backend provider status
    const checkProviders = async () => {
      try {
        const [settingsRes, localRes] = await Promise.all([
          fetch(`${apiUrl}/api/settings`).then((r) => r.json()).catch(() => ({})),
          fetch(`${apiUrl}/api/settings/local-status`).then((r) => r.json()).catch(() => ({})),
        ]);

        const hasKey = Boolean(
          settingsRes.has_anthropic_key ||
          settingsRes.has_openai_key ||
          settingsRes.has_google_key
        );

        setProviderInfo({
          ollamaOnline: Boolean(localRes?.ollama?.online),
          ollamaModel: settingsRes.ollama_model || "qwen2.5-coder:7b",
          hasCloudKey: hasKey,
        });
      } catch {
        // Fallback on error
      }
    };

    checkProviders();
  }, [isOpen, apiUrl]);

  if (!isOpen) return null;

  const tasksCount = sessionState?.tasks ? Object.keys(sessionState.tasks).length : 0;
  const projectType = (sessionState?.project_type || "generic").toUpperCase();
  const projectPath = sessionState?.project_path || "Default Sandbox Directory";

  const handleStart = () => {
    onConfirm(simulateFailure, currentSimulationMode);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* MODAL HEADER */}
        <div className="p-5 border-b border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-500/20">
              <Play className="w-5 h-5 fill-current" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Confirm Execution Run
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                  PRE-RUN CHECK
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Verify target environment, project path, and engine mode before starting.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* MODAL BODY */}
        <div className="p-5 space-y-4 overflow-y-auto">
          {/* OBJECTIVE CARD */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-semibold uppercase text-slate-400 tracking-wider">
                Objective / Target Goal
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {tasksCount} Subtasks Planned
              </span>
            </div>
            <p className="text-xs font-semibold text-slate-200 leading-relaxed">
              "{sessionState?.objective || "No objective defined"}"
            </p>
          </div>

          {/* PROJECT & DESTINATION INFO */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-semibold uppercase text-slate-400 tracking-wider">
                Target Project Environment
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                projectType === "UNITY"
                  ? "bg-purple-950 text-purple-300 border border-purple-500/30"
                  : "bg-cyan-950 text-cyan-300 border border-cyan-500/30"
              }`}>
                {projectType}
              </span>
            </div>

            <div className="flex items-start gap-2 text-xs font-mono text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
              <Folder className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-0.5 overflow-hidden">
                <span className="text-[10px] text-slate-400 font-sans">Workspace Directory:</span>
                <span className="truncate text-slate-200 font-medium" title={projectPath}>
                  {projectPath}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-0.5">
              <span className="flex items-center gap-1 text-emerald-400 font-mono">
                <ShieldCheck className="w-3.5 h-3.5" />
                {sessionState?.ingested_rules?.length || 0} Rules Ingested
              </span>
              <span>•</span>
              <span className="font-mono text-indigo-300">
                {sessionState?.ingested_skills?.length || 0} Specialized Skills
              </span>
            </div>
          </div>

          {/* EXECUTION ENGINE SELECTION */}
          <div className="space-y-2">
            <label className="text-[10px] font-mono font-semibold uppercase text-slate-400 tracking-wider block">
              Execution Engine Mode
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              {/* Simulation Mode Option */}
              <button
                type="button"
                onClick={() => onToggleSimulationMode(true)}
                className={`p-3 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                  currentSimulationMode
                    ? "bg-amber-950/40 border-amber-500/80 text-amber-200 shadow-md shadow-amber-950/40 ring-1 ring-amber-500/40"
                    : "bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-300"
                }`}
              >
                <div className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  ⚡ Fast Simulation (~3-5s)
                </div>
                <div className="text-[10px] text-slate-400 leading-snug">
                  Zero token cost. Fast-forwards subtasks to inspect DAG layout, websocket logs, and UI.
                </div>
              </button>

              {/* Real Multi-Agent Option */}
              <button
                type="button"
                onClick={() => onToggleSimulationMode(false)}
                className={`p-3 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                  !currentSimulationMode
                    ? "bg-emerald-950/40 border-emerald-500/80 text-emerald-200 shadow-md shadow-emerald-950/40 ring-1 ring-emerald-500/40"
                    : "bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-300"
                }`}
              >
                <div className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  <Bot className="w-3.5 h-3.5 text-emerald-400" />
                  🤖 Real Multi-Agent (~2-10m)
                </div>
                <div className="text-[10px] text-slate-400 leading-snug">
                  Invokes actual AI (Ollama Local or Cloud LLMs) to analyze codebase and write real code.
                </div>
              </button>
            </div>

            {/* Provider status indicator when Real Mode is active */}
            {!currentSimulationMode && (
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px] font-mono">
                <div className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-slate-300">Active AI Backend:</span>
                  {providerInfo.ollamaOnline ? (
                    <span className="text-emerald-400 font-bold">
                      Local Ollama ({providerInfo.ollamaModel}) [Free]
                    </span>
                  ) : providerInfo.hasCloudKey ? (
                    <span className="text-cyan-400 font-bold">Cloud API Keys Configured</span>
                  ) : (
                    <span className="text-amber-400 font-bold">Fallback / Ollama Standby</span>
                  )}
                </div>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>
            )}
          </div>

          {/* SIMULATE FAILURE OPTION */}
          <div className="pt-2 border-t border-slate-800/80">
            <label className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer hover:bg-slate-950 transition-colors">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-orange-500 focus:ring-orange-500 focus:ring-offset-0"
              />
              <div className="flex flex-col">
                <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
                  Simulate Flaw for Re-Plan Verification
                </span>
                <span className="text-[10px] text-slate-400">
                  Injects a syntax flaw into the first coding task to prove the Adaptive DAG auto-heals with a fix node.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* MODAL FOOTER */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-800 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleStart}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-cyan-500/25 transition-all"
          >
            <Play className="w-4 h-4 fill-current" />
            Confirm & Start Execution
          </button>
        </div>
      </div>
    </div>
  );
}
