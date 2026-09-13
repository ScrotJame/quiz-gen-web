"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { StudioHeader } from "../../../components/studio/StudioHeader";
import { Filmstrip } from "../../../components/studio/Filmstrip";
import { SplitScreen } from "../../../components/studio/SplitScreen";
import { MergeCleanPanel } from "../../../components/studio/MergeCleanPanel";
import { BankReviewPanel } from "../../../components/studio/BankReviewPanel";
import { QuizEditor } from "../../../components/studio/QuizEditor";
import {
  BankQuestionCreate,
  Difficulty,
  OcrRetryOptions,
  QuestionEdit,
  QuizCreatePayload,
  StudioPageItem,
} from "../../../lib/types";
import {
  batchCreateBankQuestions,
  cleanText,
  createQuiz,
  generateQuizFromText,
  ocrPage,
} from "../../../lib/api-client";
import { AlertCircle, RotateCcw, X } from "lucide-react";

const DRAFT_STORAGE_KEY = "ocr_studio_draft_v2";

interface SavedDraft {
  step: 1 | 2 | 3 | 4;
  title: string;
  category: string;
  numQuestions: number;
  difficulty: Difficulty;
  temperature: number;
  mergedText: string;
  hasCleaned: boolean;
  pagesText: { id: string; text: string; rotation: number }[];
  /** Câu hỏi trích xuất từ AI — ở Bước 3 chờ lưu vào Bank */
  bankQuestions: BankQuestionCreate[];
  /** Câu hỏi đã được nạp vào đề thi ở Bước 4 */
  questions: QuestionEdit[];
  /** true nếu đã lưu vào Bank thành công (mở khoá Bước 4) */
  bankSaved: boolean;
  timestamp: string;
}

