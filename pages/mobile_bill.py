"""
pages/mobile_bill.py  —  Mobile-friendly Government Bill
Replicates the exact structure of Bill 6 To 8 and Bill 5th sheets
from the MDM Excel template, with Unicode Marathi text.
Works on any mobile browser / can be printed as PDF.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

BASE_DIR    = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from auth            import get_current_user, logout
from attendance_db   import get_month_attendance, get_attendance_records
from bill_calculator import calculate_bill, FOOD_ITEMS, RATES
from holiday_manager import HolidayManager

st.set_page_config(
    page_title="MDM Bill — Mobile",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Noto Sans Devanagari', 'Mangal', 'Segoe UI', sans-serif; }

/* ── Bill card ── */
.bill-card {
    background: white;
    border: 2px solid #1B5E20;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.bill-title {
    text-align: center;
    font-size: 1.1rem;
    font-weight: 800;
    color: #1B5E20;
    border-bottom: 2px solid #1B5E20;
    padding-bottom: 0.5rem;
    margin-bottom: 0.8rem;
}
.bill-subtitle {
    text-align: center;
    font-size: 0.82rem;
    color: #444;
    margin-bottom: 0.3rem;
}
.bill-school {
    font-size: 0.9rem;
    font-weight: 700;
    color: #1B5E20;
    margin: 0.5rem 0 0.3rem 0;
}
.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin: 0.6rem 0;
}
.info-item {
    background: #f1f8f1;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.82rem;
}
.info-label { color: #555; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; }
.info-value { font-weight: 700; color: #1B5E20; font-size: 0.95rem; }

/* ── Table ── */
.mdm-table { width: 100%; border-collapse: collapse; margin: 0.8rem 0; font-size: 0.78rem; }
.mdm-table th {
    background: #1B5E20;
    color: white;
    padding: 7px 5px;
    text-align: center;
    font-weight: 600;
    font-size: 0.72rem;
    line-height: 1.3;
}
.mdm-table td {
    padding: 6px 5px;
    border: 1px solid #c8e6c9;
    text-align: center;
    font-size: 0.8rem;
}
.mdm-table tr:nth-child(even) { background: #f9fdf9; }
.mdm-table tr:hover { background: #e8f5e9; }
.item-name { text-align: left !important; font-weight: 600; color: #1B5E20; }

/* ── Expense section ── */
.expense-card {
    background: #e8f5e9;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.8rem 0;
}
.expense-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #1B5E20;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #a5d6a7;
    padding-bottom: 4px;
}
.expense-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
    font-size: 0.83rem;
    border-bottom: 1px dashed #c8e6c9;
}
.expense-row:last-child { border-bottom: none; }
.expense-total {
    display: flex;
    justify-content: space-between;
    font-weight: 800;
    color: #1B5E20;
    font-size: 0.95rem;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 2px solid #1B5E20;
}

/* ── Summary section ── */
.summary-card {
    background: #fff8e1;
    border: 1px solid #ffe082;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.8rem 0;
    font-size: 0.83rem;
}
.summary-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px dashed #ffe082;
}
.summary-row:last-child { border-bottom: none; }

/* ── Signature section ── */
.sig-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 1rem;
    font-size: 0.8rem;
    text-align: center;
}
.sig-box {
    border-top: 1px solid #333;
    padding-top: 4px;
    color: #333;
}

/* ── Section divider ── */
.section-divider {
    height: 3px;
    background: linear-gradient(90deg, #1B5E20, #66BB6A, #1B5E20);
    border-radius: 3px;
    margin: 1.5rem 0;
}

@media print {
    .stApp > header, .stSidebar, footer, [data-testid="stToolbar"] { display: none !important; }
    .bill-card { break-inside: avoid; box-shadow: none; border: 1.5px solid #333; }
}
@media (max-width: 480px) {
    .info-grid { grid-template-columns: 1fr; }
    .sig-section { grid-template-columns: 1fr; gap: 6px; }
    .mdm-table { font-size: 0.7rem; }
    .mdm-table th { font-size: 0.65rem; padding: 5px 3px; }
    .mdm-table td { padding: 4px 3px; }
}
</style>
""", unsafe_allow_html=True)


# ── Auth guard ─────────────────────────────────────────────────────────────────
user = get_current_user()
if not user:
    st.error("Please log in first.")
    st.page_link("../home.py", label="Go to Login")
    st.stop()


# ── Controls ───────────────────────────────────────────────────────────────────
today = date.today()

