"use client";

import React from "react";
import { Flag, CheckCircle2, Circle } from "lucide-react";

interface ProgressBarProps {
  currentIndex: number;
  totalQuestions: number;
  answeredCount: number;
  flaggedCount: number;
}

export function ProgressBar({
  currentIndex,
  totalQuestions,
  answeredCount,
  flaggedCount,
}: ProgressBarProps) {
  const percentage =
    totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  return (
    <div className="w-full bg-white/90 dark:bg-zinc-900/90 border-b border-zinc-200/80 dark:border-zinc-800/80 px-4 py-3 backdrop-blur-md">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Question Step info */}
          <div className="flex items-center gap-2 font-medium text-zinc-700 dark:text-zinc-300">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950/60 font-bold text-indigo-600 dark:text-indigo-400 text-xs">
              {currentIndex + 1}
            </span>
            <span>
              Câu {currentIndex + 1} / {totalQuestions}
            </span>
          </div>

          {/* Stats Pills */}
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 font-semibold text-emerald-700 dark:text-emerald-300 border border-emerald-200/50 dark:border-emerald-800/50">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>
                Đã làm: {answeredCount}/{totalQuestions}
              </span>
            </div>

            {flaggedCount > 0 && (
              <div className="flex items-center gap-1.5 rounded-full bg-amber-50 dark:bg-amber-950/40 px-2.5 py-1 font-semibold text-amber-700 dark:text-amber-300 border border-amber-200/50 dark:border-amber-800/50">
                <Flag className="h-3.5 w-3.5 fill-current" />
                <span>Gắn cờ: {flaggedCount}</span>
              </div>
            )}

            {/* Unanswered count */}
            <div className="hidden sm:flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
              <Circle className="h-3 w-3 text-zinc-400" />
              <span>Còn lại: {totalQuestions - answeredCount} câu</span>
            </div>

            <span className="font-bold text-indigo-600 dark:text-indigo-400 min-w-[36px] text-right">
              {percentage}%
            </span>
          </div>
        </div>

        {/* Linear progress track */}
        <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500 transition-all duration-500 ease-out"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}
