import {
  AnswerSubmission,
  ApiError,
  AttemptResult,
  CleanTextResponse,
  DashboardStats,
  Difficulty,
  GeneratedQuizResponse,
  OcrPageResponse,
  OcrRetryOptions,
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
      if (typeof err.detail === "object" && err.detail !== null) {
        errorDetail = err.detail.message || JSON.stringify(err.detail);
        errorCode = err.detail.error_code || err.detail.errorCode || errorCode;
      } else {
        errorDetail = err.detail || err.message || errorDetail;
      }
      errorCode = err.error_code || err.errorCode || errorCode;
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
 * Trích xuất OCR một trang ảnh đơn lẻ (kèm metadata: lineCount, averageConfidence, và tùy chọn trọng số)
 */
export async function ocrPage(
  file: Blob | File,
  options?: OcrRetryOptions | string
): Promise<OcrPageResponse> {
  const formData = new FormData();
  formData.append("file", file);

  if (typeof options === "string") {
    if (options && options !== "auto") {
      formData.append("engine", options);
    }
  } else if (options) {
    if (options.engine && options.engine !== "auto") {
      formData.append("engine", options.engine);
    }
    if (options.unclipRatio !== undefined) {
      formData.append("unclip_ratio", String(options.unclipRatio));
    }
    if (options.boxThresh !== undefined) {
      formData.append("box_thresh", String(options.boxThresh));
    }
    if (options.limitSideLen !== undefined) {
      formData.append("limit_side_len", String(options.limitSideLen));
    }
    if (options.enableClahe !== undefined) {
      formData.append("enable_clahe", String(options.enableClahe));
    }
    if (options.splitTallBoxes !== undefined) {
      formData.append("split_tall_boxes", String(options.splitTallBoxes));
    }
  }

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

// ─── Question Bank API ────────────────────────────────────────────────────────

import type {
  BankCategoriesResponse,
  BankListParams,
  BankQuestionBatchCreate,
  BankQuestionListResponse,
  BankQuestionSchema,
  BankQuestionUpdate,
} from "./types";

/**
 * Batch lưu câu hỏi vào Ngân hàng câu hỏi
 */
export async function batchCreateBankQuestions(
  payload: BankQuestionBatchCreate
): Promise<BankQuestionSchema[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/bank/questions/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return await handleResponse<BankQuestionSchema[]>(res);
}

/**
 * Lấy danh sách câu hỏi trong Ngân hàng (có lọc, tìm kiếm, phân trang)
 */
export async function getBankQuestions(
  params: BankListParams = {}
): Promise<BankQuestionListResponse> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.difficulty) query.set("difficulty", params.difficulty);
  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.page) query.set("page", String(params.page));
  if (params.limit) query.set("limit", String(params.limit));

  const res = await fetch(
    `${API_BASE_URL}/api/v1/bank/questions?${query.toString()}`,
    { method: "GET", headers: { "Content-Type": "application/json" }, cache: "no-store" }
  );
  return await handleResponse<BankQuestionListResponse>(res);
}

/**
 * Lấy danh sách danh mục trong Ngân hàng câu hỏi
 */
export async function getBankCategories(): Promise<BankCategoriesResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/bank/categories`, {
    method: "GET",
    cache: "no-store",
  });
  return await handleResponse<BankCategoriesResponse>(res);
}

/**
 * Cập nhật câu hỏi trong Ngân hàng
 */
export async function updateBankQuestion(
  questionId: string,
  data: BankQuestionUpdate
): Promise<BankQuestionSchema> {
  const res = await fetch(`${API_BASE_URL}/api/v1/bank/questions/${questionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return await handleResponse<BankQuestionSchema>(res);
}

/**
 * Xóa câu hỏi khỏi Ngân hàng
 */
export async function deleteBankQuestion(questionId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/bank/questions/${questionId}`, {
    method: "DELETE",
  });
  if (!res.ok) await handleResponse<void>(res);
}
