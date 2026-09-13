"use client";

import React, { useState, useEffect } from "react";
import { X, Loader2, Save, AlertCircle } from "lucide-react";
import { BankQuestionSchema, Difficulty } from "../../lib/types";
import { updateBankQuestion } from "../../lib/api-client";

interface EditBankQuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  question: BankQuestionSchema | null;
  onSuccess: (updated: BankQuestionSchema) => void;
}

export function EditBankQuestionModal({
  isOpen,
  onClose,
  question,
  onSuccess,
}: EditBankQuestionModalProps) {
  const [questionText, setQuestionText] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [explanation, setExplanation] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (question) {
      setQuestionText(question.questionText);
      setCategory(question.category);
      setDifficulty(question.difficulty);
      setExplanation(question.explanation || "");
      setError(null);
    }
  }, [question]);

  if (!isOpen || !question) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim()) {
      setError("Nội dung câu hỏi không được để trống.");
      return;
    }
    if (!category.trim()) {
      setError("Môn học / Danh mục không được để trống.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const updated = await updateBankQuestion(question.id, {
        questionText: questionText.trim(),
        category: category.trim(),
        difficulty,
        explanation: explanation.trim() || null,
      });
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Lỗi khi cập nhật câu hỏi."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-xs"
        onClick={isLoading ? undefined : onClose}
      />

      <div className="relative w-full max-w-xl rounded-3xl border border-zinc-200 bg-white p-6 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900 sm:p-8">
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-5 right-5 flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>

        <h3 className="text-xl font-bold text-zinc-900 dark:text-white">
          Chỉnh Sửa Câu Hỏi Ngân Hàng
        </h3>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase text-zinc-600 dark:text-zinc-300 mb-1">
              Nội dung câu hỏi
            </label>
            <textarea
              rows={3}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold uppercase text-zinc-600 dark:text-zinc-300 mb-1">
                Môn học / Danh mục
              </label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-zinc-600 dark:text-zinc-300 mb-1">
                Độ khó
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as Difficulty)}
                disabled={isLoading}
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
              >
                <option value="easy">Dễ</option>
                <option value="medium">Trung bình</option>
                <option value="hard">Khó</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-zinc-600 dark:text-zinc-300 mb-1">
              Lời giải thích chi tiết (tùy chọn)
            </label>
            <textarea
              rows={2}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              disabled={isLoading}
              placeholder="Giải thích tại sao đáp án đúng..."
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
            />
          </div>

          <div className="mt-6 flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-md hover:bg-indigo-500 disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              <span>Lưu Thay Đổi</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
