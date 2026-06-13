-- Mid-Day Meal (MDM) PostgreSQL Schema  — 11 tables
-- School: Indirabaai Kanya Vidyalaya, Shirala, Amravati
-- Replaces Excel as primary data store; Excel still generated for govt submission
--
-- Tables: schools, users, meal_types, holidays, daily_attendance,
--         food_items, daily_consumption, food_stock, expense_rates,
--         monthly_bills, audit_log

-- ─────────────────────────────────────────────
-- 1. Schools (multi-school ready)
-- ─────────────────────────────────────────────
CREATE TABLE schools (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20)  UNIQUE NOT NULL,   -- e.g. 'SCH001'
    name        TEXT         NOT NULL,
    district    VARCHAR(100),
    taluka      VARCHAR(100),
    address     TEXT,
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 2. Users (authentication)
-- ─────────────────────────────────────────────
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    school_id       INT          REFERENCES schools(id) ON DELETE CASCADE,
    username        VARCHAR(50)  UNIQUE NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,          -- SHA256 / bcrypt hash
    role            VARCHAR(20)  NOT NULL DEFAULT 'teacher'
                    CHECK (role IN ('admin', 'teacher', 'cook')),
    full_name       TEXT,
    is_active       BOOLEAN      DEFAULT TRUE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- Seed: default admin user (password = 'change_me_now')
INSERT INTO users (school_id, username, password_hash, role, full_name)
VALUES (1, 'admin',
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f',
        'admin', 'School Admin');

-- ─────────────────────────────────────────────
-- 3. Meal Types (dropdown options for daily entry)
-- ─────────────────────────────────────────────
CREATE TABLE meal_types (
    id          SERIAL PRIMARY KEY,
    name_en     VARCHAR(100) NOT NULL,
    name_marathi VARCHAR(100),
    active      BOOLEAN DEFAULT TRUE
);

INSERT INTO meal_types (name_en, name_marathi) VALUES
    ('Rice + Dal',         'भात + डाळ'),
    ('Rice + Chickpea',    'भात + हरभरा'),
    ('Rice + Matki',       'भात + मटकी'),
    ('Rice + Masur Dal',   'भात + मसूर डाळ'),
    ('Rice + Chavli',      'भात + चवळी'),
    ('Khichdi',            'खिचडी'),
    ('Rice + Vatana',      'भात + वाटाणा'),
    ('Holiday / No Meal',  'सुट्टी / जेवण नाही'),
    ('Rice + Mixed Veg',   'भात + मिश्र भाजी'),
    ('Special Menu',       'विशेष मेनू');

-- ─────────────────────────────────────────────
-- 4. Holidays
-- ─────────────────────────────────────────────
CREATE TABLE holidays (
    id          SERIAL PRIMARY KEY,
    school_id   INT          REFERENCES schools(id) ON DELETE CASCADE,
    holiday_date DATE        NOT NULL,
    holiday_type VARCHAR(20) NOT NULL CHECK (holiday_type IN ('sunday', 'govt', 'school')),
    description TEXT,
    UNIQUE (school_id, holiday_date)
);

-- ─────────────────────────────────────────────
-- 3. Daily Attendance  ← THE CORE TABLE
--    Mirrors columns C / E / F / G in Sheet1
-- ─────────────────────────────────────────────
CREATE TABLE daily_attendance (
    id              SERIAL PRIMARY KEY,
    school_id       INT     NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    attendance_date DATE    NOT NULL,

    -- 4 primary inputs (Sheet1 cols C, E, F, G)
    class5_count    SMALLINT NOT NULL DEFAULT 0 CHECK (class5_count >= 0),
    class6_count    SMALLINT NOT NULL DEFAULT 0 CHECK (class6_count >= 0),
    class7_count    SMALLINT NOT NULL DEFAULT 0 CHECK (class7_count >= 0),
    class8_count    SMALLINT NOT NULL DEFAULT 0 CHECK (class8_count >= 0),

    -- derived (could be views, stored here for audit)
    class5_total    SMALLINT GENERATED ALWAYS AS (class5_count) STORED,
    class68_total   SMALLINT GENERATED ALWAYS AS (class6_count + class7_count + class8_count) STORED,
    total_students  SMALLINT GENERATED ALWAYS AS (class5_count + class6_count + class7_count + class8_count) STORED,

    menu_item       VARCHAR(100),   -- daily menu (pre-filled rotation)
    is_holiday      BOOLEAN  NOT NULL DEFAULT FALSE,
    notes           TEXT,

    entered_by      TEXT,
    entered_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (school_id, attendance_date)
);

