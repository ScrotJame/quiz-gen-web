"use client";

import React, { useState, useMemo } from "react";
import {
  X,
  Sparkles,
  Loader2,
  AlertTriangle,
  Minus,
  Plus,
  Dices,
} from "lucide-react";
import { generateBankMatrix } from "../../lib/api-client";
import { BankMatrixGenerateResponse } from "../../lib/types";

interface MatrixGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: string[];
  onSuccess: (res: BankMatrixGenerateResponse, categoryName: string) => void;
}

export function MatrixGenerateModal({
  isOpen,
  onClose,
  categories,
  onSuccess,
}: MatrixGenerateModalProps) {
  const [category, setCategory] = useState<string>("");
  const [easyCount, setEasyCount] = useState<number>(5);
  const [mediumCount, setMediumCount] = useState<number>(3);
  const [hardCount, setHardCount] = useState<number>(2);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const totalQuestions = useMemo(
    () => easyCount + mediumCount + hardCount,
    [easyCount, mediumCount, hardCount]
  );

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (totalQuestions <= 0) {
      setErrorMessage("Vui lòng chọn ít nhất 1 câu hỏi để sinh đề.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await generateBankMatrix({
        category: category || null,
        easyCount,
        mediumCount,
        hardCount,
      });

      if (res.questions.length === 0) {
        setErrorMessage(
          "Không tìm thấy câu hỏi nào thỏa mãn tiêu chí đã chọn trong kho."
        );
        setIsLoading(false);
        return;
      }

      onSuccess(res, category || "Tổng hợp");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Đã có lỗi xảy ra khi sinh đề.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={isLoading ? undefined : onClose}
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-zinc-200/80 bg-white p-6 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900 sm:p-8">
        {/* Ambient Glow */}
        <div className="pointer-events-none absolute -top-16 -right-16 h-40 w-40 rounded-full bg-indigo-500/15 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-16 -left-16 h-40 w-40 rounded-full bg-purple-500/15 blur-2xl" />

        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-5 right-5 flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 transition-colors disabled:opacity-50"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-500/25">
            <Dices className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-black text-zinc-900 dark:text-white tracking-tight">
              Tạo Đề Thi Theo Ma Trận
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Bốc ngẫu nhiên câu hỏi từ Ngân hàng theo tỷ lệ độ khó
            </p>
          </div>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Form Body */}
        <div className="mt-6 space-y-5">
          {/* Môn học / Danh mục */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-300 mb-1.5">
              Môn học / Danh mục
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isLoading}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2.5 text-sm font-medium text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-white transition-colors"
            >
              <option value="">Tất cả môn học</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Cấu hình số câu theo độ khó */}
          <div className="space-y-3 rounded-2xl border border-zinc-200/80 bg-zinc-50/60 p-4 dark:border-zinc-800/80 dark:bg-zinc-800/30">
            <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-zinc-600 dark:text-zinc-300">
              <span>Phân bổ số lượng câu hỏi</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-extrabold">
                Tổng: {totalQuestions} câu
              </span>
            </div>

            {/* Câu Dễ */}
            <div className="flex items-center justify-between rounded-xl bg-white p-2.5 shadow-2xs border border-zinc-100 dark:bg-zinc-900 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20" />
                <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  Mức Dễ
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setEasyCount((c) => Math.max(0, c - 1))}
                  disabled={isLoading || easyCount <= 0}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={easyCount}
                  onChange={(e) =>
                    setEasyCount(Math.max(0, parseInt(e.target.value) || 0))
                  }
                  disabled={isLoading}
                  className="w-12 text-center text-sm font-bold text-zinc-900 dark:text-white bg-transparent focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={() => setEasyCount((c) => c + 1)}
                  disabled={isLoading}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Câu Trung Bình */}
            <div className="flex items-center justify-between rounded-xl bg-white p-2.5 shadow-2xs border border-zinc-100 dark:bg-zinc-900 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-amber-500 ring-2 ring-amber-500/20" />
                <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  Mức Trung Bình
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setMediumCount((c) => Math.max(0, c - 1))}
                  disabled={isLoading || mediumCount <= 0}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={mediumCount}
                  onChange={(e) =>
                    setMediumCount(Math.max(0, parseInt(e.target.value) || 0))
                  }
                  disabled={isLoading}
                  className="w-12 text-center text-sm font-bold text-zinc-900 dark:text-white bg-transparent focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={() => setMediumCount((c) => c + 1)}
                  disabled={isLoading}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Câu Khó */}
            <div className="flex items-center justify-between rounded-xl bg-white p-2.5 shadow-2xs border border-zinc-100 dark:bg-zinc-900 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-rose-500 ring-2 ring-rose-500/20" />
                <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  Mức Khó
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setHardCount((c) => Math.max(0, c - 1))}
                  disabled={isLoading || hardCount <= 0}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={hardCount}
                  onChange={(e) =>
                    setHardCount(Math.max(0, parseInt(e.target.value) || 0))
                  }
                  disabled={isLoading}
                  className="w-12 text-center text-sm font-bold text-zinc-900 dark:text-white bg-transparent focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={() => setHardCount((c) => c + 1)}
                  disabled={isLoading}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 disabled:opacity-40"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="mt-8 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="rounded-xl border border-zinc-200 px-4 py-2.5 text-sm font-semibold text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
          >
            Hủy
          </button>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={isLoading || totalQuestions <= 0}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 px-6 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-600/30 hover:opacity-95 active:scale-98 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang bốc câu hỏi...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Sinh Đề Thi Ngay</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
