-- ============================================================
-- Patch 005 — Add kendra (केंद्र) and state columns to schools
--             Update handle_new_user trigger to store them
-- Run in: Supabase SQL Editor
-- ============================================================

-- 1) Add new columns
ALTER TABLE public.schools
    ADD COLUMN IF NOT EXISTS kendra TEXT,
    ADD COLUMN IF NOT EXISTS state  TEXT DEFAULT 'Maharashtra';

-- Set default state for existing rows
UPDATE public.schools SET state = 'Maharashtra' WHERE state IS NULL;

-- 2) Update the signup trigger to extract kendra + state from metadata
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_school_id   UUID;
    v_school_code TEXT;
    v_phone       TEXT;
    v_school_name TEXT;
    v_district    TEXT;
    v_taluka      TEXT;
    v_udise       TEXT;
    v_kendra      TEXT;
    v_state       TEXT;
    v_trial_ends  TIMESTAMPTZ;
BEGIN
    v_phone       := NEW.raw_user_meta_data->>'phone';
    v_school_name := NEW.raw_user_meta_data->>'school_name';

    IF v_phone IS NULL OR v_school_name IS NULL THEN
        RETURN NEW;
    END IF;

    v_district := NULLIF(TRIM(NEW.raw_user_meta_data->>'district'),   '');
    v_taluka   := NULLIF(TRIM(NEW.raw_user_meta_data->>'taluka'),     '');
    v_udise    := NULLIF(TRIM(NEW.raw_user_meta_data->>'udise_code'), '');
    v_kendra   := NULLIF(TRIM(NEW.raw_user_meta_data->>'kendra'),     '');
    v_state    := COALESCE(NULLIF(TRIM(NEW.raw_user_meta_data->>'state'), ''), 'Maharashtra');

    v_school_code := regexp_replace(v_phone, '[^0-9]', '', 'g');
    v_trial_ends  := NOW() + INTERVAL '30 days';

    INSERT INTO public.schools
        (school_code, name, district, taluka, udise_code, kendra, state,
         subscription_status, trial_ends_at)
    VALUES
        (v_school_code, v_school_name, v_district, v_taluka, v_udise,
         v_kendra, v_state, 'trial', v_trial_ends)
    ON CONFLICT (school_code) DO NOTHING
    RETURNING id, school_code INTO v_school_id, v_school_code;

    IF v_school_id IS NULL THEN
        SELECT id, school_code
        INTO   v_school_id, v_school_code
        FROM   public.schools
        WHERE  school_code = regexp_replace(v_phone, '[^0-9]', '', 'g');
    END IF;

    INSERT INTO public.user_profiles (id, school_id, school_code, full_name, role)
    VALUES (NEW.id, v_school_id, v_school_code, '', 'teacher')
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 3) RPC for teachers to update their own school's kendra/district/taluka/state
CREATE OR REPLACE FUNCTION public.update_school_info(
    p_school_id UUID,
    p_kendra    TEXT,
    p_district  TEXT,
    p_taluka    TEXT,
    p_state     TEXT
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    UPDATE public.schools
    SET
        kendra   = NULLIF(TRIM(p_kendra),   ''),
        district = NULLIF(TRIM(p_district), ''),
        taluka   = NULLIF(TRIM(p_taluka),   ''),
        state    = COALESCE(NULLIF(TRIM(p_state), ''), 'Maharashtra')
    WHERE id = p_school_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.update_school_info TO authenticated;
