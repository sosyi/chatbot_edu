PRAGMA foreign_keys = ON;

-- Users table maps Telegram users to internal IDs
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER NOT NULL UNIQUE,
    first_name TEXT,
    last_name  TEXT,
    username   TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FAQ bank (can be expanded or replaced with CSV imports)
CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer   TEXT NOT NULL,
    tags     TEXT
);

-- Message log (incoming/outgoing; helpful for analytics and audits)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    direction TEXT CHECK(direction IN ('in','out')) NOT NULL,
    text      TEXT,
    intent    TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User feedback (rating + free text)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_id INTEGER,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- Configurable rule-based intents (name + JSON array of regex patterns)
CREATE TABLE IF NOT EXISTS intents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    patterns TEXT
);

-- Conversational session state (multi-turn context)
-- context_json example: {"pending_intent":"deadline","slots":{"course":"158.780"},"last_course":"158.780","last_assignment":"A1"}
CREATE TABLE IF NOT EXISTS sessions (
    user_id INTEGER PRIMARY KEY,
    context_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Business data: course schedules (minimal schema; extend as needed)
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL,
    title TEXT,
    details TEXT
);

-- Business data: assignment deadlines per course
CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL,
    assignment  TEXT NOT NULL,
    due_at      TEXT,
    submit_to   TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_faqs_tags ON faqs(tags);
CREATE INDEX IF NOT EXISTS idx_schedules_course ON schedules(course_code);
CREATE INDEX IF NOT EXISTS idx_deadlines_course_assign ON deadlines(course_code, assignment);
