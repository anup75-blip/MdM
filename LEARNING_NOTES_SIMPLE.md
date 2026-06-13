# MDM Project — Simple Language Learning Notes
### (Read this to become an expert — no prior knowledge needed)

---

## PART 1: What is a Database?

Imagine you are a teacher and you have a **big register book**.
Every day you write:
- Date
- How many students came to Class 5
- How many came to Class 6, 7, 8

At the end of the month, you count everything and make a bill.

A **database** is exactly this register book — but stored on a computer in the cloud.
Instead of pages, it has **tables**.
Instead of lines, it has **rows**.
Instead of columns, it has... **columns** (same word!).

Our database has 4 tables (4 register books):

| Table Name | What it stores | Real-life comparison |
|---|---|---|
| `schools` | School name, district, subscription | School's identity card |
| `user_profiles` | Teacher name, role, which school | Teacher's staff record |
| `attendance` | Daily class 5/6/7/8 numbers | Daily attendance register |
| `audit_log` | Who logged in, who saved what, when | CCTV recording |

---

## PART 2: What is SQL?

**SQL** = Structured Query Language.
It is the language you use to talk to a database.

Think of it like this:
- Database = a very obedient assistant sitting in a room with all the registers
- SQL = the instructions you shout through the door

Four most important SQL words:

| SQL Word | What it means | Example |
|---|---|---|
| `SELECT` | Show me data | "Show me all attendance for June" |
| `INSERT` | Add new data | "Add today's attendance" |
| `UPDATE` | Change existing data | "Fix yesterday's Class 5 count" |
| `DELETE` | Remove data | "Delete this wrong entry" |

### Example SELECT:
```sql
SELECT date, class5, class6
FROM attendance
WHERE school_id = 'abc123'
AND date >= '2026-06-01';
```
**In plain English:** "Show me the date, class5, and class6 numbers from the attendance table, but only for school abc123, and only from June 1st onwards."

### Example INSERT:
```sql
INSERT INTO attendance (school_id, date, class5, class6, class7, class8)
VALUES ('abc123', '2026-06-11', 45, 38, 32, 29);
```
**In plain English:** "Add a new row in the attendance table with these values."

---

## PART 3: What is CREATE TABLE?

When you first set up the database, you have to tell it:
"I want a table named `attendance`. It should have these columns."

```sql
CREATE TABLE attendance (
    id        UUID PRIMARY KEY,   -- unique ID for every row
    school_id UUID,               -- which school this belongs to
    date      DATE,               -- which day
    class5    INTEGER,            -- number of class 5 students
    class6    INTEGER,            -- number of class 6 students
    class7    INTEGER,            -- number of class 7 students
    class8    INTEGER             -- number of class 8 students
);
```

This is like drawing the columns in a new register before you start writing in it.

**You only run CREATE TABLE once.**
If you run it again, the database says: "Error — table already exists!"

---

## PART 4: What is ALTER TABLE?

After some time, you realize: "I need one more column — I forgot to add `entered_by` (who filled this attendance)."

You can't run CREATE TABLE again (it will fail).
So you use ALTER TABLE — which means "change the existing table":

```sql
ALTER TABLE attendance
    ADD COLUMN entered_by UUID;
```

This adds one new column to the existing table.
**All old data is preserved — only the new column is added (it will be empty/NULL for old rows).**

This is like adding a new column to an existing register using a ruler — old entries are untouched.

---

## PART 5: What are SQL Patch Files?

In real projects, the database keeps changing as you build new features.
You can't redo the whole setup every time.

So we create **numbered patch files**:
- `supabase_schema.sql` — original setup (run once at the start)
- `supabase_schema_patch_001.sql` — first change (run after original)
- `supabase_schema_patch_002.sql` — second change (run after 001)

Each patch file only adds/changes a small thing.
They are run **in order**, one time each.

**Why numbered?** Because the order matters.
Patch 002 might depend on something patch 001 added.
If you run 002 before 001, it could fail.

This is called **database migration** — a standard practice in all professional software.

---

## PART 6: What is a PRIMARY KEY and UUID?

Every row in every table has a **unique ID** called a primary key.
This is like a roll number for students — every student has a different one.

In our database we use **UUID** as the primary key.

**UUID** = Universally Unique Identifier
Example: `550e8400-e29b-41d4-a716-446655440000`

It looks random because it IS random. The computer generates it automatically.
The chances of two UUIDs being the same are basically zero.

**Why not just use 1, 2, 3, 4... ?**
Because if School A has ID=5 and School B has ID=5 (in different systems), they'd clash.
UUID avoids this completely. Used in all large-scale software.

---

## PART 7: What is NULL?

**NULL** means "empty — no value stored here."

Example:
```sql
INSERT INTO schools (name, district, udise_code)
VALUES ('Indirabaai Vidyalaya', 'Amravati', NULL);
```

