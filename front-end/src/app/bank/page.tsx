"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Database,
  Search,
  Dices,
  PlusCircle,
  Filter,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
  ChevronLeft,
  ChevronRight,
  ArrowRight,
  Sparkles,
  Loader2,
  AlertCircle,
  X,
  CheckCircle2,
} from "lucide-react";
import { Navbar } from "../../components/layout/Navbar";
import { MatrixGenerateModal } from "../../components/bank/MatrixGenerateModal";
import { EditBankQuestionModal } from "../../components/bank/EditBankQuestionModal";
import {
  getBankQuestions,
  getBankCategories,
  deleteBankQuestion,
} from "../../lib/api-client";
import {
  BankQuestionSchema,
  BankMatrixGenerateResponse,
  Difficulty,
} from "../../lib/types";

const DIFFICULTY_CONFIG: Record<
  string,
  { label: string; badgeClass: string; dotClass: string }
> = {
  easy: {
    label: "Dễ",
    badgeClass:
      "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800/40",
    dotClass: "bg-emerald-500",
  },
  medium: {
    label: "Trung bình",
    badgeClass:
      "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/40",
    dotClass: "bg-amber-500",
  },
  hard: {
    label: "Khó",
    badgeClass:
      "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800/40",
    dotClass: "bg-rose-500",
  },
};

