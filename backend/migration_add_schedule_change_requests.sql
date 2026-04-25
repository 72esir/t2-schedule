CREATE TABLE IF NOT EXISTS schedule_change_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES collection_periods(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    employee_comment TEXT,
    manager_comment TEXT,
    proposed_schedule JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_by_manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT uq_schedule_change_request_user_period UNIQUE (user_id, period_id)
);

CREATE INDEX IF NOT EXISTS idx_schedule_change_requests_period_id
    ON schedule_change_requests(period_id);

CREATE INDEX IF NOT EXISTS idx_schedule_change_requests_status
    ON schedule_change_requests(status);
