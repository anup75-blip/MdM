"""
generate_bill.py
Monthly Government Bill page — reads from Supabase, isolated per school.
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

from auth            import require_login
from attendance_db   import get_month_attendance, get_attendance_records
from bill_calculator import FOOD_ITEMS, BillResult, calculate_bill
from excel_export    import generate_excel_buffer
from holiday_manager import HolidayManager

HOLIDAY_FILE = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"
TEMPLATE_DIR = BASE_DIR / "templates"

st.set_page_config(
    page_title="MDM Bill Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth check ────────────────────────────────────────────────────────────────
user        = require_login()
school_id   = user["school_id"]
school_name = user["school_name"]
school_code = user["school_code"]

st.title("Monthly Bill Generator")
st.caption(f"मासिक बिल — {school_name}  |  Maharashtra Mid-Day Meal Scheme")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Period / कालावधी")

    today = date.today()
    month_map      = {date(today.year, m, 1).strftime("%B"): m for m in range(1, 13)}
    sel_month_name = st.selectbox("Month", list(month_map.keys()), index=today.month - 1)
    sel_month      = month_map[sel_month_name]
    sel_year       = int(st.number_input("Year", value=today.year,
                                         min_value=2020, max_value=2035, step=1))
    st.divider()

    st.subheader("Enrolled Students / पटसंख्या")
    c5_enrolled  = int(st.number_input("Class 5 / इ.5",     min_value=0, value=60, step=1))
    c68_enrolled = int(st.number_input("Class 6-8 / इ.6-8", min_value=0, value=80, step=1))

    st.divider()
    if st.button("Back to Dashboard"):
        st.switch_page("home.py")

# ── Load attendance from Supabase ─────────────────────────────────────────────
month_label = date(sel_year, sel_month, 1).strftime("%B %Y")

hm = HolidayManager(year=sel_year)
if HOLIDAY_FILE.exists():
    hm.load_school_holidays(HOLIDAY_FILE)

working_days = len(hm.get_working_days(sel_month))
month_df     = get_month_attendance(school_id, sel_year, sel_month)

if month_df.empty:
    st.warning(f"No attendance data found for **{month_label}**. Enter attendance on the main dashboard first.")
    st.stop()

def _is_working(d) -> bool:
    try:
        return hm.is_working_day(d)
    except Exception:
        return True

working_df  = month_df[month_df["date"].apply(_is_working)].copy()
filled_days = int((working_df["total"] > 0).sum())
unfilled    = working_days - filled_days

if unfilled > 0:
    st.warning(
        f"{unfilled} of {working_days} working days have zero attendance. "
        "Bill totals may be incomplete."
    )

# Rename columns for bill_calculator compatibility
att_for_bill = working_df.rename(columns={"class5": "Class5", "class68": "Class68"})

# ── Opening stock inputs ──────────────────────────────────────────────────────
with st.expander("Opening Stock / मागील शिल्लक (optional)", expanded=False):
    st.caption("Enter in kg (or litres for oil). Leave at 0 if not known.")

    c5_opening:   dict[str, float] = {}
    c68_opening:  dict[str, float] = {}
    c5_received:  dict[str, float] = {}
    c68_received: dict[str, float] = {}

    grid = st.columns(4)
    for i, (name_en, name_marathi, *_) in enumerate(FOOD_ITEMS):
        with grid[i % 4]:
            st.markdown(f"**{name_marathi}**")
            c5_opening[name_en]   = st.number_input(f"इ.5 मागील (kg)",    key=f"c5op_{i}",  value=0.0, min_value=0.0, step=0.1, format="%.3f")
            c5_received[name_en]  = st.number_input(f"इ.5 प्राप्त (kg)",   key=f"c5rx_{i}",  value=0.0, min_value=0.0, step=0.1, format="%.3f")
            c68_opening[name_en]  = st.number_input(f"इ.6-8 मागील (kg)",  key=f"c68op_{i}", value=0.0, min_value=0.0, step=0.1, format="%.3f")
            c68_received[name_en] = st.number_input(f"इ.6-8 प्राप्त (kg)", key=f"c68rx_{i}", value=0.0, min_value=0.0, step=0.1, format="%.3f")

# ── Calculate bills ───────────────────────────────────────────────────────────
c5_bill, c68_bill = calculate_bill(
    attendance_df    = att_for_bill,
    working_days     = working_days,
    class5_enrolled  = c5_enrolled,
    class68_enrolled = c68_enrolled,
    class5_opening   = c5_opening,
    class68_opening  = c68_opening,
    class5_received  = c5_received,
    class68_received = c68_received,
)


def render_bill(bill: BillResult) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("पटसंख्या / Enrolled",        bill.students_enrolled)
    m2.metric("कामाचे दिवस / Working Days",  bill.working_days)
    m3.metric("एकूण उपस्थिती / Attendance",  bill.total_student_days)
    avg = round(bill.total_student_days / bill.working_days, 1) if bill.working_days else 0
    m4.metric("सरासरी / Avg per Day",         avg)

    st.markdown("#### वस्तू साठा / Food Stock")
    stock_rows = []
    for fl in bill.food_lines:
        stock_rows.append({
            "क्र":                 fl.serial,
            "वस्तूचे नाव":         fl.name_marathi,
            "English Name":        fl.name_en,
            "एकक":                 fl.unit,
            "मागील शिल्लक (kg)":  fl.opening_kg,
            "प्राप्त (kg)":        fl.received_kg,
            "एकूण (kg)":          fl.total_kg,
            "वापरलेले (kg)":       fl.used_kg,
            "शिल्लक (kg)":        fl.closing_kg,
            "पुढील मागणी (kg)":   fl.demand_kg,
        })
    st.dataframe(
        pd.DataFrame(stock_rows), use_container_width=True, hide_index=True,
        column_config={k: st.column_config.NumberColumn(format="%.3f")
                       for k in ["मागील शिल्लक (kg)", "प्राप्त (kg)", "एकूण (kg)",
                                  "वापरलेले (kg)", "शिल्लक (kg)", "पुढील मागणी (kg)"]},
    )

    st.markdown("#### खर्च विवरण / Expense Summary")
    exp_rows = [
        {"तपशील": el.label, "उपस्थिती": el.student_days,
         "दर (₹)": f"₹{el.rate_inr:.2f}", "रक्कम (₹)": f"₹{el.amount_inr:,.2f}"}
        for el in bill.expense_lines
    ]
    exp_rows.append({"तपशील": "एकूण / Total", "उपस्थिती": "",
                     "दर (₹)": "", "रक्कम (₹)": f"₹{bill.total_expense:,.2f}"})
    st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)
    st.success(f"**एकूण बिल रक्कम / Total Bill:  ₹{bill.total_expense:,.2f}**")


# ── Display bills ─────────────────────────────────────────────────────────────
st.subheader(f"{school_name} — {month_label}")

tab5, tab68, tab_both = st.tabs(["इ.5 — Class 5", "इ.6 ते 8 — Class 6–8", "Combined Summary"])

with tab5:
    render_bill(c5_bill)

with tab68:
    render_bill(c68_bill)

with tab_both:
    col5, col68 = st.columns(2)
    with col5:
        st.markdown("### इ.5 (Class 5)")
        st.metric("Working Days",     c5_bill.working_days)
        st.metric("Total Attendance", c5_bill.total_student_days)
        st.metric("Total Bill",       f"₹{c5_bill.total_expense:,.2f}")
    with col68:
        st.markdown("### इ.6 ते 8 (Class 6–8)")
        st.metric("Working Days",     c68_bill.working_days)
        st.metric("Total Attendance", c68_bill.total_student_days)
        st.metric("Total Bill",       f"₹{c68_bill.total_expense:,.2f}")

    st.divider()
    grand_total = c5_bill.total_expense + c68_bill.total_expense
    st.subheader(f"Grand Total / एकूण: ₹{grand_total:,.2f}")

    combined_rows = []
    for fl5, fl68 in zip(c5_bill.food_lines, c68_bill.food_lines):
        combined_rows.append({
            "वस्तूचे नाव":      fl5.name_marathi,
            "एकक":              fl5.unit,
            "इ.5 वापर (kg)":   fl5.used_kg,
            "इ.6-8 वापर (kg)": fl68.used_kg,
            "एकूण वापर (kg)":  round(fl5.used_kg + fl68.used_kg, 3),
        })
    st.dataframe(pd.DataFrame(combined_rows), use_container_width=True, hide_index=True)

# ── Download Excel ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Download Excel Bill / एक्सेल बिल डाउनलोड")
st.caption("Open in Microsoft Excel — all bill formulas recalculate automatically.")

template_files = sorted(TEMPLATE_DIR.glob("*.xlsx")) if TEMPLATE_DIR.exists() else []
if template_files:
    records    = get_attendance_records(school_id, sel_year, sel_month)
    xlsx_bytes = generate_excel_buffer(template_files[0], records, sel_year, sel_month)
    file_label = date(sel_year, sel_month, 1).strftime("%b").upper()
    st.download_button(
        label=f"Download {school_code}_{file_label}_{sel_year}.xlsx",
        data=xlsx_bytes,
        file_name=f"{school_code}_{file_label}_{sel_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
else:
    st.warning("No Excel template found in `templates/` folder.")