The `udise_code` column exists but has no value for this school.
It's not zero. It's not blank text. It's NULL — meaning "not filled in."

You see `NULL` a lot in databases. It just means that particular cell is empty.

---

## PART 8: What is Row Level Security (RLS)?

This is one of the most important concepts.

**The problem:**
Imagine all schools are using the same database.
Without any protection, Teacher A could accidentally (or intentionally) see Teacher B's data.
That would be a serious privacy problem.

**The solution: RLS (Row Level Security)**
It's a filter that automatically applies to every query.
You define rules like: "A teacher can only see rows where school_id matches their own."

```sql
CREATE POLICY "attendance_select" ON attendance
    FOR SELECT
    USING (school_id = my_school_id());
```

**In plain English:**
"When anyone tries to SELECT from the attendance table,
only show them rows where the school_id equals THEIR school_id.
Block everything else automatically."

`my_school_id()` is a helper function we wrote that returns the school_id of whoever is currently logged in.

**How it works behind the scenes:**
- Teacher from "Indirabaai School" logs in → `my_school_id()` returns their school's UUID
- They run any query → Supabase automatically adds `WHERE school_id = 'their-uuid'`
- They can NEVER see other schools' data, even if they try

**USING vs WITH CHECK:**
- `USING` — filter applied on SELECT, UPDATE, DELETE (reading/changing existing rows)
- `WITH CHECK` — filter applied on INSERT (creating new rows)

---

## PART 9: What is Authentication?

**Authentication** = verifying "who are you?"

When a teacher opens the app and types their phone number and password:
1. Streamlit sends this to Supabase
2. Supabase checks: "Does this phone+password combination exist?"
3. If yes → Supabase sends back a **session token**
4. Streamlit stores this token and uses it for all future requests

A **session token** is like a temporary pass/badge.
It says: "This person logged in successfully. Trust them for the next few hours."

### Our synthetic email trick:
Supabase Auth normally works with email addresses.
But our teachers use phone numbers, not emails.
Sending SMS costs money (₹ per message).

**Our solution:**
We convert the phone number to a fake email address:
```
9876543210  →  9876543210@mdm.app
```

Supabase sees it as a normal email+password login.
No SMS sent. No cost. Works perfectly.

```python
def _to_auth_email(phone):
    digits = "9876543210"           # the phone number
    return "9876543210@mdm.app"     # fake email we made up
```

Nobody actually receives email at `@mdm.app` — it's just a format trick.

---

## PART 10: What is a Session (in Streamlit)?

When a teacher logs in, we need the app to "remember" who they are as they click around.

In Streamlit, this is called **session state**.
It's a dictionary (like a box of labeled items) that lasts as long as the browser tab is open.

```python
# After login, we store everything about the teacher here:
st.session_state["mdm_user"] = {
    "user_id":    "uuid...",
    "school_id":  "uuid...",
    "school_name": "Indirabaai Vidyalaya",
    "role":       "teacher",
    "full_name":  "Sunita Deshmukh",
}

# On any other page, we can read it back:
user = st.session_state.get("mdm_user")
if user:
    print(user["school_name"])   # "Indirabaai Vidyalaya"
```

When the teacher clicks Logout, we do:
```python
st.session_state.pop("mdm_user", None)   # delete it from the box
```

After that, the app sees no user → shows login page again.

---

## PART 11: What is TIMESTAMPTZ?

`TIMESTAMPTZ` = Timestamp With Time Zone.
It stores an exact point in time: date + time + timezone.

Example value: `2026-07-11 14:30:00+05:30`
This means: July 11, 2026, 2:30 PM, Indian Standard Time.

**Why include timezone?**
If you store "2026-07-11 14:30:00" without timezone, and the server is in a different timezone (like USA), the time would be wrong.
TIMESTAMPTZ always stores in UTC (world standard time) and converts on display.

We use it for:
- `trial_ends_at` — exactly when the 30-day trial ends
- `created_at` — exactly when the school signed up
- `updated_at` — exactly when attendance was last changed

**In Python, we create one like this:**
```python
from datetime import datetime, timezone, timedelta

# "Now + 30 days" in UTC
trial_ends = datetime.now(timezone.utc) + timedelta(days=30)
# Result: 2026-07-11 09:00:00+00:00
```

---

## PART 12: What is the Subscription System We Built?

We added a business model: 1 month free trial, then pay to continue.

**How it works technically:**

**Step 1 — During signup (auth.py):**
```python
trial_ends_at = datetime.now() + 30 days
# Save to database: subscription_status='trial', trial_ends_at=that date
```

**Step 2 — Every time teacher opens the app (home.py):**
```python
sub = get_subscription_info(school_id)
# This reads from database: what is subscription_status? when does trial end?

if sub["status"] == "expired":
    show_payment_page()   # block the app
    st.stop()             # stop loading rest of page
```

