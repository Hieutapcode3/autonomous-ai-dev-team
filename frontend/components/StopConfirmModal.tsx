"use client";

import React, { useState } from "react";
import { X, Square, AlertOctagon, KeyRound, Eye, EyeOff, Loader2 } from "lucide-react";

interface StopConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmStop: (taskKey?: string) => Promise<{ success: boolean; error?: string } | boolean>;
  hasTaskKey: boolean;
  sessionId: string;
}

export function StopConfirmModal({
  isOpen,
  onClose,
  onConfirmStop,
  hasTaskKey,
  sessionId,
}: StopConfirmModalProps) {
  const [taskKeyInput, setTaskKeyInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setTaskKeyInput("");
      setErrorMessage(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleStop = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (hasTaskKey && !taskKeyInput.trim()) {
      setErrorMessage("Vui lòng nhập Task Key bảo vệ để dừng phiên chạy.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await onConfirmStop(taskKeyInput.trim() || undefined);
      const isSuccess = typeof res === "boolean" ? res : res.success;
      if (isSuccess) {
        onClose();
      } else {
        const errorDetail =
          typeof res === "object" && res.error
            ? res.error
            : "Không thể dừng quy trình. Vui lòng thử lại.";
        setErrorMessage(errorDetail);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Lỗi khi gửi yêu cầu dừng workflow.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-slate-900 border border-rose-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* HEADER */}
        <div className="p-4 border-b border-rose-500/20 bg-rose-950/40 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-rose-900/60 border border-rose-500/50 flex items-center justify-center text-rose-300 shadow-sm shadow-rose-950">
              <Square className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Stop Workflow Execution
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/30">
                  HALT
                </span>
              </h2>
              <p className="text-[11px] text-slate-400 font-mono">
                Session #{sessionId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* BODY */}
        <form onSubmit={handleStop} className="p-5 space-y-4">
          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300">
            <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-semibold text-slate-200">Xác nhận dừng workflow</div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Hệ thống sẽ ngay lập tức hủy các tác vụ AI và Sandbox đang chạy. Tiến độ và các file đã hoàn thành trước đó sẽ được lưu lại.
              </p>
            </div>
          </div>

          {hasTaskKey ? (
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                Nhập Task Key bảo vệ:
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={taskKeyInput}
                  onChange={(e) => setTaskKeyInput(e.target.value)}
                  placeholder="Nhập mã Task Key đã thiết lập lúc Run..."
                  autoFocus
                  className="w-full pl-3.5 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-rose-500/80 focus:ring-1 focus:ring-rose-500/50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[10px] text-slate-500">
                Phiên chạy này đã được khóa bằng mã bảo vệ. Phải nhập đúng Task Key mới có thể Stop.
              </p>
            </div>
          ) : (
            <div className="text-xs text-slate-400 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
              Phiên chạy này không thiết lập Task Key bảo vệ. Bạn có thể bấm xác nhận để dừng ngay lập tức.
            </div>
          )}

          {errorMessage && (
            <div className="p-2.5 rounded-xl bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-medium animate-in fade-in duration-200">
              {errorMessage}
            </div>
          )}

          {/* FOOTER BUTTONS */}
          <div className="pt-3 border-t border-slate-800/80 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-slate-800 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:bg-rose-900 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-rose-600/30 transition-all"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Đang dừng...
                </>
              ) : (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  Xác nhận Dừng Workflow
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
