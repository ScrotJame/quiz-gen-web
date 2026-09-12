"use client";

import React, { useRef } from "react";
import {
  Plus,
  RotateCw,
  Trash2,
  ChevronUp,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Image as ImageIcon,
} from "lucide-react";
import { StudioPageItem } from "../../lib/types";

interface FilmstripProps {
  pages: StudioPageItem[];
  selectedIndex: number;
  onSelectPage: (index: number) => void;
  onAddFiles: (files: FileList | File[]) => void;
  onRotatePage: (index: number) => void;
  onDeletePage: (index: number) => void;
  onMovePage: (index: number, direction: "up" | "down") => void;
  onRetryPage: (index: number) => void;
}

export function Filmstrip({
  pages,
  selectedIndex,
  onSelectPage,
  onAddFiles,
  onRotatePage,
  onDeletePage,
  onMovePage,
  onRetryPage,
}: FilmstripProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAddFiles(e.target.files);
      e.target.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(e.dataTransfer.files);
    }
  };

  const completedCount = pages.filter((p) => p.status === "success").length;

  return (
    <aside
      className="flex w-full md:w-[280px] shrink-0 flex-col border-b md:border-b-0 md:border-r border-zinc-200 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-900/40"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      {/* Header & Add Button */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            Danh sách trang ({pages.length})
          </h2>
          {pages.length > 0 && (
            <span className="text-[11px] font-medium text-zinc-400">
              {completedCount}/{pages.length} đã xong
            </span>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/jpg"
          multiple
          className="hidden"
          onChange={handleFileInputChange}
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          type="button"
          className="group flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-indigo-300 bg-indigo-50/60 p-3 text-xs font-semibold text-indigo-700 transition-all hover:border-indigo-500 hover:bg-indigo-100/70 hover:shadow-xs active:scale-[0.98] dark:border-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:border-indigo-600 dark:hover:bg-indigo-950/80"
        >
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-600 text-white transition-transform group-hover:scale-110">
            <Plus className="h-3.5 w-3.5" />
          </div>
          <span>+ Thêm trang ảnh</span>
        </button>
      </div>

      {/* Pages List */}
      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1 pb-4 max-h-[calc(100vh-280px)] md:max-h-[calc(100vh-220px)]">
        {pages.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-200 py-10 px-4 text-center dark:border-zinc-800">
            <ImageIcon className="h-8 w-8 text-zinc-400 dark:text-zinc-600 mb-2" />
            <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Chưa có trang ảnh nào
            </p>
            <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">
              Kéo thả hoặc bấm &quot;+ Thêm trang ảnh&quot; để tải lên nhiều trang cùng lúc
            </p>
          </div>
        ) : (
          pages.map((page, index) => {
            const isSelected = index === selectedIndex;
            return (
              <div
                key={page.id}
                onClick={() => onSelectPage(index)}
                className={`group relative flex cursor-pointer gap-3 rounded-xl border p-2.5 transition-all ${
                  isSelected
                    ? "border-indigo-500 bg-white shadow-md ring-2 ring-indigo-500/20 dark:border-indigo-500 dark:bg-zinc-800"
                    : "border-zinc-200/90 bg-white/70 hover:border-zinc-300 hover:bg-white dark:border-zinc-800 dark:bg-zinc-900/60 dark:hover:border-zinc-700 dark:hover:bg-zinc-800/60"
                }`}
              >
                {/* Thumbnail Preview with rotation */}
                <div className="relative h-20 w-16 shrink-0 overflow-hidden rounded-lg border border-zinc-200 bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 flex items-center justify-center">
                  <img
                    src={page.previewUrl}
                    alt={`Trang ${index + 1}`}
                    className="h-full w-full object-cover transition-transform duration-200"
                    style={{
                      transform: `rotate(${page.rotation}deg)`,
                    }}
                  />
                  {/* Status Overlay Icon */}
                  {page.status === "scanning" && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
                      <Loader2 className="h-5 w-5 animate-spin text-white" />
                    </div>
                  )}
                  {page.status === "error" && (
                    <div className="absolute inset-0 flex items-center justify-center bg-rose-500/30 backdrop-blur-[1px]">
                      <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400" />
                    </div>
                  )}
                </div>

                {/* Info & Meta */}
                <div className="flex flex-1 flex-col justify-between min-w-0">
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 truncate">
                        Trang {index + 1}
                      </span>
                      {/* Action buttons */}
                      <div
                        className="flex items-center gap-0.5 opacity-80 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => onRotatePage(index)}
                          title="Xoay 90°"
                          className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-700 dark:hover:text-zinc-200"
                        >
                          <RotateCw className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          disabled={index === 0}
                          onClick={() => onMovePage(index, "up")}
                          title="Di chuyển lên"
                          className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:hover:bg-zinc-700 dark:hover:text-zinc-200"
                        >
                          <ChevronUp className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          disabled={index === pages.length - 1}
                          onClick={() => onMovePage(index, "down")}
                          title="Di chuyển xuống"
                          className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-30 dark:hover:bg-zinc-700 dark:hover:text-zinc-200"
                        >
                          <ChevronDown className="h-3 w-3" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeletePage(index)}
                          title="Xóa trang"
                          className="rounded-md p-1 text-zinc-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/50 dark:hover:text-rose-400"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-1">
                      {page.status === "scanning" && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 dark:text-indigo-400">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Đang nhận diện OCR...
                        </span>
                      )}
                      {page.status === "success" && (
                        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 dark:text-zinc-400">
                          <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 font-medium">
                            <CheckCircle2 className="h-3 w-3" />
                            {Math.round(page.confidence * 100)}%
                          </span>
                          <span>•</span>
                          <span>{page.lineCount} dòng</span>
                        </div>
                      )}
                      {page.status === "error" && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[11px] font-medium text-rose-600 dark:text-rose-400 truncate">
                            {page.errorMessage || "Không đọc được chữ"}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onRetryPage(index);
                            }}
                            className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300 hover:bg-rose-100"
                          >
                            <RefreshCw className="h-2.5 w-2.5" />
                            Thử lại
                          </button>
                        </div>
                      )}
                      {page.status === "idle" && (
                        <span className="text-[11px] text-zinc-400">Chờ quét</span>
                      )}
                    </div>
                  </div>

                  {/* Character preview */}
                  {page.text && (
                    <p className="line-clamp-1 text-[10px] text-zinc-400 dark:text-zinc-500 font-mono mt-1">
                      {page.text.replace(/\s+/g, " ").slice(0, 40)}...
                    </p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
