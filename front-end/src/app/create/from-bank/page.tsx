"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Database,
  AlertTriangle,
  Clock,
  Sparkles,
  BookOpen,
  Edit3,
  Loader2,
  X,
  FileCheck,
} from "lucide-react";
import { Navbar } from "../../../components/layout/Navbar";
import { QuizEditor } from "../../../components/studio/QuizEditor";
import { createQuiz } from "../../../lib/api-client";
import {
  BankQuestionSchema,
  QuestionEdit,
  QuizCreatePayload,
} from "../../../lib/types";

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

export default function CreateQuizFromBankPage() {
  const router = useRouter();

  const [isLoading, setIsLoading] = useState(true);
  const [questions, setQuestions] = useState<QuestionEdit[]>([]);
  const [title, setTitle] = useState("Đề thi từ Ngân hàng câu hỏi");
  const [category, setCategory] = useState("Tổng hợp");
  const [timeLimitMinutes, setTimeLimitMinutes] = useState(30);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Read staging data from sessionStorage
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("quiz_bank_staging");
      if (raw) {
        const parsed = JSON.parse(raw);
        const bankQuestions: BankQuestionSchema[] = parsed.questions || [];
        const cat = parsed.category || "Tổng hợp";
        const warn = parsed.warnings || [];

        const converted = bankQuestions.map(bankToQuestionEdit);
        setQuestions(converted);
        setCategory(cat);
        setWarnings(warn);

        const nowStr = new Date().toLocaleDateString("vi-VN");
        setTitle(`Đề thi ${cat} — ${nowStr}`);
      }
    } catch (err) {
      console.error("Lỗi đọc staging từ sessionStorage:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleBackToBank = () => {
    if (questions.length > 0) {
      if (
        window.confirm(
          "Bạn có chắc muốn rời khỏi màn hình biên tập? Các chỉnh sửa chưa lưu sẽ bị mất."
        )
      ) {
        sessionStorage.removeItem("quiz_bank_staging");
        router.push("/bank");
      }
    } else {
      router.push("/bank");
    }
  };

  // Build QuizCreate payload
  const buildPayload = (): QuizCreatePayload => {
    return {
      title: title.trim() || "Đề thi từ Ngân hàng câu hỏi",
      description: `Đề thi được tạo từ Ngân hàng câu hỏi (${questions.length} câu hỏi)`,
      category: category.trim() || "Tổng hợp",
      timeLimitMinutes: Number(timeLimitMinutes) || 30,
      authorName: "Giáo viên",
      isPublished: true,
      questions: questions.map((q, idx) => ({
        questionText: q.questionText,
        questionType: q.questionType,
        points: q.points || 10,
        explanation: q.explanation || undefined,
        orderNum: idx + 1,
        options: q.options.map((opt, oIdx) => ({
          optionText: opt.optionText,
          isCorrect: opt.isCorrect,
          orderNum: oIdx + 1,
        })),
      })),
    };
  };

  // Save to Library only
  const handleSaveToLibrary = async () => {
    if (questions.length === 0) return;
    setIsSaving(true);
    try {
      const payload = buildPayload();
      await createQuiz(payload);
      sessionStorage.removeItem("quiz_bank_staging");
      showToast("Đã lưu đề thi thành công vào danh sách!");
      setTimeout(() => router.push("/"), 1000);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Lỗi khi lưu đề thi");
      setIsSaving(false);
    }
  };

  // Save and go directly to Take Quiz
  const handleSaveAndPlay = async () => {
    if (questions.length === 0) return;
    setIsSaving(true);
    try {
      const payload = buildPayload();
      const created = await createQuiz(payload);
      sessionStorage.removeItem("quiz_bank_staging");
      showToast("Đã lưu đề thi! Đang chuyển đến phòng thi...");
      router.push(`/quiz/${created.id}`);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Lỗi khi lưu đề thi");
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col">
        <Navbar />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      </div>
    );
  }

  // Empty state: No questions in staging
  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col">
        <Navbar />
        <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center p-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 mb-4 border border-indigo-200/50 dark:border-indigo-800/50 shadow-sm">
            <Database className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white">
            Chưa có câu hỏi nào được chọn
          </h2>
          <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 max-w-md leading-relaxed">
            Bạn cần tích chọn các câu hỏi trong Ngân hàng câu hỏi hoặc sử dụng tính năng sinh đề theo ma trận trước khi biên tập.
          </p>
          <div className="mt-6 flex gap-3">
            <Link
              href="/bank"
              className="inline-flex items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-md hover:bg-indigo-500 transition-all"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Vào Ngân Hàng Câu Hỏi</span>
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50/80 text-zinc-900 selection:bg-indigo-500 selection:text-white dark:bg-zinc-950 dark:text-zinc-100 flex flex-col">
      {/* Top Header */}
      <header className="sticky top-0 z-40 border-b border-zinc-200/80 bg-white/90 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/90">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
          <button
            type="button"
            onClick={handleBackToBank}
            className="flex items-center gap-2 text-xs font-semibold text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Quay lại Ngân hàng</span>
          </button>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
              <span>Biên Tập Đề Thi Từ Kho</span>
            </span>
          </div>
        </div>
      </header>

      {/* Toast */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 flex items-center gap-2 rounded-2xl bg-zinc-900 px-4 py-3 text-sm font-semibold text-white shadow-xl dark:bg-zinc-100 dark:text-zinc-900 animate-in fade-in">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Container */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 space-y-6">
        {/* Warning Banner if Matrix had insufficient questions */}
        {warnings.length > 0 && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-300 space-y-1">
            <div className="flex items-center gap-2 font-bold text-amber-800 dark:text-amber-200">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>Thông báo về số lượng câu hỏi thực tế:</span>
            </div>
            <ul className="list-disc list-inside space-y-0.5 pl-1">
              {warnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Metadata Configuration Bar */}
        <div className="grid grid-cols-1 gap-4 rounded-3xl border border-zinc-200/80 bg-white p-5 shadow-xs dark:border-zinc-800/80 dark:bg-zinc-900/80 sm:grid-cols-12 sm:items-center">
          {/* Title input */}
          <div className="sm:col-span-6 space-y-1">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Tiêu đề đề thi
            </label>
            <div className="relative">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Nhập tiêu đề đề thi..."
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm font-bold text-zinc-900 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
              />
            </div>
          </div>

          {/* Category input */}
          <div className="sm:col-span-3 space-y-1">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Môn học / Danh mục
            </label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Toán, Lý, Lịch sử..."
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2 text-sm font-semibold text-zinc-800 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
            />
          </div>

          {/* Time limit */}
          <div className="sm:col-span-3 space-y-1">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Thời gian làm bài
            </label>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-zinc-400 shrink-0" />
              <select
                value={timeLimitMinutes}
                onChange={(e) => setTimeLimitMinutes(Number(e.target.value))}
                className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-semibold text-zinc-800 focus:border-indigo-500 focus:bg-white focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
              >
                <option value={15}>15 phút</option>
                <option value={30}>30 phút</option>
                <option value={45}>45 phút</option>
                <option value={60}>60 phút</option>
                <option value={90}>90 phút</option>
                <option value={120}>120 phút</option>
              </select>
            </div>
          </div>
        </div>

        {/* Reusing QuizEditor component */}
        <div className="rounded-3xl border border-zinc-200/80 bg-white/70 dark:border-zinc-800/80 dark:bg-zinc-900/50 backdrop-blur-xs">
          <QuizEditor
            questions={questions}
            onQuestionsChange={setQuestions}
            title={title}
            category={category}
            onBackToStep2={handleBackToBank}
            onSaveToLibrary={handleSaveToLibrary}
            onSaveAndPlay={handleSaveAndPlay}
            isSaving={isSaving}
          />
        </div>
      </main>
    </div>
  );
}
