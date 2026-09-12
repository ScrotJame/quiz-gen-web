"use client";

import React, { useState } from "react";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCw,
  Copy,
  Check,
  RefreshCw,
  ArrowLeft,
  ArrowRight,
  FileText,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { StudioPageItem } from "../../lib/types";

interface SplitScreenProps {
  pages: StudioPageItem[];
  selectedIndex: number;
  onSelectPage: (index: number) => void;
  onTextChange: (index: number, newText: string) => void;
  onRotatePage: (index: number) => void;
  onRetryPage: (index: number) => void;
  onContinue: () => void;
  canContinue: boolean;
}

export function SplitScreen({
  pages,
  selectedIndex,
  onSelectPage,
  onTextChange,
  onRotatePage,
  onRetryPage,
  onContinue,
  canContinue,
}: SplitScreenProps) {
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [copied, setCopied] = useState(false);

  const currentPage = pages[selectedIndex];

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => setZoomLevel(1);

  const handleCopy = async () => {
    if (!currentPage?.text) return;
    await navigator.clipboard.writeText(currentPage.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Word count across all pages
  const totalWords = pages.reduce((acc, p) => {
    if (!p.text) return acc;
    return acc + p.text.trim().split(/\s+/).filter(Boolean).length;
  }, 0);

  const completedPages = pages.filter((p) => p.status === "success").length;

  if (!currentPage) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center text-zinc-400">
        <div className="max-w-md space-y-3">
          <FileText className="mx-auto h-12 w-12 text-zinc-300 dark:text-zinc-600" />
          <h3 className="text-base font-semibold text-zinc-700 dark:text-zinc-300">
            Chưa có trang nào được chọn
          </h3>
          <p className="text-sm text-zinc-500">
            Vui lòng tải ảnh lên ở cột bên trái hoặc chọn một trang trong danh sách để xem đối chiếu và chỉnh sửa.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-zinc-100/60 dark:bg-zinc-950/60">
      {/* Main Split Grid: 50% Image viewer / 50% Text editor */}
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-zinc-200 dark:divide-zinc-800 overflow-hidden">
        {/* ========================================================================= */}
        {/* LEFT: IMAGE VIEWER WITH ZOOM CONTROLS                                    */}
        {/* ========================================================================= */}
        <div className="flex flex-col h-full overflow-hidden bg-zinc-900/5 dark:bg-zinc-950/40">
          {/* Viewer Toolbar */}
          <div className="flex items-center justify-between border-b border-zinc-200 bg-white/80 px-4 py-2 backdrop-blur-xs dark:border-zinc-800 dark:bg-zinc-900/80">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                Ảnh gốc (Trang {selectedIndex + 1})
              </span>
              <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-mono text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                {Math.round(zoomLevel * 100)}%
              </span>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleZoomIn}
                title="Phóng to"
                className="rounded-lg p-1.5 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleZoomOut}
                title="Thu nhỏ"
                className="rounded-lg p-1.5 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                <ZoomOut className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleResetZoom}
                title="Đặt lại kích thước"
                className="rounded-lg p-1.5 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
              <div className="mx-1 h-4 w-px bg-zinc-200 dark:bg-zinc-800" />
              <button
                type="button"
                onClick={() => onRotatePage(selectedIndex)}
                title="Xoay 90°"
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                <RotateCw className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Xoay 90°</span>
              </button>
            </div>
          </div>

          {/* Image Display Area with Canvas/Scroll */}
          <div className="relative flex flex-1 items-center justify-center overflow-auto p-4 select-none">
            <div
              className="transition-transform duration-200 ease-out origin-center"
              style={{
                transform: `scale(${zoomLevel}) rotate(${currentPage.rotation}deg)`,
              }}
            >
              <img
                src={currentPage.previewUrl}
                alt={`Trang ${selectedIndex + 1}`}
                className="max-h-[60vh] lg:max-h-[calc(100vh-270px)] rounded-lg object-contain shadow-md border border-zinc-200 dark:border-zinc-700 bg-white"
                draggable={false}
              />
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT: OCR TEXT EDITOR & REAL-TIME REFINEMENT                             */}
        {/* ========================================================================= */}
        <div className="flex flex-col h-full overflow-hidden bg-white dark:bg-zinc-900">
          {/* Editor Header */}
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2.5 dark:border-zinc-800">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                Văn bản OCR nhận diện
              </span>
              {currentPage.status === "success" && (
                <div className="flex items-center gap-1.5">
                  <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border border-emerald-200/50 dark:border-emerald-800/50">
                    {Math.round(currentPage.confidence * 100)}% chuẩn xác
                  </span>
                  <span className="text-[11px] text-zinc-400">
                    • {currentPage.lineCount} dòng
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => onRetryPage(selectedIndex)}
                disabled={currentPage.status === "scanning"}
                className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                title="Quét lại OCR trang này"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${
                    currentPage.status === "scanning" ? "animate-spin text-indigo-600" : ""
                  }`}
                />
                <span className="hidden sm:inline">Quét lại</span>
              </button>

              <button
                type="button"
                onClick={handleCopy}
                disabled={!currentPage.text}
                className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                title="Sao chép toàn bộ văn bản trang"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="text-emerald-600 font-semibold">Đã chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Text Area or Scanning State */}
          <div className="relative flex-1 p-4">
            {currentPage.status === "scanning" ? (
              <div className="flex h-full flex-col items-center justify-center space-y-3 text-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                <div>
                  <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                    Đang quét và nhận diện văn bản OCR...
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">
                    Sử dụng RapidOCR ONNX Runtime tối ưu tiếng Việt có dấu
                  </p>
                </div>
              </div>
            ) : currentPage.status === "error" ? (
              <div className="flex h-full flex-col items-center justify-center space-y-3 rounded-xl border border-dashed border-rose-200 bg-rose-50/50 p-6 text-center dark:border-rose-900/50 dark:bg-rose-950/20">
                <AlertCircle className="h-8 w-8 text-rose-500" />
                <div>
                  <p className="text-sm font-semibold text-rose-800 dark:text-rose-200">
                    {currentPage.errorMessage || "Không phát hiện được văn bản trong ảnh"}
                  </p>
                  <p className="text-xs text-rose-600/80 dark:text-rose-400/80 mt-1">
                    Vui lòng kiểm tra độ sáng, xoay lại đúng hướng ảnh hoặc chụp lại rõ nét hơn.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onRetryPage(selectedIndex)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-rose-500"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Thử quét lại trang này
                </button>
              </div>
            ) : (
              <textarea
                value={currentPage.text}
                onChange={(e) => onTextChange(selectedIndex, e.target.value)}
                placeholder="Nội dung văn bản trích xuất sẽ hiển thị ở đây. Bạn có thể chỉnh sửa trực tiếp nếu có từ nhận diện chưa đúng..."
                className="h-full w-full resize-none rounded-xl border border-zinc-200/80 bg-zinc-50/50 p-4 font-mono text-sm leading-relaxed text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-800 dark:bg-zinc-900/50 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:bg-zinc-900"
              />
            )}
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* BOTTOM ACTION BAR: NAVIGATION & PROCEED TO STEP 2                         */}
      {/* ========================================================================= */}
      <div className="flex items-center justify-between border-t border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        {/* Left: Previous / Next page buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={selectedIndex === 0}
            onClick={() => onSelectPage(selectedIndex - 1)}
            className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Trang trước</span>
          </button>

          <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 px-1">
            Trang {selectedIndex + 1} / {pages.length}
          </span>

          <button
            type="button"
            disabled={selectedIndex === pages.length - 1}
            onClick={() => onSelectPage(selectedIndex + 1)}
            className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            <span>Trang sau</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Center: Quick Summary Stats */}
        <div className="hidden sm:flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
          <span>
            Đã quét: <strong className="text-zinc-900 dark:text-white">{completedPages}/{pages.length}</strong> trang
          </span>
          <span>•</span>
          <span>
            Tổng: <strong className="text-zinc-900 dark:text-white">{totalWords.toLocaleString()}</strong> từ
          </span>
        </div>

        {/* Right: Proceed to Step 2 */}
        <button
          type="button"
          disabled={!canContinue}
          onClick={onContinue}
          className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-indigo-600/25 transition-all hover:from-indigo-500 hover:to-purple-500 hover:shadow-lg hover:shadow-indigo-600/35 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
        >
          <span>Tiếp tục: Chuẩn hóa & Nối trang</span>
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    </div>
  );
}
