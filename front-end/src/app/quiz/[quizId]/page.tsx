"use client";

import React, { use, useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, AlertCircle, Play, ArrowLeft, ArrowRight, ListOrdered, CheckCircle2 } from "lucide-react";
import { QuizHeader } from "../../../components/quiz/QuizHeader";
import { ProgressBar } from "../../../components/quiz/ProgressBar";
import { QuestionCard } from "../../../components/quiz/QuestionCard";
import { QuestionNavigator } from "../../../components/quiz/QuestionNavigator";
import { SubmitConfirmModal } from "../../../components/quiz/SubmitConfirmModal";
import { QuizResultView } from "../../../components/quiz/QuizResultView";
import {
  getQuizDetail,
  startAttempt,
  submitAttempt,
} from "../../../lib/api-client";
import {
  QuizDetail,
  AttemptResult,
  AnswerSubmission,
} from "../../../lib/types";

interface PageProps {
  params: Promise<{ quizId: string }>;
}

export default function QuizTakingPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const quizId = resolvedParams.quizId;
  const router = useRouter();

  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [attempt, setAttempt] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State bài làm
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [flaggedIds, setFlaggedIds] = useState<string[]>([]);
  const [autoSavedAt, setAutoSavedAt] = useState<Date | null>(null);

  // State Timer
  const [timeRemaining, setTimeRemaining] = useState<number>(900); // 15 phút mặc định
  const [isTimerVisible, setIsTimerVisible] = useState(true);
  const [isPaused, setIsPaused] = useState(false);

  // State Modal nộp bài & Kết quả
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<AttemptResult | null>(null);

  // Mobile drawer & swipe gesture state
  const [isNavigatorDrawerOpen, setIsNavigatorDrawerOpen] = useState(false);
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.touches[0].clientX);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX === null) return;
    const touchEndX = e.changedTouches[0].clientX;
    const diff = touchStartX - touchEndX;
    // Swipe horizontal threshold 60px
    if (diff > 60) {
      handleNext();
    } else if (diff < -60) {
      handlePrev();
    }
    setTouchStartX(null);
  };

  // 1. Tải đề thi và khởi tạo lượt thi
  useEffect(() => {
    let ignore = false;

    async function initialize() {
      try {
        setLoading(true);
        setError(null);

        // Lấy thông tin quiz từ backend
        const quizData = await getQuizDetail(quizId);
        if (ignore) return;
        setQuiz(quizData);

        // Đặt thời gian theo cấu hình đề
        const initialSeconds = (quizData.timeLimitMinutes || 15) * 60;
        setTimeRemaining(initialSeconds);

        // Khôi phục nháp từ localStorage nếu có
        const storageKey = `quiz_session_${quizId}`;
        const savedSession = localStorage.getItem(storageKey);
        let currentAttempt: AttemptResult | null = null;

        if (savedSession) {
          try {
            const parsed = JSON.parse(savedSession);
            if (parsed.attempt) currentAttempt = parsed.attempt;
            if (parsed.answers) setAnswers(parsed.answers);
            if (parsed.flaggedIds) setFlaggedIds(parsed.flaggedIds);
            if (parsed.currentIndex !== undefined)
              setCurrentIndex(parsed.currentIndex);
            if (parsed.timeRemaining !== undefined && parsed.timeRemaining > 0) {
              setTimeRemaining(parsed.timeRemaining);
            }
            setAutoSavedAt(new Date());
          } catch {
            // Không parse được thì bỏ qua
          }
        }

        // Nếu chưa có attempt hợp lệ, gọi backend startAttempt
        if (!currentAttempt) {
          currentAttempt = await startAttempt(quizId, "Thí sinh");
        }

        if (!ignore) {
          setAttempt(currentAttempt);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(
            err instanceof Error ? err.message : "Không thể tải đề thi"
          );
          setLoading(false);
        }
      }
    }

    initialize();

    return () => {
      ignore = true;
    };
  }, [quizId]);

  // 2. Tự động lưu bài làm vào localStorage
  useEffect(() => {
    if (!quiz || !attempt) return;
    const timeout = setTimeout(() => {
      try {
        const storageKey = `quiz_session_${quizId}`;
        const payload = {
          attempt,
          answers,
          flaggedIds,
          currentIndex,
          timeRemaining,
          updatedAt: new Date().toISOString(),
        };
        localStorage.setItem(storageKey, JSON.stringify(payload));
        setAutoSavedAt(new Date());
      } catch {
        // storage quota exceeded or disabled
      }
    }, 400);

    return () => clearTimeout(timeout);
  }, [quizId, attempt, answers, flaggedIds, currentIndex, timeRemaining, quiz]);

  // 3. Quản lý đồng hồ đếm ngược Timer
  useEffect(() => {
    if (loading || isPaused || submitResult || timeRemaining <= 0) {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      return;
    }

    timerIntervalRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
          setIsSubmitModalOpen(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [loading, isPaused, submitResult, timeRemaining]);

  // Lấy câu hỏi hiện tại
  const currentQuestion = quiz?.questions[currentIndex];
  const totalQuestions = quiz?.questions.length || 0;

  // Xử lý chọn đáp án
  const handleSelectOption = useCallback(
    (optionId: string) => {
      if (!currentQuestion) return;
      const qId = currentQuestion.id;
      const isMultiple = currentQuestion.questionType === "multiple_choice";

      setAnswers((prev) => {
        const currentSelections = prev[qId] || [];
        if (isMultiple) {
          if (currentSelections.includes(optionId)) {
            return {
              ...prev,
              [qId]: currentSelections.filter((id) => id !== optionId),
            };
          } else {
            return {
              ...prev,
              [qId]: [...currentSelections, optionId],
            };
          }
        } else {
          // Single choice
          return {
            ...prev,
            [qId]: [optionId],
          };
        }
      });
    },
    [currentQuestion]
  );

  // Xóa đáp án của câu hỏi
  const handleClearAnswer = useCallback(() => {
    if (!currentQuestion) return;
    const qId = currentQuestion.id;
    setAnswers((prev) => {
      const next = { ...prev };
      delete next[qId];
      return next;
    });
  }, [currentQuestion]);

  // Gắn cờ câu hỏi
  const handleToggleFlag = useCallback(() => {
    if (!currentQuestion) return;
    const qId = currentQuestion.id;
    setFlaggedIds((prev) =>
      prev.includes(qId) ? prev.filter((id) => id !== qId) : [...prev, qId]
    );
  }, [currentQuestion]);

  // Điều hướng Previous / Next
  const handlePrev = useCallback(() => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => Math.min(totalQuestions - 1, prev + 1));
  }, [totalQuestions]);

  // 4. Lắng nghe phím tắt bàn phím
  useEffect(() => {
    if (isSubmitModalOpen || submitResult || isPaused) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Bỏ qua nếu đang gõ trong input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNext();
      } else if (e.key.toLowerCase() === "f") {
        e.preventDefault();
        handleToggleFlag();
      } else if (["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        const optIndex = parseInt(e.key, 10) - 1;
        if (currentQuestion && currentQuestion.options[optIndex]) {
          handleSelectOption(currentQuestion.options[optIndex].id);
        }
      } else if (["a", "b", "c", "d"].includes(e.key.toLowerCase())) {
        e.preventDefault();
        const letterMap: Record<string, number> = { a: 0, b: 1, c: 2, d: 3 };
        const optIndex = letterMap[e.key.toLowerCase()];
        if (currentQuestion && currentQuestion.options[optIndex]) {
          handleSelectOption(currentQuestion.options[optIndex].id);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isSubmitModalOpen,
    submitResult,
    isPaused,
    handlePrev,
    handleNext,
    handleToggleFlag,
    handleSelectOption,
    currentQuestion,
  ]);

  // 5. Nộp bài thi
  const handleConfirmSubmit = async () => {
    if (!attempt || !quiz) return;
    setIsSubmitting(true);
    try {
      const submissionList: AnswerSubmission[] = quiz.questions.map((q) => ({
        questionId: q.id,
        selectedOptionIds: answers[q.id] || [],
      }));

      const res = await submitAttempt(attempt.id, submissionList);
      setSubmitResult(res);
      setIsSubmitModalOpen(false);

      // Xóa nháp sau khi nộp thành công
      localStorage.removeItem(`quiz_session_${quizId}`);
    } catch (err: unknown) {
      alert(
        err instanceof Error ? err.message : "Đã xảy ra lỗi khi nộp bài thi."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // Làm lại bài thi
  const handleRetry = async () => {
    localStorage.removeItem(`quiz_session_${quizId}`);
    setSubmitResult(null);
    setAnswers({});
    setFlaggedIds([]);
    setCurrentIndex(0);
    setTimeRemaining((quiz?.timeLimitMinutes || 15) * 60);
    setIsPaused(false);
    try {
      const newAttempt = await startAttempt(quizId, "Thí sinh");
      setAttempt(newAttempt);
    } catch {
      // fallback
    }
  };

  // Thoát về Dashboard
  const handleExit = () => {
    if (
      Object.keys(answers).length > 0 &&
      !confirm("Tiến độ làm bài đã được tự động lưu. Bạn có muốn quay về Dashboard?")
    ) {
      return;
    }
    router.push("/");
  };

  // Thống kê câu đã làm / gắn cờ
  const answeredCount = Object.keys(answers).filter(
    (qId) => (answers[qId] || []).length > 0
  ).length;
  const flaggedCount = flaggedIds.length;

  // -------------------------------------------------------------
  // Màn hình Loading / Error
  // -------------------------------------------------------------
  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-600 dark:text-indigo-400" />
        <p className="mt-4 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Đang tải đề thi và thiết lập phòng thi...
        </p>
      </div>
    );
  }

  if (error || !quiz) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h2 className="mt-4 text-xl font-bold text-zinc-900 dark:text-white">
          Không thể tải bài thi
        </h2>
        <p className="mt-2 max-w-md text-sm text-zinc-500 dark:text-zinc-400">
          {error || "Đề thi không tồn tại hoặc đã bị xóa khỏi hệ thống."}
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-indigo-500"
        >
          Quay lại Dashboard
        </Link>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Màn hình Kết Quả sau khi Nộp Bài
  // -------------------------------------------------------------
  if (submitResult) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 pb-16">
        <QuizResultView
          quiz={quiz}
          result={submitResult}
          onRetry={handleRetry}
        />
      </div>
    );
  }

  // -------------------------------------------------------------
  // Giao diện Làm Bài Thi (Quiz Taking)
  // -------------------------------------------------------------
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50/60 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {/* 1. Header (Timer, Auto-save status, Submit button) */}
      <QuizHeader
        title={quiz.title}
        category={quiz.category}
        timeRemaining={timeRemaining}
        isTimerVisible={isTimerVisible}
        onToggleTimerVisibility={() => setIsTimerVisible((prev) => !prev)}
        isPaused={isPaused}
        onTogglePause={() => setIsPaused((prev) => !prev)}
        autoSavedAt={autoSavedAt}
        onSubmitClick={() => setIsSubmitModalOpen(true)}
        onExitClick={handleExit}
      />

      {/* 2. Progress Bar */}
      <ProgressBar
        currentIndex={currentIndex}
        totalQuestions={totalQuestions}
        answeredCount={answeredCount}
        flaggedCount={flaggedCount}
      />

      {/* 3. Main Body */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
        {/* Paused Overlay Screen */}
        {isPaused ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-zinc-200 bg-white/95 py-24 text-center shadow-lg backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-900/95">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
              <Play className="h-8 w-8 fill-current translate-x-0.5" />
            </div>
            <h3 className="mt-4 text-xl font-bold text-zinc-900 dark:text-white">
              Bài thi đang tạm dừng
            </h3>
            <p className="mt-1 text-sm text-zinc-500 max-w-sm">
              Đồng hồ đếm ngược đã tạm dừng. Bạn có thể nhấn tiếp tục bất cứ lúc nào.
            </p>
            <button
              type="button"
              onClick={() => setIsPaused(false)}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500"
            >
              <Play className="h-4 w-4 fill-current" />
              <span>Tiếp tục làm bài</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
            {/* Left/Center: Question Card with touch gestures */}
            <div
              className="lg:col-span-8 space-y-4 touch-pan-y"
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              {currentQuestion ? (
                <QuestionCard
                  question={currentQuestion}
                  index={currentIndex}
                  totalQuestions={totalQuestions}
                  selectedOptionIds={answers[currentQuestion.id] || []}
                  isFlagged={flaggedIds.includes(currentQuestion.id)}
                  onToggleFlag={handleToggleFlag}
                  onSelectOption={handleSelectOption}
                  onClearAnswer={handleClearAnswer}
                  onPrev={handlePrev}
                  onNext={handleNext}
                  hasPrev={currentIndex > 0}
                  hasNext={currentIndex < totalQuestions - 1}
                  onSubmitPrompt={() => setIsSubmitModalOpen(true)}
                />
              ) : null}

              {/* Keyboard Shortcuts Hint Bar */}
              <div className="hidden sm:flex items-center justify-center gap-6 rounded-2xl bg-zinc-100/70 dark:bg-zinc-900/50 py-2.5 px-4 text-xs text-zinc-500 dark:text-zinc-400">
                <span className="flex items-center gap-1.5">
                  <kbd className="rounded bg-white dark:bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] shadow-xs">
                    1 - 4
                  </kbd>{" "}
                  hoặc{" "}
                  <kbd className="rounded bg-white dark:bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] shadow-xs">
                    A - D
                  </kbd>{" "}
                  Chọn đáp án
                </span>
                <span>•</span>
                <span className="flex items-center gap-1.5">
                  <kbd className="rounded bg-white dark:bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] shadow-xs">
                    F
                  </kbd>{" "}
                  Gắn cờ
                </span>
                <span>•</span>
                <span className="flex items-center gap-1.5">
                  <kbd className="rounded bg-white dark:bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] shadow-xs">
                    ←
                  </kbd>
                  <kbd className="rounded bg-white dark:bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] shadow-xs">
                    →
                  </kbd>{" "}
                  Chuyển câu
                </span>
              </div>
            </div>

            {/* Right: Question Navigator (Desktop only) */}
            <div className="hidden lg:block lg:col-span-4 sticky top-24">
              <QuestionNavigator
                totalQuestions={totalQuestions}
                currentIndex={currentIndex}
                onSelectIndex={(idx) => setCurrentIndex(idx)}
                isAnswered={(idx) => {
                  const q = quiz.questions[idx];
                  return q ? (answers[q.id] || []).length > 0 : false;
                }}
                isFlagged={(idx) => {
                  const q = quiz.questions[idx];
                  return q ? flaggedIds.includes(q.id) : false;
                }}
              />
            </div>
          </div>
        )}
      </main>

      {/* Mobile Sticky Bottom Action Bar (< lg) */}
      {!isPaused && (
        <div className="sticky bottom-0 z-30 lg:hidden w-full border-t border-zinc-200/90 bg-white/95 backdrop-blur-md px-3 py-2 shadow-lg dark:border-zinc-800/90 dark:bg-zinc-950/95 pb-safe">
          <div className="flex items-center justify-between gap-2">
            {/* Prev button */}
            <button
              type="button"
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className="inline-flex min-h-[42px] items-center gap-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-semibold text-zinc-700 shadow-xs hover:bg-zinc-50 disabled:opacity-40 disabled:pointer-events-none dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 active:scale-95 shrink-0"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Trước</span>
            </button>

            {/* Trigger Bottom Sheet to pick question */}
            <button
              type="button"
              onClick={() => setIsNavigatorDrawerOpen(true)}
              className="inline-flex min-h-[42px] flex-1 items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50/80 px-2.5 py-2 text-xs font-bold text-indigo-700 shadow-xs hover:bg-indigo-100/80 dark:border-indigo-900/60 dark:bg-indigo-950/60 dark:text-indigo-300 active:scale-95"
            >
              <ListOrdered className="h-4 w-4 shrink-0" />
              <span>Câu {currentIndex + 1}/{totalQuestions}</span>
              <span className="text-[10px] font-normal text-indigo-500 dark:text-indigo-400">
                ({answeredCount} đã làm)
              </span>
            </button>

            {/* Next or Submit Button */}
            {currentIndex < totalQuestions - 1 ? (
              <button
                type="button"
                onClick={handleNext}
                className="inline-flex min-h-[42px] items-center gap-1 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 active:scale-95 shrink-0"
              >
                <span>Sau</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsSubmitModalOpen(true)}
                className="inline-flex min-h-[42px] items-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-3.5 py-2 text-xs font-bold text-white shadow-md shadow-emerald-600/20 active:scale-95 shrink-0"
              >
                <span>Nộp bài</span>
                <CheckCircle2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Mobile Question Navigator Bottom Sheet Drawer */}
      {isNavigatorDrawerOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end lg:hidden bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div
            className="flex-1"
            onClick={() => setIsNavigatorDrawerOpen(false)}
          />
          <div className="rounded-t-3xl border-t border-zinc-200 bg-white p-4 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900 max-h-[85vh] overflow-y-auto pb-safe animate-in slide-in-from-bottom duration-300">
            <div className="mx-auto mb-3 h-1.5 w-12 rounded-full bg-zinc-300 dark:bg-zinc-700" />
            <QuestionNavigator
              totalQuestions={totalQuestions}
              currentIndex={currentIndex}
              onSelectIndex={(idx) => {
                setCurrentIndex(idx);
                setIsNavigatorDrawerOpen(false);
              }}
              isAnswered={(idx) => {
                const q = quiz.questions[idx];
                return q ? (answers[q.id] || []).length > 0 : false;
              }}
              isFlagged={(idx) => {
                const q = quiz.questions[idx];
                return q ? flaggedIds.includes(q.id) : false;
              }}
              onClose={() => setIsNavigatorDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* 4. Submit Confirmation Modal */}
      <SubmitConfirmModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onConfirm={handleConfirmSubmit}
        isSubmitting={isSubmitting}
        totalQuestions={totalQuestions}
        answeredCount={answeredCount}
        flaggedCount={flaggedCount}
      />
    </div>
  );
}
