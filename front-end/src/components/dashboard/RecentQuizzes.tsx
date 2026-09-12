"use client";

import React from "react";
import Link from "next/link";
import {
  BookOpen,
  Clock,
  Calendar,
  Play,
  Search,
  Sparkles,
  HelpCircle,
  Layers,
  ChevronRight,
} from "lucide-react";
import { QuizSummary, Difficulty } from "../../lib/types";

interface RecentQuizzesProps {
  quizzes: QuizSummary[];
  isLoading: boolean;
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

const difficultyConfig: Record<
  Difficulty,
  { label: string; bg: string; text: string; dot: string }
> = {
  easy: {
    label: "Dễ",
    bg: "bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800/60",
    text: "text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  medium: {
    label: "Trung bình",
    bg: "bg-amber-50 dark:bg-amber-950/50 border-amber-200 dark:border-amber-800/60",
    text: "text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  hard: {
    label: "Khó",
    bg: "bg-rose-50 dark:bg-rose-950/50 border-rose-200 dark:border-rose-800/60",
    text: "text-rose-700 dark:text-rose-300",
    dot: "bg-rose-500",
  },
};

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Mới tạo";
    return d.toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "Mới tạo";
  }
}

export function RecentQuizzes({
  quizzes,
  isLoading,
  categories,
  selectedCategory,
  onSelectCategory,
  searchQuery,
  onSearchChange,
}: RecentQuizzesProps) {
  return (
    <div className="rounded-3xl border border-zinc-200/80 bg-white/70 p-6 shadow-sm backdrop-blur-md sm:p-8 dark:border-zinc-800/80 dark:bg-zinc-900/60">
      {/* Header section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
              <Layers className="h-5 w-5" />
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
              Quiz gần đây
            </h2>
            <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-semibold text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
              {quizzes.length} đề thi
            </span>
          </div>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Các bộ câu hỏi trắc nghiệm vừa được tạo hoặc làm gần đây nhất
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm kiếm theo tiêu đề..."
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2 pl-10 pr-4 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-800 dark:bg-zinc-950/60 dark:text-white dark:focus:bg-zinc-900"
          />
        </div>
      </div>

      {/* Category Pills Filter */}
      {categories.length > 1 && (
        <div className="mt-6 flex flex-wrap gap-2 overflow-x-auto pb-1">
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat;
            return (
              <button
                key={cat}
                type="button"
                onClick={() => onSelectCategory(cat)}
                className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-all ${
                  isSelected
                    ? "bg-indigo-600 text-white shadow-xs shadow-indigo-600/30"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700/80"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      )}

      {/* Content Area */}
      <div className="mt-6">
        {isLoading ? (
          // Loading Skeletons
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="animate-pulse rounded-2xl border border-zinc-200/60 bg-zinc-50/50 p-5 dark:border-zinc-800/60 dark:bg-zinc-950/40"
              >
                <div className="flex items-center justify-between">
                  <div className="h-5 w-20 rounded bg-zinc-200 dark:bg-zinc-800" />
                  <div className="h-5 w-16 rounded bg-zinc-200 dark:bg-zinc-800" />
                </div>
                <div className="mt-4 h-6 w-3/4 rounded bg-zinc-200 dark:bg-zinc-800" />
                <div className="mt-2 h-4 w-full rounded bg-zinc-200 dark:bg-zinc-800" />
                <div className="mt-6 flex items-center justify-between">
                  <div className="h-4 w-24 rounded bg-zinc-200 dark:bg-zinc-800" />
                  <div className="h-8 w-20 rounded-xl bg-zinc-200 dark:bg-zinc-800" />
                </div>
              </div>
            ))}
          </div>
        ) : quizzes.length === 0 ? (
          // Empty State
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 py-16 text-center dark:border-zinc-800">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
              <BookOpen className="h-8 w-8" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-zinc-900 dark:text-white">
              {searchQuery ? "Không tìm thấy quiz phù hợp" : "Chưa có quiz nào được tạo"}
            </h3>
            <p className="mt-1 max-w-sm text-sm text-zinc-500 dark:text-zinc-400">
              {searchQuery
                ? "Thử thay đổi từ khóa hoặc bộ lọc danh mục để tìm kiếm lại."
                : "Bắt đầu bằng cách nhấn 'Tạo Quiz' để trích xuất câu hỏi từ ảnh hoặc chủ đề của bạn."}
            </p>
            <Link
              href="/create/ocr"
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-500 active:scale-95"
            >
              <Sparkles className="h-4 w-4" />
              <span>Tạo Đề Thi Ngay</span>
            </Link>
          </div>
        ) : (
          // Quizzes Grid
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {quizzes.map((quiz) => {
              const diff =
                difficultyConfig[quiz.difficulty] || difficultyConfig.medium;

              return (
                <div
                  key={quiz.id}
                  className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-zinc-200/90 bg-white p-5 shadow-xs transition-all duration-300 hover:-translate-y-1 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/10 dark:border-zinc-800 dark:bg-zinc-900/90 dark:hover:border-indigo-700/60"
                >
                  {/* Top Metadata row */}
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center rounded-md bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                        {quiz.category || "Chung"}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${diff.bg} ${diff.text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${diff.dot}`} />
                        {diff.label}
                      </span>
                    </div>

                    {/* Title & Description */}
                    <h3
                      className="mt-3 line-clamp-2 text-base font-bold tracking-tight text-zinc-900 transition-colors group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-400"
                      title={quiz.title}
                    >
                      {quiz.title}
                    </h3>
                    <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
                      {quiz.description || "Bộ câu hỏi trắc nghiệm rèn luyện kiến thức."}
                    </p>
                  </div>

                  {/* Meta pills & Action footer */}
                  <div className="mt-5 border-t border-zinc-100 pt-4 dark:border-zinc-800/80">
                    <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
                      <div className="flex items-center gap-1.5">
                        <HelpCircle className="h-3.5 w-3.5 text-indigo-500" />
                        <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                          {quiz.totalQuestions}
                        </span>{" "}
                        câu hỏi
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-amber-500" />
                        <span>{quiz.timeLimitMinutes || 15} phút</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5 text-zinc-400" />
                        <span>{formatDate(quiz.createdAt)}</span>
                      </div>
                    </div>

                    {/* Play Quiz CTA button */}
                    <a
                      href={`/quiz/${quiz.id}`}
                      className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-zinc-900 to-zinc-800 py-2.5 text-xs font-semibold text-white shadow-sm transition-all duration-200 group-hover:from-indigo-600 group-hover:to-purple-600 group-hover:shadow-md group-hover:shadow-indigo-500/20 active:scale-95 dark:from-zinc-100 dark:to-zinc-200 dark:text-zinc-950 dark:group-hover:from-indigo-500 dark:group-hover:to-purple-500 dark:group-hover:text-white"
                    >
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>Làm bài ngay</span>
                      <ChevronRight className="h-3.5 w-3.5 opacity-70 transition-transform group-hover:translate-x-0.5" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
