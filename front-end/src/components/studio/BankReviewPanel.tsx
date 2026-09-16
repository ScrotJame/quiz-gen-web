"use client";

import React, { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Database,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Layers,
  BookOpen,
} from "lucide-react";
import { BankQuestionCreate, Difficulty, QuestionType } from "../../lib/types";

interface BankReviewPanelProps {
  questions: BankQuestionCreate[];
  onQuestionsChange: (questions: BankQuestionCreate[]) => void;
  defaultCategory: string;
  isSaving: boolean;
  onSaveToBank: () => Promise<void>;
  onBackToStep2: () => void;
  cleanedText?: string;
  onReExtract?: () => Promise<void>;
  isExtracting?: boolean;
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
  "Giáo dục công dân",
  "Chung",
];

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "Dễ",
  medium: "Trung bình",
  hard: "Khó",
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300",
  medium: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300",
  hard: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300",
};

export function BankReviewPanel({
  questions,
  onQuestionsChange,
  defaultCategory,
  isSaving,
  onSaveToBank,
  onBackToStep2,
  onReExtract,
  isExtracting = false,
}: BankReviewPanelProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);
  const [bulkCategory, setBulkCategory] = useState<string>(defaultCategory || "Chung");
  const [bulkDifficulty, setBulkDifficulty] = useState<Difficulty>("medium");

  const updateQuestion = (idx: number, updates: Partial<BankQuestionCreate>) => {
    const next = [...questions];
    next[idx] = { ...next[idx], ...updates };
    onQuestionsChange(next);
  };

  const deleteQuestion = (idx: number) => {
    onQuestionsChange(questions.filter((_, i) => i !== idx));
  };

  const updateOptionText = (qIdx: number, oIdx: number, text: string) => {
    const next = [...questions];
    const opts = [...next[qIdx].options];
    opts[oIdx] = { ...opts[oIdx], optionText: text };
    next[qIdx] = { ...next[qIdx], options: opts };
    onQuestionsChange(next);
  };

  const setCorrectOption = (qIdx: number, oIdx: number) => {
    const next = [...questions];
    const opts = next[qIdx].options.map((opt, i) => ({
      ...opt,
      isCorrect: i === oIdx,
    }));
    next[qIdx] = { ...next[qIdx], options: opts };
    onQuestionsChange(next);
  };

  const deleteOption = (qIdx: number, oIdx: number) => {
    const next = [...questions];
    next[qIdx] = {
      ...next[qIdx],
      options: next[qIdx].options.filter((_, i) => i !== oIdx),
    };
    onQuestionsChange(next);
  };

  const addOption = (qIdx: number) => {
    const next = [...questions];
    next[qIdx] = {
      ...next[qIdx],
      options: [
        ...next[qIdx].options,
        { optionText: "Đáp án mới", isCorrect: false, orderNum: next[qIdx].options.length },
      ],
    };
    onQuestionsChange(next);
  };

  const addNewQuestion = () => {
    const newQ: BankQuestionCreate = {
      questionText: `Câu ${questions.length + 1}: `,
      questionType: "single_choice",
      category: bulkCategory,
      difficulty: bulkDifficulty,
      explanation: "",
      sourceNote: "Tự nhập tay",
      options: [
        { optionText: "A. Phương án 1", isCorrect: true, orderNum: 0 },
        { optionText: "B. Phương án 2", isCorrect: false, orderNum: 1 },
        { optionText: "C. Phương án 3", isCorrect: false, orderNum: 2 },
        { optionText: "D. Phương án 4", isCorrect: false, orderNum: 3 },
      ],
    };
    const next = [...questions, newQ];
    onQuestionsChange(next);
    setExpandedIdx(next.length - 1);
  };

  // Bulk update category for all questions
  const handleApplyBulkCategory = () => {
    const next = questions.map((q) => ({ ...q, category: bulkCategory }));
    onQuestionsChange(next);
  };

  // Bulk update difficulty for all questions
  const handleApplyBulkDifficulty = () => {
    const next = questions.map((q) => ({ ...q, difficulty: bulkDifficulty }));
    onQuestionsChange(next);
  };

  const letters = ["A", "B", "C", "D", "E", "F", "G", "H"];

  const isValid =
    questions.length > 0 &&
    questions.every(
      (q) =>
        q.questionText.trim().length > 0 &&
        q.options.length >= 2 &&
        q.options.some((o) => o.isCorrect)
    );

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Top Header Bar */}
      <div className="flex flex-col gap-3 border-b border-zinc-200 bg-white px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold text-zinc-900 dark:text-white">
                Duyệt & Lưu Thư viện câu hỏi
              </h2>
              <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300">
                {questions.length} câu hỏi bóc tách
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Kiểm tra toàn bộ câu hỏi đã quét từ tài liệu, chỉnh sửa đáp án trước khi lưu vào ngân hàng chung.
            </p>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center flex-wrap gap-2">
          <button
            id="btn-bank-review-back"
            type="button"
            onClick={onBackToStep2}
            disabled={isSaving || isExtracting}
            className="flex items-center gap-1.5 rounded-xl border border-zinc-200 px-3 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 cursor-pointer"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>← Quay lại chuẩn hóa</span>
          </button>

          {onReExtract && (
            <button
              id="btn-re-extract"
              type="button"
              onClick={onReExtract}
              disabled={isSaving || isExtracting}
              title="Yêu cầu AI quét và bóc tách lại toàn bộ câu hỏi từ văn bản đã chuẩn hóa"
              className="flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50/70 px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-300 dark:hover:bg-indigo-900/50 cursor-pointer"
            >
              {isExtracting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              <span>{isExtracting ? "Đang bóc tách..." : "Bóc tách lại"}</span>
            </button>
          )}

          <button
            id="btn-add-bank-question"
            type="button"
            onClick={addNewQuestion}
            disabled={isSaving || isExtracting}
            className="flex items-center gap-1.5 rounded-xl border border-zinc-200 px-3 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>+ Thêm câu hỏi</span>
          </button>

          <button
            id="btn-save-to-bank"
            type="button"
            onClick={onSaveToBank}
            disabled={isSaving || isExtracting || !isValid}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Database className="h-3.5 w-3.5" />
            )}
            <span>{isSaving ? "Đang lưu kho..." : `Lưu ${questions.length} câu vào Thư viện`}</span>
            {!isSaving && <ArrowRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Bulk Action & Tagging Toolbar */}
      {questions.length > 0 && (
        <div className="border-b border-zinc-200 bg-zinc-50 px-6 py-2.5 dark:border-zinc-800 dark:bg-zinc-900/50 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400 font-medium">
            <Layers className="h-3.5 w-3.5 text-indigo-500" />
            <span>Gán nhanh hàng loạt:</span>
          </div>

          <div className="flex items-center flex-wrap gap-3">
            {/* Bulk Category */}
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500">Môn học:</span>
              <select
                value={bulkCategory}
                onChange={(e) => setBulkCategory(e.target.value)}
                className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-xs font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleApplyBulkCategory}
                className="rounded-lg bg-zinc-200 px-2 py-1 text-[11px] font-semibold text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 cursor-pointer"
              >
                Gán tất cả
              </button>
            </div>

            {/* Bulk Difficulty */}
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500">Độ khó:</span>
              <select
                value={bulkDifficulty}
                onChange={(e) => setBulkDifficulty(e.target.value as Difficulty)}
                className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-xs font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
              >
                <option value="easy">Dễ</option>
                <option value="medium">Trung bình</option>
                <option value="hard">Khó</option>
              </select>
              <button
                type="button"
                onClick={handleApplyBulkDifficulty}
                className="rounded-lg bg-zinc-200 px-2 py-1 text-[11px] font-semibold text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 cursor-pointer"
              >
                Gán tất cả
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Questions List / Empty State */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {questions.length === 0 ? (
          <div className="mx-auto flex max-w-lg flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white p-10 text-center dark:border-zinc-700 dark:bg-zinc-900 shadow-xs">
            <div className="rounded-2xl bg-indigo-50 p-4 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 mb-4">
              <BookOpen className="h-8 w-8" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-white">
              Chưa có câu hỏi trắc nghiệm nào
            </h3>
            <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400 max-w-sm">
              AI không tìm thấy cấu trúc câu hỏi trắc nghiệm trong văn bản đã quét, hoặc tài liệu là đoạn văn lý thuyết.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              {onReExtract && (
                <button
                  type="button"
                  onClick={onReExtract}
                  disabled={isExtracting}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 shadow-xs cursor-pointer"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Bóc tách lại từ văn bản
                </button>
              )}
              <button
                type="button"
                onClick={addNewQuestion}
                className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-200 px-4 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
                + Tự thêm câu hỏi thủ công
              </button>
              <button
                type="button"
                onClick={onBackToStep2}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline py-2"
              >
                ← Quay lại kiểm tra văn bản đã quét
              </button>
            </div>
          </div>
        ) : (
          questions.map((q, qIdx) => {
            const isExpanded = expandedIdx === qIdx;
            const hasCorrect = q.options.some((o) => o.isCorrect);

            return (
              <div
                key={qIdx}
                className="rounded-2xl border border-zinc-200 bg-white shadow-xs transition-all dark:border-zinc-800 dark:bg-zinc-900"
              >
                {/* Header item */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer select-none"
                  onClick={() => setExpandedIdx(isExpanded ? null : qIdx)}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <button
                      type="button"
                      className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </button>

                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      <span className="font-bold text-sm text-zinc-900 dark:text-white">
                        Câu {qIdx + 1}
                      </span>
                      <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                        {q.category}
                      </span>
                      <span
                        className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                          DIFFICULTY_COLORS[q.difficulty || "medium"]
                        }`}
                      >
                        {DIFFICULTY_LABELS[q.difficulty || "medium"]}
                      </span>
                      {!hasCorrect && (
                        <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                          <AlertCircle className="h-3 w-3" />
                          Chưa chọn đáp án đúng
                        </span>
                      )}
                    </div>
                  </div>

                  <div
                    className="flex items-center gap-2 shrink-0 ml-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={() => deleteQuestion(qIdx)}
                      className="rounded-lg p-1.5 text-zinc-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40 dark:hover:text-red-400 cursor-pointer transition-colors"
                      title="Xóa câu hỏi này"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Question Details Content (Expanded) */}
                {isExpanded && (
                  <div className="border-t border-zinc-100 p-4 space-y-4 dark:border-zinc-800">
                    {/* Category & Difficulty for this specific question */}
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-semibold text-zinc-500">Môn học:</label>
                        <select
                          value={q.category}
                          onChange={(e) => updateQuestion(qIdx, { category: e.target.value })}
                          className="rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                        >
                          {CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>
                              {cat}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="flex items-center gap-2">
                        <label className="text-xs font-semibold text-zinc-500">Độ khó:</label>
                        <select
                          value={q.difficulty || "medium"}
                          onChange={(e) =>
                            updateQuestion(qIdx, { difficulty: e.target.value as Difficulty })
                          }
                          className="rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                        >
                          <option value="easy">Dễ</option>
                          <option value="medium">Trung bình</option>
                          <option value="hard">Khó</option>
                        </select>
                      </div>

                      <div className="flex items-center gap-2">
                        <label className="text-xs font-semibold text-zinc-500">Loại:</label>
                        <select
                          value={q.questionType || "single_choice"}
                          onChange={(e) =>
                            updateQuestion(qIdx, {
                              questionType: e.target.value as QuestionType,
                            })
                          }
                          className="rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                        >
                          <option value="single_choice">Trắc nghiệm 1 đáp án</option>
                          <option value="multiple_choice">Nhiều đáp án đúng</option>
                          <option value="true_false">Đúng / Sai</option>
                        </select>
                      </div>
                    </div>

                    {/* Question text textarea */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
                        Nội dung câu hỏi:
                      </label>
                      <textarea
                        value={q.questionText}
                        onChange={(e) => updateQuestion(qIdx, { questionText: e.target.value })}
                        rows={3}
                        placeholder="Nhập nội dung câu hỏi..."
                        className="w-full rounded-xl border border-zinc-200 bg-zinc-50/60 p-3 text-xs sm:text-sm text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100"
                      />
                    </div>

                    {/* Options list */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
                          Các lựa chọn trả lời (Tích chọn đáp án đúng):
                        </label>
                        <button
                          type="button"
                          onClick={() => addOption(qIdx)}
                          className="flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 cursor-pointer"
                        >
                          <Plus className="h-3 w-3" />
                          Thêm lựa chọn
                        </button>
                      </div>

                      <div className="space-y-2">
                        {q.options.map((opt, oIdx) => {
                          const letter = letters[oIdx] || `${oIdx + 1}`;
                          return (
                            <div
                              key={oIdx}
                              className={`flex items-center gap-2 rounded-xl border p-2.5 transition-colors ${
                                opt.isCorrect
                                  ? "border-emerald-300 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/20"
                                  : "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
                              }`}
                            >
                              <input
                                type="radio"
                                name={`correct-opt-${qIdx}`}
                                checked={opt.isCorrect}
                                onChange={() => setCorrectOption(qIdx, oIdx)}
                                className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                                title="Đánh dấu đây là đáp án đúng"
                              />

                              <span
                                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                                  opt.isCorrect
                                    ? "bg-emerald-600 text-white"
                                    : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                                }`}
                              >
                                {letter}
                              </span>

                              <input
                                type="text"
                                value={opt.optionText}
                                onChange={(e) => updateOptionText(qIdx, oIdx, e.target.value)}
                                placeholder={`Nội dung lựa chọn ${letter}...`}
                                className="flex-1 rounded-lg border-0 bg-transparent px-2 py-1 text-xs text-zinc-900 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 dark:text-zinc-100"
                              />

                              {opt.isCorrect && (
                                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 dark:text-emerald-400 shrink-0">
                                  <CheckCircle2 className="h-3.5 w-3.5" />
                                  Đáp án đúng
                                </span>
                              )}

                              {q.options.length > 2 && (
                                <button
                                  type="button"
                                  onClick={() => deleteOption(qIdx, oIdx)}
                                  className="rounded-lg p-1 text-zinc-400 hover:text-red-500 cursor-pointer"
                                  title="Xóa lựa chọn này"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Explanation */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
                        Lời giải thích / Hướng dẫn giải (nếu có):
                      </label>
                      <textarea
                        value={q.explanation || ""}
                        onChange={(e) => updateQuestion(qIdx, { explanation: e.target.value })}
                        rows={2}
                        placeholder="Giải thích vì sao đáp án này đúng..."
                        className="w-full rounded-xl border border-zinc-200 bg-zinc-50/60 p-2.5 text-xs text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100"
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Floating Bar */}
      <div className="flex items-center justify-between border-t border-zinc-200 bg-white px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <button
          type="button"
          onClick={onBackToStep2}
          disabled={isSaving || isExtracting}
          className="flex items-center gap-1.5 text-xs font-semibold text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white cursor-pointer"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Quay lại Bước 2 (Chuẩn hóa)</span>
        </button>

        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-500 dark:text-zinc-400 hidden sm:inline">
            {questions.length} câu hỏi sẵn sàng lưu kho
          </span>
          <button
            type="button"
            onClick={onSaveToBank}
            disabled={isSaving || isExtracting || !isValid}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Database className="h-4 w-4" />
            )}
            <span>{isSaving ? "Đang lưu vào kho..." : "Lưu vào Thư viện & Tiếp tục"}</span>
            {!isSaving && <ArrowRight className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
