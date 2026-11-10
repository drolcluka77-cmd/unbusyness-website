-- Reference schema for the Replit-managed PostgreSQL development database.
-- Apply changes to development with the Replit database workflow; Publish
-- carries the resulting schema diff to production.
CREATE TABLE IF NOT EXISTS public.waitlist_signups (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    segment TEXT NOT NULL,
    email TEXT NOT NULL,
    payload JSONB NOT NULL,
    consent BOOLEAN NOT NULL CHECK (consent = TRUE),
    notification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (notification_status IN ('pending', 'sending', 'sent', 'failed')),
    notification_attempts INTEGER NOT NULL DEFAULT 0
        CHECK (notification_attempts >= 0),
    notification_attempted_at TIMESTAMPTZ,
    notification_sent_at TIMESTAMPTZ,
    notification_error TEXT
);

CREATE INDEX IF NOT EXISTS waitlist_signups_created_at_idx
    ON public.waitlist_signups (created_at DESC);

CREATE INDEX IF NOT EXISTS waitlist_signups_notification_status_idx
    ON public.waitlist_signups (notification_status, created_at ASC);
