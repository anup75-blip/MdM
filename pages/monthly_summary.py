"""
monthly_summary.py
Monthly Summary — mirrors Sheet2 of the government Excel.
Shows total food consumed and overall bill summary for the month.
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
from bill_calculator import calculate_bill, FOOD_ITEMS
from bill_header     import render_bill_header
from holiday_manager import HolidayManager

HOLIDAY_FILE = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"

st.set_page_config(page_title="Monthly Summary", layout="wide", initial_sidebar_state="expanded")

user = require_login()

with st.sidebar:
    st.title("Monthly Summary")
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

working_day_dates = hm.get_working_days(sel_month)
working_days      = len(working_day_dates)

st.title(f"Monthly Summary — {month_label}")
render_bill_header(user, bill_label="Monthly Summary", month_label=month_label)

if month_df.empty or month_df["total"].sum() == 0:
    st.info("No attendance entered for this month yet.")
    st.stop()

filled_df = month_df[month_df["total"] > 0]

# ── Summary metrics ───────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Working Days",      working_days)
m2.metric("Days Filled",       len(filled_df))
m3.metric("Days Missing",      working_days - len(filled_df))
m4.metric("Class 5 Total",     int(filled_df["class5"].sum()))
m5.metric("Class 6-8 Total",   int(filled_df["class68"].sum()))

st.divider()

# ── Bill summary ──────────────────────────────────────────────────────────────
c5_bill, c68_bill = calculate_bill(
    attendance_df=filled_df.rename(columns={"class5": "Class5", "class68": "Class68"}),
    working_days=working_days,
)

col5, col68 = st.columns(2)

with col5:
    st.subheader("इ.5 — Class 5")
    st.metric("Student-Days", c5_bill.total_student_days)
    for el in c5_bill.expense_lines:
        st.metric(el.label, f"₹{el.amount_inr:,.2f}")
    st.success(f"**Total: ₹{c5_bill.total_expense:,.2f}**")

with col68:
    st.subheader("इ.6 ते 8 — Class 6–8")
    st.metric("Student-Days", c68_bill.total_student_days)
    for el in c68_bill.expense_lines:
        st.metric(el.label, f"₹{el.amount_inr:,.2f}")
    st.success(f"**Total: ₹{c68_bill.total_expense:,.2f}**")

st.divider()
grand = c5_bill.total_expense + c68_bill.total_expense
st.subheader(f"Grand Total: ₹{grand:,.2f}")

st.divider()

# ── Food consumed summary ──────────────────────────────────────────────────────
st.subheader("Total Food Consumed")
food_rows = []
for fl5, fl68 in zip(c5_bill.food_lines, c68_bill.food_lines):
    food_rows.append({
        "Food Item":           fl5.name_marathi,
        "English Name":        fl5.name_en,
        "Unit":                fl5.unit,
        "Class 5 Used":        fl5.used_kg,
        "Class 6-8 Used":      fl68.used_kg,
        "Total Used":          round(fl5.used_kg + fl68.used_kg, 3),
    })
st.dataframe(pd.DataFrame(food_rows), use_container_width=True, hide_index=True)
