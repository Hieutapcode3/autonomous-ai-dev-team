"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Settings,
  Key,
  Check,
  Info,
  GitBranch,
  ToggleLeft,
  ToggleRight,
  Terminal,
  Cpu,
  CheckCircle2,
  Server,
  Zap,
  Sparkles,
  AlertCircle,
} from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiUrl: string;
}

interface LocalStatus {
  ollama: {
    online: boolean;
    base_url: string;
    models: string[];
  };
  claude_cli: {
    found: boolean;
    path: string | null;
  };
  gemini_cli: {
    found: boolean;
    path: string | null;
    authenticated?: boolean;
  };
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

  // Local AI & CLI runner state
  const [useLocalProvider, setUseLocalProvider] = useState(false);
  const [localProviderType, setLocalProviderType] = useState<"ollama" | "claude-cli" | "gemini-cli">("ollama");
  const [ollamaModel, setOllamaModel] = useState("qwen2.5-coder:7b");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://localhost:11434");
  const [geminiCliCommand, setGeminiCliCommand] = useState("gemini");
  const [localStatus, setLocalStatus] = useState<LocalStatus | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetch(`${apiUrl}/api/settings`)
        .then((res) => res.json())
        .then((data) => {
          setSimulationMode(data.simulation_mode ?? true);
          setAutoPushGithub(data.auto_push_github ?? false);
          setHasGithubToken(data.has_github_token ?? false);
          setUseLocalProvider(data.use_local_provider ?? false);
          setLocalProviderType(data.local_provider_type ?? "ollama");
          if (data.ollama_model) setOllamaModel(data.ollama_model);
          if (data.ollama_base_url) setOllamaBaseUrl(data.ollama_base_url);
          if (data.gemini_cli_command) setGeminiCliCommand(data.gemini_cli_command);
        })
        .catch(() => {});