-- ─────────────────────────────────────────────
-- 4. Food Items catalogue
-- ─────────────────────────────────────────────
CREATE TABLE food_items (
    id              SERIAL PRIMARY KEY,
    name_en         VARCHAR(100) NOT NULL,
    name_marathi    VARCHAR(100),               -- Unicode Marathi
    unit            VARCHAR(20)  NOT NULL,      -- 'g', 'ml', 'kg', 'L'

    -- per-student daily quantity (grams or ml)
    qty_class5      NUMERIC(8,3) DEFAULT 0,
    qty_class68     NUMERIC(8,3) DEFAULT 0,

    active          BOOLEAN DEFAULT TRUE
);

-- Seed food items from the Excel template
INSERT INTO food_items (name_en, name_marathi, unit, qty_class5, qty_class68) VALUES
    ('Rice (Tandul)',       'तांदूळ',      'g',  100,   150),
    ('Masur Dal',           'मसूर डाळ',   'g',   20,    30),
    ('Harbhara (Chickpea)', 'हरभरा',       'g',   20,    30),
    ('Matki / Chavli',      'मटकी/चवळी',  'g',   20,    30),
    ('Mohari (Mustard)',    'मोहरी',       'g',  0.5,   0.5),
    ('Haldi (Turmeric)',    'हळद',         'g',  0.5,   0.5),
    ('Kanda Masala',        'कांदा मसाला', 'g',    2,     5),
    ('Mith (Salt)',         'मीठ',         'g',    2,     4),
    ('Tel (Oil)',           'तेल',         'ml',   5,   7.5),
    ('Bhajipala (Veggies)', 'भाजीपाला',   'g',    0,     0);  -- cost-only item

-- ─────────────────────────────────────────────
-- 5. Daily Food Consumption  (calculated, one row per item per day)
-- ─────────────────────────────────────────────
CREATE TABLE daily_consumption (
    id              SERIAL PRIMARY KEY,
    attendance_id   INT NOT NULL REFERENCES daily_attendance(id) ON DELETE CASCADE,
    food_item_id    INT NOT NULL REFERENCES food_items(id),

    qty_used_class5  NUMERIC(10,3),   -- grams/ml consumed
    qty_used_class68 NUMERIC(10,3),
    qty_total        NUMERIC(10,3),

    UNIQUE (attendance_id, food_item_id)
);

-- ─────────────────────────────────────────────
-- 6. Food Stock (monthly opening/closing balances)
-- ─────────────────────────────────────────────
CREATE TABLE food_stock (
    id              SERIAL PRIMARY KEY,
    school_id       INT  NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    food_item_id    INT  NOT NULL REFERENCES food_items(id),
    year            SMALLINT NOT NULL,
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),

    opening_qty_kg  NUMERIC(10,3) DEFAULT 0,    -- stock at month start
    received_qty_kg NUMERIC(10,3) DEFAULT 0,    -- received during month
    used_qty_kg     NUMERIC(10,3) DEFAULT 0,    -- auto-calculated from meals
    closing_qty_kg  NUMERIC(10,3)               -- opening + received - used
        GENERATED ALWAYS AS (opening_qty_kg + received_qty_kg - used_qty_kg) STORED,

    wastage_kg      NUMERIC(10,3) DEFAULT 0,
    notes           TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (school_id, food_item_id, year, month)
);

