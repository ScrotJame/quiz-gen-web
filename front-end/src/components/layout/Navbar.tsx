"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, PlusCircle, Database } from "lucide-react";
import { checkBackendHealth } from "../../lib/api-client";

export function Navbar() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    async function check() {
      const health = await checkBackendHealth();
      setBackendOnline(health !== null);
    }
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 bg-white/80 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/80 transition-colors">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20 transition-transform group-hover:scale-105">
            <Sparkles className="h-5 w-5" />
            <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 opacity-20 blur" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-black tracking-tight text-zinc-900 dark:text-white">
                Quiz<span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">Gen</span>
              </span>
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200/50 dark:border-indigo-800/50">
                AI + OCR
              </span>
            </div>
            <p className="hidden text-[11px] text-zinc-500 dark:text-zinc-400 sm:block">
              Tạo đề thi trắc nghiệm từ ảnh thông minh
            </p>
          </div>
        </Link>

        {/* Right navigation / actions */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Backend Status indicator */}
          <div
            className="flex items-center gap-1.5 rounded-full border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-600 shadow-xs dark:border-zinc-800 dark:text-zinc-400"
            title={
              backendOnline === true
                ? "Backend FastAPI đang hoạt động"
                : backendOnline === false
                ? "Không thể kết nối Backend FastAPI (Port 8000)"
                : "Đang kiểm tra kết nối..."
            }
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendOnline === true
                  ? "bg-emerald-500 ring-4 ring-emerald-500/20 animate-pulse"
                  : backendOnline === false
                  ? "bg-rose-500 ring-4 ring-rose-500/20"
                  : "bg-amber-400"
              }`}
            />
            <span className="hidden sm:inline">
              {backendOnline === true
                ? "Hệ thống Sẵn sàng"
                : backendOnline === false
                ? "Backend Offline"
                : "Đang kiểm tra..."}
            </span>
          </div>

          {/* Question Bank Link -> /bank */}
          <Link
            href="/bank"
            className="flex items-center gap-1.5 rounded-xl border border-zinc-200/80 bg-zinc-50 px-3.5 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-100 hover:text-indigo-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 transition-colors shadow-2xs"
          >
            <Database className="h-4 w-4 text-indigo-500" />
            <span className="hidden sm:inline">Ngân Hàng Câu Hỏi</span>
          </Link>

          {/* Primary Create Quiz Button -> /create/ocr */}
          <Link
            href="/create/ocr"
            className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-600/25 transition-all duration-200 hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-600/35 active:scale-95"
          >
            <PlusCircle className="h-4 w-4 transition-transform group-hover:rotate-90 duration-300" />
            <span>Tạo Đề Thi</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
