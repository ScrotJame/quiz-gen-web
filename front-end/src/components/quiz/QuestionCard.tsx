"use client";

import React from "react";
import {
  Flag,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  RotateCcw,
} from "lucide-react";
import { Question } from "../../lib/types";

interface QuestionCardProps {
  question: Question;
  index: number;
  totalQuestions: number;
  selectedOptionIds: string[];
  isFlagged: boolean;
  onToggleFlag: () => void;
  onSelectOption: (optionId: string) => void;
  onClearAnswer: () => void;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  onSubmitPrompt: () => void;
}

const optionLabels = ["A", "B", "C", "D", "E", "F", "G", "H"];

export function QuestionCard({
  question,
  index,
  totalQuestions,
  selectedOptionIds,
  isFlagged,
  onToggleFlag,
  onSelectOption,
  onClearAnswer,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  onSubmitPrompt,
}: QuestionCardProps) {
  const isMultiple = question.questionType === "multiple_choice";

  return (
    <div className="w-full rounded-2xl sm:rounded-3xl border border-zinc-200/90 bg-white p-4.5 sm:p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90 transition-all">
      {/* Question Header */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pb-4 sm:pb-5 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <span className="flex h-7 px-2.5 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs tracking-wide">
            CÂU {index + 1} / {totalQuestions}
          </span>
          <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
            {question.points || 10}đ
          </span>
          <span className="rounded-md bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 text-[10px] sm:text-[11px] font-medium text-zinc-600 dark:text-zinc-300">
            {isMultiple ? "Nhiều đáp án" : "1 đáp án"}
          </span>
        </div>

        {/* Flag Question Button */}
        <div className="flex items-center gap-2">
          {selectedOptionIds.length > 0 && (
            <button
              type="button"
              onClick={onClearAnswer}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors min-h-[36px]"
              title="Xóa lựa chọn câu này"
            >
              <RotateCcw className="h-3 w-3" />
              <span className="text-xs">Bỏ chọn</span>
            </button>
          )}

          <button
            type="button"
            onClick={onToggleFlag}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all duration-200 min-h-[36px] ${
              isFlagged
                ? "border-amber-300 bg-amber-50 text-amber-700 shadow-xs dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                : "border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }`}
            title="Gắn cờ để xem lại sau (Phím tắt: F)"
          >
            <Flag
              className={`h-3.5 w-3.5 ${
                isFlagged ? "fill-amber-500 text-amber-500" : "text-zinc-400"
              }`}
            />
            <span>{isFlagged ? "Đã cờ" : "Gắn cờ"}</span>
            <kbd className="hidden sm:inline-block rounded bg-zinc-200/70 px-1 py-0.2 text-[10px] font-mono text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
              F
            </kbd>
          </button>
        </div>
      </div>

      {/* Question Text */}
      <div className="py-4 sm:py-6">
        <h2 className="text-base sm:text-xl font-bold leading-relaxed tracking-tight text-zinc-900 dark:text-white max-w-3xl">
          {question.questionText}
        </h2>
      </div>

      {/* Options List */}
      <div className="space-y-2.5 sm:space-y-3">
        {question.options.map((option, optIdx) => {
          const isSelected = selectedOptionIds.includes(option.id);
          const letter = optionLabels[optIdx] || String(optIdx + 1);

          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onSelectOption(option.id)}
              className={`group relative flex w-full items-start gap-3 rounded-xl sm:rounded-2xl border p-3.5 sm:p-4 text-left transition-all duration-200 cursor-pointer min-h-[52px] active:scale-[0.99] touch-manipulation ${
                isSelected
                  ? "border-indigo-600 bg-indigo-50/70 shadow-sm ring-1 ring-indigo-600 dark:border-indigo-500 dark:bg-indigo-950/40 dark:ring-indigo-500"
                  : "border-zinc-200/80 bg-zinc-50/40 hover:border-indigo-200 hover:bg-indigo-50/20 dark:border-zinc-800/80 dark:bg-zinc-950/40 dark:hover:border-indigo-900 dark:hover:bg-zinc-800/50"
              }`}
            >
              {/* Option Letter Tag */}
              <div
                className={`flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-lg sm:rounded-xl font-bold text-xs transition-colors mt-0.5 ${
                  isSelected
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "border border-zinc-300/80 bg-white text-zinc-700 group-hover:border-indigo-300 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
                }`}
              >
                {letter}
              </div>

              {/* Option Text */}
              <div className="flex-1 pt-0.5 min-w-0">
                <p
                  className={`text-sm sm:text-base leading-relaxed font-medium transition-colors ${
                    isSelected
                      ? "text-indigo-950 dark:text-indigo-100 font-semibold"
                      : "text-zinc-800 dark:text-zinc-200"
                  }`}
                >
                  {option.optionText}
                </p>
              </div>

              {/* Indicator Radio / Checkbox Circle */}
              <div className="pt-1">
                <div
                  className={`flex h-5 w-5 shrink-0 items-center justify-center ${
                    isMultiple ? "rounded-md" : "rounded-full"
                  } border transition-all ${
                    isSelected
                      ? "border-indigo-600 bg-indigo-600 text-white"
                      : "border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900"
                  }`}
                >
                  {isSelected && (
                    <CheckCircle2 className="h-3.5 w-3.5 fill-current" />
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer Navigation Bar */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-zinc-100 pt-6 dark:border-zinc-800">
        {/* Previous Button */}
        <button
          type="button"
          onClick={onPrev}
          disabled={!hasPrev}
          className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-xs sm:text-sm font-semibold text-zinc-700 shadow-xs transition-all hover:bg-zinc-50 hover:text-zinc-900 disabled:opacity-40 disabled:pointer-events-none dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 active:scale-95"
          title="Câu trước (Phím tắt: ←)"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Câu trước</span>
          <kbd className="hidden sm:inline-block rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 dark:bg-zinc-800">
            ←
          </kbd>
        </button>

        {/* Next or Finish Button */}
        {hasNext ? (
          <button
            type="button"
            onClick={onNext}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-500 active:scale-95"
            title="Câu tiếp theo (Phím tắt: →)"
          >
            <span>Câu tiếp theo</span>
            <ArrowRight className="h-4 w-4" />
            <kbd className="hidden sm:inline-block rounded bg-indigo-700 px-1.5 py-0.5 text-[10px] font-mono text-indigo-200">
              →
            </kbd>
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmitPrompt}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-md shadow-emerald-600/20 transition-all hover:from-emerald-500 hover:to-teal-500 active:scale-95"
          >
            <span>Kiểm tra & Nộp bài</span>
            <CheckCircle2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