**Step 3 — subscription.py logic:**
```python
if trial_ends_at is in the past:
    return "expired"
elif trial_ends_at is in the future:
    return "trial" with days_left = (trial_ends_at - today)
elif paid and subscription_ends_at is in the future:
    return "active"
```

**The 3 possible statuses:**

| Status | Meaning | What teacher sees |
|---|---|---|
| `trial` | Within 30-day free period | Normal dashboard + "X days left" badge |
| `active` | Paid subscription, still valid | Normal dashboard + "Subscribed" badge |
| `expired` | Trial/subscription ended | Blocked page with payment info |

---

## PART 13: What is "No rows returned"?

When you run SQL and see **"Success. No rows returned"** it means:
- The command worked correctly ✅
- The command was a CREATE, ALTER, UPDATE, or INSERT — not a SELECT
- These commands *do* things, they don't *show* things
- "No rows returned" = there's nothing to display back to you

Compare:
```sql
SELECT * FROM schools;       -- Returns rows (shows you data)
ALTER TABLE schools ADD ...;  -- "Success. No rows returned" (just made a change)
CREATE INDEX ...;             -- "Success. No rows returned" (just created index)
```

If you saw an error instead, the change did NOT happen.
"Success. No rows returned" = everything went fine.

---

## PART 14: What is an INDEX?

An index speeds up searches in a database.

Imagine a book without an index at the back.
To find the word "Amravati", you'd read every single page.
With an index, you go directly to the right page.

```sql
CREATE INDEX idx_attendance_school_date
    ON attendance (school_id, date);
```

This creates an index on the `attendance` table for `school_id` and `date`.
Now when the app asks "show me June attendance for school X", the database finds it instantly instead of scanning all rows.

Without indexes, as you get 500 schools × 30 days × 12 months = millions of rows, queries get slow.
With indexes, they stay fast.

---

## PART 15: What is Email Confirmation and Why We Turned It Off?

By default, Supabase sends a confirmation email when someone signs up:
1. User signs up
2. Supabase sends email: "Click here to confirm your account"
3. Only after clicking → account is active

**Why we turned it off:**
Our teachers sign up with phone numbers.
We store them as fake emails: `9876543210@mdm.app`
Nobody checks that inbox — it doesn't exist.
So the confirmation email would go nowhere and the teacher could never activate their account.

**After turning it off:**
1. Teacher signs up
2. Account is IMMEDIATELY active
3. Supabase returns a session right away
4. Our code detects: `if result.session:` → log in immediately

**Is this safe?**
Yes. For phone-number-based systems, confirming via OTP (one-time password SMS) is the right alternative.
We're skipping OTP for now to save cost.
In the future, you could add OTP verification as an extra security step.

---

## PART 16: How Python Talks to Supabase

We use a Python library called `supabase-py`.
It converts Python code into HTTP requests to the Supabase server.

```python
# This Python code:
result = supabase.table("attendance").select("*").eq("school_id", sid).execute()

# Behind the scenes sends this to Supabase:
# GET https://pbaarfqqyvkjnrxtpbks.supabase.co/rest/v1/attendance?school_id=eq.sid

# Supabase runs SQL: SELECT * FROM attendance WHERE school_id = 'sid'
# And returns the result as JSON → Python dictionary
```

Every database operation (read, write, update) goes through HTTPS — encrypted, like online banking.

---

## Key Concepts Summary Table

| Concept | Simple meaning |
|---|---|
| Database | Cloud register book with tables |
| Table | One register (e.g. attendance register) |
| Row | One entry/record in the register |
| Column | One field (e.g. "class5" column) |
| SQL | Language to talk to the database |
| SELECT | Read data |
| INSERT | Add new data |
| UPDATE | Change existing data |
| CREATE TABLE | Make a new table (run once) |
| ALTER TABLE | Add/change columns in existing table |
| Patch file | SQL file that makes small changes to existing DB |
| PRIMARY KEY | Unique ID for every row (like roll number) |
| UUID | Random unique ID (e.g. 550e8400-e29b-41d4) |
| NULL | Empty — no value stored |
| RLS | Privacy filter — each teacher sees only their data |
| Policy | One specific privacy rule in RLS |
| Authentication | Verifying who you are (login) |
| Session | Temporary "I'm logged in" memory |
| session_state | Streamlit's memory during one browser session |
| TIMESTAMPTZ | Date + time + timezone stored together |
| Index | Speed booster for database searches |
| Email confirmation | Step that verifies email is real (we turned off) |
| Synthetic email | Fake email (9876543210@mdm.app) for phone login |
| Subscription status | trial / active / expired |
| trial_ends_at | Exact timestamp when 30-day free trial ends |
