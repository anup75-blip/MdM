# MDMS Project - File Organization & Quick Reference

## Final Project Structure

```
mdms/
│
├── home.py                          # Main Streamlit app (entry point)
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
├── DEPLOY.md                        # Deployment guide
├── schema.sql                       # PostgreSQL schema
│
├── pages/
│   ├── login.py                     # Login page
│   ├── daily_entry.py              # Daily meal entry form
│   ├── monthly_entry.py            # Monthly calendar entry
│   ├── food_stock.py               # Food stock tracking
│   ├── generate_bill.py            # Excel bill generator
│   └── sync.py                      # Offline sync manager
│
├── backend/
│   ├── database.py                 # PostgreSQL connections & queries
│   ├── auth.py                      # JWT, hashing, encryption
│   ├── models.py                    # SQLAlchemy models (optional)
│   └── xlsx_generator.py           # openpyxl bill creation
│
├── local/
│   ├── sqlite_init.py              # Local SQLite setup
│   └── sync_logic.py               # Offline-first sync
│
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   └── secrets.toml                # Database credentials (GITIGNORE this!)
│
├── assets/
│   └── logo.png                    # School logo (optional)
│
└── tests/
    ├── test_auth.py
    ├── test_meal_entry.py
    └── test_xlsx_generation.py
```

---

## Key Files Explained

### **1. home.py (Entry Point)**
```python
# What it does:
- Check if user is logged in
- Show dashboard with 4 buttons
- Navigate to different pages

# When to use:
- This is the first file user sees
- Always running (sidebar navigation)
```

### **2. pages/login.py**
```python
# What it does:
- Accept school code + password
- Hash & verify against users table
- Store session_state["school_id"]

# When to run:
- First time opening app
- After logout
```

### **3. pages/daily_entry.py**
```python
# What it does:
- Form to enter one day's meal data
- Saves to local SQLite (offline-first)
- Ready for sync

# When to use:
- Teacher enters data same-day or next day
```

### **4. pages/monthly_entry.py**
```python
# What it does:
- Calendar view of entire month
- Click on day → enter all meals for that day
- Bulk save at end

# When to use:
- Teacher compiles month's data at end of month
- Faster for catching up on missed days
```

### **5. pages/food_stock.py**
```python
# What it does:
- Track opening/closing balance of each food item
- Auto-calculate from daily meals
- Detect wastage/discrepancies

# When to use:
- Cook/in-charge enters daily after meals served
```

### **6. pages/generate_bill.py**
```python
# What it does:
- Query entire month's data
- Create Excel file (openpyxl)
- User downloads it

# When to use:
- At month-end or on-demand
- Before submitting to district
```

### **7. pages/sync.py**
```python
# What it does:
- Show pending records
- Detect network status
- Upload to PostgreSQL
- Mark as synced

# When to use:
- Periodic sync (manual or auto)
- After internet is back online
```

### **8. backend/database.py**
```python
# Functions:
- get_db_connection()      → Returns DB connection
- get_meal_types()          → Fetch dropdown options
- get_food_items()          → Fetch dropdown options
- insert_daily_meal()       → Save meal to DB
- insert_food_stock()       → Save stock to DB

# Usage:
from backend.database import get_meal_types
types = get_meal_types()
```

### **9. backend/auth.py**
```python
# Functions:
- hash_password(pwd)        → SHA256 hash
- verify_password()         → Check hash
- create_jwt_token()        → Generate session token
- encrypt_field()           → Fernet encryption
- decrypt_field()           → Fernet decryption

# Usage:
from backend.auth import hash_password
hash = hash_password("password123")
```

### **10. backend/xlsx_generator.py**
```python
# Functions:
- generate_daily_meals_sheet()   → Sheet 1 data
- generate_food_stock_sheet()    → Sheet 2 data
- create_workbook()              → Build Excel
- save_to_file()                 → Download

# Usage:
from backend.xlsx_generator import create_workbook
wb = create_workbook(school_id, month, year)
wb.save("bill.xlsx")
```

### **11. local/sqlite_init.py**
```python
# Functions:
- init_local_db()           → Create local SQLite
- save_meal_pending()       → Save to local (offline)
- save_stock_pending()      → Save to local (offline)
- get_pending_meals()       → Fetch unsync'd records
- mark_synced()             → Mark as sent to server

# Usage:
from local.sqlite_init import save_meal_pending
save_meal_pending(school_id, date, grade, meal_type, qty)
```

### **12. schema.sql**
```sql
-- What it contains:
- CREATE TABLE statements (11 tables)
- PRIMARY KEY, FOREIGN KEY constraints
- Sample INSERT data (5 schools, 10 meal types, 15 food items)

-- How to use:
psql -U postgres < schema.sql
-- Or in PostgreSQL CLI:
\i schema.sql
```

### **13. .streamlit/config.toml**
```toml
[theme]
primaryColor = "#2E7D32"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"

[client]
showErrorDetails = true

[server]
port = 8501
headless = true
```

