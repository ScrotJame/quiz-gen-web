"use client";

import React, { useState } from "react";
import {
  Sparkles,
  ArrowLeft,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Sliders,
} from "lucide-react";
import { Difficulty } from "../../lib/types";

interface MergeCleanPanelProps {
  mergedText: string;
  onMergedTextChange: (text: string) => void;
  onCleanWithAi: (targetLang: string) => Promise<void>;
  isCleaning: boolean;
  hasCleaned: boolean;
  // Quiz config
  title: string;
  onTitleChange: (title: string) => void;
  category: string;
  onCategoryChange: (category: string) => void;
  numQuestions: number;
  onNumQuestionsChange: (num: number) => void;
  difficulty: Difficulty;
  onDifficultyChange: (diff: Difficulty) => void;
  temperature: number;
  onTemperatureChange: (temp: number) => void;
  // Nav
  onBackToStep1: () => void;
  onGenerateQuiz: () => Promise<void>;
  isGenerating: boolean;
  pageCount: number;
}

const CATEGORIES = [
  "Toán học",
  "Ngữ văn",
  "Tiếng Anh",
  "Lịch sử",
  "Địa lý",
  "Khoa học tự nhiên",
  "Vật lý",
  "Hóa học",
  "Sinh học",
  "Tin học",
  "Chung",
];

const QUESTION_COUNTS = [3, 5, 10, 15, 20];

