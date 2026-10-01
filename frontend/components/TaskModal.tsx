"use client";

import React, { useState, useEffect } from "react";
import { X, Sparkles, Sliders, ShieldAlert, Check } from "lucide-react";

interface TaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (objective: string, costConstrained: boolean, simulateFailure: boolean) => void;
  initialObjective?: string;
}

const TEMPLATES = [
  "Build a Python order processing engine with tax calculation, unit tests, and validation.",
  "Implement a user authentication and JWT session token verification pipeline.",
  "Construct an asynchronous event-driven task queue with retry logic and telemetry metrics.",
  "Fix memory leak and boundary condition errors in the matrix transformation module.",
];

export function TaskModal({ isOpen, onClose, onSubmit, initialObjective }: TaskModalProps) {
  const [objective, setObjective] = useState<string>(initialObjective || TEMPLATES[0]);
  const [costConstrained, setCostConstrained] = useState<boolean>(false);
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);

  // Sync textarea when modal opens with a different objective
  useEffect(() => {
    if (isOpen) {
      setObjective(initialObjective || TEMPLATES[0]);
    }
  }, [isOpen, initialObjective]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim()) return;
    onSubmit(objective.trim(), costConstrained, simulateFailure);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-slate-950/80 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            <h2 className="font-semibold text-slate-100 text-base">
              New Software Team Objective
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Software Engineering Goal / User Request
            </label>
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              rows={3}
              placeholder="Describe what you want the multi-agent software team to build, refactor, or test..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors placeholder:text-slate-600"
              required
            />
          </div>

          <div>
            <span className="block text-xs font-medium text-slate-400 mb-2">
              Or pick an architecture template:
            </span>
            <div className="flex flex-col gap-1.5">
              {TEMPLATES.map((tmpl, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => setObjective(tmpl)}
                  className="text-left text-xs p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 text-slate-300 hover:border-cyan-500/50 hover:bg-cyan-950/20 transition-all truncate"
                >
                  • {tmpl}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4 flex flex-col gap-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={costConstrained}
                onChange={(e) => setCostConstrained(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-cyan-500"
              />
              <div className="text-xs">
                <span className="text-slate-200 font-medium">Cost-Constrained Routing Mode</span>
                <p className="text-slate-400 text-[11px]">
                  Directs Tier 2 Router to prioritize lightweight/fast models (GPT-4o-mini & DeepSeek Coder).
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-orange-500 focus:ring-orange-500"
              />
              <div className="text-xs">
                <span className="text-orange-300 font-medium flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Simulate Quality Gate Failure (Demo Adaptive Re-planning)
                </span>
                <p className="text-slate-400 text-[11px]">
                  Injects an intentional syntax defect in Step 2 to demonstrate how the Verifier catches it and triggers the Replanner to dynamically expand the DAG with a fix node.
                </p>
              </div>
            </label>
          </div>

          <div className="mt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/25 flex items-center gap-2 transition-all"
            >
              <Sparkles className="w-4 h-4" />
              Generate & Plan DAG
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