export default function OcrStudioPage() {
  const router = useRouter();

  // Step state (1: Quét, 2: Chuẩn hóa & Hợp nhất, 3: Duyệt & Lưu Thư viện, 4: Biên tập đề thi)
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

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

  // Bước 3: Ngân hàng câu hỏi (chờ duyệt)
  const [bankQuestions, setBankQuestions] = useState<BankQuestionCreate[]>([]);
  const [isSavingBank, setIsSavingBank] = useState<boolean>(false);
  const [bankSaved, setBankSaved] = useState<boolean>(false);

  // Bước 4: Editor
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
    if (pages.length === 0 && !mergedText.trim() && questions.length === 0 && bankQuestions.length === 0) {
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
          bankQuestions,
          questions,
          bankSaved,
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
    step, pages, mergedText, hasCleaned, title, category,
    numQuestions, difficulty, temperature, bankQuestions, questions, bankSaved,
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
    setBankQuestions(draft.bankQuestions || []);
    setQuestions(draft.questions || []);
    setBankSaved(draft.bankSaved || false);
    setStep(draft.step || 1);
    setDraftPrompt(null);
    showToast("Đã khôi phục phiên làm việc trước đó!");
  };

  const handleDismissDraft = () => {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
    setDraftPrompt(null);
  };

  // Process OCR for a single page item
  const processOcrForPage = async (pageItem: StudioPageItem, options?: OcrRetryOptions) => {
    setPages((prev) =>
      prev.map((p) =>
        p.id === pageItem.id
          ? { ...p, status: "scanning", errorMessage: undefined }
          : p
      )
    );

    try {
      const res = await ocrPage(pageItem.file, options);
      setPages((prev) =>
        prev.map((p) =>
          p.id === pageItem.id
            ? {
                ...p,
                status: "success",
                text: res.text,
                lineCount: res.lineCount,
                confidence: res.averageConfidence,
                provider: res.provider,
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
            ? { ...p, status: "error", errorMessage: msg }
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

    setPages((prev) => [...prev, ...newPages]);
    newPages.forEach((item) => processOcrForPage(item));
  };

  const handleRotatePage = (index: number) => {
    setPages((prev) => {
      const next = [...prev];
      if (next[index]) {
        next[index] = { ...next[index], rotation: (next[index].rotation + 90) % 360 };
      }
      return next;
    });
  };

  const handleDeletePage = (index: number) => {
    setPages((prev) => prev.filter((_, i) => i !== index));
    setSelectedIndex((prev) => (prev >= index ? Math.max(0, prev - 1) : prev));
  };

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
        ? prev === index ? index - 1 : prev
        : prev === index ? index + 1 : prev
    );
  };

  const handleRetryPage = (index: number, options?: OcrRetryOptions) => {
    const target = pages[index];
    if (target) processOcrForPage(target, options);
  };

  const handleTextChange = (index: number, newText: string) => {
    setPages((prev) => {
      const next = [...prev];
      if (next[index]) next[index] = { ...next[index], text: newText };
      return next;
    });
  };

  // Proceed to Step 2 (Merge & Clean)
  const handleProceedToStep2 = () => {
    const merged = pages
      .map((p, i) => {
        const header = pages.length > 1 ? `[Trang ${i + 1}]\n` : "";
        return `${header}${p.text.trim()}`;
      })
      .filter((t) => t.length > 0)
      .join("\n\n");

    setMergedText(merged);
    if (!title) {
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
      showToast(err instanceof Error ? err.message : "Lỗi khi gọi AI Clean");
    } finally {
      setIsCleaning(false);
    }
  };

  // Step 2 -> Step 3: Generate questions with AI, display on BankReviewPanel
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
        authorName: "OCR Studio + AI",
      });

      if (res.title) setTitle(res.title);

      // Chuyển sang BankQuestionCreate để hiển thị ở Bước 3
      const extracted: BankQuestionCreate[] = (res.questions || []).map((q) => ({
        questionText: q.questionText,
        questionType: q.questionType || "single_choice",
        category,
        difficulty,
        explanation: q.explanation || "",
        sourceNote: `OCR Studio – ${pages.length} trang ảnh`,
        options: (q.options || []).map((opt, idx) => ({
          optionText: opt.optionText,
          isCorrect: Boolean(opt.isCorrect),
          orderNum: idx,
        })),
      }));

      setBankQuestions(extracted);
      setBankSaved(false);
      setStep(3);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Lỗi khi sinh câu hỏi bằng AI");
    } finally {
      setIsGenerating(false);
    }
  };

  // Step 3: Save bank questions and proceed to Step 4
  const handleSaveToBank = async () => {
    if (bankQuestions.length === 0) return;
    setIsSavingBank(true);
    try {
      await batchCreateBankQuestions({ questions: bankQuestions });
      setBankSaved(true);

      // Clone bankQuestions sang QuestionEdit để nạp sẵn vào Bước 4
      const preloaded: QuestionEdit[] = bankQuestions.map((q) => ({
        id: crypto.randomUUID(),
        questionText: q.questionText,
        questionType: q.questionType || "single_choice",
        points: 10,
        explanation: q.explanation || "",
        options: q.options.map((opt) => ({
          optionText: opt.optionText,
          isCorrect: opt.isCorrect,
        })),
      }));
      setQuestions(preloaded);

      showToast(`Đã lưu ${bankQuestions.length} câu hỏi vào Thư viện! Đang chuyển sang Biên tập đề thi...`);
      setTimeout(() => setStep(4), 800);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Lỗi khi lưu vào Thư viện câu hỏi");
    } finally {
      setIsSavingBank(false);
    }
  };

  // Step 4: Build save payload
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
      showToast(err instanceof Error ? err.message : "Lỗi khi lưu đề thi");
      setIsSaving(false);
    }
  };

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
      showToast(err instanceof Error ? err.message : "Lỗi khi lưu đề thi");
      setIsSaving(false);
    }
  };

  // Step navigation permissions
  const canNavigateToStep = (targetStep: 1 | 2 | 3 | 4) => {
    if (targetStep === 1) return true;
    if (targetStep === 2) return pages.length > 0 && pages.some((p) => p.text.trim().length > 0);
    if (targetStep === 3) return bankQuestions.length > 0;
    if (targetStep === 4) return bankSaved && questions.length > 0;
    return false;
  };

  const handleBackClick = () => {
    if (pages.length > 0 || questions.length > 0 || bankQuestions.length > 0) {
      if (window.confirm("Bạn có chắc muốn thoát khỏi Studio? Bản nháp hiện tại đã được tự động lưu trên máy này.")) {
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
          <BankReviewPanel
            questions={bankQuestions}
            onQuestionsChange={setBankQuestions}
            defaultCategory={category}
            isSaving={isSavingBank}
            onSaveToBank={handleSaveToBank}
            onBackToStep2={() => setStep(2)}
          />
        )}

        {step === 4 && (
          <QuizEditor
            questions={questions}
            onQuestionsChange={setQuestions}
            title={title}
            category={category}
            onBackToStep2={() => setStep(3)}
            onSaveToLibrary={handleSaveToLibrary}
            onSaveAndPlay={handleSaveAndPlay}
            isSaving={isSaving}
          />
        )}
      </main>
    </div>
  );
}
