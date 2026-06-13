-- ============================================================
-- PATCH 001 — Self-registration + admin management policies
-- Run in Supabase SQL Editor AFTER supabase_schema.sql
--
-- IMPORTANT: Also disable email confirmation in Supabase:
--   Authentication → Providers → Email → "Confirm email" → OFF
-- ============================================================

-- Any logged-in user can insert one school (their own, during self-registration)
CREATE POLICY "schools_insert_self" ON schools
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Admin can edit school details (for corrections)
CREATE POLICY "schools_update_admin" ON schools
    FOR UPDATE USING (my_role() = 'admin');

-- Admin can update any user's profile (role changes, corrections)
CREATE POLICY "profiles_update_admin" ON user_profiles
    FOR UPDATE USING (my_role() = 'admin');

-- ============================================================
-- DONE.
-- Signup flow after this patch:
--   Teacher enters phone + password + school details
--   → account created → school record created → profile created
--   → logged in immediately (no email confirmation needed)
-- ============================================================