export default function QuestionBankPage() {
  const router = useRouter();

  const [questions, setQuestions] = useState<BankQuestionSchema[]>([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [page, setPage] = useState(1);
  const limit = 15;

  // Selections
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Modals
  const [isMatrixOpen, setIsMatrixOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] =
    useState<BankQuestionSchema | null>(null);

  // Toast / notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch Questions
  const loadQuestions = useCallback(
    async (params: {
      search?: string;
      category?: string;
      difficulty?: string;
      page?: number;
    }) => {
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
      } catch (err) {
        console.error("Lỗi tải câu hỏi:", err);
      } finally {
        setIsLoading(false);
      }
    },
    [limit]
  );

  // Initial Load & Categories
  useEffect(() => {
    getBankCategories()
      .then((res) => setCategories(res.categories))
      .catch((err) => console.error("Lỗi nạp danh mục:", err));
    loadQuestions({ page: 1 });
  }, [loadQuestions]);

  // Debounced Search Handler
  const handleSearchChange = (val: string) => {
    setSearch(val);
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    searchDebounce.current = setTimeout(() => {
      setPage(1);
      loadQuestions({ search: val, category, difficulty, page: 1 });
    }, 300);
  };

  const handleCategoryChange = (val: string) => {
    setCategory(val);
    setPage(1);
    loadQuestions({ search, category: val, difficulty, page: 1 });
  };

  const handleDifficultyChange = (val: string) => {
    setDifficulty(val);
    setPage(1);
    loadQuestions({ search, category, difficulty: val, page: 1 });
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    loadQuestions({ search, category, difficulty, page: newPage });
  };

  // Toggle selection
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllCurrentPage = () => {
    const allPageIds = questions.map((q) => q.id);
    const allSelected = allPageIds.every((id) => selectedIds.has(id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        allPageIds.forEach((id) => next.delete(id));
      } else {
        allPageIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Delete question
  const handleDelete = async (q: BankQuestionSchema) => {
    if (
      !confirm(
        `Bạn có chắc chắn muốn xóa câu hỏi này khỏi kho?\n"${q.questionText.slice(
          0,
          60
        )}..."`
      )
    ) {
      return;
    }

    try {
      await deleteBankQuestion(q.id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(q.id);
        return next;
      });
      loadQuestions({ search, category, difficulty, page });
      setToastMessage("Đã xóa câu hỏi thành công.");
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      alert("Không thể xóa câu hỏi: " + (err as Error).message);
    }
  };

  // Create Quiz from selected questions
  const handleCreateFromSelected = () => {
    const selectedQuestions = questions.filter((q) => selectedIds.has(q.id));
    if (selectedQuestions.length === 0) return;

    // Stage in sessionStorage
    sessionStorage.setItem(
      "quiz_bank_staging",
      JSON.stringify({
        questions: selectedQuestions,
        category: selectedQuestions[0]?.category || "Tổng hợp",
        source: "manual_selection",
        warnings: [],
      })
    );

    router.push("/create/from-bank");
  };

  // Create Quiz from Matrix
  const handleMatrixSuccess = (
    res: BankMatrixGenerateResponse,
    categoryName: string
  ) => {
    setIsMatrixOpen(false);

    sessionStorage.setItem(
      "quiz_bank_staging",
      JSON.stringify({
        questions: res.questions,
        category: categoryName || "Tổng hợp",
        source: "matrix_generate",
        warnings: res.warnings,
      })
    );

    router.push("/create/from-bank");
  };

  const totalPages = Math.ceil(total / limit) || 1;
  const isAllCurrentPageSelected =
    questions.length > 0 && questions.every((q) => selectedIds.has(q.id));

  return (
    <div className="min-h-screen bg-zinc-50/80 text-zinc-900 selection:bg-indigo-500 selection:text-white dark:bg-zinc-950 dark:text-zinc-100 flex flex-col pb-24">
      <Navbar />

      {/* Notification Toast */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 flex items-center gap-2 rounded-2xl bg-zinc-900 px-4 py-3 text-sm font-semibold text-white shadow-xl dark:bg-zinc-100 dark:text-zinc-900 animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 dark:text-emerald-600" />
          <span>{toastMessage}</span>
        </div>
      )}

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* ========================================================================= */}
        {/* HEADER SECTION                                                            */}
        {/* ========================================================================= */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-500/25">
                <Database className="h-5 w-5" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-zinc-900 dark:text-white">
                Ngân Hàng Câu Hỏi
              </h1>
              <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800">
                {total} câu hỏi
              </span>
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Quản lý kho câu hỏi đã lưu, chọn câu hỏi hoặc tạo đề thi tự động
              theo ma trận.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* Tạo đề theo Ma trận Button */}
            <button
              onClick={() => setIsMatrixOpen(true)}
              className="group inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-600/30 hover:opacity-95 active:scale-98 transition-all cursor-pointer"
            >
              <Dices className="h-4 w-4 transition-transform group-hover:rotate-45" />
              <span>Tạo Đề Theo Ma Trận</span>
            </button>

            {/* Quét OCR thêm câu hỏi */}
            <Link
              href="/create/ocr"
              className="inline-flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-800 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800/80 transition-colors shadow-2xs"
            >
              <PlusCircle className="h-4 w-4 text-indigo-500" />
              <span className="hidden sm:inline">Quét Ảnh Thêm Câu</span>
            </Link>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* FILTER & SEARCH TOOLBAR                                                  */}
        {/* ========================================================================= */}
        <div className="grid grid-cols-1 gap-3 rounded-2xl border border-zinc-200/80 bg-white p-4 shadow-xs dark:border-zinc-800/80 dark:bg-zinc-900/80 sm:grid-cols-12 sm:items-center">
          {/* Search Input */}
          <div className="relative sm:col-span-5">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="Tìm kiếm nội dung câu hỏi..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 pl-9 pr-4 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white transition-colors"
            />
          </div>

          {/* Category Filter */}
          <div className="sm:col-span-4">
            <select
              value={category}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm font-medium text-zinc-800 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 transition-colors"
            >
              <option value="">Tất cả môn học ({categories.length})</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Difficulty Filter */}
          <div className="sm:col-span-3">
            <select
              value={difficulty}
              onChange={(e) => handleDifficultyChange(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm font-medium text-zinc-800 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 transition-colors"
            >
              <option value="">Tất cả độ khó</option>
              <option value="easy">Dễ</option>
              <option value="medium">Trung bình</option>
              <option value="hard">Khó</option>
            </select>
          </div>
        </div>

        {/* Select all bar */}
        <div className="flex items-center justify-between px-1 text-xs font-semibold text-zinc-500 dark:text-zinc-400">
          <button
            onClick={selectAllCurrentPage}
            className="flex items-center gap-2 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            {isAllCurrentPageSelected ? (
              <CheckSquare className="h-4 w-4 text-indigo-600" />
            ) : (
              <Square className="h-4 w-4" />
            )}
            <span>
              {isAllCurrentPageSelected
                ? "Bỏ chọn tất cả trên trang này"
                : "Chọn tất cả trên trang này"}
            </span>
          </button>

          <span>
            Trang {page} / {totalPages} (Hiển thị {questions.length} câu)
          </span>
        </div>

        {/* ========================================================================= */}
        {/* QUESTIONS LIST                                                            */}
        {/* ========================================================================= */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-400">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm">Đang tải danh sách câu hỏi...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-zinc-300 py-16 text-center dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/30">
            <Database className="h-12 w-12 text-zinc-300 dark:text-zinc-700 mb-3" />
            <h3 className="text-base font-bold text-zinc-700 dark:text-zinc-300">
              Không tìm thấy câu hỏi nào
            </h3>
            <p className="mt-1 max-w-sm text-xs text-zinc-500 dark:text-zinc-400">
              {search || category || difficulty
                ? "Hãy thử điều chỉnh bộ lọc hoặc từ khóa tìm kiếm."
                : "Kho câu hỏi đang trống. Hãy quét tài liệu bằng OCR để nạp câu hỏi vào kho."}
            </p>
            {!(search || category || difficulty) && (
              <Link
                href="/create/ocr"
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500"
              >
                <PlusCircle className="h-4 w-4" />
                Quét ảnh ngay
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {questions.map((q, idx) => {
              const isSelected = selectedIds.has(q.id);
              const isExpanded = expandedIds.has(q.id);
              const diffConfig =
                DIFFICULTY_CONFIG[q.difficulty] || DIFFICULTY_CONFIG.medium;

              return (
                <div
                  key={q.id}
                  className={`group relative overflow-hidden rounded-2xl border transition-all ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-50/20 shadow-md dark:border-indigo-500/60 dark:bg-indigo-950/20"
                      : "border-zinc-200/80 bg-white hover:border-zinc-300 shadow-2xs dark:border-zinc-800/80 dark:bg-zinc-900/90 dark:hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-start gap-3 p-4 sm:p-5">
                    {/* Checkbox */}
                    <button
                      type="button"
                      onClick={() => toggleSelect(q.id)}
                      className="mt-1 shrink-0 text-zinc-400 hover:text-indigo-600 dark:hover:text-indigo-400"
                    >
                      {isSelected ? (
                        <CheckSquare className="h-5 w-5 text-indigo-600" />
                      ) : (
                        <Square className="h-5 w-5" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Index */}
                        <span className="font-mono text-xs font-bold text-zinc-400">
                          #{(page - 1) * limit + idx + 1}
                        </span>

                        {/* Category Badge */}
                        <span className="rounded-lg bg-zinc-100 px-2 py-0.5 text-xs font-semibold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 border border-zinc-200/60 dark:border-zinc-700/60">
                          {q.category}
                        </span>

                        {/* Difficulty Badge */}
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-xs font-semibold ${diffConfig.badgeClass}`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${diffConfig.dotClass}`}
                          />
                          {diffConfig.label}
                        </span>

                        {/* Options count */}
                        <span className="text-[11px] text-zinc-400">
                          {q.options.length} đáp án
                        </span>
                      </div>

                      {/* Question Text */}
                      <p className="text-sm sm:text-base font-semibold text-zinc-900 dark:text-zinc-100 leading-relaxed">
                        {q.questionText}
                      </p>

                      {/* Expand / Collapse Button */}
                      <button
                        type="button"
                        onClick={() => toggleExpand(q.id)}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                      >
                        <span>
                          {isExpanded
                            ? "Ẩn đáp án & giải thích"
                            : "Xem đáp án & giải thích"}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5" />
                        )}
                      </button>

                      {/* Expanded Options & Explanation */}
                      {isExpanded && (
                        <div className="mt-3 space-y-2.5 rounded-xl border border-zinc-200/60 bg-zinc-50/80 p-3.5 dark:border-zinc-800/80 dark:bg-zinc-950/50">
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {q.options.map((opt, oIdx) => (
                              <div
                                key={opt.id || oIdx}
                                className={`flex items-center gap-2 rounded-lg border p-2.5 text-xs font-medium ${
                                  opt.isCorrect
                                    ? "border-emerald-200 bg-emerald-50/80 text-emerald-800 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-300 font-bold"
                                    : "border-zinc-200 bg-white text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
                                }`}
                              >
                                <span
                                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                                    opt.isCorrect
                                      ? "bg-emerald-500 text-white"
                                      : "bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
                                  }`}
                                >
                                  {String.fromCharCode(65 + oIdx)}
                                </span>
                                <span className="flex-1">{opt.optionText}</span>
                              </div>
                            ))}
                          </div>

                          {q.explanation && (
                            <div className="text-xs text-zinc-600 dark:text-zinc-400 pt-1 border-t border-zinc-200/60 dark:border-zinc-800/60">
                              <span className="font-bold text-zinc-700 dark:text-zinc-300">
                                Lời giải:{" "}
                              </span>
                              {q.explanation}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => setEditingQuestion(q)}
                        className="flex h-8 w-8 items-center justify-center rounded-xl text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 transition-colors"
                        title="Chỉnh sửa câu hỏi"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(q)}
                        className="flex h-8 w-8 items-center justify-center rounded-xl text-zinc-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/30 dark:hover:text-rose-400 transition-colors"
                        title="Xóa câu hỏi"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ========================================================================= */}
        {/* PAGINATION CONTROLS                                                       */}
        {/* ========================================================================= */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-4">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
              className="flex h-9 items-center gap-1 rounded-xl border border-zinc-200 bg-white px-3 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Trước</span>
            </button>

            <span className="text-xs font-bold text-zinc-600 dark:text-zinc-400 px-2">
              {page} / {totalPages}
            </span>

            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages}
              className="flex h-9 items-center gap-1 rounded-xl border border-zinc-200 bg-white px-3 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
            >
              <span>Sau</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </main>

      {/* ========================================================================= */}
      {/* FLOATING ACTION BAR (When items selected)                                 */}
      {/* ========================================================================= */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 inset-x-0 z-40 flex justify-center px-4 animate-in slide-in-from-bottom-6">
          <div className="flex items-center gap-3 sm:gap-6 rounded-3xl border border-indigo-200/80 bg-zinc-900/95 px-5 py-3.5 text-white shadow-2xl shadow-indigo-950/40 backdrop-blur-md dark:border-indigo-800/80 dark:bg-zinc-900/95">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-500 font-mono text-xs font-black">
                {selectedIds.size}
              </span>
              <span className="text-sm font-bold text-zinc-100 hidden sm:inline">
                câu hỏi đã chọn
              </span>
            </div>

            <div className="h-4 w-px bg-zinc-700 hidden sm:block" />

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={clearSelection}
                className="rounded-xl px-3 py-1.5 text-xs font-semibold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                Bỏ chọn
              </button>

              <button
                type="button"
                onClick={handleCreateFromSelected}
                className="group flex items-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 px-5 py-2 text-sm font-bold text-white shadow-md shadow-indigo-500/30 hover:opacity-95 active:scale-98 transition-all cursor-pointer"
              >
                <span>Tạo Đề Thi Ngay</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Matrix Generate Modal */}
      <MatrixGenerateModal
        isOpen={isMatrixOpen}
        onClose={() => setIsMatrixOpen(false)}
        categories={categories}
        onSuccess={handleMatrixSuccess}
      />

      {/* Edit Bank Question Modal */}
      <EditBankQuestionModal
        isOpen={editingQuestion !== null}
        onClose={() => setEditingQuestion(null)}
        question={editingQuestion}
        onSuccess={(updated) => {
          setQuestions((prev) =>
            prev.map((item) => (item.id === updated.id ? updated : item))
          );
          setToastMessage("Đã cập nhật câu hỏi thành công.");
          setTimeout(() => setToastMessage(null), 3000);
        }}
      />
    </div>
  );
}
