"use client";

import React from "react";
import {
  Plus,
  Trash2,
  Copy,
  CheckCircle2,
  HelpCircle,
  Save,
  Play,
  ArrowLeft,
  Loader2,
  FileCheck,
} from "lucide-react";
import { QuestionEdit } from "../../lib/types";

interface QuizEditorProps {
  questions: QuestionEdit[];
  onQuestionsChange: (questions: QuestionEdit[]) => void;
  title: string;
  category: string;
  onBackToStep2: () => void;
  onSaveToLibrary: () => Promise<void>;
  onSaveAndPlay: () => Promise<void>;
  isSaving: boolean;
}

export function QuizEditor({
  questions,
  onQuestionsChange,
  title,
  category,
  onBackToStep2,
  onSaveToLibrary,
  onSaveAndPlay,
  isSaving,
}: QuizEditorProps) {
  const letters = ["A", "B", "C", "D", "E", "F", "G", "H"];

  // Update a question field
  const handleUpdateQuestion = (index: number, updates: Partial<QuestionEdit>) => {
    const next = [...questions];
    next[index] = { ...next[index], ...updates };
    onQuestionsChange(next);
  };

  // Update an option inside a question
  const handleUpdateOption = (
    qIndex: number,
    oIndex: number,
    newText: string
  ) => {
    const next = [...questions];
    const opts = [...next[qIndex].options];
    opts[oIndex] = { ...opts[oIndex], optionText: newText };
    next[qIndex] = { ...next[qIndex], options: opts };
    onQuestionsChange(next);
  };

  // Set the correct option (single choice)
  const handleSelectCorrect = (qIndex: number, oIndex: number) => {
    const next = [...questions];
    const opts = next[qIndex].options.map((opt, i) => ({
      ...opt,
      isCorrect: i === oIndex,
    }));
    next[qIndex] = { ...next[qIndex], options: opts };
    onQuestionsChange(next);
  };

  // Add option to question
  const handleAddOption = (qIndex: number) => {
    const next = [...questions];
    const opts = [
      ...next[qIndex].options,
      { optionText: `Lựa chọn mới`, isCorrect: false },
    ];
    next[qIndex] = { ...next[qIndex], options: opts };
    onQuestionsChange(next);
  };

  // Delete option
  const handleDeleteOption = (qIndex: number, oIndex: number) => {
    const next = [...questions];
    if (next[qIndex].options.length <= 2) return;
    const opts = next[qIndex].options.filter((_, i) => i !== oIndex);
    // Ensure at least one is correct
    if (!opts.some((o) => o.isCorrect) && opts.length > 0) {
      opts[0].isCorrect = true;
    }
    next[qIndex] = { ...next[qIndex], options: opts };
    onQuestionsChange(next);
  };

  // Duplicate question
  const handleDuplicateQuestion = (qIndex: number) => {
    const next = [...questions];
    const target = next[qIndex];
    const duplicated: QuestionEdit = {
      ...target,
      id: crypto.randomUUID(),
      questionText: `${target.questionText} (Bản sao)`,
      options: target.options.map((o) => ({ ...o })),
    };
    next.splice(qIndex + 1, 0, duplicated);
    onQuestionsChange(next);
  };

  // Delete question
  const handleDeleteQuestion = (qIndex: number) => {
    if (questions.length <= 1) return;
    const next = questions.filter((_, i) => i !== qIndex);
    onQuestionsChange(next);
  };

  // Add a brand new empty question
  const handleAddNewQuestion = () => {
    const newQ: QuestionEdit = {
      id: crypto.randomUUID(),
      questionText: "Nhập nội dung câu hỏi tại đây...",
      questionType: "single_choice",
      points: 10,
      explanation: "",
      options: [
        { optionText: "Phương án A", isCorrect: true },
        { optionText: "Phương án B", isCorrect: false },
        { optionText: "Phương án C", isCorrect: false },
        { optionText: "Phương án D", isCorrect: false },
      ],
    };
    onQuestionsChange([...questions, newQ]);
  };

  const totalPoints = questions.reduce((acc, q) => acc + (q.points || 10), 0);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col p-4 sm:p-6 lg:p-8 space-y-6 pb-28">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs dark:border-zinc-800 dark:bg-zinc-900">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-emerald-500 p-1 text-white">
              <FileCheck className="h-4 w-4" />
            </span>
            <h2 className="text-base sm:text-lg font-bold text-zinc-900 dark:text-white">
              {title || "Đề thi trắc nghiệm"}
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-zinc-500 dark:text-zinc-400">
            Chủ đề: <strong className="text-zinc-700 dark:text-zinc-300">{category}</strong> •{" "}
            Tổng cộng <strong className="text-zinc-700 dark:text-zinc-300">{questions.length}</strong> câu hỏi •{" "}
            <strong className="text-zinc-700 dark:text-zinc-300">{totalPoints}</strong> điểm
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleAddNewQuestion}
            className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50/70 px-3.5 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-900/60"
          >
            <Plus className="h-4 w-4" />
            <span>Thêm câu hỏi mới</span>
          </button>
        </div>
      </div>

      {/* Questions Card List */}
      <div className="space-y-6">
        {questions.map((q, qIndex) => (
          <div
            key={q.id || qIndex}
            className="group rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6 shadow-xs transition-all hover:border-zinc-300 hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
          >
            {/* Card Header: Number, points, duplicate, delete */}
            <div className="flex items-center justify-between border-b border-zinc-100 pb-4 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white shadow-xs">
                  {qIndex + 1}
                </span>
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                  Câu hỏi {qIndex + 1}
                </span>
                <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                  Trắc nghiệm 1 đáp án
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* Points */}
                <div className="flex items-center gap-1 text-xs">
                  <span className="text-zinc-400">Điểm:</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={q.points || 10}
                    onChange={(e) =>
                      handleUpdateQuestion(qIndex, {
                        points: parseInt(e.target.value) || 10,
                      })
                    }
                    className="w-14 rounded-lg border border-zinc-200 px-2 py-1 text-center font-bold text-xs text-zinc-800 focus:border-indigo-500 focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                  />
                </div>

                <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-700" />

                {/* Duplicate */}
                <button
                  type="button"
                  onClick={() => handleDuplicateQuestion(qIndex)}
                  title="Nhân bản câu hỏi"
                  className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                >
                  <Copy className="h-4 w-4" />
                </button>

                {/* Delete */}
                <button
                  type="button"
                  disabled={questions.length <= 1}
                  onClick={() => handleDeleteQuestion(qIndex)}
                  title="Xóa câu hỏi này"
                  className="rounded-lg p-1.5 text-zinc-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-30 dark:hover:bg-rose-950/50 dark:hover:text-rose-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Question Text Input */}
            <div className="mt-4 space-y-1.5">
              <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                Nội dung câu hỏi
              </label>
              <textarea
                value={q.questionText}
                onChange={(e) =>
                  handleUpdateQuestion(qIndex, { questionText: e.target.value })
                }
                rows={2}
                placeholder="Nhập câu hỏi..."
                className="w-full rounded-xl border border-zinc-200 p-3 text-sm text-zinc-900 focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-100"
              />
            </div>

            {/* Options List */}
            <div className="mt-4 space-y-2.5">
              <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                Các phương án lựa chọn (Bấm nút tròn để chọn đáp án đúng)
              </label>
              <div className="space-y-2">
                {q.options.map((opt, oIndex) => {
                  const letter = letters[oIndex] || `${oIndex + 1}`;
                  return (
                    <div
                      key={oIndex}
                      className={`flex items-center gap-3 rounded-xl border p-2.5 transition-all ${
                        opt.isCorrect
                          ? "border-emerald-500 bg-emerald-50/50 dark:border-emerald-500 dark:bg-emerald-950/30 ring-1 ring-emerald-500/20"
                          : "border-zinc-200 bg-zinc-50/60 dark:border-zinc-700/80 dark:bg-zinc-800/40"
                      }`}
                    >
                      {/* Correct radio toggle */}
                      <button
                        type="button"
                        onClick={() => handleSelectCorrect(qIndex, oIndex)}
                        title={opt.isCorrect ? "Đáp án đúng" : "Chọn làm đáp án đúng"}
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all ${
                          opt.isCorrect
                            ? "bg-emerald-600 text-white shadow-xs"
                            : "border border-zinc-300 bg-white text-zinc-400 hover:border-zinc-400 dark:border-zinc-600 dark:bg-zinc-800"
                        }`}
                      >
                        {opt.isCorrect ? (
                          <CheckCircle2 className="h-4 w-4 stroke-[3]" />
                        ) : (
                          <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400">
                            {letter}
                          </span>
                        )}
                      </button>

                      {/* Option text input */}
                      <input
                        type="text"
                        value={opt.optionText}
                        onChange={(e) =>
                          handleUpdateOption(qIndex, oIndex, e.target.value)
                        }
                        placeholder={`Nội dung phương án ${letter}...`}
                        className={`flex-1 bg-transparent text-xs sm:text-sm font-medium focus:outline-hidden ${
                          opt.isCorrect
                            ? "text-emerald-950 dark:text-emerald-100 font-semibold"
                            : "text-zinc-800 dark:text-zinc-200"
                        }`}
                      />

                      {/* Delete Option button */}
                      {q.options.length > 2 && (
                        <button
                          type="button"
                          onClick={() => handleDeleteOption(qIndex, oIndex)}
                          title="Xóa lựa chọn này"
                          className="rounded-lg p-1 text-zinc-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/50 dark:hover:text-rose-400"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Add option button */}
              {q.options.length < 6 && (
                <button
                  type="button"
                  onClick={() => handleAddOption(qIndex)}
                  className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Thêm lựa chọn</span>
                </button>
              )}
            </div>

            {/* Explanation */}
            <div className="mt-4 space-y-1.5">
              <div className="flex items-center gap-1.5">
                <HelpCircle className="h-3.5 w-3.5 text-zinc-400" />
                <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                  Giải thích chi tiết (tùy chọn)
                </label>
              </div>
              <textarea
                value={q.explanation || ""}
                onChange={(e) =>
                  handleUpdateQuestion(qIndex, { explanation: e.target.value })
                }
                rows={2}
                placeholder="Giải thích vì sao đáp án này đúng để người làm bài hiểu rõ hơn..."
                className="w-full rounded-xl border border-zinc-200 p-2.5 text-xs text-zinc-800 placeholder:text-zinc-400 focus:border-indigo-500 focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-200"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Add question card bottom button */}
      <button
        type="button"
        onClick={handleAddNewQuestion}
        className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-zinc-200 p-4 text-xs font-bold text-zinc-600 hover:border-indigo-400 hover:bg-indigo-50/40 hover:text-indigo-600 dark:border-zinc-800 dark:text-zinc-400 dark:hover:border-indigo-600 dark:hover:bg-indigo-950/20 dark:hover:text-indigo-300 transition-all cursor-pointer"
      >
        <Plus className="h-4 w-4" />
        <span>+ Thêm câu hỏi mới</span>
      </button>

      {/* ========================================================================= */}
      {/* STICKY BOTTOM ACTION FOOTER                                               */}
      {/* ========================================================================= */}
      <div className="fixed bottom-0 inset-x-0 z-30 border-t border-zinc-200/90 bg-white/95 backdrop-blur-md dark:border-zinc-800/90 dark:bg-zinc-950/95 shadow-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 sm:px-6 py-3">
          {/* Left: Back button & counts */}
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={onBackToStep2}
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-200 px-3.5 py-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-50"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline">Quay lại cấu hình</span>
            </button>

            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              <span>
                <strong>{questions.length}</strong> câu hỏi
              </span>
              <span> • </span>
              <span>
                <strong>{totalPoints}</strong> điểm
              </span>
            </div>
          </div>

          {/* Right: Save actions */}
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onSaveToLibrary}
              disabled={isSaving || questions.length === 0}
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-xs font-bold text-zinc-800 shadow-xs hover:bg-zinc-50 hover:border-zinc-400 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800 active:scale-95"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              ) : (
                <Save className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
              )}
              <span>Lưu vào Thư viện</span>
            </button>

            <button
              type="button"
              onClick={onSaveAndPlay}
              disabled={isSaving || questions.length === 0}
              className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/25 transition-all hover:scale-[1.02] hover:shadow-lg disabled:opacity-50 active:scale-95 cursor-pointer"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                  <span>Đang lưu đề...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  <span>Lưu & Bắt đầu thi</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
