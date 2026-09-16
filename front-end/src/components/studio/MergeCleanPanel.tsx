"use client";

import React, { useState } from "react";
import {
  Sparkles,
  ArrowLeft,
  ArrowRight,
  Loader2,
  CheckCircle2,
  GripVertical,
  Eye,
  FileText,
  Trash2,
  X,
} from "lucide-react";
import { StudioPageItem } from "../../lib/types";

interface MergeCleanPanelProps {
  pages: StudioPageItem[];
  onPagesReorder: (pages: StudioPageItem[]) => void;
  onPageTextChange: (pageId: string, text: string) => void;
  onDeletePage?: (pageId: string) => void;
  onCleanWithAi: (targetLang: string) => Promise<void>;
  isCleaning: boolean;
  hasCleaned: boolean;
  isExtracting?: boolean;
  onBackToStep1: () => void;
  onProceedToStep3: () => void;
}

export function MergeCleanPanel({
  pages,
  onPagesReorder,
  onPageTextChange,
  onDeletePage,
  onCleanWithAi,
  isCleaning,
  hasCleaned,
  isExtracting = false,
  onBackToStep1,
  onProceedToStep3,
}: MergeCleanPanelProps) {
  const [targetLang, setTargetLang] = useState<string>("vi");
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [previewImage, setPreviewImage] = useState<{ url: string; pageNum: number } | null>(null);

  // Statistics across all chunks
  const totalChars = pages.reduce((acc, p) => acc + p.text.length, 0);
  const totalWords = pages.reduce(
    (acc, p) => acc + p.text.trim().split(/\s+/).filter(Boolean).length,
    0
  );

  // Drag and Drop handlers
  const handleDragStart = (index: number, e: React.DragEvent) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", index.toString());
  };

  const handleDragOver = (index: number, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDrop = (dropIndex: number, e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    const reordered = [...pages];
    const [movedItem] = reordered.splice(draggedIndex, 1);
    reordered.splice(dropIndex, 0, movedItem);

    onPagesReorder(reordered);
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-indigo-100 bg-gradient-to-r from-indigo-50/70 via-purple-50/50 to-pink-50/40 p-5 dark:border-indigo-900/40 dark:from-indigo-950/40 dark:via-purple-950/30 dark:to-zinc-900">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-indigo-600 p-1 text-white shadow-xs">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <h2 className="text-base sm:text-lg font-bold text-zinc-900 dark:text-white">
              Sắp xếp thứ tự & Chuẩn hóa AI
            </h2>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-zinc-600 dark:text-zinc-400">
            Kéo thả các trang để xếp đúng thứ tự (Trang 1, 2, 3...). Bạn có thể chỉnh sửa trực tiếp text của từng trang trước khi chuẩn hóa AI.
          </p>
          <div className="mt-2 flex items-center gap-3 text-[11px] font-semibold text-zinc-500 dark:text-zinc-400">
            <span>{pages.length} trang ảnh</span>
            <span>•</span>
            <span>{totalWords.toLocaleString()} từ</span>
            <span>•</span>
            <span>{totalChars.toLocaleString()} ký tự</span>
          </div>
        </div>

        {/* AI Clean Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            disabled={isCleaning}
            className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold text-zinc-700 shadow-xs focus:border-indigo-500 focus:outline-hidden dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
          </select>

          <button
            type="button"
            id="btn-ai-clean"
            onClick={() => onCleanWithAi(targetLang)}
            disabled={isCleaning || totalChars === 0}
            className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/25 transition-all hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg disabled:opacity-50 active:scale-95 cursor-pointer"
          >
            {isCleaning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-white" />
                <span>AI đang chuẩn hóa...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 transition-transform duration-300 group-hover:rotate-12" />
                <span>AI Chuẩn hóa tất cả</span>
              </>
            )}
          </button>
        </div>
      </div>

      {hasCleaned && (
        <div className="flex items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50/80 px-4 py-2.5 text-xs text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            <strong>Đã chuẩn hóa thành công:</strong> AI đã sửa lỗi dấu tiếng Việt và nối liền câu liên trang.
          </span>
        </div>
      )}

      {/* Notice on Drag and Drop */}
      <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400 px-1">
        <span>Kéo vào biểu tượng <GripVertical className="inline h-3.5 w-3.5 text-zinc-400" /> để đổi vị trí chunk:</span>
        <span>Thứ tự từ trên xuống dưới sẽ được gộp theo thứ tự đọc</span>
      </div>

      {/* Drag & Drop Chunks List */}
      <div className="space-y-4">
        {pages.map((page, index) => {
          const isDragging = draggedIndex === index;
          const isOver = dragOverIndex === index;
          const words = page.text.trim().split(/\s+/).filter(Boolean).length;

          return (
            <div
              key={page.id}
              draggable
              onDragStart={(e) => handleDragStart(index, e)}
              onDragOver={(e) => handleDragOver(index, e)}
              onDragEnd={handleDragEnd}
              onDrop={(e) => handleDrop(index, e)}
              className={`group relative rounded-2xl border transition-all duration-200 bg-white shadow-xs dark:bg-zinc-900 ${
                isDragging
                  ? "opacity-40 border-dashed border-indigo-400 scale-[0.99]"
                  : isOver
                  ? "border-2 border-indigo-500 shadow-md ring-2 ring-indigo-500/20"
                  : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700"
              }`}
            >
              <div className="flex flex-col md:flex-row gap-4 p-4 items-stretch">
                {/* Drag Handle & Page Indicator */}
                <div className="flex md:flex-col items-center justify-between md:justify-start gap-3 shrink-0">
                  <div
                    className="flex cursor-grab active:cursor-grabbing items-center gap-1.5 rounded-lg px-2 py-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                    title="Kéo thả để sắp xếp lại vị trí"
                  >
                    <GripVertical className="h-4 w-4" />
                    <span className="text-xs font-bold text-zinc-700 dark:text-zinc-300">
                      Trang {index + 1}
                    </span>
                  </div>

                  {/* Image Thumbnail Preview */}
                  <div
                    onClick={() => setPreviewImage({ url: page.previewUrl, pageNum: index + 1 })}
                    className="relative group/thumb cursor-pointer overflow-hidden rounded-xl border border-zinc-200 bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 w-24 h-28 shrink-0 flex items-center justify-center shadow-xs"
                    title="Bấm để phóng to xem trước ảnh"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={page.previewUrl}
                      alt={`Trang ${index + 1}`}
                      className="h-full w-full object-cover transition-transform duration-200 group-hover/thumb:scale-105"
                      style={{ transform: `rotate(${page.rotation}deg)` }}
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/thumb:opacity-100 transition-opacity flex flex-col items-center justify-center text-white text-[10px] font-semibold gap-1">
                      <Eye className="h-4 w-4" />
                      <span>Xem ảnh</span>
                    </div>
                  </div>

                  <div className="hidden md:flex flex-col items-center gap-1 text-[10px] text-zinc-400">
                    <span>{words} từ</span>
                    {page.confidence > 0 && (
                      <span>{Math.round(page.confidence)}% OCR</span>
                    )}
                  </div>
                </div>

                {/* Editable Text Area for Chunk */}
                <div className="flex-1 flex flex-col space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5 text-indigo-500" />
                      Nội dung văn bản nhận diện (Trang {index + 1})
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-zinc-400">
                        {page.text.length} ký tự
                      </span>
                      {onDeletePage && (
                        <button
                          type="button"
                          onClick={() => onDeletePage(page.id)}
                          className="text-zinc-400 hover:text-red-500 p-1 rounded-md transition-colors"
                          title="Xóa trang này"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  <textarea
                    value={page.text}
                    onChange={(e) => onPageTextChange(page.id, e.target.value)}
                    rows={6}
                    placeholder={`Nội dung OCR của trang ${index + 1}...`}
                    className="w-full flex-1 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3 font-mono text-xs sm:text-sm leading-relaxed text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
                  />
                </div>
              </div>
            </div>
          );
        })}

        {pages.length === 0 && (
          <div className="flex flex-col items-center justify-center p-12 text-zinc-400 border border-dashed rounded-2xl">
            <FileText className="h-10 w-10 mb-2 opacity-40" />
            <p className="text-sm">Chưa có trang nào được quét.</p>
          </div>
        )}
      </div>

      {/* Lightbox / Image Preview Modal */}
      {previewImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-xs animate-in fade-in duration-200"
          onClick={() => setPreviewImage(null)}
        >
          <div
            className="relative max-h-[90vh] max-w-[90vw] overflow-hidden rounded-2xl bg-zinc-900 p-2 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-3 py-2 text-white border-b border-zinc-800">
              <span className="text-sm font-bold">Xem trước: Trang {previewImage.pageNum}</span>
              <button
                type="button"
                onClick={() => setPreviewImage(null)}
                className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex max-h-[80vh] items-center justify-center overflow-auto p-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewImage.url}
                alt={`Trang ${previewImage.pageNum}`}
                className="max-h-[75vh] w-auto rounded-lg object-contain"
              />
            </div>
          </div>
        </div>
      )}

      {/* Bottom Nav: Back & Next buttons */}
      <div className="flex items-center justify-between border-t border-zinc-200 pt-4 dark:border-zinc-800">
        <button
          type="button"
          onClick={onBackToStep1}
          disabled={isCleaning}
          className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-200 px-4 py-2.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>← Quay lại bước Quét</span>
        </button>

        <button
          type="button"
          id="btn-proceed-to-step3"
          onClick={onProceedToStep3}
          disabled={isCleaning || isExtracting || totalChars === 0}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs sm:text-sm font-bold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-all"
        >
          {isExtracting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-white" />
              <span>AI đang bóc tách câu hỏi...</span>
            </>
          ) : (
            <>
              <span>Tiếp tục: Duyệt & Lưu Thư viện</span>
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
