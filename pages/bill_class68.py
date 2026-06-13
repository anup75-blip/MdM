"""
bill_class68.py
Class 6-8 Government Bill — mirrors 'Bill 6 To 8' sheet of the government Excel.
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
from bill_calculator import calculate_bill
from bill_header     import render_bill_header
from holiday_manager import HolidayManager

HOLIDAY_FILE = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"

st.set_page_config(page_title="Bill — Class 6-8", layout="wide", initial_sidebar_state="expanded")

user = require_login()

with st.sidebar:
    st.title("Bill — Class 6-8")
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

working_days = len(hm.get_working_days(sel_month))

st.title("Bill — इ.6 ते 8 (Class 6–8)")
render_bill_header(user, bill_label="इ.6 ते 8 (Class 6–8)", month_label=month_label)

if month_df.empty or month_df["class68"].sum() == 0:
    st.info("No Class 6-8 attendance entered for this month yet.")
    st.stop()

filled_df = month_df[month_df["total"] > 0]
_, c68_bill = calculate_bill(
    attendance_df=filled_df.rename(columns={"class5": "Class5", "class68": "Class68"}),
    working_days=working_days,
)

# ── Key metrics ───────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric("Working Days",   working_days)
m2.metric("Student-Days",   c68_bill.total_student_days)
m3.metric("Total Bill",     f"₹{c68_bill.total_expense:,.2f}")

st.divider()

# ── Expense breakdown ─────────────────────────────────────────────────────────
st.subheader("Expense Breakdown")
exp_rows = []
for el in c68_bill.expense_lines:
    exp_rows.append({
        "Expense Item":  el.label,
        "Rate (₹/day)":  el.rate_inr,
        "Student-Days":  el.student_days,
        "Amount (₹)":    f"₹{el.amount_inr:,.2f}",
    })
exp_rows.append({
    "Expense Item": "**TOTAL**",
    "Rate (₹/day)": "",
    "Student-Days": "",
    "Amount (₹)":   f"**₹{c68_bill.total_expense:,.2f}**",
})
st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Food consumed ─────────────────────────────────────────────────────────────
st.subheader("Food Consumed — Class 6–8")
food_rows = []
for i, fl in enumerate(c68_bill.food_lines, start=1):
    food_rows.append({
        "Sr.":          i,
        "Food Item":    fl.name_marathi,
        "English":      fl.name_en,
        "Unit":         fl.unit,
        "Used":         fl.used_kg,
    })
st.dataframe(pd.DataFrame(food_rows), use_container_width=True, hide_index=True)
