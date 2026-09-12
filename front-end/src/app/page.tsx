"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  BookOpen,
  Award,
  CheckCircle2,
  Zap,
  Sparkles,
  ArrowRight,
  RefreshCw,
  FileImage,
  Flame,
} from "lucide-react";
import { Navbar } from "../components/layout/Navbar";
import { StatCard } from "../components/dashboard/StatCard";
import { RecentQuizzes } from "../components/dashboard/RecentQuizzes";
import { getDashboardStats, getRecentQuizzes } from "../lib/api-client";
import { DashboardStats, QuizSummary } from "../lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalQuizzes: 0,
    averageScore: 0,
    totalQuestionsCompleted: 0,
    totalAttempts: 0,
  });
  const [recentQuizzes, setRecentQuizzes] = useState<QuizSummary[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingQuizzes, setLoadingQuizzes] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("Tất cả");

  // Manual refresh handler for user click
  const handleRefresh = useCallback(async () => {
    setLoadingStats(true);
    setLoadingQuizzes(true);
    try {
      const [statsData, quizzesData] = await Promise.all([
        getDashboardStats(),
        getRecentQuizzes(30),
      ]);
      setStats(statsData);
      setRecentQuizzes(quizzesData.items || []);
    } catch (err) {
      console.error("Lỗi khi tải dữ liệu Dashboard:", err);
    } finally {
      setLoadingStats(false);
      setLoadingQuizzes(false);
    }
  }, []);

  // Initial load on component mount
  useEffect(() => {
    let isMounted = true;
    Promise.all([getDashboardStats(), getRecentQuizzes(30)])
      .then(([statsData, quizzesData]) => {
        if (isMounted) {
          setStats(statsData);
          setRecentQuizzes(quizzesData.items || []);
        }
      })
      .catch((err) => {
        console.error("Lỗi khi tải dữ liệu Dashboard:", err);
      })
      .finally(() => {
        if (isMounted) {
          setLoadingStats(false);
          setLoadingQuizzes(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Filter categories
  const categories = useMemo(() => {
    const set = new Set<string>();
    set.add("Tất cả");
    recentQuizzes.forEach((q) => {
      if (q.category) set.add(q.category);
    });
    return Array.from(set);
  }, [recentQuizzes]);

  // Filter quizzes by search and category
  const filteredQuizzes = useMemo(() => {
    return recentQuizzes.filter((q) => {
      const matchesCat =
        selectedCategory === "Tất cả" || q.category === selectedCategory;
      const matchesSearch =
        !searchQuery.trim() ||
        q.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (q.description &&
          q.description.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesCat && matchesSearch;
    });
  }, [recentQuizzes, selectedCategory, searchQuery]);

  return (
    <div className="min-h-screen bg-zinc-50/70 text-zinc-900 selection:bg-indigo-500 selection:text-white dark:bg-zinc-950 dark:text-zinc-100 flex flex-col">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* ========================================================================= */}
        {/* 1. HERO SECTION & PRIMARY "CREATE QUIZ" BUTTON                           */}
        {/* ========================================================================= */}
        <section className="relative overflow-hidden rounded-3xl border border-indigo-100/80 bg-gradient-to-br from-indigo-900 via-indigo-950 to-zinc-950 p-6 sm:p-10 text-white shadow-xl shadow-indigo-950/20 dark:border-indigo-900/40">
          {/* Ambient decorative glow elements */}
          <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-indigo-500/25 blur-3xl" />
          <div className="pointer-events-none absolute -left-20 -bottom-20 h-72 w-72 rounded-full bg-purple-500/20 blur-3xl" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#ffffff0a_1px,transparent_1px)] [background-size:16px_16px]" />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
            <div className="max-w-2xl space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 px-3.5 py-1 text-xs font-semibold text-indigo-300 backdrop-blur-md border border-indigo-400/20">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
                <span>Công nghệ OCR tiếng Việt & AI Mistral thế hệ mới</span>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight leading-tight sm:leading-tight">
                Tạo Đề Thi Trắc Nghiệm{" "}
                <span className="bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300 bg-clip-text text-transparent">
                  Từ Ảnh Chụp
                </span>
              </h1>
              <p className="text-sm sm:text-base text-zinc-300/90 leading-relaxed">
                Tải ảnh sách giáo khoa, slide bài giảng hoặc tài liệu để trích xuất
                văn bản tự động và sinh bộ câu hỏi trắc nghiệm có đáp án & lời giải chi tiết.
              </p>
            </div>

            {/* Primary Action Button: CREATE QUIZ -> /create/ocr */}
            <div className="flex flex-col sm:flex-row lg:flex-col shrink-0 gap-3">
              <Link
                id="btn-create-quiz-primary"
                href="/create/ocr"
                className="group relative inline-flex items-center justify-center gap-3 overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 px-8 py-4 text-base sm:text-lg font-bold text-white shadow-xl shadow-indigo-600/40 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-indigo-500/50 active:scale-95 cursor-pointer"
              >
                <div className="absolute inset-0 bg-white/20 opacity-0 transition-opacity group-hover:opacity-100" />
                <Sparkles className="h-5 w-5 transition-transform duration-300 group-hover:rotate-12" />
                <span>Tạo Đề Thi — Quét Ảnh OCR</span>
                <ArrowRight className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
              </Link>

              <div className="flex items-center justify-center gap-3 text-xs text-zinc-400">
                <span className="flex items-center gap-1">
                  <FileImage className="h-3.5 w-3.5 text-indigo-400" />
                  Hỗ trợ PNG/JPG/WEBP
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Flame className="h-3.5 w-3.5 text-amber-400" />
                  AI Sửa lỗi & Nối trang
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* 2. STATS SECTION (TỔNG SỐ QUIZ, ĐIỂM TRUNG BÌNH, TỔNG SỐ CÂU ĐÃ LÀM)      */}
        {/* ========================================================================= */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <span>Chỉ số tổng quan</span>
              {loadingStats && (
                <span className="inline-block h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
              )}
            </h2>
            <button
              onClick={handleRefresh}
              type="button"
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-zinc-500 hover:bg-zinc-200/60 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 transition-colors"
              title="Làm mới số liệu"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingStats ? "animate-spin" : ""}`} />
              <span>Cập nhật</span>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Stat 1: Tổng số quiz đã tạo */}
            <StatCard
              title="Tổng số quiz đã tạo"
              value={loadingStats ? "..." : stats.totalQuizzes}
              subtitle="Tổng bộ đề thi hiện có trong hệ thống"
              icon={BookOpen}
              badgeText="Đã lưu"
              accentColor="indigo"
            />

            {/* Stat 2: Điểm trung bình */}
            <StatCard
              title="Điểm trung bình"
              value={loadingStats ? "..." : `${stats.averageScore}%`}
              subtitle="Tính trên các lượt thi đã hoàn thành"
              icon={Award}
              badgeText="Toàn hệ thống"
              accentColor="emerald"
              progressPercent={loadingStats ? 0 : stats.averageScore}
            />

            {/* Stat 3: Tổng số câu đã làm */}
            <StatCard
              title="Tổng số câu đã làm"
              value={loadingStats ? "..." : stats.totalQuestionsCompleted}
              subtitle="Câu trắc nghiệm đã được thí sinh trả lời"
              icon={CheckCircle2}
              badgeText="Luyện tập"
              accentColor="sky"
            />

            {/* Stat 4: Lượt thi hoàn thành (Chỉ số phụ trợ) */}
            <StatCard
              title="Tổng lượt làm bài"
              value={loadingStats ? "..." : stats.totalAttempts}
              subtitle="Lượt thi đã nộp bài và chấm điểm xong"
              icon={Zap}
              badgeText="Tương tác"
              accentColor="amber"
            />
          </div>
        </section>

        {/* ========================================================================= */}
        {/* 3. RECENT QUIZZES SECTION (QUIZ GẦN ĐÂY)                                  */}
        {/* ========================================================================= */}
        <section>
          <RecentQuizzes
            quizzes={filteredQuizzes}
            isLoading={loadingQuizzes}
            categories={categories}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-zinc-200/80 bg-white/40 py-6 text-center text-xs text-zinc-500 dark:border-zinc-800/80 dark:bg-zinc-950/40">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>© 2026 QuizGen AI. Hệ thống tạo đề trắc nghiệm tự động từ hình ảnh.</p>
          <div className="flex items-center gap-4 text-zinc-400">
            <span>FastAPI Backend</span>
            <span>•</span>
            <span>RapidOCR OnnxRuntime</span>
            <span>•</span>
            <span>Next.js 16</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
