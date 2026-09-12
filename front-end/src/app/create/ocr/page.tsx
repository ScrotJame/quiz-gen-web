"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  StudioHeader,
} from "../../../components/studio/StudioHeader";
import { Filmstrip } from "../../../components/studio/Filmstrip";
import { SplitScreen } from "../../../components/studio/SplitScreen";
import { MergeCleanPanel } from "../../../components/studio/MergeCleanPanel";
import { QuizEditor } from "../../../components/studio/QuizEditor";
import {
  Difficulty,
  QuestionEdit,
  QuizCreatePayload,
  StudioPageItem,
} from "../../../lib/types";
import {
  cleanText,
  createQuiz,
  generateQuizFromText,
  ocrPage,
} from "../../../lib/api-client";
import { AlertCircle, RotateCcw, X } from "lucide-react";

const DRAFT_STORAGE_KEY = "ocr_studio_draft_v1";

interface SavedDraft {
  step: 1 | 2 | 3;
  title: string;
  category: string;
  numQuestions: number;
  difficulty: Difficulty;
  temperature: number;
  mergedText: string;
  hasCleaned: boolean;
  pagesText: { id: string; text: string; rotation: number }[];
  questions: QuestionEdit[];
  timestamp: string;
}

export default function OcrStudioPage() {
  const router = useRouter();

  // Step state (1: Quét, 2: Chuẩn hóa & Hợp nhất, 3: Biên tập)
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Pages state
  const [pages, setPages] = useState<StudioPageItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  // Merged & AI Clean state
  const [mergedText, setMergedText] = useState<string>("");
  const [isCleaning, setIsCleaning] = useState<boolean>(false);
  const [hasCleaned, setHasCleaned] = useState<boolean>(false);

  // Quiz config state
  const [title, setTitle] = useState<string>("");
  const [category, setCategory] = useState<string>("Chung");
  const [numQuestions, setNumQuestions] = useState<number>(5);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [temperature, setTemperature] = useState<number>(0.3);

  // AI Generation & Editor state
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [questions, setQuestions] = useState<QuestionEdit[]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Auto-save & drafts
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [draftPrompt, setDraftPrompt] = useState<SavedDraft | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (saved) {
        const parsed: SavedDraft = JSON.parse(saved);
        if (
          parsed &&
          (parsed.pagesText?.length > 0 || parsed.mergedText?.trim().length > 0)
        ) {
          return parsed;
        }
      }
    } catch (err) {
      console.error("Lỗi khi đọc draft localStorage:", err);
    }
    return null;
  });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Track if scanning
  const isScanningAny = pages.some((p) => p.status === "scanning");

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Auto-save draft debounced
  useEffect(() => {
    if (pages.length === 0 && !mergedText.trim() && questions.length === 0) {
      return;
    }

    const timer = setTimeout(() => {
      try {
        const draft: SavedDraft = {
          step,
          title,
          category,
          numQuestions,
          difficulty,
          temperature,
          mergedText,
          hasCleaned,
          pagesText: pages.map((p) => ({
            id: p.id,
            text: p.text,
            rotation: p.rotation,
          })),
          questions,
          timestamp: new Date().toISOString(),
        };
        localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
        setLastSavedAt(new Date());
      } catch (err) {
        console.error("Lỗi khi lưu nháp:", err);
      }
    }, 1500);

    return () => clearTimeout(timer);
  }, [
    step,
    pages,
    mergedText,
    hasCleaned,
    title,
    category,
    numQuestions,
    difficulty,
    temperature,
    questions,
  ]);

  // Restore Draft
  const handleRestoreDraft = (draft: SavedDraft) => {
    setTitle(draft.title || "");
    setCategory(draft.category || "Chung");
    setNumQuestions(draft.numQuestions || 5);
    setDifficulty(draft.difficulty || "medium");
    setTemperature(draft.temperature ?? 0.3);
    setMergedText(draft.mergedText || "");
    setHasCleaned(draft.hasCleaned || false);
    setQuestions(draft.questions || []);
    setStep(draft.step || 1);
    setDraftPrompt(null);
    showToast("Đã khôi phục phiên làm việc trước đó!");
  };

  const handleDismissDraft = () => {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
    setDraftPrompt(null);
  };

  // Process OCR for a single page item
  const processOcrForPage = async (pageItem: StudioPageItem) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === pageItem.id
          ? { ...p, status: "scanning", errorMessage: undefined }
          : p
      )
    );

    try {
      const res = await ocrPage(pageItem.file);
      setPages((prev) =>
        prev.map((p) =>
          p.id === pageItem.id
            ? {
                ...p,
                status: "success",
                text: res.text,
                lineCount: res.lineCount,
                confidence: res.averageConfidence,
              }
            : p
        )
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Lỗi không xác định khi OCR";
      setPages((prev) =>
        prev.map((p) =>
          p.id === pageItem.id
            ? {
                ...p,
                status: "error",
                errorMessage: msg,
              }
            : p
        )
      );
    }
  };

  // Add files
  const handleAddFiles = (filesInput: FileList | File[]) => {
    const fileArray = Array.from(filesInput);
    const validFiles: File[] = [];

    for (const f of fileArray) {
      if (!f.type.startsWith("image/")) {
        showToast(`File "${f.name}" không phải ảnh. Vui lòng chọn PNG/JPG.`);
        continue;
      }
      if (f.size > 10 * 1024 * 1024) {
        showToast(`File "${f.name}" vượt quá 10MB.`);
        continue;
      }
      validFiles.push(f);
    }

    if (validFiles.length === 0) return;

    const newPages: StudioPageItem[] = validFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      previewUrl: URL.createObjectURL(file),
      rotation: 0,
      status: "idle",
      text: "",
      lineCount: 0,
      confidence: 0,
    }));

    setPages((prev) => {
      const next = [...prev, ...newPages];
      return next;
    });

    // Run OCR in parallel for each added page
    newPages.forEach((item) => {
      processOcrForPage(item);
    });
  };

  // Rotate page
  const handleRotatePage = (index: number) => {
    setPages((prev) => {
      const next = [...prev];
      if (next[index]) {
        next[index] = {
          ...next[index],
          rotation: (next[index].rotation + 90) % 360,
        };
      }
      return next;
    });
  };

  // Delete page
  const handleDeletePage = (index: number) => {
    setPages((prev) => {
      const next = prev.filter((_, i) => i !== index);
      return next;
    });
    setSelectedIndex((prev) => (prev >= index ? Math.max(0, prev - 1) : prev));
  };

  // Move page up / down
  const handleMovePage = (index: number, direction: "up" | "down") => {
    setPages((prev) => {
      const next = [...prev];
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return prev;
      const [removed] = next.splice(index, 1);
      next.splice(targetIndex, 0, removed);
      return next;
    });
    setSelectedIndex((prev) =>
      direction === "up"
        ? prev === index
          ? index - 1
          : prev
        : prev === index
        ? index + 1
        : prev
    );
  };

  // Retry page OCR
  const handleRetryPage = (index: number) => {
    const target = pages[index];
    if (target) {
      processOcrForPage(target);
    }
  };

  // Text change for single page
  const handleTextChange = (index: number, newText: string) => {
    setPages((prev) => {
      const next = [...prev];
      if (next[index]) {
        next[index] = { ...next[index], text: newText };
      }
      return next;
    });
  };

  // Proceed to Step 2 (Merge & Clean)
  const handleProceedToStep2 = () => {
    // Merge all page texts in order
    const merged = pages
      .map((p, i) => {
        const header = pages.length > 1 ? `[Trang ${i + 1}]\n` : "";
        return `${header}${p.text.trim()}`;
      })
      .filter((t) => t.length > 0)
      .join("\n\n");

    setMergedText(merged);
    if (!title) {
      // Auto-extract candidate title from first line
      const firstLine = pages[0]?.text.trim().split("\n")[0] || "";
      if (firstLine && firstLine.length < 80) {
        setTitle(firstLine.replace(/^[0-9.\-–\s]+/, ""));
      } else {
        setTitle(`Đề thi từ tài liệu (${pages.length} trang)`);
      }
    }
    setStep(2);
  };

  // Step 2: Clean Text with AI
  const handleCleanWithAi = async (targetLang: string) => {
    if (!mergedText.trim()) return;
    setIsCleaning(true);
    try {
      const res = await cleanText(mergedText, targetLang);
      setMergedText(res.cleanedText);
      setHasCleaned(true);
      showToast("AI đã chuẩn hóa văn bản và nối liền câu liên trang thành công!");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi khi gọi AI Clean";
      showToast(msg);
    } finally {
      setIsCleaning(false);
    }
  };

  // Step 2: Generate Quiz with AI
  const handleGenerateQuiz = async () => {
    if (!mergedText.trim()) return;
    setIsGenerating(true);
    try {
      const res = await generateQuizFromText({
        topic: category,
        content: mergedText,
        numQuestions,
        difficulty,
        temperature,
        saveImmediately: false,
        authorName: "OCR Studio + Mistral",
      });

      if (res.title) setTitle(res.title);

      // Convert generated questions to editable questions
      const parsedQuestions: QuestionEdit[] = (res.questions || []).map((q) => ({
        id: crypto.randomUUID(),
        questionText: q.questionText,
        questionType: q.questionType || "single_choice",
        points: q.points || 10,
        explanation: q.explanation || "",
        options: (q.options || []).map((opt) => ({
          optionText: opt.optionText,
          isCorrect: Boolean(opt.isCorrect),
        })),
      }));

      setQuestions(parsedQuestions);
      setStep(3);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Lỗi khi sinh câu hỏi bằng AI";
      showToast(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  // Step 3: Save quiz payload
  const buildSavePayload = (): QuizCreatePayload => {
    return {
      title: title.trim() || "Đề thi trắc nghiệm không tên",
      description: `Đề thi trắc nghiệm được tạo tự động từ OCR Studio (${pages.length} trang ảnh).`,
      category: category || "Chung",
      difficulty,
      timeLimitMinutes: Math.max(5, questions.length * 2),
      authorName: "OCR Studio",
      isPublished: true,
      questions: questions.map((q, idx) => ({
        questionText: q.questionText,
        questionType: q.questionType,
        points: q.points || 10,
        orderNum: idx + 1,
        explanation: q.explanation || null,
        options: q.options.map((opt, oIdx) => ({
          optionText: opt.optionText,
          isCorrect: opt.isCorrect,
          orderNum: oIdx + 1,
        })),
      })),
    };
  };

  // Save to Library & return to Dashboard
  const handleSaveToLibrary = async () => {
    if (questions.length === 0) return;
    setIsSaving(true);
    try {
      const payload = buildSavePayload();
      await createQuiz(payload);
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      showToast("Đã lưu đề thi vào Thư viện thành công!");
      router.push("/");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi khi lưu đề thi";
      showToast(msg);
      setIsSaving(false);
    }
  };

  // Save & Start Attempt immediately
  const handleSaveAndPlay = async () => {
    if (questions.length === 0) return;
    setIsSaving(true);
    try {
      const payload = buildSavePayload();
      const created = await createQuiz(payload);
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      showToast("Đã lưu đề thi! Đang chuyển đến phòng thi...");
      router.push(`/quiz/${created.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi khi lưu đề thi";
      showToast(msg);
      setIsSaving(false);
    }
  };

  // Step navigation permissions
  const canNavigateToStep = (targetStep: 1 | 2 | 3) => {
    if (targetStep === 1) return true;
    if (targetStep === 2) return pages.length > 0 && pages.some((p) => p.text.trim().length > 0);
    if (targetStep === 3) return questions.length > 0;
    return false;
  };

  const handleBackClick = () => {
    if (pages.length > 0 || questions.length > 0) {
      if (
        window.confirm(
          "Bạn có chắc muốn thoát khỏi Studio? Bản nháp hiện tại đã được tự động lưu trên máy này."
        )
      ) {
        router.push("/");
      }
    } else {
      router.push("/");
    }
  };

  const canContinueToStep2 =
    pages.length > 0 && pages.some((p) => p.text.trim().length > 0) && !isScanningAny;

  return (
    <div className="flex min-h-screen flex-col bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {/* Top Header & Stepper */}
      <StudioHeader
        currentStep={step}
        onStepChange={(s) => setStep(s)}
        canNavigateToStep={canNavigateToStep}
        onBackClick={handleBackClick}
        lastSavedAt={lastSavedAt}
      />

      {/* Restore Draft Modal Alert */}
      {draftPrompt && (
        <div className="border-b border-indigo-200 bg-indigo-50/90 px-4 py-2.5 dark:border-indigo-900/60 dark:bg-indigo-950/70">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-indigo-900 dark:text-indigo-200">
              <RotateCcw className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <span>
                Tìm thấy bản quét dở trước đó (
                <strong>
                  {new Date(draftPrompt.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </strong>
                ). Bạn có muốn khôi phục không?
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleRestoreDraft(draftPrompt)}
                className="rounded-lg bg-indigo-600 px-3 py-1 text-xs font-bold text-white hover:bg-indigo-500 shadow-xs cursor-pointer"
              >
                Khôi phục
              </button>
              <button
                type="button"
                onClick={handleDismissDraft}
                className="rounded-lg border border-zinc-300 px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
              >
                Bỏ qua
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-16 right-4 z-50 flex items-center gap-2 rounded-xl border border-zinc-300 bg-white/95 px-4 py-3 text-xs font-semibold text-zinc-800 shadow-xl backdrop-blur-md dark:border-zinc-700 dark:bg-zinc-900/95 dark:text-zinc-100 animate-in fade-in slide-in-from-bottom-2">
          <AlertCircle className="h-4 w-4 text-indigo-600 shrink-0" />
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-zinc-400 hover:text-zinc-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Main Studio Body Based on Step */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {step === 1 && (
          <div className="flex flex-1 flex-col md:flex-row overflow-hidden">
            {/* Filmstrip Left Sidebar */}
            <Filmstrip
              pages={pages}
              selectedIndex={selectedIndex}
              onSelectPage={(idx) => setSelectedIndex(idx)}
              onAddFiles={handleAddFiles}
              onRotatePage={handleRotatePage}
              onDeletePage={handleDeletePage}
              onMovePage={handleMovePage}
              onRetryPage={handleRetryPage}
            />

            {/* Split Screen Center View */}
            <SplitScreen
              pages={pages}
              selectedIndex={selectedIndex}
              onSelectPage={(idx) => setSelectedIndex(idx)}
              onTextChange={handleTextChange}
              onRotatePage={handleRotatePage}
              onRetryPage={handleRetryPage}
              onContinue={handleProceedToStep2}
              canContinue={canContinueToStep2}
            />
          </div>
        )}

        {step === 2 && (
          <MergeCleanPanel
            mergedText={mergedText}
            onMergedTextChange={setMergedText}
            onCleanWithAi={handleCleanWithAi}
            isCleaning={isCleaning}
            hasCleaned={hasCleaned}
            title={title}
            onTitleChange={setTitle}
            category={category}
            onCategoryChange={setCategory}
            numQuestions={numQuestions}
            onNumQuestionsChange={setNumQuestions}
            difficulty={difficulty}
            onDifficultyChange={setDifficulty}
            temperature={temperature}
            onTemperatureChange={setTemperature}
            onBackToStep1={() => setStep(1)}
            onGenerateQuiz={handleGenerateQuiz}
            isGenerating={isGenerating}
            pageCount={pages.length || 1}
          />
        )}

        {step === 3 && (
          <QuizEditor
            questions={questions}
            onQuestionsChange={setQuestions}
            title={title}
            category={category}
            onBackToStep2={() => setStep(2)}
            onSaveToLibrary={handleSaveToLibrary}
            onSaveAndPlay={handleSaveAndPlay}
            isSaving={isSaving}
          />
        )}
      </main>
    </div>
  );
}
