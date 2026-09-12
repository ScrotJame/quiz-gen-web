import {
  AnswerSubmission,
  ApiError,
  AttemptResult,
  CleanTextResponse,
  DashboardStats,
  Difficulty,
  GeneratedQuizResponse,
  OcrPageResponse,
  PaginatedQuizList,
  QuizCreatePayload,
  QuizDetail,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = "Đã xảy ra lỗi khi gọi API";
    let errorCode = "UNKNOWN_ERROR";
    try {
      const err = await res.json();
      errorDetail = err.detail || err.message || errorDetail;
      errorCode = err.error_code || err.errorCode || `HTTP_${res.status}`;
    } catch {
      errorDetail = res.statusText || errorDetail;
    }
    throw new ApiError(errorCode, errorDetail, res.status);
  }
  return res.json();
}

/**
 * Lấy số liệu thống kê Dashboard
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/quizzes/stats`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    return await handleResponse<DashboardStats>(res);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    // Fallback nếu server backend tạm thời không kết nối được
    return {
      totalQuizzes: 0,
      averageScore: 0,
      totalQuestionsCompleted: 0,
      totalAttempts: 0,
    };
  }
}

/**
 * Lấy danh sách quiz gần đây
 */
export async function getRecentQuizzes(
  limit: number = 10,
  category?: string,
  search?: string
): Promise<PaginatedQuizList> {
  try {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: "0",
    });
    if (category && category !== "Tất cả") {
      params.append("category", category);
    }
    if (search && search.trim()) {
      params.append("search", search.trim());
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/quizzes?${params.toString()}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    return await handleResponse<PaginatedQuizList>(res);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    return {
      items: [],
      total: 0,
      limit,
      offset: 0,
    };
  }
}

/**
 * Tạo quiz từ ảnh (OCR + AI)
 */
export async function generateQuizFromImage(
  file: File,
  options?: {
    numQuestions?: number;
    difficulty?: Difficulty;
    temperature?: number;
    saveImmediately?: boolean;
    authorName?: string;
  }
): Promise<GeneratedQuizResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.numQuestions) formData.append("numQuestions", String(options.numQuestions));
  if (options?.difficulty) formData.append("difficulty", options.difficulty);
  if (options?.temperature !== undefined) formData.append("temperature", String(options.temperature));
  if (options?.saveImmediately !== undefined)
    formData.append("saveImmediately", String(options.saveImmediately));
  if (options?.authorName) formData.append("authorName", options.authorName);

  const res = await fetch(`${API_BASE_URL}/api/v1/ai/generate-from-image`, {
    method: "POST",
    body: formData,
  });
  return await handleResponse<GeneratedQuizResponse>(res);
}

/**
 * Tạo quiz từ chủ đề / văn bản
 */
export async function generateQuizFromText(payload: {
  topic?: string;
  content?: string;
  numQuestions?: number;
  difficulty?: Difficulty;
  temperature?: number;
  saveImmediately?: boolean;
  authorName?: string;
}): Promise<GeneratedQuizResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ai/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return await handleResponse<GeneratedQuizResponse>(res);
}

/**
 * Kiểm tra kết nối backend
 */
export async function checkBackendHealth(): Promise<{ status: string; appName: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Lấy chi tiết đề thi theo ID
 */
export async function getQuizDetail(quizId: string): Promise<QuizDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/quizzes/${quizId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  return await handleResponse<QuizDetail>(res);
}

/**
 * Khởi tạo lượt làm bài mới
 */
export async function startAttempt(
  quizId: string,
  participantName: string = "Thí sinh"
): Promise<AttemptResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/attempts/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quizId, participantName }),
  });
  return await handleResponse<AttemptResult>(res);
}

/**
 * Nộp bài thi để chấm điểm
 */
export async function submitAttempt(
  attemptId: string,
  answers: AnswerSubmission[]
): Promise<AttemptResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/attempts/${attemptId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  return await handleResponse<AttemptResult>(res);
}

/**
 * Trích xuất OCR một trang ảnh đơn lẻ (kèm metadata: lineCount, averageConfidence)
 */
export async function ocrPage(file: Blob | File): Promise<OcrPageResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/v1/ai/ocr-page`, {
    method: "POST",
    body: formData,
  });
  return await handleResponse<OcrPageResponse>(res);
}

/**
 * Làm sạch và sửa lỗi chính tả văn bản OCR bằng Mistral AI
 */
export async function cleanText(
  rawText: string,
  targetLanguage: string = "vi"
): Promise<CleanTextResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ai/clean-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rawText, targetLanguage }),
  });
  return await handleResponse<CleanTextResponse>(res);
}

/**
 * Lưu đề thi vào cơ sở dữ liệu
 */
export async function createQuiz(payload: QuizCreatePayload): Promise<QuizDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/quizzes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return await handleResponse<QuizDetail>(res);
}


