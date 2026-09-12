"use client";

import React from "react";
import { ArrowLeft, Check, CheckCircle, Sparkles } from "lucide-react";

interface StudioHeaderProps {
  currentStep: 1 | 2 | 3;
  onStepChange?: (step: 1 | 2 | 3) => void;
  canNavigateToStep?: (step: 1 | 2 | 3) => boolean;
  onBackClick: () => void;
  lastSavedAt?: Date | null;
}

export function StudioHeader({
  currentStep,
  onStepChange,
  canNavigateToStep,
  onBackClick,
  lastSavedAt,
}: StudioHeaderProps) {
  const steps = [
    { num: 1 as const, label: "Quét tài liệu", desc: "Scan & Đối chiếu" },
    { num: 2 as const, label: "Chuẩn hóa AI", desc: "Clean & Nối trang" },
    { num: 3 as const, label: "Biên tập đề thi", desc: "Preview & Lưu đề" },
  ];

  return (
    <header className="sticky top-0 z-30 w-full border-b border-zinc-200/80 bg-white/90 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/90 transition-colors shadow-xs pt-safe">
      <div className="mx-auto flex h-14 sm:h-16 max-w-7xl items-center justify-between px-3 sm:px-6 lg:px-8">
        {/* Left: Back button & Title */}
        <div className="flex items-center gap-2.5 sm:gap-4 min-w-0">
          <button
            onClick={onBackClick}
            type="button"
            className="group flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl border border-zinc-200 bg-zinc-50 text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-700 dark:hover:bg-zinc-800"
            title="Quay lại Dashboard"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-sm sm:text-base font-bold text-zinc-900 dark:text-white truncate">
                OCR Studio
              </span>
              <span className="hidden min-[400px]:inline-flex items-center gap-1 rounded-md bg-indigo-50 px-1.5 py-0.5 text-[10px] sm:text-xs font-semibold text-indigo-600 dark:bg-indigo-950/70 dark:text-indigo-400 border border-indigo-200/40 dark:border-indigo-800/40 shrink-0">
                <Sparkles className="h-3 w-3" />
                Multi-page
              </span>
            </div>
            <p className="hidden text-xs text-zinc-500 dark:text-zinc-400 sm:block">
              Quét tài liệu nhiều trang & biên tập đề thi
            </p>
          </div>
        </div>

        {/* Center: Mobile Step Indicator (< md) */}
        <div className="flex md:hidden flex-col items-center">
          <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
            Bước {currentStep}/3
          </span>
          <span className="text-[10px] text-zinc-500 dark:text-zinc-400 font-medium truncate max-w-[120px]">
            {steps[currentStep - 1]?.label}
          </span>
        </div>

        {/* Center: Desktop Stepper (md+) */}
        <nav className="hidden md:flex items-center gap-2 sm:gap-4" aria-label="Tiến trình Studio">
          {steps.map((s, idx) => {
            const isCompleted = currentStep > s.num;
            const isCurrent = currentStep === s.num;
            const isClickable = canNavigateToStep ? canNavigateToStep(s.num) : false;

            return (
              <React.Fragment key={s.num}>
                {idx > 0 && (
                  <div
                    className={`h-0.5 w-6 sm:w-10 transition-colors ${
                      currentStep >= s.num
                        ? "bg-indigo-600 dark:bg-indigo-500"
                        : "bg-zinc-200 dark:bg-zinc-800"
                    }`}
                  />
                )}
                <button
                  type="button"
                  disabled={!isClickable && !isCurrent}
                  onClick={() => isClickable && onStepChange && onStepChange(s.num)}
                  className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-all ${
                    isCurrent
                      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 ring-1 ring-indigo-500/30"
                      : isCompleted
                      ? "text-zinc-700 hover:text-indigo-600 dark:text-zinc-300 dark:hover:text-indigo-400 cursor-pointer"
                      : "text-zinc-400 dark:text-zinc-600 cursor-not-allowed"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${
                      isCompleted
                        ? "bg-emerald-500 text-white"
                        : isCurrent
                        ? "bg-indigo-600 text-white"
                        : "bg-zinc-200 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                    }`}
                  >
                    {isCompleted ? <Check className="h-3 w-3 stroke-[3]" /> : s.num}
                  </span>
                  <div className="text-left">
                    <div>{s.label}</div>
                  </div>
                </button>
              </React.Fragment>
            );
          })}
        </nav>

        {/* Right: Auto-save badge */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50/80 px-2 sm:px-2.5 py-1 text-[10px] sm:text-[11px] font-medium text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/80 dark:text-zinc-400">
            <CheckCircle className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-emerald-500 shrink-0" />
            <span className="hidden sm:inline">Tự động lưu nháp</span>
            {lastSavedAt && (
              <span className="text-[9px] sm:text-[10px] text-zinc-400 dark:text-zinc-500">
                {lastSavedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Mobile progress line */}
      <div className="md:hidden w-full bg-zinc-100 dark:bg-zinc-800 h-0.5 overflow-hidden">
        <div
          className="h-full bg-indigo-600 transition-all duration-300"
          style={{ width: `${(currentStep / 3) * 100}%` }}
        />
      </div>
    </header>
  );
}
