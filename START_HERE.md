# Mid-Day Meal Project — PostgreSQL Setup Guide

## What This Does
Migrates the attendance data store from Excel-only to PostgreSQL + Excel.
- PostgreSQL stores all daily attendance, food consumption, and bills
- Excel is still generated for government submission (openpyxl pipeline unchanged)
- Streamlit dashboard reads/writes from PostgreSQL instead of Excel directly

---

## Step 1 — Install PostgreSQL (if not done)

1. Download: https://www.postgresql.org/download/windows/
2. Install with default settings, remember the `postgres` password you set
3. Open **pgAdmin** or use **psql** in terminal

---

## Step 2 — Create the Database

Open pgAdmin Query Tool or psql and run:

```sql
CREATE DATABASE midday_meal;
\c midday_meal
```

---

## Step 3 — Run the Schema

In the project root, run:

```powershell
psql -U postgres -d midday_meal -f schema.sql
```

Or paste contents of `schema.sql` into pgAdmin Query Tool and run.

This creates all tables and seeds:
- `schools` — default school (SCH001, Indirabaai Kanya Vidyalaya)
- `food_items` — all 10 food items with quantities
- `expense_rates` — ₹ rates per student (April 2026)

---

## Step 4 — Add Python Database Connector

Install psycopg2 in your venv:

```powershell
.\venv\Scripts\activate
pip install psycopg2-binary python-dotenv
```

---

## Step 5 — Create .env File

Create `.env` in project root (never commit this):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=midday_meal
DB_USER=postgres
DB_PASSWORD=your_password_here
```

---

## Step 6 — Test the Connection

```python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
print("Connected:", conn.status)
conn.close()
```

---

## Schema Overview

| Table | Purpose |
|-------|---------|
| `schools` | School master (multi-school ready) |
| `holidays` | Sundays + govt + school holidays |
| `daily_attendance` | **Core table** — 4 numbers per day (Class 5/6/7/8) |
| `food_items` | Food catalogue with per-student quantities |
| `daily_consumption` | Calculated food used per day |
| `expense_rates` | ₹ rates per student per category |
| `monthly_bills` | Monthly bill totals |
| `audit_log` | Who changed what and when |

### Key: daily_attendance columns
```
attendance_date   → the school day
class5_count      → Col C in Excel
class6_count      → Col E in Excel
class7_count      → Col F in Excel
class8_count      → Col G in Excel
```

---

## Next: QUICK_START_PROMPTS.md

Once schema is running, open `QUICK_START_PROMPTS.md` for copy-paste prompts to:
- Build the db.py connector module
- Update dashboard.py to use PostgreSQL
- Migrate existing April 2026 Excel data to the database
