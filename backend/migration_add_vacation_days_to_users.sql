-- Migration: Add vacation days moderation fields to users
-- Date: 2026-04-25

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS vacation_days_declared INTEGER;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS vacation_days_approved INTEGER;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS vacation_days_status VARCHAR(32) NOT NULL DEFAULT 'pending';

UPDATE users
SET vacation_days_status = 'pending'
WHERE vacation_days_status IS NULL;