      fetch(`${apiUrl}/api/local-status`)
        .then((res) => res.json())
        .then((data) => {
          setLocalStatus(data);
          if (data?.ollama?.models?.length > 0 && !data.ollama.models.includes(ollamaModel)) {
            setOllamaModel(data.ollama.models[0]);
          }
          if (data?.gemini_cli?.found && (!geminiCliCommand || geminiCliCommand === "gemini")) {
            setGeminiCliCommand(data.gemini_cli.path || "gemini-cli");
          }
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
          use_local_provider: useLocalProvider,
          local_provider_type: localProviderType,
          ollama_model: ollamaModel,
          ollama_base_url: ollamaBaseUrl,
          gemini_cli_command: geminiCliCommand,
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

          {/* Local AI & Direct Terminal CLI Section */}
          <div className="flex flex-col gap-3 pt-3 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Local AI &amp; Direct CLI Runner
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 font-semibold">
                No API Key Required
              </span>
            </div>

            <label className="flex items-center gap-3 cursor-pointer p-3 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-emerald-500/40 transition-colors">
              <div className="relative" onClick={() => setUseLocalProvider((v) => !v)}>
                {useLocalProvider ? (
                  <ToggleRight className="w-8 h-8 text-emerald-400" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-slate-600" />
                )}
              </div>
              <div className="text-xs">
                <span className={`font-semibold ${useLocalProvider ? "text-emerald-300" : "text-slate-400"}`}>
                  {useLocalProvider ? "Run via Local AI / Terminal CLI (Active)" : "Run via Local AI / Terminal CLI (Disabled)"}
                </span>
                <p className="text-slate-500 text-[11px]">
                  Bypasses cloud API tokens and executes directly through your machine's Ollama, Claude, or Gemini CLI.
                </p>
              </div>
            </label>

            {useLocalProvider && (
              <div className="flex flex-col gap-3 p-3.5 bg-slate-950/90 border border-slate-800/90 rounded-xl animate-in fade-in duration-150">
                {/* Provider Type Selection */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  {/* Ollama option */}
                  <button
                    type="button"
                    onClick={() => setLocalProviderType("ollama")}
                    className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                      localProviderType === "ollama"
                        ? "bg-teal-950/40 border-teal-500/60 text-slate-100 shadow-sm"
                        : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold flex items-center gap-1.5 text-teal-300">
                        <Cpu className="w-3.5 h-3.5" /> Ollama
                      </span>
                      {localStatus?.ollama?.online && (
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="Ollama Online" />
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400">Offline &amp; Free</span>
                  </button>

                  {/* Claude CLI option */}
                  <button
                    type="button"
                    onClick={() => setLocalProviderType("claude-cli")}
                    className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                      localProviderType === "claude-cli"
                        ? "bg-amber-950/40 border-amber-500/60 text-slate-100 shadow-sm"
                        : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold flex items-center gap-1.5 text-amber-300">
                        <Terminal className="w-3.5 h-3.5" /> Claude CLI
                      </span>
                      {localStatus?.claude_cli?.found && (
                        <span title="Claude CLI Detected">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400">Claude Code tool</span>
                  </button>

                  {/* Gemini CLI option */}
                  <button
                    type="button"
                    onClick={() => setLocalProviderType("gemini-cli")}
                    className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition-all ${
                      localProviderType === "gemini-cli"
                        ? "bg-sky-950/40 border-sky-500/60 text-slate-100 shadow-sm"
                        : "bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold flex items-center gap-1.5 text-sky-300">
                        <Sparkles className="w-3.5 h-3.5" /> Gemini CLI
                      </span>
                      {localStatus?.gemini_cli?.found && (
                        localStatus?.gemini_cli?.authenticated ? (
                          <span title="Gemini CLI Ready">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          </span>
                        ) : (
                          <span title="Gemini CLI detected but requires API Key" className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40">
                            Needs Key
                          </span>
                        )
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400">Google Gemini CLI</span>
                  </button>
                </div>

                {/* Ollama options detail */}
                {localProviderType === "ollama" && (
                  <div className="flex flex-col gap-2 pt-1">
                    <div className="flex items-center justify-between text-xs">
                      <label className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                        <Server className="w-3 h-3 text-teal-400" /> Active Ollama Model
                      </label>
                      <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                        {localStatus?.ollama?.online ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" /> {localStatus.ollama.models.length} model(s) available
                          </>
                        ) : (
                          <span className="text-amber-400">Ollama service not detected</span>
                        )}
                      </span>
                    </div>

                    {localStatus?.ollama?.models && localStatus.ollama.models.length > 0 ? (
                      <select
                        value={ollamaModel}
                        onChange={(e) => setOllamaModel(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
                      >
                        {localStatus.ollama.models.map((m) => (
                          <option key={m} value={m}>
                            {m} {m.includes("qwen") ? "(Recommended for Coding)" : ""}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={ollamaModel}
                        onChange={(e) => setOllamaModel(e.target.value)}
                        placeholder="e.g. qwen2.5-coder:7b"
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
                      />
                    )}

                    <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
                      <span>Server URL: {ollamaBaseUrl}</span>
                      <span className="text-teal-400 font-semibold">Zero API Cost</span>
                    </div>
                  </div>
                )}

                {/* Claude CLI detail */}
                {localProviderType === "claude-cli" && (
                  <div className="flex flex-col gap-2 pt-1">
                    <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs text-slate-300">
                      <div className="font-semibold text-amber-300 flex items-center gap-1.5 mb-1">
                        <Zap className="w-3.5 h-3.5" /> Direct Subprocess Terminal Runner
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        Spawns <code className="text-amber-200 font-mono">claude --print</code> directly from your machine. Real-time stdout will stream into the Terminal below.
                      </p>
                      <div className="mt-2 text-[10px] text-slate-400">
                        {localStatus?.claude_cli?.found ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <Check className="w-3 h-3" /> Detected at: {localStatus.claude_cli.path}
                          </span>
                        ) : (
                          <span className="text-amber-400">
                            Run <code className="font-mono">claude auth login</code> in terminal before starting.
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Gemini CLI detail */}
                {localProviderType === "gemini-cli" && (
                  <div className="flex flex-col gap-2.5 pt-1">
                    <div className="p-2.5 rounded-lg bg-sky-950/20 border border-sky-500/30 text-xs text-slate-300">
                      <div className="font-semibold text-sky-300 flex items-center gap-1.5 mb-1">
                        <Sparkles className="w-3.5 h-3.5" /> Google Gemini Terminal CLI Runner
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        Spawns local terminal command <code className="text-sky-200 font-mono">{geminiCliCommand}</code> and streams real-time output into the Terminal below.
                      </p>
                      <div className="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                        {localStatus?.gemini_cli?.found ? (
                          localStatus?.gemini_cli?.authenticated ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <Check className="w-3 h-3" /> Ready &amp; Authenticated: {localStatus.gemini_cli.path}
                            </span>
                          ) : (
                            <span className="text-amber-400 flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" /> Detected, but requires API Key in field below.
                            </span>
                          )
                        ) : (
                          <span className="text-amber-400">
                            Install CLI via: <code className="font-mono bg-slate-900 px-1 py-0.5 rounded text-amber-200">pip install gemini-cli</code>
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1 flex items-center gap-1">
                        <Terminal className="w-3 h-3 text-sky-400" /> CLI Executable / Command
                      </label>
                      <input
                        type="text"
                        value={geminiCliCommand}
                        onChange={(e) => setGeminiCliCommand(e.target.value)}
                        placeholder="gemini"
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

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
