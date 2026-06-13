-- ============================================================
-- PATCH 002 — Subscription columns on schools table
-- Run in Supabase SQL Editor AFTER supabase_schema_patch_001.sql
--
-- Adds: subscription_status, trial_ends_at,
--       subscription_ends_at, razorpay_payment_id
-- ============================================================

ALTER TABLE schools
    ADD COLUMN IF NOT EXISTS subscription_status    TEXT    DEFAULT 'trial'
        CHECK (subscription_status IN ('trial', 'active', 'expired')),
    ADD COLUMN IF NOT EXISTS trial_ends_at          TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS subscription_ends_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS razorpay_payment_id    TEXT;

-- Backfill existing rows: 30-day trial from their created_at
UPDATE schools
SET
    subscription_status = 'trial',
    trial_ends_at       = created_at + INTERVAL '30 days'
WHERE subscription_status IS NULL
   OR trial_ends_at        IS NULL;

-- Index for fast subscription status lookups
CREATE INDEX IF NOT EXISTS idx_schools_subscription
    ON schools (subscription_status, trial_ends_at, subscription_ends_at);

-- Admin can update subscription fields (e.g. after payment verified)
CREATE POLICY "schools_subscription_admin" ON schools
    FOR UPDATE USING (my_role() = 'admin');

-- ============================================================
-- DONE.
-- After running this patch:
--   - New signups will have trial_ends_at = NOW() + 30 days
--   - Existing schools get a 30-day trial from their created_at
--   - subscription.py module handles status checks client-side
-- ============================================================
