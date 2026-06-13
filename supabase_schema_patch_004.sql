-- ============================================================
-- PATCH 004 — Auto-create school + profile on teacher signup
-- Run in Supabase SQL Editor AFTER patch_003
--
-- HOW IT WORKS:
--   When a new user is inserted into auth.users (signup),
--   this trigger fires automatically. It reads the school
--   details from user_metadata and creates the school +
--   user_profile records.
--
-- WHY THIS WORKS:
--   Trigger functions with SECURITY DEFINER run as the
--   database owner (postgres superuser), bypassing RLS.
--   No service role key needed. No client-side INSERTs.
-- ============================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_school_id   UUID;
    v_school_code TEXT;
    v_phone       TEXT;
    v_school_name TEXT;
    v_district    TEXT;
    v_taluka      TEXT;
    v_udise       TEXT;
    v_trial_ends  TIMESTAMPTZ;
BEGIN
    -- Only run for teacher signups (phone-based, have school_name in metadata)
    v_phone       := NEW.raw_user_meta_data->>'phone';
    v_school_name := NEW.raw_user_meta_data->>'school_name';

    IF v_phone IS NULL OR v_school_name IS NULL THEN
        RETURN NEW;   -- skip admin / Google OAuth signups
    END IF;

    v_district   := NULLIF(TRIM(NEW.raw_user_meta_data->>'district'),   '');
    v_taluka     := NULLIF(TRIM(NEW.raw_user_meta_data->>'taluka'),     '');
    v_udise      := NULLIF(TRIM(NEW.raw_user_meta_data->>'udise_code'), '');
    v_school_code := regexp_replace(v_phone, '[^0-9]', '', 'g');
    v_trial_ends  := NOW() + INTERVAL '30 days';

    -- Create school
    INSERT INTO public.schools (
        school_code, name, district, taluka,
        udise_code, subscription_status, trial_ends_at
    )
    VALUES (
        v_school_code, v_school_name, v_district, v_taluka,
        v_udise, 'trial', v_trial_ends
    )
    ON CONFLICT (school_code) DO NOTHING
    RETURNING id, school_code INTO v_school_id, v_school_code;

    -- If school already existed (conflict), fetch its id
    IF v_school_id IS NULL THEN
        SELECT id, school_code INTO v_school_id, v_school_code
        FROM public.schools
        WHERE school_code = regexp_replace(v_phone, '[^0-9]', '', 'g');
    END IF;

    -- Create user profile
    INSERT INTO public.user_profiles (id, school_id, school_code, full_name, role)
    VALUES (NEW.id, v_school_id, v_school_code, '', 'teacher')
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$;

-- Attach trigger to auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- DONE.
-- Signup flow after this patch:
--   1. sign_up(email, password, metadata={phone, school_name...})
--   2. Trigger fires → school + profile created automatically
--   3. sign_in(email, password) → JWT established
--   4. Load profile from DB → school_id available → dashboard
-- ============================================================