-- ─────────────────────────────────────────────
-- 7. Expense Rates
-- ─────────────────────────────────────────────
CREATE TABLE expense_rates (
    id          SERIAL PRIMARY KEY,
    school_id   INT NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    class_group VARCHAR(10) NOT NULL CHECK (class_group IN ('class5', 'class68')),
    category    VARCHAR(50) NOT NULL,   -- 'bhajipala', 'fuel', 'supplementary'
    rate_inr    NUMERIC(6,2) NOT NULL,  -- ₹ per student per day
    effective_from DATE NOT NULL,
    effective_to   DATE,

    UNIQUE (school_id, class_group, category, effective_from)
);

-- ─────────────────────────────────────────────
-- 8. Monthly Bill Summary
-- ─────────────────────────────────────────────
CREATE TABLE monthly_bills (
    id              SERIAL PRIMARY KEY,
    school_id       INT  NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    year            SMALLINT NOT NULL,
    month           SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),

    -- totals for the month
    working_days    SMALLINT,
    class5_total    INT,    -- sum of daily class5_count
    class68_total   INT,    -- sum of daily class68_total

    -- expense totals (₹)
    bhajipala_class5   NUMERIC(10,2),
    bhajipala_class68  NUMERIC(10,2),
    fuel_class5        NUMERIC(10,2),
    fuel_class68       NUMERIC(10,2),
    supp_class5        NUMERIC(10,2),
    supp_class68       NUMERIC(10,2),
    grand_total        NUMERIC(10,2),

    excel_file_path TEXT,   -- path to generated .xlsx for download
    generated_at    TIMESTAMPTZ,

    UNIQUE (school_id, year, month)
);

-- ─────────────────────────────────────────────
-- 9. Audit Log
-- ─────────────────────────────────────────────
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    table_name  TEXT NOT NULL,
    record_id   INT  NOT NULL,
    action      VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data    JSONB,
    new_data    JSONB,
    changed_by  TEXT,
    changed_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 10. Helper: auto-update updated_at
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_attendance_updated_at
    BEFORE UPDATE ON daily_attendance
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────
-- 11. Seed: default school + reference data
-- ─────────────────────────────────────────────
INSERT INTO schools (code, name, district, taluka) VALUES
    ('SCH001', 'Indirabaai Kanya Vidyalaya', 'Amravati', 'Shirala');

-- Expense rates (inserted after school exists)
INSERT INTO expense_rates (school_id, class_group, category, rate_inr, effective_from) VALUES
    (1, 'class5',  'bhajipala',     1.00, '2026-04-01'),
    (1, 'class5',  'fuel',          0.89, '2026-04-01'),
    (1, 'class5',  'supplementary', 0.70, '2026-04-01'),
    (1, 'class68', 'bhajipala',     1.64, '2026-04-01'),
    (1, 'class68', 'fuel',          1.14, '2026-04-01'),
    (1, 'class68', 'supplementary', 1.10, '2026-04-01');

-- ─────────────────────────────────────────────
-- Useful views
-- ─────────────────────────────────────────────
CREATE VIEW v_attendance_summary AS
SELECT
    da.attendance_date,
    s.name AS school,
    da.class5_count,
    da.class6_count,
    da.class7_count,
    da.class8_count,
    da.class68_total,
    da.total_students,
    da.menu_item,
    da.is_holiday
FROM daily_attendance da
JOIN schools s ON s.id = da.school_id
ORDER BY da.attendance_date DESC;

CREATE VIEW v_monthly_totals AS
SELECT
    s.code AS school_code,
    EXTRACT(YEAR  FROM da.attendance_date)::INT AS year,
    EXTRACT(MONTH FROM da.attendance_date)::INT AS month,
    COUNT(*) FILTER (WHERE NOT da.is_holiday)  AS working_days,
    SUM(da.class5_count)  AS class5_total,
    SUM(da.class68_total) AS class68_total,
    SUM(da.total_students) AS grand_total_students
FROM daily_attendance da
JOIN schools s ON s.id = da.school_id
GROUP BY s.code, year, month
ORDER BY year DESC, month DESC;