### **14. .streamlit/secrets.toml** (KEEP SECRET!)
```toml
[database]
host = "localhost"
port = 5432
database = "mdms_db"
user = "mdms_user"
password = "your-strong-password"

[api]
jwt_secret = "random-secret-key-here"
encryption_key = "fernet-key-here"
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                         │
│  (Runs in browser, mobile-friendly)                         │
└────┬──────────────┬────────────────┬───────────────┬────────┘
     │              │                │               │
     v              v                v               v
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│ Login   │   │Daily/    │   │Food      │   │Generate      │
│Page     │   │Monthly   │   │Stock     │   │Bill & Sync   │
│         │   │Entry     │   │Entry     │   │              │
└────┬────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘
     │             │               │                │
     └─────────────┴───────────────┴────────────────┘
                    │
                    v
          ┌──────────────────────┐
          │  backend/database.py │
          │  (Query/Insert logic)│
          └──────────┬───────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        v                       v
  ┌──────────────┐      ┌──────────────────┐
  │ PostgreSQL   │      │  SQLite (Local)  │
  │ (Server)     │      │  (Offline Cache) │
  └──────────────┘      └──────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
                    v
         ┌────────────────────┐
         │  backend/          │
         │  xlsx_generator.py │
         │  (openpyxl)        │
         └────────┬───────────┘
                  │
                  v
         ┌─────────────────┐
         │ Excel File      │
         │ (Download to    │
         │  school/admin)  │
         └─────────────────┘
```

---

## Session State Variables

```python
# After login:
st.session_state["school_id"]      # int
st.session_state["is_logged_in"]   # bool
st.session_state["teacher_name"]   # str

# For forms:
st.session_state["current_date"]   # date object
st.session_state["current_grade"]  # str ("5" or "6-8")
st.session_state["form_dirty"]     # bool (form modified?)

# For sync:
st.session_state["last_sync"]      # datetime
st.session_state["pending_count"]  # int
st.session_state["is_online"]      # bool
```

---

## Common Operations

### **Read from PostgreSQL**
```python
from backend.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM schools WHERE id = %s", (school_id,))
result = cursor.fetchone()
conn.close()
```

### **Write to Local SQLite (Offline)**
```python
from local.sqlite_init import save_meal_pending

save_meal_pending(
    school_id=1,
    date="2026-04-15",
    grade="5",
    meal_type="रिकली",
    qty_gm=3000,
    student_count=60,
    wastage_gm=150
)
```

### **Generate Excel**
```python
from backend.xlsx_generator import create_workbook

wb = create_workbook(school_id=1, month=4, year=2026)
wb.save("April_2026.xlsx")
st.download_button("Download Bill", open("April_2026.xlsx", "rb"))
```

### **Sync to Server**
```python
from local.sync_logic import sync_to_server

success, message = sync_to_server(school_id=1)
if success:
    st.success(f"Synced! {message}")
else:
    st.error(f"Sync failed: {message}")
```

---

## Environment Variables

Create a `.env` file (for local testing):

```env
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_LOGGER_LEVEL=info
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mdms_db
DB_USER=mdms_user
DB_PASSWORD=change-me
JWT_SECRET=your-secret-key
```

---

## Dependency Tree

```
home.py
├── pages/login.py
├── pages/daily_entry.py
│   ├── backend/database.py
│   ├── local/sqlite_init.py
│   └── backend/auth.py
├── pages/monthly_entry.py
├── pages/food_stock.py
├── pages/generate_bill.py
│   ├── backend/xlsx_generator.py
│   └── backend/database.py
└── pages/sync.py
    └── local/sync_logic.py
```

---

## Checklist Before Going Live

### **Code Quality**
- [ ] No hardcoded passwords (use secrets.toml)
- [ ] All imports at top of file
- [ ] Functions have docstrings
- [ ] Error handling for DB queries
- [ ] Logging for debugging

### **Security**
- [ ] Passwords hashed (SHA256 or bcrypt)
- [ ] JWT tokens for sessions
- [ ] Sensitive data encrypted (Fernet)
- [ ] SQL injection prevention (parameterized queries)
- [ ] No sensitive data in logs

### **Testing**
- [ ] Login works with test user
- [ ] Daily entry saves locally
- [ ] Monthly entry saves correctly
- [ ] Offline mode works (disconnect internet)
- [ ] Sync uploads to server
- [ ] Excel generation is correct
- [ ] Mobile responsiveness checked
- [ ] Marathi text rendering OK

### **Performance**
- [ ] Page load < 2 seconds
- [ ] Forms submit < 1 second
- [ ] No console errors
- [ ] Images optimized (if any)
- [ ] Database queries indexed

### **Deployment**
- [ ] .gitignore includes secrets.toml
- [ ] README.md updated
- [ ] requirements.txt complete
- [ ] Nginx config ready
- [ ] SSL certificate configured
- [ ] Database backups scheduled
- [ ] Error monitoring setup (Sentry optional)

---

## Quick Debugging

### **Issue: Login fails**
```python
from backend.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE username=%s", ("test_user",))
print(cursor.fetchone())
```

### **Issue: Data not saving**
```python
import sqlite3
conn = sqlite3.connect("mdms_local.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM daily_meals_pending WHERE synced=0")
print(cursor.fetchall())
```

### **Issue: Excel not generating**
```python
# pip install openpyxl
from openpyxl import Workbook
wb = Workbook()
wb.save("test.xlsx")
print("Excel works!")
```

### **Issue: Can't connect to PostgreSQL**
```bash
# Check if PostgreSQL is running:
sudo systemctl status postgresql

# Test connection:
psql -U mdms_user -d mdms_db -h localhost
```

---

## That's It!

You now have:
1. Complete project structure
2. File-by-file breakdown
3. Data flow diagram
4. Quick reference for operations
5. Debugging guide

**Next: Build phase by phase using schema.sql as the foundation.**
