"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Trophy,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Home,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
} from "lucide-react";
import { AttemptResult, QuizDetail } from "../../lib/types";

interface QuizResultViewProps {
  quiz: QuizDetail;
  result: AttemptResult;
  onRetry: () => void;
}

export function QuizResultView({ quiz, result, onRetry }: QuizResultViewProps) {
  const [expandedQuestions, setExpandedQuestions] = useState<Record<string, boolean>>({});

  const toggleExpand = (qId: string) => {
    setExpandedQuestions((prev) => ({ ...prev, [qId]: !prev[qId] }));
  };

  const percentage = result.percentage;
  const isPassed = percentage >= 50;

  let verdictText = "Cần cố gắng hơn";
  let verdictColor = "text-amber-600 dark:text-amber-400";
  if (percentage >= 90) {
    verdictText = "Xuất sắc! Bạn đã làm chủ kiến thức này";
    verdictColor = "text-emerald-600 dark:text-emerald-400";
  } else if (percentage >= 70) {
    verdictText = "Làm rất tốt! Kết quả rất ấn tượng";
    verdictColor = "text-indigo-600 dark:text-indigo-400";
  } else if (percentage >= 50) {
    verdictText = "Đạt yêu cầu! Tiếp tục rèn luyện thêm nhé";
    verdictColor = "text-sky-600 dark:text-sky-400";
  }

  // Map answers by questionId
  const answerMap = new Map(
    result.answers.map((ans) => [ans.questionId, ans])
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 space-y-8 animate-in fade-in duration-300">
      {/* Score Card Hero */}
      <div className="relative overflow-hidden rounded-3xl border border-zinc-200/90 bg-white p-8 text-center shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
        {/* Glow ambient background */}
        <div
          className={`pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-48 w-48 rounded-full blur-3xl opacity-20 ${
            isPassed ? "bg-emerald-500" : "bg-amber-500"
          }`}
        />

        {/* Trophy icon */}
        <div
          className={`mx-auto flex h-16 w-16 items-center justify-center rounded-3xl shadow-lg ${
            isPassed
              ? "bg-gradient-to-tr from-emerald-500 to-teal-600 text-white shadow-emerald-500/30"
              : "bg-gradient-to-tr from-amber-500 to-orange-600 text-white shadow-amber-500/30"
          }`}
        >
          <Trophy className="h-8 w-8" />
        </div>

        {/* Title & Verdict */}
        <h2 className="mt-4 text-2xl sm:text-3xl font-black text-zinc-900 dark:text-white">
          Kết Quả Làm Bài
        </h2>
        <p className={`mt-1 text-sm sm:text-base font-bold ${verdictColor}`}>
          {verdictText}
        </p>

        {/* Score Ring / Numbers */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-6">
          {/* Percentage */}
          <div className="rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800 px-6 py-4">
            <span className="block text-xs font-semibold text-zinc-500 dark:text-zinc-400">
              Tỷ lệ chính xác
            </span>
            <span className="text-4xl sm:text-5xl font-extrabold tracking-tight text-indigo-600 dark:text-indigo-400">
              {percentage}%
            </span>
          </div>

          {/* Points */}
          <div className="rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800 px-6 py-4">
            <span className="block text-xs font-semibold text-zinc-500 dark:text-zinc-400">
              Điểm đạt được
            </span>
            <span className="text-4xl sm:text-5xl font-extrabold tracking-tight text-zinc-900 dark:text-white">
              {result.score}
              <span className="text-2xl font-normal text-zinc-400">
                /{result.maxScore}
              </span>
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 active:scale-95 transition-all"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Làm lại bài thi</span>
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-6 py-3 text-sm font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-all"
          >
            <Home className="h-4 w-4" />
            <span>Về Dashboard</span>
          </Link>
        </div>
      </div>

      {/* Questions Review Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-500" />
            <span>Chi tiết câu hỏi & Lời giải</span>
          </h3>
          <span className="text-xs text-zinc-500">
            {quiz.questions.length} câu hỏi
          </span>
        </div>

        <div className="space-y-4">
          {quiz.questions.map((q, idx) => {
            const ans = answerMap.get(q.id);
            const isCorrect = ans?.isCorrect ?? false;
            const isExpanded = expandedQuestions[q.id] ?? true; // Mặc định mở
            const selectedIds = ans?.selectedOptionIds || [];

            return (
              <div
                key={q.id}
                className={`overflow-hidden rounded-2xl border transition-all ${
                  isCorrect
                    ? "border-emerald-200/80 bg-white dark:border-emerald-900/50 dark:bg-zinc-900/90"
                    : "border-rose-200/80 bg-white dark:border-rose-900/50 dark:bg-zinc-900/90"
                }`}
              >
                {/* Accordion header */}
                <button
                  type="button"
                  onClick={() => toggleExpand(q.id)}
                  className="flex w-full items-center justify-between p-5 text-left transition-colors hover:bg-zinc-50/50 dark:hover:bg-zinc-800/40"
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="pt-0.5">
                      {isCorrect ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                      ) : (
                        <XCircle className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400">
                          Câu {idx + 1}
                        </span>
                        <span
                          className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                            isCorrect
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                          }`}
                        >
                          {isCorrect
                            ? `+${ans?.earnedPoints ?? q.points} điểm`
                            : "0 điểm"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-white line-clamp-2">
                        {q.questionText}
                      </p>
                    </div>
                  </div>

                  <div className="ml-3 shrink-0 text-zinc-400">
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                  </div>
                </button>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="border-t border-zinc-100 p-5 dark:border-zinc-800 space-y-3">
                    {/* Options list */}
                    <div className="space-y-2">
                      {q.options.map((opt, oIdx) => {
                        const isUserSelected = selectedIds.includes(opt.id);
                        const isRightAnswer =
                          ans?.correctOptionIds && ans.correctOptionIds.length > 0
                            ? ans.correctOptionIds.includes(opt.id)
                            : (opt.isCorrect ?? false);

                        let optClass = "border-zinc-200 bg-zinc-50/50 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-950/40 dark:text-zinc-300";
                        if (isRightAnswer) {
                          optClass = "border-emerald-500 bg-emerald-50 text-emerald-950 dark:border-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-100 font-semibold";
                        } else if (isUserSelected && !isRightAnswer) {
                          optClass = "border-rose-400 bg-rose-50 text-rose-950 dark:border-rose-700 dark:bg-rose-950/40 dark:text-rose-100 line-through opacity-80";
                        }

                        return (
                          <div
                            key={opt.id}
                            className={`flex items-center justify-between rounded-xl border p-3 text-xs sm:text-sm ${optClass}`}
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="font-bold">{String.fromCharCode(65 + oIdx)}.</span>
                              <span>{opt.optionText}</span>
                            </div>

                            <div className="flex items-center gap-1 text-[11px] shrink-0 font-medium">
                              {isUserSelected && (
                                <span className="rounded bg-zinc-200/80 px-1.5 py-0.5 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                                  Bạn đã chọn
                                </span>
                              )}
                              {isRightAnswer && (
                                <span className="rounded bg-emerald-600 px-1.5 py-0.5 text-white font-bold">
                                  Đáp án đúng
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Explanation */}
                    {(ans?.explanation || q.explanation) && (
                      <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/50 p-3.5 text-xs text-indigo-950 dark:border-indigo-900/50 dark:bg-indigo-950/30 dark:text-indigo-200">
                        <span className="font-bold flex items-center gap-1.5 mb-1">
                          <HelpCircle className="h-3.5 w-3.5 text-indigo-500" />
                          Giải thích chi tiết:
                        </span>
                        <p className="leading-relaxed">{ans?.explanation || q.explanation}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
