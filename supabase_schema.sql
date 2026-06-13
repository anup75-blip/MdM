-- ============================================================
-- MDM (Mid-Day Meal) Supabase PostgreSQL Schema
-- Run this entire file in Supabase SQL Editor (one time setup)
-- Supports 500+ schools with Row Level Security
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ────────────────────────────────────────────────────────────
-- SCHOOLS TABLE
-- ────────────────────────────────────────────────────────────
CREATE TABLE schools (
    id           UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    school_code  TEXT UNIQUE NOT NULL,         -- e.g. SCH001
    name         TEXT NOT NULL,
    district     TEXT,
    taluka       TEXT,
    block_name   TEXT,
    udise_code   TEXT,                         -- govt UDISE number
    principal    TEXT,
    phone        TEXT,
    active       BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────
-- USER PROFILES TABLE
-- Links to Supabase Auth users (auth.users)
-- ────────────────────────────────────────────────────────────
CREATE TABLE user_profiles (
    id          UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    school_id   UUID REFERENCES schools(id),
    school_code TEXT,
    full_name   TEXT,
    role        TEXT DEFAULT 'teacher' CHECK (
                    role IN ('teacher', 'principal', 'admin', 'block_officer')
                ),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────
-- ATTENDANCE TABLE
-- One row per school per calendar day
-- ────────────────────────────────────────────────────────────
CREATE TABLE attendance (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    school_id   UUID REFERENCES schools(id) NOT NULL,
    date        DATE NOT NULL,
    class5      INTEGER NOT NULL DEFAULT 0 CHECK (class5 >= 0 AND class5 <= 500),
    class6      INTEGER NOT NULL DEFAULT 0 CHECK (class6 >= 0 AND class6 <= 500),
    class7      INTEGER NOT NULL DEFAULT 0 CHECK (class7 >= 0 AND class7 <= 500),
    class8      INTEGER NOT NULL DEFAULT 0 CHECK (class8 >= 0 AND class8 <= 500),
    entered_by  UUID REFERENCES auth.users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (school_id, date)
);

-- Auto-update updated_at on every UPDATE
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER attendance_updated_at
    BEFORE UPDATE ON attendance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ────────────────────────────────────────────────────────────
-- AUDIT LOG TABLE
-- Every attendance save is recorded here
-- ────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    school_id   UUID REFERENCES schools(id),
    user_id     UUID REFERENCES auth.users(id),
    action      TEXT NOT NULL,                 -- 'login', 'attendance_save', 'report_download'
    details     JSONB,                         -- e.g. {"date":"2026-06-08","class5":45}
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Teachers see ONLY their own school's data
-- Admins/block officers see all
-- ────────────────────────────────────────────────────────────
ALTER TABLE schools        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance     ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log      ENABLE ROW LEVEL SECURITY;

-- Helper function: get school_id of the logged-in user
CREATE OR REPLACE FUNCTION my_school_id()
RETURNS UUID AS $$
    SELECT school_id FROM user_profiles WHERE id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER;

-- Helper function: get role of the logged-in user
CREATE OR REPLACE FUNCTION my_role()
RETURNS TEXT AS $$
    SELECT role FROM user_profiles WHERE id = auth.uid()
$$ LANGUAGE SQL SECURITY DEFINER;

-- schools: teacher sees own school only; admin/block_officer see all
CREATE POLICY "schools_select" ON schools FOR SELECT USING (
    id = my_school_id()
    OR my_role() IN ('admin', 'block_officer')
);

-- user_profiles: user sees own profile; admin sees all
CREATE POLICY "profiles_select_own" ON user_profiles
    FOR SELECT USING (id = auth.uid() OR my_role() = 'admin');

CREATE POLICY "profiles_insert_own" ON user_profiles
    FOR INSERT WITH CHECK (id = auth.uid());

CREATE POLICY "profiles_update_own" ON user_profiles
    FOR UPDATE USING (id = auth.uid());

-- attendance: teacher can SELECT/INSERT/UPDATE own school; admin/block_officer see all
CREATE POLICY "attendance_select" ON attendance FOR SELECT USING (
    school_id = my_school_id()
    OR my_role() IN ('admin', 'block_officer')
);

CREATE POLICY "attendance_insert" ON attendance FOR INSERT WITH CHECK (
    school_id = my_school_id()
);

CREATE POLICY "attendance_update" ON attendance FOR UPDATE USING (
    school_id = my_school_id()
);

-- audit_log: teacher sees own school; admin sees all
CREATE POLICY "audit_select" ON audit_log FOR SELECT USING (
    school_id = my_school_id()
    OR my_role() = 'admin'
);

CREATE POLICY "audit_insert" ON audit_log FOR INSERT WITH CHECK (
    school_id = my_school_id()
    OR my_role() = 'admin'
);

-- ────────────────────────────────────────────────────────────
-- INDEXES (for performance with 500 schools)
-- ────────────────────────────────────────────────────────────
CREATE INDEX idx_attendance_school_date ON attendance (school_id, date);
CREATE INDEX idx_audit_school           ON audit_log  (school_id, created_at DESC);
CREATE INDEX idx_schools_code           ON schools    (school_code);

-- ────────────────────────────────────────────────────────────
-- DONE
-- Next step: Run scripts/setup_schools.py to import schools
-- ────────────────────────────────────────────────────────────
