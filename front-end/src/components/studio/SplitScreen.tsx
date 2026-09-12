"use client";

import React, { useState, useRef, useEffect } from "react";
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
  SlidersHorizontal,
  RotateCcw,
  Sparkles,
  Cpu,
  X,
} from "lucide-react";
import { OcrRetryOptions, StudioPageItem } from "../../lib/types";

interface SplitScreenProps {
  pages: StudioPageItem[];
  selectedIndex: number;
  onSelectPage: (index: number) => void;
  onTextChange: (index: number, newText: string) => void;
  onRotatePage: (index: number) => void;
  onRetryPage: (index: number, options?: OcrRetryOptions) => void;
  onContinue: () => void;
  canContinue: boolean;
}

const DEFAULT_OCR_OPTIONS: OcrRetryOptions = {
  engine: "auto",
  unclipRatio: 1.35,
  boxThresh: 0.42,
  limitSideLen: 1024,
  enableClahe: true,
  splitTallBoxes: true,
};

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
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [retryOptions, setRetryOptions] = useState<OcrRetryOptions>(DEFAULT_OCR_OPTIONS);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Click outside to close settings popover
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setShowSettings(false);
      }
    }
    if (showSettings) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showSettings]);

  const isCustomized =
    retryOptions.engine !== "auto" ||
    (retryOptions.unclipRatio !== undefined && retryOptions.unclipRatio !== 1.35) ||
    (retryOptions.boxThresh !== undefined && retryOptions.boxThresh !== 0.42) ||
    (retryOptions.limitSideLen !== undefined && retryOptions.limitSideLen !== 1024) ||
    !retryOptions.enableClahe ||
    !retryOptions.splitTallBoxes;

  const handleApplyRetry = (opts?: OcrRetryOptions) => {
    const finalOpts = opts || retryOptions;
    setShowSettings(false);
    onRetryPage(selectedIndex, finalOpts);
  };

  const handleResetDefaults = () => {
    setRetryOptions(DEFAULT_OCR_OPTIONS);
  };

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
              {currentPage.status === "success" && (() => {
                const isLocal =
                  currentPage.provider === "local_vietocr" ||
                  (!currentPage.provider && currentPage.confidence < 0.99);

                return (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                        isLocal
                          ? "bg-amber-50 text-amber-700 border-amber-200/70 dark:bg-amber-950/60 dark:text-amber-400 dark:border-amber-800/50"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200/50 dark:bg-emerald-950/60 dark:text-emerald-400 dark:border-emerald-800/50"
                      }`}
                    >
                      {Math.round(currentPage.confidence * 100)}% chuẩn xác
                    </span>
                    <span className="text-[11px] text-zinc-400">
                      • {currentPage.lineCount} dòng
                    </span>
                    {isLocal && (
                      <span
                        className="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-950/80 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 shadow-sm"
                        title="Văn bản nhận diện từ Local OCR — khuyến nghị xem lại và chỉnh sửa trước khi sinh đề"
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                        Cần chỉnh sửa
                      </span>
                    )}
                  </div>
                );
              })()}
            </div>

            <div className="flex items-center gap-1.5">
              {/* Composite Quét lại + Nút tùy chỉnh trọng số */}
              <div className="relative" ref={settingsRef}>
                <div className="inline-flex items-center rounded-lg border border-zinc-200 bg-white shadow-xs dark:border-zinc-700 dark:bg-zinc-800">
                  <button
                    type="button"
                    onClick={() => handleApplyRetry()}
                    disabled={currentPage.status === "scanning"}
                    className="inline-flex items-center gap-1.5 rounded-l-lg px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 dark:text-zinc-200 dark:hover:bg-zinc-750"
                    title="Quét lại OCR trang này"
                  >
                    <RefreshCw
                      className={`h-3.5 w-3.5 ${
                        currentPage.status === "scanning"
                          ? "animate-spin text-indigo-600 dark:text-indigo-400"
                          : "text-zinc-500"
                      }`}
                    />
                    <span className="hidden sm:inline">Quét lại</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowSettings((v) => !v)}
                    disabled={currentPage.status === "scanning"}
                    className={`relative inline-flex items-center rounded-r-lg border-l border-zinc-200 px-2 py-1 text-xs hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-750 ${
                      showSettings
                        ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400"
                        : "text-zinc-500 dark:text-zinc-400"
                    }`}
                    title="Tùy chỉnh thông số Local OCR trước khi quét lại"
                  >
                    <SlidersHorizontal className="h-3.5 w-3.5" />
                    {isCustomized && (
                      <span className="absolute -top-1 -right-1 flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
                      </span>
                    )}
                  </button>
                </div>

                {/* Popover tùy chỉnh trọng số */}
                {showSettings && (
                  <div className="absolute right-0 top-full mt-2 w-[340px] sm:w-[380px] rounded-2xl border border-zinc-200/90 bg-white/95 p-4 shadow-2xl backdrop-blur-md z-50 dark:border-zinc-800 dark:bg-zinc-900/95">
                    {/* Header */}
                    <div className="flex items-center justify-between pb-3 border-b border-zinc-100 dark:border-zinc-800">
                      <div className="flex items-center gap-2">
                        <div className="rounded-lg bg-indigo-50 p-1.5 text-indigo-600 dark:bg-indigo-950/70 dark:text-indigo-400">
                          <SlidersHorizontal className="h-4 w-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                            Cấu hình OCR & Trọng số
                          </h4>
                          <p className="text-[11px] text-zinc-500">
                            Dành cho trường hợp chữ mờ hoặc Gemini lỗi
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowSettings(false)}
                        className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                    {/* Body */}
                    <div className="py-3 space-y-4 max-h-[60vh] overflow-y-auto pr-1 text-xs">
                      {/* Workflow Banner */}
                      <div className="rounded-xl bg-indigo-50/90 p-3 dark:bg-indigo-950/50 border border-indigo-200/80 dark:border-indigo-800/60 flex items-start gap-2.5">
                        <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                        <div className="text-[11px] text-indigo-950 dark:text-indigo-200 leading-relaxed">
                          <strong className="font-bold">Quy trình quét thông minh:</strong> Luôn gọi <strong>AI Gemini Vision OCR trước</strong> để trích xuất chữ và công thức. Nếu Gemini không nhận diện được hoặc gặp lỗi (429/mất mạng), hệ thống sẽ <strong>tự động chuyển sang Local OCR</strong> với các trọng số tinh chỉnh bên dưới.
                        </div>
                      </div>

                      {/* Engine Selector */}
                      <div>
                        <label className="block text-[11px] font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
                          Chế độ quét
                        </label>
                        <div className="grid grid-cols-3 gap-1.5 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
                          <button
                            type="button"
                            onClick={() =>
                              setRetryOptions((prev) => ({ ...prev, engine: "auto" }))
                            }
                            className={`rounded-md py-1.5 px-1.5 text-[11px] font-medium transition-all ${
                              retryOptions.engine === "auto"
                                ? "bg-white text-indigo-600 font-bold shadow-xs dark:bg-zinc-700 dark:text-indigo-300"
                                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
                            }`}
                            title="Ưu tiên Gemini OCR trước -> Tự động chuyển Local OCR nếu Gemini không tìm thấy chữ"
                          >
                            Tự động (Chuẩn)
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setRetryOptions((prev) => ({ ...prev, engine: "local_vietocr" }))
                            }
                            className={`rounded-md py-1.5 px-1.5 text-[11px] font-medium transition-all ${
                              retryOptions.engine === "local_vietocr"
                                ? "bg-white text-indigo-600 font-bold shadow-xs dark:bg-zinc-700 dark:text-indigo-300"
                                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
                            }`}
                            title="Bỏ qua Gemini, quét trực tiếp bằng Local RapidOCR + VietOCR"
                          >
                            Chỉ Local OCR
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setRetryOptions((prev) => ({ ...prev, engine: "gemini" }))
                            }
                            className={`rounded-md py-1.5 px-1.5 text-[11px] font-medium transition-all ${
                              retryOptions.engine === "gemini"
                                ? "bg-white text-indigo-600 font-bold shadow-xs dark:bg-zinc-700 dark:text-indigo-300"
                                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
                            }`}
                            title="Chỉ dùng Gemini Vision OCR"
                          >
                            Chỉ Gemini
                          </button>
                        </div>
                      </div>

                      {/* Detector Parameters (Hiển thị khi chọn Local OCR hoặc Auto) */}
                      {retryOptions.engine !== "gemini" && (
                        <div className="space-y-3.5 pt-1 border-t border-zinc-100 dark:border-zinc-800">
                          <div className="flex items-center gap-1.5">
                            <Cpu className="h-3.5 w-3.5 text-indigo-500" />
                            <span className="font-bold text-zinc-800 dark:text-zinc-200 text-[11px]">
                              Trọng số Local OCR (Dự phòng phòng khi Gemini không nhận diện được)
                            </span>
                          </div>
                          {/* Unclip Ratio Slider */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                Mở rộng viền dòng (Unclip)
                              </span>
                              <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] font-bold text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                                {retryOptions.unclipRatio ?? 1.35}x
                              </span>
                            </div>
                            <input
                              type="range"
                              min="1.10"
                              max="1.80"
                              step="0.05"
                              value={retryOptions.unclipRatio ?? 1.35}
                              onChange={(e) =>
                                setRetryOptions((prev) => ({
                                  ...prev,
                                  unclipRatio: parseFloat(e.target.value),
                                }))
                              }
                              className="w-full accent-indigo-600 cursor-pointer"
                            />
                            <p className="text-[10px] text-zinc-400 mt-0.5">
                              Tăng nếu bị cắt xén viền chữ/dấu; giảm nếu 2 dòng bị gộp dính.
                            </p>
                          </div>

                          {/* Box Thresh Slider */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                Ngưỡng nhận diện (Box Thresh)
                              </span>
                              <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] font-bold text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                                {retryOptions.boxThresh ?? 0.42}
                              </span>
                            </div>
                            <input
                              type="range"
                              min="0.25"
                              max="0.65"
                              step="0.01"
                              value={retryOptions.boxThresh ?? 0.42}
                              onChange={(e) =>
                                setRetryOptions((prev) => ({
                                  ...prev,
                                  boxThresh: parseFloat(e.target.value),
                                }))
                              }
                              className="w-full accent-indigo-600 cursor-pointer"
                            />
                            <p className="text-[10px] text-zinc-400 mt-0.5">
                              Giảm để bắt chữ mờ/nhạt; tăng để lọc bớt nhiễu hoặc đường kẻ.
                            </p>
                          </div>

                          {/* Limit Side Len Chips */}
                          <div>
                            <span className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                              Độ phân giải xử lý ảnh
                            </span>
                            <div className="grid grid-cols-4 gap-1">
                              {[
                                { label: "960px", val: 960 },
                                { label: "1024px", val: 1024 },
                                { label: "1280px", val: 1280 },
                                { label: "1536px", val: 1536 },
                              ].map((item) => (
                                <button
                                  key={item.val}
                                  type="button"
                                  onClick={() =>
                                    setRetryOptions((prev) => ({
                                      ...prev,
                                      limitSideLen: item.val,
                                    }))
                                  }
                                  className={`rounded-lg py-1 text-[11px] font-medium border text-center transition-all ${
                                    (retryOptions.limitSideLen ?? 1024) === item.val
                                      ? "border-indigo-500 bg-indigo-50 text-indigo-700 font-bold dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-600"
                                      : "border-zinc-200 text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
                                  }`}
                                >
                                  {item.label}
                                </button>
                              ))}
                            </div>
                            <p className="text-[10px] text-zinc-400 mt-0.5">
                              Chọn 1280px hoặc 1536px đối với ảnh bài thi có chữ in nhỏ.
                            </p>
                          </div>

                          {/* Toggles */}
                          <div className="space-y-2 pt-1">
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={retryOptions.enableClahe ?? true}
                                onChange={(e) =>
                                  setRetryOptions((prev) => ({
                                    ...prev,
                                    enableClahe: e.target.checked,
                                  }))
                                }
                                className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800"
                              />
                              <div>
                                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                  Tăng tương phản cục bộ (CLAHE)
                                </span>
                                <p className="text-[10px] text-zinc-400">
                                  Cân bằng độ sáng khi chụp bị bóng mờ
                                </p>
                              </div>
                            </label>

                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={retryOptions.splitTallBoxes ?? true}
                                onChange={(e) =>
                                  setRetryOptions((prev) => ({
                                    ...prev,
                                    splitTallBoxes: e.target.checked,
                                  }))
                                }
                                className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500 dark:border-zinc-700 dark:bg-zinc-800"
                              />
                              <div>
                                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                                  Tách khối chữ cao (Auto-split)
                                </span>
                                <p className="text-[10px] text-zinc-400">
                                  Tự động tách nếu phát hiện nhiều dòng bị gộp chung
                                </p>
                              </div>
                            </label>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-3 border-t border-zinc-100 dark:border-zinc-800">
                      <button
                        type="button"
                        onClick={handleResetDefaults}
                        className="inline-flex items-center gap-1 text-[11px] font-medium text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
                      >
                        <RotateCcw className="h-3 w-3" />
                        Mặc định
                      </button>

                      <button
                        type="button"
                        onClick={() => handleApplyRetry()}
                        disabled={currentPage.status === "scanning"}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 transition-all disabled:opacity-50"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Áp dụng & Quét lại
                      </button>
                    </div>
                  </div>
                )}
              </div>

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
