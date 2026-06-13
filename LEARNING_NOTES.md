# MDM Project — How Everything Works (Learning Notes)

---

## 11. What We Just Did — SQL Patches & Email Confirmation

### What is "Success. No rows returned"?
When you run SQL in Supabase and see this message, it means:
- The command ran successfully
- It was a command that **changes** something (CREATE, ALTER, UPDATE, INSERT)
- "No rows returned" just means it's not a SELECT — it doesn't give back data to show you

Think of it like sending a letter — you get a receipt saying "delivered", not the letter back.

---

### What did Patch 001 do?

Patch 001 added 3 **RLS policies** (security rules) to the database.

**Before patch 001:**
- Teachers could NOT sign up themselves — the database would block the INSERT
- Admin could NOT edit school details
- Admin could NOT change a teacher's role

**After patch 001:**
```sql
-- Any logged-in user can create ONE school (their own, during signup)
CREATE POLICY "schools_insert_self" ON schools
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Admin can edit school details
CREATE POLICY "schools_update_admin" ON schools
    FOR UPDATE USING (my_role() = 'admin');

-- Admin can change a teacher's role
CREATE POLICY "profiles_update_admin" ON user_profiles
    FOR UPDATE USING (my_role() = 'admin');
```

**Why didn't we put this in the original schema.sql?**
We forgot it the first time. That's normal in real projects — you always discover missing pieces after the fact. SQL patch files are the standard way to fix this without breaking anything.

---

### What did Patch 002 do?

Patch 002 added 4 new **columns** to the `schools` table:

| Column | Type | Purpose |
|---|---|---|
| `subscription_status` | TEXT | 'trial', 'active', or 'expired' |
| `trial_ends_at` | TIMESTAMPTZ | Date when free trial ends |
| `subscription_ends_at` | TIMESTAMPTZ | Date when paid subscription ends |
| `razorpay_payment_id` | TEXT | Stored after successful Razorpay payment |

It also ran this UPDATE:
```sql
UPDATE schools
SET subscription_status = 'trial',
    trial_ends_at = created_at + INTERVAL '30 days'
WHERE subscription_status IS NULL;
```
This backfills existing rows — any school already in the database automatically got a 30-day trial starting from when they were created.

**Why ALTER TABLE and not CREATE TABLE?**
The `schools` table already existed. `CREATE TABLE` would fail ("table already exists").
`ALTER TABLE ... ADD COLUMN` just adds new columns to the existing table — existing data is preserved.

---

### Why did we get a syntax error on Patch 002?

```sql
-- This FAILED — PostgreSQL does not support IF NOT EXISTS for CREATE POLICY
CREATE POLICY IF NOT EXISTS "schools_subscription_admin" ON schools ...

-- This WORKS — correct syntax
CREATE POLICY "schools_subscription_admin" ON schools ...
```

`IF NOT EXISTS` is supported for `CREATE TABLE`, `CREATE INDEX`, `CREATE EXTENSION` — but NOT for `CREATE POLICY`. This is a quirk of PostgreSQL. The fix was to simply remove `IF NOT EXISTS`.

**Lesson:** SQL has many small syntax rules that vary by command. When you see an error like `syntax error at or near "NOT"`, it usually means one word in your SQL is in the wrong place or not supported by that command.

---

### Why did we disable Email Confirmation?

Supabase Auth by default sends a confirmation email before activating an account.

**The problem for us:**
- Teachers in rural Maharashtra use phone numbers, not emails
- We store phone as `9876543210@mdm.app` — a fake email address
- No one checks that inbox — confirmation email would be sent to a fake address
- Teacher signs up → gets stuck waiting for email → can never log in

**After disabling:**
- Teacher signs up → account is active immediately → logged in right away
- Supabase returns a `session` object in the signup response
- Our code detects this: `if result.session: → log in immediately`

