import React, { useState, useEffect, useRef } from "react";
import { X, Sparkles, ShieldAlert, Gamepad2, Globe, ShieldCheck, Image as ImageIcon, Video, UploadCloud, Trash2, Loader2, Code2, ExternalLink } from "lucide-react";

export interface ReferenceMediaItem {
  name: string;
  filename: string;
  file_path: string;
  url: string;
  media_type: string;
  size_bytes?: number;
  extracted_logic?: any;
}

interface TaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    objective: string,
    costConstrained: boolean,
    simulateFailure: boolean,
    projectType: string,
    projectPath: string,
    referenceMedia: ReferenceMediaItem[],
    useSimulation: boolean
  ) => void;
  initialObjective?: string;
}

const WEB_TEMPLATES = [
  "Build a Playable HTML5 Canvas 2D puzzle game prototype with juice, particle FX, and Web Audio.",
  "Create a modern Next.js TypeScript responsive web application with interactive components.",
  "Construct an asynchronous Python FastAPI order processing service with validation and tests.",
  "Build a Go distributed task queue with worker pools and telemetry metrics.",
];

const UNITY_TEMPLATES = [
  "Implement a Block actor scoring system with ScriptableObject event channel.",
  "Create a GridManager script to spawn, position, and cache BlockActor GameObjects.",
  "Implement a player interaction raycaster and touch controller for BlockHome.",
  "Design state machine architecture for GameLoopController and human actor states.",
];

