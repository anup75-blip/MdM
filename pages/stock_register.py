"""
stock_register.py
Daily Stock Register — mirrors Sheet1 of the government Excel.
Shows daily food quantities consumed based on attendance entered.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
sys.path.insert(0, str(BASE_DIR / "backend"))

from auth            import require_login, logout
from attendance_db   import get_month_attendance
from bill_calculator import FOOD_ITEMS
from bill_header     import render_bill_header
from holiday_manager import HolidayManager

HOLIDAY_FILE = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"

st.set_page_config(page_title="Stock Register", layout="wide", initial_sidebar_state="expanded")

user = require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Stock Register")
    st.markdown(f"**{user['school_name']}**")
    st.caption(f"Code: {user['school_code']}  |  Role: {user['role'].title()}")
    st.divider()

    today       = date.today()
    month_names = [date(today.year, m, 1).strftime("%B") for m in range(1, 13)]
    month_map   = {name: i + 1 for i, name in enumerate(month_names)}

    sel_month_name = st.selectbox("Month", month_names, index=today.month - 1)
    sel_month      = month_map[sel_month_name]
    sel_year       = int(st.number_input("Year", value=today.year, min_value=2020, max_value=2035, step=1))
    month_label    = date(sel_year, sel_month, 1).strftime("%B %Y")

    st.divider()
    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
school_id = user["school_id"]
month_df  = get_month_attendance(school_id, sel_year, sel_month)

hm = HolidayManager(year=sel_year)
if HOLIDAY_FILE.exists():
    hm.load_school_holidays(HOLIDAY_FILE)

st.title(f"Stock Register — {month_label}")
render_bill_header(user, bill_label="Stock Register (Sheet 1)", month_label=month_label)

if month_df.empty or month_df["total"].sum() == 0:
    st.info("No attendance entered for this month yet. Enter attendance from the Home page first.")
    st.stop()

# ── Build daily stock table ───────────────────────────────────────────────────
rows = []
for _, row in month_df.iterrows():
    d       = row["date"]
    c5      = int(row["class5"])
    c68     = int(row["class68"])
    total   = int(row["total"])
    holiday = hm.holiday_name(d)

    food_cols = {}
    for name_en, name_marathi, qty5, qty68, unit in FOOD_ITEMS:
        used = round((c5 * qty5 + c68 * qty68) / 1000.0, 3)
        food_cols[f"{name_en} ({unit})"] = used if total > 0 else 0.0

    rows.append({
        "Date":      d.strftime("%d/%m/%Y"),
        "Day":       d.strftime("%A"),
        "Holiday":   holiday or "",
        "Class 5":   c5,
        "Class 6":   int(row["class6"]),
        "Class 7":   int(row["class7"]),
        "Class 8":   int(row["class8"]),
        "Class 6-8": c68,
        "Total":     total,
        **food_cols,
    })

df = pd.DataFrame(rows)

# Highlight holidays
def highlight(row):
    if row["Holiday"]:
        return ["background-color:#f5f5f5; color:#aaa"] * len(row)
    if row["Total"] == 0:
        return ["background-color:#fff3cd"] * len(row)
    return ["background-color:#d4edda"] * len(row)

st.dataframe(
    df.style.apply(highlight, axis=1),
    use_container_width=True,
    hide_index=True,
    height=600,
)

# ── Monthly totals ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Monthly Totals")

filled = month_df[month_df["total"] > 0]
c5_total  = int(filled["class5"].sum())
c68_total = int(filled["class68"].sum())

t1, t2, t3 = st.columns(3)
t1.metric("Total Class 5 Student-Days",   c5_total)
t2.metric("Total Class 6-8 Student-Days", c68_total)
t3.metric("Grand Total Student-Days",     c5_total + c68_total)

st.divider()
st.subheader("Total Food Consumed This Month")

food_rows = []
for name_en, name_marathi, qty5, qty68, unit in FOOD_ITEMS:
    c5_used  = round(c5_total  * qty5  / 1000.0, 3)
    c68_used = round(c68_total * qty68 / 1000.0, 3)
    food_rows.append({
        "Food Item":      f"{name_marathi} ({name_en})",
        "Unit":           unit,
        "Class 5":        c5_used,
        "Class 6-8":      c68_used,
        "Total":          round(c5_used + c68_used, 3),
    })

st.dataframe(pd.DataFrame(food_rows), use_container_width=True, hide_index=True)
