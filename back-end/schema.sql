-- ==============================================================================
-- SCHEMA DDL CHO HỆ THỐNG QUIZGEN AI (POSTGRESQL)
-- Chạy trực tiếp trong pgAdmin, DBeaver, psql hoặc Navicat
-- Database: web_quiz
-- ==============================================================================

-- 1. BẢNG QUIZZES (Bộ đề thi)
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) DEFAULT 'Chung',
    difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
    time_limit_minutes INTEGER DEFAULT 15,
    author_name VARCHAR(100) DEFAULT 'Nội bộ',
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_quizzes_title ON quizzes (title);
CREATE INDEX IF NOT EXISTS ix_quizzes_category ON quizzes (category);

-- 2. BẢNG QUESTIONS (Câu hỏi trắc nghiệm)
CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY,
    quiz_id UUID NOT NULL REFERENCES quizzes (id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL DEFAULT 'single_choice',
    points INTEGER DEFAULT 10,
    order_num INTEGER DEFAULT 0,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_questions_quiz_id ON questions (quiz_id);

-- 3. BẢNG OPTIONS (Lựa chọn đáp án A, B, C, D...)
CREATE TABLE IF NOT EXISTS options (
    id UUID PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    order_num INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_options_question_id ON options (question_id);

-- 4. BẢNG ATTEMPTS (Lượt làm bài thi)
CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY,
    quiz_id UUID NOT NULL REFERENCES quizzes (id) ON DELETE CASCADE,
    participant_name VARCHAR(100) DEFAULT 'Thí sinh',
    score INTEGER DEFAULT 0,
    max_score INTEGER DEFAULT 0,
    percentage DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_attempts_quiz_id ON attempts (quiz_id);

-- 5. BẢNG ATTEMPT_ANSWERS (Chi tiết câu trả lời của thí sinh)
CREATE TABLE IF NOT EXISTS attempt_answers (
    id UUID PRIMARY KEY,
    attempt_id UUID NOT NULL REFERENCES attempts (id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    selected_option_ids_json TEXT DEFAULT '[]',
    is_correct BOOLEAN DEFAULT FALSE,
    earned_points INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_attempt_answers_attempt_id ON attempt_answers (attempt_id);