export function TaskModal({ isOpen, onClose, onSubmit, initialObjective }: TaskModalProps) {
  const [projectType, setProjectType] = useState<string>("unity");
  const [projectPath, setProjectPath] = useState<string>("d:\\Unity\\Project\\Category Search");
  const [objective, setObjective] = useState<string>(initialObjective || UNITY_TEMPLATES[0]);
  const [costConstrained, setCostConstrained] = useState<boolean>(false);
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [useSimulation, setUseSimulation] = useState<boolean>(true);
  const [referenceMedia, setReferenceMedia] = useState<ReferenceMediaItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedPath = localStorage.getItem("last_project_path");
      if (savedPath) {
        setProjectPath(savedPath);
      }
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      if (initialObjective) {
        setObjective(initialObjective);
      } else {
        setObjective(projectType === "unity" ? UNITY_TEMPLATES[0] : WEB_TEMPLATES[0]);
      }
    }
  }, [isOpen, initialObjective, projectType]);

  if (!isOpen) return null;

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("http://localhost:8000/api/upload-reference", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          throw new Error(`Upload failed for ${file.name}`);
        }

        const data: ReferenceMediaItem = await res.json();
        setReferenceMedia((prev) => [...prev, data]);
      }
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload reference file.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removeReference = (index: number) => {
    setReferenceMedia((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim()) return;
    if (typeof window !== "undefined" && projectPath.trim()) {
      localStorage.setItem("last_project_path", projectPath.trim());
    }
    onSubmit(
      objective.trim(),
      costConstrained,
      simulateFailure,
      projectType,
      projectPath.trim(),
      referenceMedia,
      useSimulation
    );
    onClose();
  };

  const activeTemplates = projectType === "unity" ? UNITY_TEMPLATES : WEB_TEMPLATES;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-slate-950/80 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            <h2 className="font-semibold text-slate-100 text-base">
              New Multi-Agent Software Team Objective
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4 max-h-[85vh] overflow-y-auto">
          {/* Project Type Switcher */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Target Project Domain
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setProjectType("unity");
                  setObjective(UNITY_TEMPLATES[0]);
                }}
                className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all text-left ${
                  projectType === "unity"
                    ? "bg-purple-950/50 border-purple-500/60 text-purple-200 shadow-md shadow-purple-950/50"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <Gamepad2 className="w-5 h-5 text-purple-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold text-slate-100">Unity Game Project</div>
                  <div className="text-[10px] text-slate-400">C# Gameplay, Prefabs, Unity MCP</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  setProjectType("generic");
                  setObjective(WEB_TEMPLATES[0]);
                }}
                className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all text-left ${
                  projectType === "generic"
                    ? "bg-cyan-950/50 border-cyan-500/60 text-cyan-200 shadow-md shadow-cyan-950/50"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <Globe className="w-5 h-5 text-cyan-400 shrink-0" />
                <div>
                  <div className="text-xs font-bold text-slate-100">Web, Game & Software Project</div>
                  <div className="text-[10px] text-slate-400">HTML5 Canvas, Next.js, Python, Go, Rust</div>
                </div>
              </button>
            </div>
          </div>

          {/* Project Workspace Directory Input (For both Unity and Web/Software) */}
          <div className={`p-3 rounded-xl border flex flex-col gap-2 ${
            projectType === "unity"
              ? "bg-purple-950/20 border-purple-500/30"
              : "bg-cyan-950/20 border-cyan-500/30"
          }`}>
            <label className={`text-[11px] font-semibold uppercase tracking-wider ${
              projectType === "unity" ? "text-purple-300" : "text-cyan-300"
            }`}>
              {projectType === "unity"
                ? "Unity Project Workspace Directory"
                : "Project Destination Directory (Optional)"}
            </label>
            <input
              type="text"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder={
                projectType === "unity"
                  ? "e.g. D:\\Unity\\Project\\ls004-block-home"
                  : "e.g. D:\\Projects\\MyGameApp (or leave empty for Sandbox)"
              }
              className={`w-full bg-slate-950 border rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none ${
                projectType === "unity"
                  ? "border-slate-800 focus:border-purple-400"
                  : "border-slate-800 focus:border-cyan-400"
              }`}
            />

            {/* Quick Pick Recent Projects */}
            {projectType === "unity" && (
              <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                <span className="text-[10px] text-slate-400">Quick select:</span>
                {[
                  "D:\\Unity\\Project\\Category Search",
                  "D:\\Unity\\Project\\ls004-block-home",
                ].map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setProjectPath(p)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-all ${
                      projectPath === p
                        ? "bg-purple-950 text-purple-200 border-purple-500 font-bold"
                        : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700"
                    }`}
                  >
                    {p.split("\\").pop()}
                  </button>
                ))}
              </div>
            )}
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>
                {projectType === "unity"
                  ? "Phase 0 Ingestion: Auto-reads project rules, CLAUDE.md, .agents, and enforces English comments."
                  : "Code, assets, and project files will be created and written directly to this directory."}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Engineering Goal / Task Description
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
              {activeTemplates.map((tmpl, idx) => (
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

          {/* Visual & Playable References Section */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-cyan-400" />
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Visual, Video & HTML Demo References
                </label>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                {referenceMedia.length} attached
              </span>
            </div>

            <p className="text-[11px] text-slate-400 leading-normal">
              Upload UI mockups, gameplay videos, or an HTML playable game demo (<span className="text-amber-300 font-mono">.html</span>). Vision models analyze layout/art, while engineering agents parse core JS game loops and mechanics into Unity C#.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/mp4,video/webm,video/quicktime,.html,.htm"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                handleFileUpload(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-slate-800 hover:border-cyan-500/60 bg-slate-900/40 hover:bg-cyan-950/20 rounded-xl p-3.5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all"
            >
              {isUploading ? (
                <div className="flex items-center gap-2 text-xs text-cyan-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Uploading reference or demo file...</span>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2 text-slate-400">
                    <UploadCloud className="w-5 h-5 text-cyan-400" />
                    <span className="text-xs font-medium text-slate-300">
                      Click or drag images, videos & HTML game demos here
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                    <span>PNG, JPG, WEBP, MP4, WEBM, HTML DEMO</span>
                  </div>
                </>
              )}
            </div>

            {uploadError && (
              <div className="text-[11px] text-red-400 bg-red-950/40 border border-red-900/60 p-2 rounded-lg">
                {uploadError}
              </div>
            )}

            {referenceMedia.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                {referenceMedia.map((media, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs"
                  >
                    {media.media_type === "image" ? (
                      <img
                        src={media.url.startsWith("http") ? media.url : `http://localhost:8000${media.url}`}
                        alt={media.name}
                        className="w-12 h-12 object-cover rounded-md border border-slate-700 shrink-0"
                      />
                    ) : media.media_type === "video" ? (
                      <div className="w-12 h-12 bg-purple-950/80 border border-purple-500/40 rounded-md flex flex-col items-center justify-center text-purple-300 shrink-0">
                        <Video className="w-5 h-5" />
                        <span className="text-[8px] font-bold mt-0.5">VIDEO</span>
                      </div>
                    ) : (
                      <div className="w-12 h-12 bg-amber-950/80 border border-amber-500/40 rounded-md flex flex-col items-center justify-center text-amber-300 shrink-0">
                        <Code2 className="w-5 h-5" />
                        <span className="text-[8px] font-bold mt-0.5">HTML DEMO</span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-slate-200 truncate text-[11px]">
                        {media.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono uppercase">
                        {media.media_type}
                        {media.size_bytes ? ` • ${Math.round(media.size_bytes / 1024)} KB` : ""}
                      </div>
                      {media.extracted_logic?.functions && media.extracted_logic.functions.length > 0 && (
                        <div className="text-[9px] text-amber-300/80 truncate font-mono">
                          fn: {media.extracted_logic.functions.slice(0, 3).join(", ")}
                          {media.extracted_logic.functions.length > 3 ? "..." : ""}
                        </div>
                      )}
                    </div>
                    {media.media_type === "html" && (
                      <a
                        href={media.url.startsWith("http") ? media.url : `http://localhost:8000${media.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1 text-slate-400 hover:text-cyan-300 rounded transition-colors"
                        title="Play / Inspect HTML Demo"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => removeReference(idx)}
                      className="p-1 text-slate-500 hover:text-red-400 rounded transition-colors"
                      title="Remove"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Execution Engine Mode: Fast Simulation vs Real AI Multi-Agent */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Execution Engine Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setUseSimulation(true)}
                className={`p-2.5 rounded-xl border flex flex-col gap-1 transition-all text-left ${
                  useSimulation
                    ? "bg-cyan-950/60 border-cyan-500/80 text-cyan-200 shadow-md shadow-cyan-950"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <div className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  ⚡ Fast Simulation (~3-5s)
                </div>
                <div className="text-[10px] text-slate-400 leading-snug">
                  Zero token cost. Rapidly tests DAG flow, websocket, UI state, and auto-replanning.
                </div>
              </button>

              <button
                type="button"
                onClick={() => setUseSimulation(false)}
                className={`p-2.5 rounded-xl border flex flex-col gap-1 transition-all text-left ${
                  !useSimulation
                    ? "bg-purple-950/60 border-purple-500/80 text-purple-200 shadow-md shadow-purple-950"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <div className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                  🤖 Real Multi-Agent (~2-10 min)
                </div>
                <div className="text-[10px] text-slate-400 leading-snug">
                  Invokes LLM APIs / Local CLI (Gemini, Claude, GPT-4o, Ollama) to generate real code.
                </div>
              </button>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-3 flex flex-col gap-2.5">
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
                  Directs Tier 2 Router to prioritize lightweight/fast models.
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
                  Injects an intentional defect to demonstrate how the Verifier triggers Adaptive Replanning.
                </p>
              </div>
            </label>
          </div>

          <div className="mt-2 flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 via-blue-600 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white shadow-lg shadow-cyan-500/25 flex items-center gap-2 transition-all font-mono"
            >
              <Sparkles className="w-4 h-4" />
              Generate & Ingest Context
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
