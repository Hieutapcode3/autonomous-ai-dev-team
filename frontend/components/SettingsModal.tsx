"use client";

import React, { useState, useEffect } from "react";
import { X, Settings, Key, Check, Info, GitBranch, ToggleLeft, ToggleRight } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiUrl: string;
}

export function SettingsModal({ isOpen, onClose, apiUrl }: SettingsModalProps) {
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [simulationMode, setSimulationMode] = useState(true);
  const [autoPushGithub, setAutoPushGithub] = useState(false);
  const [hasGithubToken, setHasGithubToken] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetch(`${apiUrl}/api/settings`)
        .then((res) => res.json())
        .then((data) => {
          setSimulationMode(data.simulation_mode ?? true);
          setAutoPushGithub(data.auto_push_github ?? false);
          setHasGithubToken(data.has_github_token ?? false);
        })
        .catch(() => {});
    }
  }, [isOpen, apiUrl]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch(`${apiUrl}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          anthropic_api_key: anthropicKey || undefined,
          openai_api_key: openaiKey || undefined,
          google_api_key: googleKey || undefined,
          openrouter_api_key: openrouterKey || undefined,
          github_token: githubToken || undefined,
          simulation_mode: simulationMode,
          auto_push_github: autoPushGithub,
        }),
      });
      setSaved(true);
      setTimeout(() => {
        setSaved(false);
        onClose();
      }, 1200);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-slate-950/80 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyan-400" />
            <h2 className="font-semibold text-slate-100 text-base">
              System &amp; Model Provider Settings
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 flex flex-col gap-4 max-h-[80vh] overflow-y-auto">
          {/* Simulation mode info */}
          <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/30 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 leading-relaxed">
              <strong>Offline Simulation Mode</strong> allows the entire Two-Tier Dynamic Router, Verifier Quality Gate, and Adaptive Replanning to run instantly with zero API keys required.
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer p-2 rounded-xl bg-slate-950/50 border border-slate-800">
            <input
              type="checkbox"
              checked={simulationMode}
              onChange={(e) => setSimulationMode(e.target.checked)}
              className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-cyan-500"
            />
            <div className="text-xs">
              <span className="text-slate-200 font-semibold">Enable Zero-Cost Simulator Mode</span>
              <p className="text-slate-400 text-[11px]">
                Runs synthetic high-fidelity LLM outputs and deterministic code generation.
              </p>
            </div>
          </label>

          {/* LLM API Keys */}
          <div className="flex flex-col gap-3 pt-2 border-t border-slate-800">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">LLM Provider Keys</p>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-purple-400" /> Anthropic (Claude 3.5 Sonnet / Opus)
              </label>
              <input
                type="password"
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-amber-400" /> OpenAI (GPT-4o / GPT-4o-mini)
              </label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-teal-400" /> Google Gemini (Gemini 1.5 Pro)
              </label>
              <input
                type="password"
                value={googleKey}
                onChange={(e) => setGoogleKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          {/* GitHub Section */}
          <div className="flex flex-col gap-3 pt-2 border-t border-slate-800">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-slate-300" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">GitHub Auto-Push</p>
              {hasGithubToken && (
                <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 font-semibold flex items-center gap-1">
                  <Check className="w-3 h-3" /> Token saved
                </span>
              )}
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-400 leading-relaxed">
              When enabled, after every successful workflow run the agent will <strong className="text-slate-200">automatically create a private GitHub repo</strong> and push all generated files with a single commit.
              <br />
              <a
                href="https://github.com/settings/tokens/new?scopes=repo&description=AI+Software+Team"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:text-cyan-300 underline mt-1 inline-block"
              >
                → Generate a Personal Access Token (repo scope)
              </a>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-slate-300" /> GitHub Personal Access Token
              </label>
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder="ghp_..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <label className="flex items-center gap-3 cursor-pointer p-2.5 rounded-xl bg-slate-950/50 border border-slate-800 hover:border-emerald-500/40 transition-colors">
              <div className="relative" onClick={() => setAutoPushGithub((v) => !v)}>
                {autoPushGithub ? (
                  <ToggleRight className="w-8 h-8 text-emerald-400" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-slate-600" />
                )}
              </div>
              <div className="text-xs">
                <span className={`font-semibold ${autoPushGithub ? "text-emerald-300" : "text-slate-400"}`}>
                  {autoPushGithub ? "Auto-Push Enabled" : "Auto-Push Disabled"}
                </span>
                <p className="text-slate-500 text-[11px]">
                  Creates a new repo and commits all generated files when the workflow completes.
                </p>
              </div>
            </label>
          </div>

          <div className="mt-3 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/25 flex items-center gap-2 transition-all"
            >
              {saved ? (
                <>
                  <Check className="w-4 h-4 text-emerald-300" /> Saved!
                </>
              ) : (
                "Save Configuration"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
