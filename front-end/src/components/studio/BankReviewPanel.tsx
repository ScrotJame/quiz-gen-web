"use client";

import React, { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  Edit3,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { BankQuestionCreate, Difficulty, QuestionType } from "../../lib/types";

interface BankReviewPanelProps {
  questions: BankQuestionCreate[];
  onQuestionsChange: (questions: BankQuestionCreate[]) => void;
  defaultCategory: string;
  isSaving: boolean;
  onSaveToBank: () => Promise<void>;
  onBackToStep2: () => void;
}

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
}: BankReviewPanelProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);

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
      questionText: "Câu hỏi mới",
      questionType: "single_choice",
      category: defaultCategory,
      difficulty: "medium",
      explanation: "",
      options: [
        { optionText: "Đáp án A", isCorrect: true, orderNum: 0 },
        { optionText: "Đáp án B", isCorrect: false, orderNum: 1 },
        { optionText: "Đáp án C", isCorrect: false, orderNum: 2 },
        { optionText: "Đáp án D", isCorrect: false, orderNum: 3 },
      ],
    };
    const next = [...questions, newQ];
    onQuestionsChange(next);
    setExpandedIdx(next.length - 1);
  };

  const letters = ["A", "B", "C", "D", "E", "F"];

  const isValid = questions.length > 0 && questions.every((q) => {
    return (
      q.questionText.trim().length > 0 &&
      q.options.length >= 2 &&
      q.options.some((o) => o.isCorrect)
    );
  });

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-indigo-600" />
          <div>
            <h2 className="text-sm font-bold text-zinc-900 dark:text-white">
              Duyệt & Lưu vào Thư viện câu hỏi
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {questions.length} câu hỏi được trích xuất — Kiểm tra và chỉnh sửa trước khi lưu
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="btn-bank-review-back"
            type="button"
            onClick={onBackToStep2}
            disabled={isSaving}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại
          </button>
          <button
            id="btn-add-bank-question"
            type="button"
            onClick={addNewQuestion}
            disabled={isSaving}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <Plus className="h-3.5 w-3.5" />
            Thêm câu hỏi
          </button>
          <button
            id="btn-save-to-bank"
            type="button"
            onClick={onSaveToBank}
            disabled={isSaving || !isValid}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSaving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Database className="h-3.5 w-3.5" />
            )}
            {isSaving ? "Đang lưu..." : "Lưu vào Thư viện"}
            {!isSaving && <ArrowRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Question list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {questions.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-400">
            <Database className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm font-medium">Không có câu hỏi nào</p>
            <p className="text-xs mt-1">Nhấn "Thêm câu hỏi" để tạo câu hỏi mới</p>
          </div>
        )}
        {questions.map((q, qIdx) => {
          const isExpanded = expandedIdx === qIdx;
          const hasError =
            q.questionText.trim().length === 0 ||
            q.options.length < 2 ||
            !q.options.some((o) => o.isCorrect);

          return (
            <div
              key={qIdx}
              className={`rounded-xl border bg-white shadow-xs transition-all dark:bg-zinc-900 ${
                hasError
                  ? "border-red-200 dark:border-red-800"
                  : isExpanded
                  ? "border-indigo-200 dark:border-indigo-800"
                  : "border-zinc-200 dark:border-zinc-800"
              }`}
            >
              {/* Question header */}
              <div
                className="flex cursor-pointer items-center gap-3 px-4 py-3 select-none"
                onClick={() => setExpandedIdx(isExpanded ? null : qIdx)}
              >
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    hasError
                      ? "bg-red-100 text-red-600 dark:bg-red-900/40"
                      : "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300"
                  }`}
                >
                  {qIdx + 1}
                </span>
                <p className="flex-1 text-sm font-medium text-zinc-900 dark:text-zinc-100 line-clamp-1">
                  {q.questionText || <span className="text-zinc-400 italic">Chưa có nội dung câu hỏi</span>}
                </p>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                      DIFFICULTY_COLORS[q.difficulty ?? "medium"]
                    }`}
                  >
                    {DIFFICULTY_LABELS[q.difficulty ?? "medium"]}
                  </span>
                  <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[10px] font-medium text-zinc-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400">
                    {q.category}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteQuestion(qIdx);
                    }}
                    className="ml-1 text-zinc-400 hover:text-red-500 transition-colors"
                    title="Xóa câu hỏi"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-zinc-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-zinc-400" />
                  )}
                </div>
              </div>

              {/* Expanded edit */}
              {isExpanded && (
                <div className="border-t border-zinc-100 px-4 py-4 space-y-4 dark:border-zinc-800">
                  {/* Question text */}
                  <div>
                    <label className="block mb-1 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      Nội dung câu hỏi
                    </label>
                    <textarea
                      value={q.questionText}
                      onChange={(e) => updateQuestion(qIdx, { questionText: e.target.value })}
                      rows={2}
                      className="w-full resize-none rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100"
                    />
                  </div>

                  {/* Category & Difficulty */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block mb-1 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                        Danh mục
                      </label>
                      <input
                        type="text"
                        value={q.category}
                        onChange={(e) => updateQuestion(qIdx, { category: e.target.value })}
                        className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                        Độ khó
                      </label>
                      <select
                        value={q.difficulty ?? "medium"}
                        onChange={(e) => updateQuestion(qIdx, { difficulty: e.target.value as Difficulty })}
                        className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100"
                      >
                        <option value="easy">Dễ</option>
                        <option value="medium">Trung bình</option>
                        <option value="hard">Khó</option>
                      </select>
                    </div>
                  </div>

                  {/* Options */}
                  <div>
                    <label className="block mb-2 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      Đáp án
                    </label>
                    <div className="space-y-2">
                      {q.options.map((opt, oIdx) => (
                        <div key={oIdx} className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setCorrectOption(qIdx, oIdx)}
                            title={opt.isCorrect ? "Đáp án đúng" : "Đánh dấu đúng"}
                            className={`shrink-0 transition-colors ${
                              opt.isCorrect
                                ? "text-emerald-500"
                                : "text-zinc-300 hover:text-emerald-400"
                            }`}
                          >
                            <CheckCircle2 className="h-5 w-5" />
                          </button>
                          <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-100 text-[10px] font-bold text-zinc-500 dark:bg-zinc-800">
                            {letters[oIdx] ?? oIdx + 1}
                          </span>
                          <input
                            type="text"
                            value={opt.optionText}
                            onChange={(e) => updateOptionText(qIdx, oIdx, e.target.value)}
                            className={`flex-1 rounded-lg border px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:bg-zinc-800/60 dark:text-zinc-100 ${
                              opt.isCorrect
                                ? "border-emerald-300 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/20"
                                : "border-zinc-200 bg-zinc-50 dark:border-zinc-700"
                            }`}
                          />
                          {q.options.length > 2 && (
                            <button
                              type="button"
                              onClick={() => deleteOption(qIdx, oIdx)}
                              className="shrink-0 text-zinc-300 hover:text-red-400 transition-colors"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      ))}
                      {q.options.length < 6 && (
                        <button
                          type="button"
                          onClick={() => addOption(qIdx)}
                          className="flex items-center gap-1 text-xs text-zinc-400 hover:text-indigo-600 transition-colors"
                        >
                          <Plus className="h-3.5 w-3.5" />
                          Thêm đáp án
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Explanation */}
                  <div>
                    <label className="block mb-1 text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      Lời giải thích (tùy chọn)
                    </label>
                    <textarea
                      value={q.explanation ?? ""}
                      onChange={(e) => updateQuestion(qIdx, { explanation: e.target.value })}
                      rows={1}
                      placeholder="Nhập lời giải thích cho câu hỏi..."
                      className="w-full resize-none rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-500 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-400 placeholder:text-zinc-300"
                    />
                  </div>

                  {/* Error hint */}
                  {hasError && (
                    <p className="text-xs text-red-500 font-medium">
                      ⚠ Câu hỏi phải có nội dung, ít nhất 2 đáp án và 1 đáp án đúng.
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom save bar */}
      {questions.length > 0 && (
        <div className="border-t border-zinc-200 bg-white/90 backdrop-blur-md px-6 py-3 dark:border-zinc-800 dark:bg-zinc-900/90">
          <div className="flex items-center justify-between">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {questions.filter((q) => q.options.some((o) => o.isCorrect)).length}/{questions.length} câu hỏi hợp lệ
            </p>
            <button
              id="btn-save-to-bank-bottom"
              type="button"
              onClick={onSaveToBank}
              disabled={isSaving || !isValid}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-bold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Database className="h-4 w-4" />
              )}
              {isSaving ? "Đang lưu vào Thư viện..." : `Lưu ${questions.length} câu vào Thư viện`}
              {!isSaving && <ArrowRight className="h-4 w-4" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
