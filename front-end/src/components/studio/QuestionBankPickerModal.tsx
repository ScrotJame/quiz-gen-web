"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  Search,
  X,
} from "lucide-react";
import { BankQuestionSchema, Difficulty, QuestionEdit } from "../../lib/types";
import { getBankCategories, getBankQuestions } from "../../lib/api-client";

interface QuestionBankPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddQuestions: (questions: QuestionEdit[]) => void;
  /** IDs đã có trong đề thi hiện tại để không chọn trùng */
  existingQuestionTexts?: Set<string>;
}

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "Dễ",
  medium: "TB",
  hard: "Khó",
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  hard: "bg-red-50 text-red-700 border-red-200",
};

function bankToQuestionEdit(q: BankQuestionSchema): QuestionEdit {
  return {
    id: `bank_${q.id}_${crypto.randomUUID()}`,
    questionText: q.questionText,
    questionType: q.questionType,
    points: 10,
    explanation: q.explanation ?? "",
    options: q.options.map((opt) => ({
      optionText: opt.optionText,
      isCorrect: opt.isCorrect,
    })),
  };
}

export function QuestionBankPickerModal({
  isOpen,
  onClose,
  onAddQuestions,
  existingQuestionTexts = new Set(),
}: QuestionBankPickerModalProps) {
  const [questions, setQuestions] = useState<BankQuestionSchema[]>([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [page, setPage] = useState(1);
  const limit = 10;

  const [selected, setSelected] = useState<Set<string>>(new Set());

  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchQuestions = useCallback(
    async (params: { search?: string; category?: string; difficulty?: string; page?: number }) => {
      setIsLoading(true);
      try {
        const res = await getBankQuestions({
          search: params.search,
          category: params.category || undefined,
          difficulty: params.difficulty || undefined,
          page: params.page ?? 1,
          limit,
        });
        setQuestions(res.items);
        setTotal(res.total);
      } catch {
        setQuestions([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    },
    [limit]
  );

  // Load on open
  useEffect(() => {
    if (!isOpen) return;
    setSelected(new Set());
    setPage(1);
    setSearchInput("");
    setCategory("");
    setDifficulty("");

    getBankCategories()
      .then((res) => setCategories(res.categories))
      .catch(() => setCategories([]));

    fetchQuestions({});
  }, [isOpen, fetchQuestions]);

  // Re-fetch on filter/page change
  useEffect(() => {
    if (!isOpen) return;
    fetchQuestions({ search: searchInput, category, difficulty, page });
  }, [category, difficulty, page, isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearchChange = (val: string) => {
    setSearchInput(val);
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    searchDebounce.current = setTimeout(() => {
      setPage(1);
      fetchQuestions({ search: val, category, difficulty, page: 1 });
    }, 400);
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAddSelected = () => {
    const picked = questions.filter((q) => selected.has(q.id));
    onAddQuestions(picked.map(bankToQuestionEdit));
    onClose();
  };

  const totalPages = Math.ceil(total / limit);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="flex flex-col w-full max-w-3xl max-h-[90vh] rounded-2xl border border-zinc-200 bg-white shadow-2xl dark:border-zinc-700 dark:bg-zinc-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-indigo-600" />
            <div>
              <h2 className="text-sm font-bold text-zinc-900 dark:text-white">
                Chọn câu hỏi từ Thư viện
              </h2>
              <p className="text-xs text-zinc-500">
                {total} câu hỏi trong kho · {selected.size} đã chọn
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-zinc-200 p-1.5 text-zinc-500 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 border-b border-zinc-100 px-6 py-3 dark:border-zinc-800">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400" />
            <input
              id="bank-picker-search"
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Tìm kiếm câu hỏi..."
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 pl-9 pr-3 py-1.5 text-sm text-zinc-900 focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
            />
          </div>
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
            className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-700 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="">Tất cả danh mục</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={difficulty}
            onChange={(e) => { setDifficulty(e.target.value); setPage(1); }}
            className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-700 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="">Tất cả độ khó</option>
            <option value="easy">Dễ</option>
            <option value="medium">Trung bình</option>
            <option value="hard">Khó</option>
          </select>
        </div>

        {/* Question list */}
        <div className="flex-1 overflow-y-auto px-6 py-3 space-y-2">
          {isLoading && (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
            </div>
          )}
          {!isLoading && questions.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-400">
              <Database className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">Không tìm thấy câu hỏi nào</p>
            </div>
          )}
          {!isLoading && questions.map((q) => {
            const isSelected = selected.has(q.id);
            const isAlreadyAdded = existingQuestionTexts.has(q.questionText.trim());

            return (
              <div
                key={q.id}
                onClick={() => !isAlreadyAdded && toggleSelect(q.id)}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-all ${
                  isAlreadyAdded
                    ? "cursor-not-allowed border-zinc-100 bg-zinc-50 opacity-50 dark:border-zinc-800 dark:bg-zinc-900/50"
                    : isSelected
                    ? "border-indigo-300 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950/30"
                    : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
                }`}
              >
                <div
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-500"
                      : "border-zinc-300 dark:border-zinc-600"
                  }`}
                >
                  {isSelected && <Check className="h-3 w-3 text-white stroke-[3]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 line-clamp-2">
                    {q.questionText}
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[10px] font-medium text-zinc-500 dark:border-zinc-700 dark:bg-zinc-800">
                      {q.category}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                        DIFFICULTY_COLORS[q.difficulty] ?? ""
                      }`}
                    >
                      {DIFFICULTY_LABELS[q.difficulty] ?? q.difficulty}
                    </span>
                    <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[10px] text-zinc-400 dark:border-zinc-700 dark:bg-zinc-800">
                      {q.options.length} đáp án
                    </span>
                    {isAlreadyAdded && (
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-600">
                        Đã có trong đề
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 border-t border-zinc-100 px-6 py-3 dark:border-zinc-800">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-zinc-200 p-1.5 text-zinc-500 hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs text-zinc-500">
              Trang {page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-zinc-200 p-1.5 text-zinc-500 hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400"
          >
            Hủy
          </button>
          <button
            id="btn-bank-picker-add"
            type="button"
            disabled={selected.size === 0}
            onClick={handleAddSelected}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-bold text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <Check className="h-4 w-4" />
            Thêm {selected.size > 0 ? `${selected.size} câu` : ""} vào đề thi
          </button>
        </div>
      </div>
    </div>
  );
}
