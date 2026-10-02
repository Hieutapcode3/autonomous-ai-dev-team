import React, { useState, useEffect, useRef } from "react";
import { X, Sparkles, ShieldAlert, Gamepad2, Globe, ShieldCheck, Image as ImageIcon, Video, UploadCloud, Trash2, Loader2 } from "lucide-react";

export interface ReferenceMediaItem {
  name: string;
  filename: string;
  file_path: string;
  url: string;
  media_type: string;
  size_bytes?: number;
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
    referenceMedia: ReferenceMediaItem[]
  ) => void;
  initialObjective?: string;
}

const WEB_TEMPLATES = [
  "Build a Python order processing engine with tax calculation, unit tests, and validation.",
  "Implement a user authentication and JWT session token verification pipeline.",
  "Construct an asynchronous event-driven task queue with retry logic and telemetry metrics.",
  "Fix memory leak and boundary condition errors in the matrix transformation module.",
];

const UNITY_TEMPLATES = [
  "Implement a Block actor scoring system with ScriptableObject event channel.",
  "Create a GridManager script to spawn, position, and cache BlockActor GameObjects.",
  "Implement a player interaction raycaster and touch controller for BlockHome.",
  "Design state machine architecture for GameLoopController and human actor states.",
];

export function TaskModal({ isOpen, onClose, onSubmit, initialObjective }: TaskModalProps) {
  const [projectType, setProjectType] = useState<string>("unity");
  const [projectPath, setProjectPath] = useState<string>("d:\\Unity\\Project\\ls004-block-home");
  const [objective, setObjective] = useState<string>(initialObjective || UNITY_TEMPLATES[0]);
  const [costConstrained, setCostConstrained] = useState<boolean>(false);
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [referenceMedia, setReferenceMedia] = useState<ReferenceMediaItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
    onSubmit(
      objective.trim(),
      costConstrained,
      simulateFailure,
      projectType,
      projectType === "unity" ? projectPath.trim() : "",
      referenceMedia
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
                  <div className="text-xs font-bold text-slate-100">Python / Web Sandbox</div>
                  <div className="text-[10px] text-slate-400">Services, APIs, pytest harness</div>
                </div>
              </button>
            </div>
          </div>

          {/* Unity Project Path Input */}
          {projectType === "unity" && (
            <div className="bg-purple-950/20 border border-purple-500/30 rounded-xl p-3 flex flex-col gap-2">
              <label className="text-[11px] font-semibold text-purple-300 uppercase tracking-wider">
                Unity Project Workspace Directory
              </label>
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder="e.g. D:\Unity\Project\ls004-block-home"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-purple-400"
                required
              />
              <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Phase 0 Ingestion: Auto-reads project rules, CLAUDE.md, .agents, and enforces English comments.</span>
              </div>
            </div>
          )}

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

          {/* Visual & Art References Section */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-cyan-400" />
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Visual & Art References (Images / Videos)
                </label>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                {referenceMedia.length} attached
              </span>
            </div>

            <p className="text-[11px] text-slate-400 leading-normal">
              Upload UI mockups, art references, or gameplay clips. Vision-capable models will analyze layout anchors, composition, and visual hierarchy.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,video/mp4,video/webm,video/quicktime"
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
                  <span>Uploading reference media...</span>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2 text-slate-400">
                    <UploadCloud className="w-5 h-5 text-cyan-400" />
                    <span className="text-xs font-medium text-slate-300">
                      Click or drag images & videos here
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                    <span>PNG, JPG, WEBP, MP4, WEBM</span>
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
                    ) : (
                      <div className="w-12 h-12 bg-purple-950/80 border border-purple-500/40 rounded-md flex flex-col items-center justify-center text-purple-300 shrink-0">
                        <Video className="w-5 h-5" />
                        <span className="text-[8px] font-bold mt-0.5">VIDEO</span>
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
                    </div>
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
