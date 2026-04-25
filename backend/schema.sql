-- PostgreSQL schema for T2 Schedule API

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(32) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    registered BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    full_name TEXT,
    alliance TEXT,
    category VARCHAR(64),
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    vacation_days_declared INTEGER,
    vacation_days_approved INTEGER,
    vacation_days_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES collection_periods(id) ON DELETE CASCADE,
    day DATE NOT NULL,
    status VARCHAR(128) NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schedule_user_period_day UNIQUE (user_id, period_id, day)
);

CREATE TABLE IF NOT EXISTS collection_periods (
    id SERIAL PRIMARY KEY,
    alliance TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_collection_periods_alliance ON collection_periods(alliance);

CREATE TABLE IF NOT EXISTS schedule_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    work_days INTEGER NOT NULL,
    rest_days INTEGER NOT NULL,
    shift_start VARCHAR(5) NOT NULL,
    shift_end VARCHAR(5) NOT NULL,
    has_break BOOLEAN NOT NULL DEFAULT FALSE,
    break_start VARCHAR(5),
    break_end VARCHAR(5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedule_templates_user_id ON schedule_templates(user_id);

CREATE TABLE IF NOT EXISTS schedule_change_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES collection_periods(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    employee_comment TEXT,
    manager_comment TEXT,
    proposed_schedule JSONB NOT NULL,
    resolved_by_manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT uq_schedule_change_request_user_period UNIQUE (user_id, period_id)
);

CREATE INDEX IF NOT EXISTS idx_schedule_change_requests_period_id ON schedule_change_requests(period_id);
CREATE INDEX IF NOT EXISTS idx_schedule_change_requests_status ON schedule_change_requests(status);