col_back, col_title = st.columns([1, 5])
with col_back:
    st.page_link("home.py", label="← Back", icon="🏠")
with col_title:
    st.markdown("### 📋 MDM Government Bill — Mobile View")

c1, c2, c3 = st.columns(3)
month_names = [date(today.year, m, 1).strftime("%B") for m in range(1, 13)]
sel_month_name = c1.selectbox("Month", month_names, index=today.month - 1)
sel_month = month_names.index(sel_month_name) + 1
sel_year  = int(c2.number_input("Year", value=today.year, min_value=2020, max_value=2035, step=1))
month_label = date(sel_year, sel_month, 1).strftime("%B %Y")

school_id   = user["school_id"]
school_name = user.get("school_name", "")
school_code = user.get("school_code", "")
kendra      = user.get("kendra", "")

c3.markdown(f"**School:** {school_name}")

st.divider()


# ── Load data ──────────────────────────────────────────────────────────────────
hm = HolidayManager(year=sel_year)
working_day_dates = hm.get_working_days(sel_month)
working_days = len(working_day_dates)

month_df = get_month_attendance(school_id, sel_year, sel_month)

def _is_working(row_date) -> bool:
    try:
        return hm.is_working_day(row_date)
    except Exception:
        return True

if month_df.empty:
    working_df = month_df.copy()
else:
    working_df = month_df[month_df["date"].apply(_is_working)]
    working_df = working_df[working_df["total"] > 0]

if working_df.empty:
    st.info("No attendance data found for this month. Enter attendance first.")
    st.stop()

c5_bill, c68_bill = calculate_bill(
    attendance_df=working_df.rename(columns={"class5": "Class5", "class68": "Class68"}),
    working_days=working_days,
)

days_food_served = len(working_df)


