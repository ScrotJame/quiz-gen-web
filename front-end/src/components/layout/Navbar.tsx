"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, PlusCircle } from "lucide-react";
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
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 bg-white/80 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/80 transition-colors pt-safe">
      <div className="mx-auto flex h-14 sm:h-16 max-w-7xl items-center justify-between px-3 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5 sm:gap-3 group">
          <div className="relative flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20 transition-transform group-hover:scale-105 shrink-0">
            <Sparkles className="h-4 w-4 sm:h-5 sm:w-5" />
            <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 opacity-20 blur" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-lg sm:text-xl font-black tracking-tight text-zinc-900 dark:text-white">
                Quiz<span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">Gen</span>
              </span>
              <span className="hidden min-[380px]:inline-block rounded-full bg-indigo-50 px-1.5 py-0.5 text-[10px] sm:text-[11px] font-semibold text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200/50 dark:border-indigo-800/50">
                AI + OCR
              </span>
            </div>
            <p className="hidden text-[11px] text-zinc-500 dark:text-zinc-400 sm:block">
              Tạo đề thi trắc nghiệm từ ảnh thông minh
            </p>
          </div>
        </Link>

        {/* Right navigation / actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Backend Status indicator */}
          <div
            className="flex items-center gap-1.5 rounded-full border border-zinc-200 px-2 sm:px-3 py-1 text-xs font-medium text-zinc-600 shadow-xs dark:border-zinc-800 dark:text-zinc-400"
            title={
              backendOnline === true
                ? "Backend FastAPI đang hoạt động"
                : backendOnline === false
                ? "Không thể kết nối Backend FastAPI (Port 8000)"
                : "Đang kiểm tra kết nối..."
            }
          >
            <span
              className={`h-2 w-2 rounded-full shrink-0 ${
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

          {/* Primary Create Quiz Button -> /create/ocr */}
          <Link
            href="/create/ocr"
            className="group relative inline-flex min-h-[38px] sm:min-h-[40px] items-center gap-1.5 sm:gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold text-white shadow-md shadow-indigo-600/25 transition-all duration-200 hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-600/35 active:scale-95 shrink-0"
          >
            <PlusCircle className="h-4 w-4 transition-transform group-hover:rotate-90 duration-300" />
            <span>Tạo Đề Thi</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
