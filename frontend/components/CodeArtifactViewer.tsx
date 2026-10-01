"use client";

import React, { useState, useEffect } from "react";
import { FileCode, FileText, CheckCircle2, Copy, Check, GitCommit } from "lucide-react";

interface ArtifactItem {
  file: string;
  action: string;
  content: string;
  diff: string;
  size_bytes: number;
}

interface CodeArtifactViewerProps {
  apiUrl: string;
}

export function CodeArtifactViewer({ apiUrl }: CodeArtifactViewerProps) {
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"code" | "diff">("diff");

  const fetchArtifacts = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/workspace/files`);
      if (res.ok) {
        const data = await res.json();
        setArtifacts(data.artifacts || []);
        if (data.artifacts && data.artifacts.length > 0 && !selectedFile) {
          setSelectedFile(data.artifacts[data.artifacts.length - 1].file);
        }
      }
    } catch {
      // Ignored if server not yet started
    }
  };

  useEffect(() => {
    fetchArtifacts();
    const interval = setInterval(fetchArtifacts, 3000);
    return () => clearInterval(interval);
  }, [apiUrl, selectedFile]);

  const activeArtifact = artifacts.find((a) => a.file === selectedFile) || artifacts[artifacts.length - 1];

  const handleCopy = () => {
    if (activeArtifact) {
      const textToCopy = viewMode === "diff" ? activeArtifact.diff || activeArtifact.content : activeArtifact.content;
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-950/90 border border-slate-800/80 rounded-2xl flex flex-col h-full shadow-2xl overflow-hidden font-mono">
      <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-300">
            Workspace Sandbox & Unified Diff Viewer
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[10px]">
            <button
              onClick={() => setViewMode("diff")}
              className={`px-2.5 py-0.5 rounded-md transition-all ${
                viewMode === "diff"
                  ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Diff View
            </button>
            <button
              onClick={() => setViewMode("code")}
              className={`px-2.5 py-0.5 rounded-md transition-all ${
                viewMode === "code"
                  ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Raw File
            </button>
          </div>

          <button
            onClick={handleCopy}
            title="Copy Content"
            className="p-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-cyan-400 hover:bg-slate-900 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* File List */}
        <div className="w-56 border-r border-slate-800/80 bg-slate-900/40 overflow-y-auto p-2 space-y-1">
          <div className="text-[10px] uppercase font-bold text-slate-500 px-2 py-1">
            Touched Files ({artifacts.length})
          </div>
          {artifacts.length === 0 ? (
            <div className="text-slate-600 text-xs px-2 py-4 italic">No files created yet</div>
          ) : (
            artifacts.map((art, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedFile(art.file)}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between transition-colors ${
                  activeArtifact?.file === art.file
                    ? "bg-cyan-950/70 border border-cyan-500/40 text-cyan-300 font-medium"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-1.5 truncate">
                  <FileText className="w-3.5 h-3.5 shrink-0 text-cyan-400" />
                  <span className="truncate">{art.file}</span>
                </div>
                <span className="text-[9px] uppercase font-mono px-1 rounded bg-slate-950 text-slate-400">
                  {art.action}
                </span>
              </button>
            ))
          )}
        </div>

        {/* File Content / Diff Display */}
        <div className="flex-1 overflow-y-auto p-4 bg-slate-950/60 text-xs">
          {activeArtifact ? (
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <GitCommit className="w-4 h-4 text-cyan-400" />
                  <span className="text-slate-200 font-mono font-semibold">
                    {activeArtifact.file}
                  </span>
                </div>
                <span className="text-slate-500 font-mono text-[11px]">
                  {activeArtifact.size_bytes} bytes
                </span>
              </div>

              {viewMode === "diff" && activeArtifact.diff ? (
                <pre className="font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre">
                  {activeArtifact.diff.split("\n").map((line, i) => {
                    const isAdd = line.startsWith("+");
                    const isDel = line.startsWith("-");
                    return (
                      <div
                        key={i}
                        className={`px-1.5 py-0.5 rounded ${
                          isAdd
                            ? "bg-emerald-950/60 text-emerald-300"
                            : isDel
                            ? "bg-red-950/60 text-red-300"
                            : "text-slate-400"
                        }`}
                      >
                        {line}
                      </div>
                    );
                  })}
                </pre>
              ) : (
                <pre className="font-mono text-xs text-slate-200 leading-relaxed overflow-x-auto whitespace-pre bg-slate-900/60 p-3 rounded-xl border border-slate-800/70">
                  {activeArtifact.content}
                </pre>
              )}
            </div>
          ) : (
            <div className="text-slate-600 text-center py-16 italic font-sans text-xs">
              Generated code files and unified diffs will appear here when tasks run.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