export function MergeCleanPanel({
  mergedText,
  onMergedTextChange,
  onCleanWithAi,
  isCleaning,
  hasCleaned,
  title,
  onTitleChange,
  category,
  onCategoryChange,
  numQuestions,
  onNumQuestionsChange,
  difficulty,
  onDifficultyChange,
  temperature,
  onTemperatureChange,
  onBackToStep1,
  onGenerateQuiz,
  isGenerating,
  pageCount,
}: MergeCleanPanelProps) {
  const [targetLang, setTargetLang] = useState<string>("vi");

  const wordCount = mergedText.trim().split(/\s+/).filter(Boolean).length;
  const lineCount = mergedText.split("\n").filter((l) => l.trim().length > 0).length;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-indigo-100 bg-gradient-to-r from-indigo-50/70 via-purple-50/50 to-pink-50/40 p-5 dark:border-indigo-900/40 dark:from-indigo-950/40 dark:via-purple-950/30 dark:to-zinc-900">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-indigo-600 p-1 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <h2 className="text-base sm:text-lg font-bold text-zinc-900 dark:text-white">
              Hợp nhất văn bản & Chuẩn hóa AI
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-zinc-600 dark:text-zinc-400">
            Đã gộp nội dung từ {pageCount} trang tài liệu ({lineCount} dòng • {wordCount.toLocaleString()} từ).
            Sử dụng AI để tự động sửa dấu tiếng Việt và nối các câu bị đứt đoạn.
          </p>
        </div>

        {/* AI Clean Button */}
        <div className="flex items-center gap-2 shrink-0">
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            disabled={isCleaning || isGenerating}
            className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold text-zinc-700 shadow-xs focus:border-indigo-500 focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
          </select>

          <button
            type="button"
            onClick={() => onCleanWithAi(targetLang)}
            disabled={isCleaning || isGenerating || !mergedText.trim()}
            className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/25 transition-all hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg disabled:opacity-50 active:scale-95 cursor-pointer"
          >
            {isCleaning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-white" />
                <span>AI đang chuẩn hóa...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 transition-transform duration-300 group-hover:rotate-12" />
                <span>AI Sửa lỗi chính tả & Nối đoạn</span>
              </>
            )}
          </button>
        </div>
      </div>

      {hasCleaned && (
        <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50/80 px-4 py-2.5 text-xs text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            <strong>Đã chuẩn hóa thành công:</strong> AI đã sửa lỗi chính tả dấu tiếng Việt và nối các câu ngắt đoạn liền mạch.
          </span>
        </div>
      )}

      {/* Main 2-column layout: Left = Merged Text, Right = Quiz Config */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ========================================================================= */}
        {/* LEFT COLUMN: MERGED TEXT AREA (7 cols)                                   */}
        {/* ========================================================================= */}
        <div className="lg:col-span-7 flex flex-col space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-400">
              Văn bản tổng hợp ({wordCount} từ)
            </label>
            <span className="text-[11px] text-zinc-400">
              Có thể sửa trực tiếp trước khi sinh câu hỏi
            </span>
          </div>

          <div className="relative">
            <textarea
              value={mergedText}
              onChange={(e) => onMergedTextChange(e.target.value)}
              rows={18}
              placeholder="Nội dung tổng hợp từ các trang..."
              className="w-full rounded-2xl border border-zinc-200 bg-white p-4 font-mono text-xs sm:text-sm leading-relaxed text-zinc-900 shadow-xs placeholder:text-zinc-400 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
            />
          </div>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT COLUMN: QUIZ CONFIGURATION FORM (5 cols)                           */}
        {/* ========================================================================= */}
        <div className="lg:col-span-5 flex flex-col space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center gap-2 border-b border-zinc-100 pb-3 dark:border-zinc-800">
            <Sliders className="h-4 w-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-zinc-900 dark:text-white">
              Cấu hình sinh đề thi AI
            </h3>
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              Tiêu đề đề thi
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="VD: Đề kiểm tra 15 phút Hoá học Chương 1..."
              className="w-full rounded-xl border border-zinc-200 px-3.5 py-2.5 text-xs sm:text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-100"
            />
          </div>

          {/* Category */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              Chủ đề / Môn học
            </label>
            <select
              value={category}
              onChange={(e) => onCategoryChange(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm text-zinc-900 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-100"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Number of Questions */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              Số lượng câu hỏi trắc nghiệm
            </label>
            <div className="grid grid-cols-5 gap-2">
              {QUESTION_COUNTS.map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => onNumQuestionsChange(num)}
                  className={`rounded-xl py-2 text-xs font-bold transition-all ${
                    numQuestions === num
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "border border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                  }`}
                >
                  {num} câu
                </button>
              ))}
            </div>
          </div>

          {/* Difficulty */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              Mức độ khó
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  { value: "easy", label: "Dễ" },
                  { value: "medium", label: "Trung bình" },
                  { value: "hard", label: "Khó" },
                ] as const
              ).map((diff) => (
                <button
                  key={diff.value}
                  type="button"
                  onClick={() => onDifficultyChange(diff.value)}
                  className={`rounded-xl py-2 text-xs font-bold transition-all ${
                    difficulty === diff.value
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "border border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                  }`}
                >
                  {diff.label}
                </button>
              ))}
            </div>
          </div>

          {/* Temperature / Prompt Style */}
          <div className="space-y-2 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3 dark:border-zinc-800 dark:bg-zinc-800/40">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                Chế độ biên soạn:
              </span>
              <span className="font-bold text-indigo-600 dark:text-indigo-400">
                {temperature === 0 ? "Trích xuất nguyên văn" : "Biên tập thông minh"}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => onTemperatureChange(0.0)}
                className={`flex-1 rounded-lg py-1.5 text-xs font-semibold ${
                  temperature === 0
                    ? "bg-indigo-600 text-white"
                    : "border border-zinc-200 bg-white text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                }`}
              >
                Nguyên văn (100%)
              </button>
              <button
                type="button"
                onClick={() => onTemperatureChange(0.3)}
                className={`flex-1 rounded-lg py-1.5 text-xs font-semibold ${
                  temperature > 0
                    ? "bg-indigo-600 text-white"
                    : "border border-zinc-200 bg-white text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                }`}
              >
                Trau chuốt (AI)
              </button>
            </div>
          </div>

          {/* Primary Generate Button */}
          <button
            type="button"
            onClick={onGenerateQuiz}
            disabled={isGenerating || !mergedText.trim()}
            className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.01] hover:shadow-xl hover:shadow-indigo-600/40 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 cursor-pointer mt-2"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin text-white" />
                <span>Mistral AI đang biên soạn đề thi...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-5 w-5 transition-transform duration-300 group-hover:rotate-12" />
                <span>Sinh câu hỏi trắc nghiệm bằng AI</span>
                <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Bottom Nav: Back button */}
      <div className="flex items-center justify-between border-t border-zinc-200 pt-4 dark:border-zinc-800">
        <button
          type="button"
          onClick={onBackToStep1}
          disabled={isGenerating}
          className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-200 px-4 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>← Quay lại đối chiếu trang</span>
        </button>
      </div>
    </div>
  );
}
