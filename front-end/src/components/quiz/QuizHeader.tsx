"use client";

import React from "react";
import {
  Clock,
  Eye,
  EyeOff,
  Pause,
  Play,
  Check,
  Send,
  ArrowLeft,
} from "lucide-react";

interface QuizHeaderProps {
  title: string;
  category?: string;
  timeRemaining: number;
  isTimerVisible: boolean;
  onToggleTimerVisibility: () => void;
  isPaused: boolean;
  onTogglePause: () => void;
  autoSavedAt: Date | null;
  onSubmitClick: () => void;
  onExitClick: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function QuizHeader({
  title,
  category,
  timeRemaining,
  isTimerVisible,
  onToggleTimerVisibility,
  isPaused,
  onTogglePause,
  autoSavedAt,
  onSubmitClick,
  onExitClick,
}: QuizHeaderProps) {
  const isTimeCritical = timeRemaining > 0 && timeRemaining <= 120; // Dưới 2 phút

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 bg-white/95 px-3 sm:px-4 py-2.5 sm:py-3 shadow-xs backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/95 pt-safe">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-2.5 sm:gap-4">
        {/* Left: Exit & Title */}
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          <button
            type="button"
            onClick={onExitClick}
            className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50 text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
            title="Thoát về trang chủ"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <h1 className="truncate text-xs sm:text-base font-bold text-zinc-900 dark:text-white">
                {title}
              </h1>
              {category && (
                <span className="hidden sm:inline-block rounded-md bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                  {category}
                </span>
              )}
            </div>
            {/* Auto-save Status pill */}
            <div className="flex items-center gap-1 text-[10px] sm:text-[11px] text-zinc-500 dark:text-zinc-400">
              <span className="relative flex h-1.5 w-1.5 sm:h-2 sm:w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 sm:h-2 sm:w-2 rounded-full bg-emerald-500" />
              </span>
              <span className="truncate">
                {autoSavedAt ? "Đã lưu nháp" : "Tự động lưu"}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Timer & Submit Action */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Timer Container (Optional toggle & pause) */}
          <div
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold shadow-xs transition-colors ${
              isTimeCritical
                ? "border-rose-300 bg-rose-50 text-rose-700 animate-pulse dark:border-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                : "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
            }`}
          >
            <Clock
              className={`h-4 w-4 ${
                isTimeCritical ? "text-rose-600 dark:text-rose-400" : "text-indigo-600 dark:text-indigo-400"
              }`}
            />

            {isTimerVisible ? (
              <span className="font-mono text-sm tracking-wider">
                {formatTime(timeRemaining)}
              </span>
            ) : (
              <span className="text-zinc-400 italic font-normal">Đã ẩn</span>
            )}

            {/* Timer visibility toggle */}
            <button
              type="button"
              onClick={onToggleTimerVisibility}
              className="ml-1 rounded p-0.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
              title={isTimerVisible ? "Ẩn đồng hồ" : "Hiện đồng hồ"}
            >
              {isTimerVisible ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>

            {/* Timer pause toggle */}
            <button
              type="button"
              onClick={onTogglePause}
              className="rounded p-0.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
              title={isPaused ? "Tiếp tục làm bài" : "Tạm dừng"}
            >
              {isPaused ? (
                <Play className="h-3.5 w-3.5 fill-current text-emerald-600" />
              ) : (
                <Pause className="h-3.5 w-3.5" />
              )}
            </button>
          </div>

          {/* Submit Button */}
          <button
            type="button"
            onClick={onSubmitClick}
            className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 px-4 py-2 text-xs sm:text-sm font-semibold text-white shadow-md shadow-indigo-600/25 transition-all duration-200 hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-600/35 active:scale-95"
          >
            <Send className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            <span>Nộp bài</span>
          </button>
        </div>
      </div>
    </header>
  );
}
