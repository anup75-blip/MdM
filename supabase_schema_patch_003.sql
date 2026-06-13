-- ============================================================
-- PATCH 003 — Signup helper function (SECURITY DEFINER)
-- Run in Supabase SQL Editor AFTER patch_002
--
-- Creates a database function that handles school + profile
-- creation during teacher self-registration.
--
-- WHY: During signup the anon client has no JWT yet, so RLS
-- blocks direct INSERTs. A SECURITY DEFINER function runs
-- with database-owner privileges, bypassing RLS safely.
-- ============================================================

CREATE OR REPLACE FUNCTION signup_create_school(
    p_user_id             UUID,
    p_school_code         TEXT,
    p_name                TEXT,
    p_district            TEXT,
    p_taluka              TEXT,
    p_udise_code          TEXT,
    p_subscription_status TEXT,
    p_trial_ends_at       TIMESTAMPTZ
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER          -- runs as DB owner, bypasses RLS
SET search_path = public  -- prevent search_path hijack attacks
AS $$
DECLARE
    v_school_id   UUID;
    v_school_code TEXT;
BEGIN
    -- Insert school
    INSERT INTO public.schools (
        school_code, name, district, taluka,
        udise_code, subscription_status, trial_ends_at
    )
    VALUES (
        p_school_code, p_name,
        NULLIF(p_district,   ''),
        NULLIF(p_taluka,     ''),
        NULLIF(p_udise_code, ''),
        p_subscription_status, p_trial_ends_at
    )
    RETURNING id, school_code INTO v_school_id, v_school_code;

    -- Insert user profile
    INSERT INTO public.user_profiles (id, school_id, school_code, full_name, role)
    VALUES (p_user_id, v_school_id, v_school_code, '', 'teacher');

    RETURN json_build_object(
        'school_id',   v_school_id,
        'school_code', v_school_code
    );
END;
$$;

-- Allow anon and authenticated users to call this function
GRANT EXECUTE ON FUNCTION signup_create_school TO anon, authenticated;

-- ============================================================
-- DONE.
-- auth.py calls this via: supabase.rpc("signup_create_school", {...})
-- ============================================================
