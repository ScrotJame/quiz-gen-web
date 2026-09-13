export type Difficulty = "easy" | "medium" | "hard";
export type QuestionType = "single_choice" | "multiple_choice";

export interface Option {
  id: string;
  questionId?: string;
  optionText: string;
  isCorrect?: boolean;
  orderNum?: number;
}

export interface Question {
  id: string;
  quizId?: string;
  questionText: string;
  questionType: QuestionType;
  points: number;
  orderNum: number;
  explanation?: string | null;
  options: Option[];
}

export interface QuizSummary {
  id: string;
  title: string;
  description?: string | null;
  category: string;
  difficulty: Difficulty;
  timeLimitMinutes: number;
  authorName: string;
  isPublished: boolean;
  totalQuestions: number;
  createdAt: string;
  updatedAt: string;
}

export interface QuizDetail extends QuizSummary {
  questions: Question[];
}

export interface DashboardStats {
  totalQuizzes: number;
  averageScore: number;
  totalQuestionsCompleted: number;
  totalAttempts: number;
}

export interface PaginatedQuizList {
  items: QuizSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface GeneratedQuizResponse {
  title: string;
  description: string;
  category: string;
  difficulty: Difficulty;
  questions: Array<{
    questionText: string;
    questionType?: QuestionType;
    points?: number;
    explanation?: string;
    options: Array<{
      optionText: string;
      isCorrect: boolean;
    }>;
  }>;
  savedQuizId?: string | null;
}

export interface AnswerSubmission {
  questionId: string;
  selectedOptionIds: string[];
}

export interface AttemptAnswerDetail {
  id: string;
  questionId: string;
  selectedOptionIds: string[];
  isCorrect: boolean;
  earnedPoints: number;
}

export interface AttemptResult {
  id: string;
  quizId: string;
  participantName: string;
  score: number;
  maxScore: number;
  percentage: number;
  status: "in_progress" | "completed";
  startedAt: string;
  completedAt?: string | null;
  answers: AttemptAnswerDetail[];
}

export class ApiError extends Error {
  constructor(
    public errorCode: string,
    message: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// --- OCR Studio & Creation Types ---

export interface OcrPageResponse {
  text: string;
  lineCount: number;
  averageConfidence: number;
  /** "gemini" | "local_vietocr" | "unknown" */
  provider?: string;
}

export interface OcrRetryOptions {
  engine?: "auto" | "gemini" | "local_vietocr";
  unclipRatio?: number;
  boxThresh?: number;
  limitSideLen?: number;
  enableClahe?: boolean;
  splitTallBoxes?: boolean;
}


export interface CleanTextRequest {
  rawText: string;
  targetLanguage?: string;
}

export interface CleanTextResponse {
  cleanedText: string;
}

export interface StudioPageItem {
  id: string;
  file: File;
  previewUrl: string;
  rotation: number; // 0, 90, 180, 270
  status: "idle" | "scanning" | "success" | "error";
  text: string;
  lineCount: number;
  confidence: number;
  provider?: string;
  errorMessage?: string;
}

export interface QuestionOptionEdit {
  optionText: string;
  isCorrect: boolean;
}

export interface QuestionEdit {
  id: string;
  questionText: string;
  questionType: QuestionType;
  points: number;
  explanation?: string;
  options: QuestionOptionEdit[];
}

export interface OptionCreatePayload {
  optionText: string;
  isCorrect: boolean;
  orderNum?: number;
}

export interface QuestionCreatePayload {
  questionText: string;
  questionType?: QuestionType;
  points?: number;
  orderNum?: number;
  explanation?: string | null;
  options: OptionCreatePayload[];
}

export interface QuizCreatePayload {
  title: string;
  description?: string | null;
  category?: string;
  difficulty?: Difficulty;
  timeLimitMinutes?: number;
  authorName?: string;
  isPublished?: boolean;
  questions: QuestionCreatePayload[];
}

// ─── Question Bank (Ngân hàng câu hỏi) ───────────────────────────────────────

export interface BankOptionCreate {
  optionText: string;
  isCorrect: boolean;
  orderNum?: number;
}

export interface BankOptionSchema {
  id: string;
  questionId: string;
  optionText: string;
  isCorrect: boolean;
  orderNum: number;
}

export interface BankQuestionCreate {
  questionText: string;
  questionType?: QuestionType;
  category: string;
  difficulty?: Difficulty;
  explanation?: string | null;
  sourceNote?: string | null;
  options: BankOptionCreate[];
}

export interface BankQuestionBatchCreate {
  questions: BankQuestionCreate[];
}

export interface BankQuestionUpdate {
  questionText?: string;
  questionType?: QuestionType;
  category?: string;
  difficulty?: Difficulty;
  explanation?: string | null;
  sourceNote?: string | null;
}

export interface BankQuestionSchema {
  id: string;
  questionText: string;
  questionType: QuestionType;
  category: string;
  difficulty: Difficulty;
  explanation?: string | null;
  sourceNote?: string | null;
  createdAt: string;
  updatedAt: string;
  options: BankOptionSchema[];
}

export interface BankQuestionListResponse {
  items: BankQuestionSchema[];
  total: number;
  page: number;
  limit: number;
}

export interface BankCategoriesResponse {
  categories: string[];
}

export interface BankListParams {
  category?: string;
  difficulty?: string;
  search?: string;
  page?: number;
  limit?: number;
}
