"use client";

import React, { useState } from "react";
import { Flag } from "lucide-react";

interface QuestionNavigatorProps {
  totalQuestions: number;
  currentIndex: number;
  onSelectIndex: (index: number) => void;
  isAnswered: (index: number) => boolean;
  isFlagged: (index: number) => boolean;
}

type FilterType = "all" | "unanswered" | "flagged";

export function QuestionNavigator({
  totalQuestions,
  currentIndex,
  onSelectIndex,
  isAnswered,
  isFlagged,
}: QuestionNavigatorProps) {
  const [filter, setFilter] = useState<FilterType>("all");

  const questionIndices = Array.from({ length: totalQuestions }, (_, i) => i);

  const filteredIndices = questionIndices.filter((idx) => {
    if (filter === "unanswered") return !isAnswered(idx);
    if (filter === "flagged") return isFlagged(idx);
    return true;
  });

  return (
    <div className="rounded-3xl border border-zinc-200/90 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90">
      {/* Navigator Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800">
        <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
          <span>Danh sách câu hỏi</span>
          <span className="rounded-full bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 text-xs text-zinc-600 dark:text-zinc-400">
            {totalQuestions}
          </span>
        </h3>

        {/* Quick Filter Selector */}
        <div className="flex items-center gap-1 text-[11px]">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`rounded-lg px-2 py-1 transition-colors ${
              filter === "all"
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            Tất cả
          </button>
          <button
            type="button"
            onClick={() => setFilter("unanswered")}
            className={`rounded-lg px-2 py-1 transition-colors ${
              filter === "unanswered"
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            Chưa làm
          </button>
          <button
            type="button"
            onClick={() => setFilter("flagged")}
            className={`rounded-lg px-2 py-1 transition-colors ${
              filter === "flagged"
                ? "bg-amber-500 text-white font-semibold"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            Gắn cờ
          </button>
        </div>
      </div>

      {/* Grid of Question Bubbles */}
      <div className="mt-4 grid grid-cols-5 sm:grid-cols-6 md:grid-cols-5 lg:grid-cols-5 gap-2 max-h-72 overflow-y-auto pr-1">
        {filteredIndices.map((idx) => {
          const active = idx === currentIndex;
          const answered = isAnswered(idx);
          const flagged = isFlagged(idx);

          let bgClass = "bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700";
          if (answered && !active) {
            bgClass = "bg-emerald-500 text-white shadow-xs hover:bg-emerald-600";
          }
          if (flagged && !active) {
            bgClass = "bg-amber-400 text-zinc-950 font-bold shadow-xs hover:bg-amber-500";
          }
          if (active) {
            bgClass = "bg-indigo-600 text-white ring-2 ring-indigo-600 ring-offset-2 dark:ring-offset-zinc-900 font-bold shadow-sm";
          }

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectIndex(idx)}
              className={`relative flex h-10 w-full items-center justify-center rounded-xl text-xs font-semibold transition-all duration-150 active:scale-90 cursor-pointer ${bgClass}`}
              title={`Câu ${idx + 1}${answered ? " - Đã làm" : ""}${flagged ? " - Gắn cờ" : ""}`}
            >
              <span>{idx + 1}</span>

              {/* Small Flag badge dot */}
              {flagged && (
                <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-amber-500 text-[9px] text-white ring-1 ring-white dark:ring-zinc-900">
                  <Flag className="h-2 w-2 fill-current" />
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-5 grid grid-cols-2 gap-2 border-t border-zinc-100 pt-4 text-[11px] text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-md bg-indigo-600" />
          <span>Đang làm</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-md bg-emerald-500" />
          <span>Đã trả lời</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-md bg-amber-400" />
          <span>Đã gắn cờ</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-md bg-zinc-200 dark:bg-zinc-800" />
          <span>Chưa làm</span>
        </div>
      </div>
    </div>
  );
}