**Is this safe?**
Yes, for our use case. We're using phone numbers as identity, not emails. The "email confirmation" step was designed for real email signups. For phone-based systems, it's normal to skip it (real phone auth uses OTP instead, but we're avoiding that cost).

---

## 1. The Big Picture (System Architecture)

```
Teacher's Phone/Browser
        │
        ▼
  ┌─────────────┐        ┌─────────────────────────────┐
  │  Streamlit  │◄──────►│  Supabase (cloud database)  │
  │  (home.py)  │        │  - stores attendance data   │
  │  frontend   │        │  - handles login/passwords  │
  └─────────────┘        │  - enforces data security   │
        │                └─────────────────────────────┘
        │
        ▼
  Teacher sees: attendance form, Excel download, bill preview
```

**In plain words:**
- Teacher opens website → Streamlit shows a login page
- Teacher logs in → Streamlit talks to Supabase to verify password
- Teacher enters attendance → Streamlit saves it to Supabase
- Teacher downloads Excel → Streamlit reads data from Supabase and builds the file

---

## 2. Streamlit — The Frontend

**What it is:** A Python library that turns Python scripts into web apps.
You write Python code, it automatically creates buttons, forms, tables on the screen.

**How we use it:**
- `home.py` is the main page
- Files inside `pages/` folder become separate pages automatically
- `st.text_input()` = text box on screen
- `st.form()` = a form with a submit button
- `st.session_state` = remembers things between page refreshes (like "who is logged in")
- `st.rerun()` = refreshes the page

**Example from our code:**
```python
# This creates a text box and a button on the screen
identifier = st.text_input("Mobile Number", placeholder="9876543210")
if st.button("Login"):
    login(identifier, password)   # calls our auth function
    st.rerun()                    # refresh page to show dashboard
```

---

## 3. Supabase — The Database (Backend)

**What it is:** A cloud PostgreSQL database + authentication system. Free for small projects.

**Think of it like:** An Excel file stored in the cloud, but much more powerful and secure.

**Our 4 tables:**

| Table | What it stores |
|---|---|
| `schools` | School name, district, subscription status |
| `user_profiles` | Teacher's name, role, which school they belong to |
| `attendance` | Each day's attendance per class (5/6/7/8) |
| `audit_log` | Record of every login and save action |

**How Python talks to Supabase:**
```python
# This is like a SQL query: "get all attendance for school X in June 2026"
result = supabase.table("attendance")
              .select("*")
              .eq("school_id", school_id)
              .gte("date", "2026-06-01")
              .execute()
rows = result.data    # list of dictionaries
```

---

## 4. SQL — The Database Language

SQL is the language Supabase understands. You write commands to create tables, add data, etc.

**Key concepts:**

### CREATE TABLE
Defines what columns a table has:
```sql
CREATE TABLE schools (
    id          UUID PRIMARY KEY,     -- unique ID (auto-generated)
    name        TEXT NOT NULL,        -- school name, required
    district    TEXT,                 -- district, optional
    active      BOOLEAN DEFAULT true  -- true/false, default is true
);
```

### ALTER TABLE (Patch files)
Adds new columns to an existing table:
```sql
-- This is what patch_002.sql does:
ALTER TABLE schools
    ADD COLUMN subscription_status TEXT DEFAULT 'trial',
    ADD COLUMN trial_ends_at       TIMESTAMPTZ;   -- TIMESTAMPTZ = date+time with timezone
```

### Row Level Security (RLS)
This is like a "privacy filter" on the database.
Without RLS: Teacher A could read Teacher B's data (dangerous!).
With RLS: Each teacher only sees their own school's data.

```sql
-- This policy says: "a teacher can only SELECT rows where the school_id matches their own"
CREATE POLICY "attendance_select" ON attendance
    FOR SELECT USING (school_id = my_school_id());
```
`my_school_id()` is a helper function we defined — it returns the school_id of whoever is currently logged in.

### Why we have patch files (001, 002...)
We can't re-run the whole schema.sql every time we want to change something (it would fail because tables already exist).
So we write small "patch" files that only ADD new things. This is called **database migration**.

---

## 5. Authentication — How Login Works

**The problem:** Supabase Auth normally uses email+password or phone+SMS.
SMS costs money (Twilio). We don't want that.

**Our solution — Synthetic Email Trick:**
We store phone numbers AS IF they were email addresses:
- Teacher enters: `9876543210`
- We convert it to: `9876543210@mdm.app`
- Supabase sees it as a normal email login — no SMS needed!

```python
def _to_auth_email(phone):
    digits = "".join(c for c in phone if c.isdigit())
    return f"{digits}@mdm.app"    # "9876543210@mdm.app"
```

**Sign-up flow (3 steps happen automatically):**
1. Create auth account in Supabase (`9876543210@mdm.app` + password)
2. Create school record in `schools` table
3. Create user profile in `user_profiles` table (links auth user → school)

**Session state:**
After login, we store user info in `st.session_state["mdm_user"]`:
```python
{
    "user_id":    "uuid...",
    "school_id":  "uuid...",
    "school_name": "Indirabaai Vidyalaya",
    "role":       "teacher",
    ...
}
```
This is how the app knows "who is logged in" on every page.

---

## 6. Subscription System — How Trial/Payment Works

**Flow:**
```
New Signup
    │
    ▼
trial_ends_at = TODAY + 30 days     ← set in auth.py during signup
subscription_status = 'trial'
    │
    ▼ (30 days later)
subscription.py checks: Is trial_ends_at in the past?
    │
    ├── YES → status = 'expired' → show "pay to continue" page
    └── NO  → status = 'trial'  → show app normally
```

**subscription.py logic:**
```python
def get_subscription_info(school_id):
    # Fetch from database
    data = supabase.table("schools").select("subscription_status, trial_ends_at")...

    now = datetime.now(timezone.utc)

    if status == "trial":
        if trial_ends_at < now:
            return {"status": "expired"}   # trial over
        else:
            return {"status": "trial", "days_left": (trial_ends_at - now).days}
```

**In home.py (the gate):**
```python
sub = get_subscription_info(user["school_id"])
if sub["status"] == "expired":
    _show_expired_page()   # show "please pay" screen
    st.stop()              # stop the rest of the app from loading
```

---

## 7. File Structure — What Each File Does

```
MidDayMealProject/
│
├── home.py                   ← MAIN FILE. Login gate + attendance dashboard
├── pages/
│   ├── generate_bill.py      ← Bill generator page
│   └── admin.py              ← Admin panel (only for deshmukha75@gmail.com)
│
├── backend/                  ← All the "logic" (not UI)
│   ├── supabase_client.py    ← Creates Supabase connection (reads secrets.toml)
│   ├── auth.py               ← Login, signup, session management
│   ├── attendance_db.py      ← Save/load attendance from Supabase
│   ├── excel_export.py       ← Build Excel file in memory
│   ├── bill_calculator.py    ← Calculate ₹ bill from attendance numbers
│   └── subscription.py       ← Check if school's trial/subscription is active
│
├── scripts/
│   ├── holiday_manager.py    ← Maharashtra govt holidays
│   └── setup_schools.py      ← Bulk import schools from CSV
│
├── templates/                ← Excel template file (.xlsx)
├── data/
│   └── holidays/             ← Holiday Excel files
│
├── supabase_schema.sql            ← ✅ Run once — creates all tables
├── supabase_schema_patch_001.sql  ← ⏳ Run next — self-registration policies
├── supabase_schema_patch_002.sql  ← ⏳ Run after 001 — subscription columns
│
└── .streamlit/
    └── secrets.toml          ← Supabase URL + anon key (NEVER share this file)
```

---

## 8. How to Build With Claude Effectively

### The method we used:
1. **Describe the goal** ("I want teachers to sign up themselves, no admin needed")
2. **Claude asks clarifying questions** (phone or email? SMS or synthetic?)
3. **Claude writes the code** in small, logical pieces
4. **We test each piece** before moving to next
5. **Memory system** saves context between sessions — Claude remembers your project

### What Claude is good at:
- Writing boilerplate code quickly (forms, tables, SQL)
- Explaining WHY code works a certain way
- Catching security issues (RLS, SQL injection, etc.)
- Designing systems step-by-step

### Tips for working with Claude:
- **Be specific** about what you want: "I want a 30-day trial, then payment via Razorpay"
- **One feature at a time** — don't ask for everything at once
- **Say what you already have** — Claude won't rewrite working code
- **Ask "why"** anytime — Claude will explain any piece of code

### Good prompts:
- "Explain how auth.py line 135 works in simple terms"
- "What happens if a teacher signs up twice with the same phone?"
- "Show me what happens step by step when I click Save Attendance"

---

## 9. What Happens End-to-End When a Teacher Saves Attendance

1. Teacher types 45 in Class 5 field and clicks "Save Attendance"
2. `home.py` → calls `save_attendance(school_id, user_id, date, 45, 30, 28, 20)`
3. `attendance_db.py` → runs Supabase upsert:
   ```sql
   INSERT INTO attendance (school_id, date, class5, class6, class7, class8, entered_by)
   VALUES (uuid, '2026-06-11', 45, 30, 28, 20, user_uuid)
   ON CONFLICT (school_id, date) DO UPDATE SET class5=45, ...
   ```
   (UPSERT = insert if new, update if already exists for that date)
4. Supabase RLS checks: does this teacher own this school_id? If yes, allow. If no, block.
5. Data is saved. Supabase returns success.
6. `home.py` shows green "Saved" message and calls `st.rerun()`

---

## 10. Key Terms Glossary

| Term | Meaning |
|---|---|
| **Supabase** | Cloud database (PostgreSQL) + auth, free tier available |
| **Streamlit** | Python library that creates web apps from Python scripts |
| **RLS** | Row Level Security — each user only sees their own data |
| **UUID** | Universally Unique ID — random 128-bit ID used as primary key |
| **UPSERT** | Insert if new, Update if already exists |
| **Session state** | Temporary memory that lasts one browser session |
| **Synthetic email** | Fake email (9876543210@mdm.app) to use phone as login |
| **Patch file** | SQL file that adds/changes things in existing database |
| **Trial** | 30-day free period after signup before payment required |
| **Razorpay** | Indian payment gateway (like Stripe for India) |
| **openpyxl** | Python library that reads/writes Excel files |
| **BytesIO** | In-memory file — Excel generated without saving to disk |
| **TIMESTAMPTZ** | Timestamp with timezone — stores exact date+time globally |