# ── Helper: render one bill ────────────────────────────────────────────────────
def render_bill_html(bill, title_marathi, month_lbl, school, kendra_name, wdays, food_days, enroll):
    c5_total_str = f"₹{bill.total_expense:,.2f}"

    # Stock table rows
    table_rows = ""
    for i, fl in enumerate(bill.food_lines, start=1):
        sr = i if i <= 1 else i + 1  # skip serial 2 (matches Excel: 1,3,4,5,6,7,8,9,10)
        if i == 1:
            sr = 1
        else:
            sr = i + 1
        table_rows += f"""
        <tr>
            <td>{sr}</td>
            <td class='item-name'>{fl.name_marathi}</td>
            <td>{fl.opening_kg:.3f}</td>
            <td>{fl.received_kg:.3f}</td>
            <td>{fl.total_kg:.3f}</td>
            <td>{fl.used_kg:.3f}</td>
            <td>{fl.closing_kg:.3f}</td>
            <td>{fl.demand_kg:.3f}</td>
            <td></td>
        </tr>"""

    # Expense rows
    expense_rows = ""
    for el in bill.expense_lines:
        label_short = el.label.split("(")[0].strip()
        expense_rows += f"""
        <div class='expense-row'>
            <span>{label_short}</span>
            <span>{el.student_days} × ₹{el.rate_inr} = <strong>₹{el.amount_inr:,.2f}</strong></span>
        </div>"""

    # Fuel + vegetable grant amount
    bhaji_fuel = sum(el.amount_inr for el in bill.expense_lines if "भाजिपाला" in el.label or "इंधन" in el.label)
    total_plates = bill.total_student_days

    today_str = date.today().strftime("%d/%m/%Y")

    html = f"""
    <div class='bill-card'>
        <div class='bill-title'>
            राष्ट्रीय मध्यान्ह भोजन कार्यक्रम योजना<br>
            प्रपत्र - ब &nbsp;·&nbsp; {title_marathi}
        </div>
        <div class='bill-subtitle'>
            शाळेने केंद्रप्रमुखांना द्यावयाचा मासिक अहवाल (२ प्रतींत)
        </div>
        <div class='bill-school'>शाळेचे नाव :- {school}</div>
        <div style='font-size:0.82rem;color:#555;margin-bottom:0.5rem;'>केंद्र :- {kendra_name or "—"}</div>

        <div class='info-grid'>
            <div class='info-item'>
                <div class='info-label'>महिना</div>
                <div class='info-value'>{month_lbl}</div>
            </div>
            <div class='info-item'>
                <div class='info-label'>एकूण कार्यदिवस</div>
                <div class='info-value'>{wdays}</div>
            </div>
            <div class='info-item'>
                <div class='info-label'>एकूण उपस्थिती (विद्यार्थी-दिवस)</div>
                <div class='info-value'>{bill.total_student_days}</div>
            </div>
            <div class='info-item'>
                <div class='info-label'>अन्न शिजवून दिलेले दिवस</div>
                <div class='info-value'>{food_days}</div>
            </div>
        </div>

        <div style='margin:0.8rem 0 0.4rem 0;font-size:0.82rem;color:#555;'>
            तांदूळ प्राप्त दिनांक व पावती क्रमांक : _______________&nbsp;&nbsp;
            धान्य प्राप्त दिनांक व पावती क्रमांक : _______________
        </div>

        <!-- Stock Table -->
        <div style='overflow-x:auto;'>
        <table class='mdm-table'>
            <thead>
                <tr>
                    <th>अ.क्र.</th>
                    <th>वस्तूचे नाव</th>
                    <th>मागील शिल्लक<br>(किं.ग्रॅ.)</th>
                    <th>चालू महिन्यात प्राप्त<br>(किं.ग्रॅ.)</th>
                    <th>एकूण वस्तू<br>(3+4)</th>
                    <th>अन्न शिजविण्यास<br>वापरलेल्या</th>
                    <th>शिल्लक वस्तू<br>(5-6)</th>
                    <th>पुढील महिन्यासाठी<br>मागणी</th>
                    <th>शेरा</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        </div>

        <!-- Expense Section -->
        <div class='expense-card'>
            <div class='expense-title'>विवरण — खर्च तपशील</div>
            {expense_rows}
            <div class='expense-total'>
                <span>एकूण =</span>
                <span>{c5_total_str}</span>
            </div>
        </div>

        <!-- Summary Section -->
        <div class='summary-card'>
            <div style='font-weight:700;font-size:0.85rem;margin-bottom:6px;color:#6d4c00;'>सारांश</div>
            <div class='summary-row'>
                <span>१) महिन्यातील एकूण ताटांची संख्या</span>
                <strong>{total_plates}</strong>
            </div>
            <div class='summary-row'>
                <span>२) इंधन व भाजिपाला खर्च — अनुदान ₹</span>
                <strong>₹{bhaji_fuel:,.2f}</strong>
            </div>
            <div class='summary-row'>
                <span>३) स्वयंपाकी तथा मदतनीस मानधन ₹ 2500/-</span>
                <strong>₹ 2500.00 × ___</strong>
            </div>
        </div>

        <div style='font-size:0.75rem;color:#555;margin:0.5rem 0;line-height:1.5;'>
            प्रमाणित करण्यात येते की, वर नमूद केलेली माहिती दैनंदिन नोंदवहीवरून घेतलेली आहे.
            ती तपासली आहे व बरोबर आहे.
        </div>

        <!-- Signature Block -->
        <div class='sig-section'>
            <div class='sig-box'>
                <div>मुख्याध्यापिका / सचिव</div>
                <div style='color:#888;font-size:0.72rem;margin-top:4px;'>दिनांक: {today_str}</div>
            </div>
            <div class='sig-box'>
                <div>केंद्र प्रमुख</div>
                <div style='color:#888;font-size:0.72rem;margin-top:4px;'>{kendra_name or "—"}</div>
            </div>
            <div class='sig-box' style='grid-column: span 2 / span 2;'>
                <div>शालेय व्यवस्थापन समिती &nbsp;&nbsp; दिनांक: {today_str}</div>
            </div>
        </div>
    </div>
    """
    return html


# ── Render both bills ──────────────────────────────────────────────────────────
tab_68, tab_5 = st.tabs(["📗 इ. 6 ते 8", "📘 इ. 5 वी"])

with tab_68:
    st.markdown(render_bill_html(
        bill          = c68_bill,
        title_marathi = "इ. 6 ते 8",
        month_lbl     = month_label,
        school        = school_name,
        kendra_name   = kendra,
        wdays         = working_days,
        food_days     = days_food_served,
        enroll        = 0,
    ), unsafe_allow_html=True)

with tab_5:
    st.markdown(render_bill_html(
        bill          = c5_bill,
        title_marathi = "इ. 5 वी",
        month_lbl     = month_label,
        school        = school_name,
        kendra_name   = kendra,
        wdays         = working_days,
        food_days     = days_food_served,
        enroll        = 0,
    ), unsafe_allow_html=True)

st.divider()
st.caption("💡 Mobile tip: tap the browser menu → **Print / Share → Save as PDF** to save this bill offline.")
