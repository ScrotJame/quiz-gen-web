"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  X,
  Send,
  Loader2,
} from "lucide-react";

interface SubmitConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isSubmitting: boolean;
  totalQuestions: number;
  answeredCount: number;
  flaggedCount: number;
}

export function SubmitConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  totalQuestions,
  answeredCount,
  flaggedCount,
}: SubmitConfirmModalProps) {
  if (!isOpen) return null;

  const unansweredCount = totalQuestions - answeredCount;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-zinc-200 bg-white p-6 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900">
        {/* Close button */}
        <button
          onClick={onClose}
          disabled={isSubmitting}
          type="button"
          className="absolute top-4 right-4 rounded-full p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3">
          <div
            className={`flex h-11 w-11 items-center justify-center rounded-2xl ${
              unansweredCount > 0
                ? "bg-amber-100 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400"
                : "bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400"
            }`}
          >
            {unansweredCount > 0 ? (
              <AlertTriangle className="h-6 w-6" />
            ) : (
              <CheckCircle2 className="h-6 w-6" />
            )}
          </div>
          <div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-white">
              Xác nhận nộp bài thi
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Kiểm tra tình trạng làm bài trước khi nộp
            </p>
          </div>
        </div>

        {/* Warning if unanswered */}
        {unansweredCount > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300">
            <span className="font-bold">Lưu ý:</span> Bạn vẫn còn{" "}
            <span className="font-extrabold">{unansweredCount}</span> câu hỏi
            chưa chọn đáp án. Các câu chưa làm sẽ không được tính điểm.
          </div>
        )}

        {/* Summary Statistics */}
        <div className="mt-4 grid grid-cols-3 gap-2 rounded-2xl bg-zinc-50 p-3.5 text-center text-xs dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800">
          <div>
            <span className="block text-[11px] text-zinc-500 dark:text-zinc-400">
              Đã làm
            </span>
            <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">
              {answeredCount}
            </span>
          </div>
          <div>
            <span className="block text-[11px] text-zinc-500 dark:text-zinc-400">
              Chưa làm
            </span>
            <span
              className={`text-base font-bold ${
                unansweredCount > 0
                  ? "text-rose-600 dark:text-rose-400"
                  : "text-zinc-700 dark:text-zinc-300"
              }`}
            >
              {unansweredCount}
            </span>
          </div>
          <div>
            <span className="block text-[11px] text-zinc-500 dark:text-zinc-400">
              Gắn cờ
            </span>
            <span className="text-base font-bold text-amber-600 dark:text-amber-400">
              {flaggedCount}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 rounded-xl border border-zinc-200 py-2.5 text-xs sm:text-sm font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-colors"
          >
            Tiếp tục làm bài
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-md shadow-indigo-600/30 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-60 transition-all active:scale-95"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang chấm...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Nộp bài ngay</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
