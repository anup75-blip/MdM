"""
home.py  —  MDM Attendance Dashboard
Multi-school | Supabase backend | Streamlit Community Cloud ready

Run locally:  streamlit run home.py
"""
from __future__ import annotations

import calendar
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR    = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from auth           import get_current_user, login, logout, signup, google_login_url, handle_oauth_callback
from attendance_db  import get_month_attendance, get_attendance_records, save_attendance
from bill_calculator import calculate_bill
from excel_export   import generate_excel_buffer
from holiday_manager import HolidayManager
from subscription   import get_subscription_info

HOLIDAY_FILE = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"
TEMPLATE_DIR = BASE_DIR / "templates"

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MDM Dashboard",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Global ── */
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #ffffff, #f1f8f1);
    border: 1px solid #c8e6c9;
    border-left: 4px solid #2E7D32;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 2px 8px rgba(46,125,50,0.08);
    transition: transform 0.15s;
}
[data-testid="metric-container"]:hover { transform: translateY(-2px); }
[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; color: #1B5E20; }
[data-testid="stMetricLabel"] { font-size: 0.78rem; font-weight: 600; color: #555; letter-spacing: 0.03em; text-transform: uppercase; }
[data-testid="stMetricDelta"] { font-size: 0.8rem; }

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2E7D32, #1B5E20);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.2rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    box-shadow: 0 3px 10px rgba(27,94,32,0.3);
    transition: all 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1B5E20, #145214);
    box-shadow: 0 5px 15px rgba(27,94,32,0.4);
    transform: translateY(-1px);
}
.stButton > button:not([kind="primary"]) {
    border-radius: 10px;
    border: 1.5px solid #c8e6c9;
    transition: all 0.2s;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #2E7D32;
    color: #1B5E20;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #1565C0, #0D47A1) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 3px 10px rgba(21,101,192,0.3) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #E8F5E9;
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 0.88rem;
}
.stTabs [aria-selected="true"] {
    background: #2E7D32 !important;
    color: white !important;
}

/* ── Forms & inputs ── */
.stTextInput input, .stNumberInput input, .stDateInput input {
    border-radius: 9px !important;
    border: 1.5px solid #c8e6c9 !important;
    padding: 0.4rem 0.8rem !important;
    font-size: 1rem !important;
    transition: border-color 0.2s;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #2E7D32 !important;
    box-shadow: 0 0 0 3px rgba(46,125,50,0.12) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B5E20 0%, #2E7D32 100%) !important;
}
[data-testid="stSidebar"] * { color: #e8f5e9 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.15) !important;
    border: 1.5px solid rgba(255,255,255,0.3) !important;
    color: white !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.25) !important;
}
[data-testid="stSidebar"] [data-testid="metric-container"] {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-left: 4px solid #A5D6A7 !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: white !important; }
[data-testid="stSidebar"] [data-testid="stMetricLabel"] { color: #A5D6A7 !important; }
[data-testid="stSidebar"] .stSelectbox select,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2) !important; }

/* ── Login card ── */
.login-card {
    background: white;
    border-radius: 20px;
    padding: 2.5rem 2rem;
    box-shadow: 0 8px 32px rgba(27,94,32,0.12);
    border: 1px solid #e8f5e9;
    max-width: 440px;
    margin: 0 auto;
}
.login-title {
    text-align: center;
    font-size: 1.8rem;
    font-weight: 800;
    color: #1B5E20;
    margin-bottom: 0.2rem;
}
.login-subtitle {
    text-align: center;
    color: #66BB6A;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

/* ── Page title ── */
h1 { color: #1B5E20 !important; font-weight: 800 !important; }
h2 { color: #2E7D32 !important; }
h3 { color: #388E3C !important; }

/* ── Alerts ── */
.stSuccess { border-radius: 10px !important; }
.stError   { border-radius: 10px !important; }
.stWarning { border-radius: 10px !important; }
.stInfo    { border-radius: 10px !important; }

/* ── Dataframe ── */
.stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN GATE
# ══════════════════════════════════════════════════════════════════════════════
if not get_current_user():
    # Handle Google OAuth redirect (?code= arrives in URL after Google login)
    if handle_oauth_callback():
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        logo = BASE_DIR / "assets" / "logo.png"
        if logo.exists():
            st.image(str(logo), width=80)

        st.markdown("""
        <div class='login-title'>🍱 MDM Dashboard</div>
        <div class='login-subtitle'>Maharashtra Mid-Day Meal Scheme<br>महाराष्ट्र शालेय पोषण आहार</div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Google login (primary) ─────────────────────────────────────────────
        try:
            st.link_button(
                "🔵  Continue with Google",
                google_login_url(),
                use_container_width=True,
            )
        except Exception:
            pass

        st.markdown(
            "<div style='text-align:center;color:#aaa;margin:12px 0;font-size:0.85rem'>— or use phone number —</div>",
            unsafe_allow_html=True,
        )

        # ── Login / Sign-Up tabs ───────────────────────────────────────────────
        tab_login, tab_signup = st.tabs(["🔐  Login", "✨  Sign Up"])

        with tab_login:
            with st.form("login_form"):
                identifier = st.text_input("Mobile Number", placeholder="9876543210")
                password   = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted  = st.form_submit_button("Login", use_container_width=True, type="primary")
            if submitted:
                if not identifier.strip() or not password.strip():
                    st.error("Please enter your mobile number and password.")
                else:
                    with st.spinner("Verifying..."):
                        ok, msg = login(identifier.strip(), password.strip())
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)
            st.caption("Admin? Use your email address in the mobile number field.")

        with tab_signup:
            st.caption("First time? Create your school account below.")
            with st.form("signup_form"):
                su_phone   = st.text_input("Mobile Number *",  placeholder="9876543210")
                su_pass    = st.text_input("Password *",        type="password", placeholder="Min 6 characters")
                su_pass2   = st.text_input("Confirm Password *",type="password", placeholder="Repeat password")
                st.divider()
                su_school  = st.text_input("School Name *",    placeholder="Indirabaai Kanya Vidyalaya, Shirala")
                su_kendra  = st.text_input("Kendra (केंद्र) *", placeholder="Kendriya Shala, Shirala")
                c1, c2, c3 = st.columns(3)
                su_dist    = c1.text_input("District (जिल्हा)", placeholder="Amravati")
                su_taluka  = c2.text_input("Taluka (तालुका)",   placeholder="Shirala")
                su_state   = c3.text_input("State (राज्य)",     placeholder="Maharashtra")
                su_udise   = st.text_input("UDISE Code",        placeholder="27XXXXXXXXXX (optional)")
                su_btn     = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            if su_btn:
                if su_pass != su_pass2:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating account..."):
                        ok, msg = signup(su_phone, su_pass, su_school, su_dist, su_taluka, su_udise,
                                         su_kendra, su_state)
                    if ok and msg == "__logged_in__":
                        st.rerun()
                    elif ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP  (only reached when logged in)
# ══════════════════════════════════════════════════════════════════════════════
user = get_current_user()


# ── Subscription gate ─────────────────────────────────────────────────────────
def _show_expired_page(u: dict) -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.title("MDM Dashboard")
        st.error("### Subscription Expired")
        st.markdown(
            f"**School:** {u.get('school_name', '')}  \n"
            "Your **free trial** (or subscription) has ended. "
            "Please renew to continue entering attendance and downloading Excel reports."
        )
        st.divider()
        st.markdown("**To renew, contact:**")
        st.markdown("📧 deshmukha75@gmail.com")
        st.info("Payment via Razorpay/UPI — pricing will be displayed here once set up.")
        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()


if user and user["role"] not in ("admin", "block_officer") and user.get("school_id"):
    _sub = get_subscription_info(user["school_id"])
    if _sub["status"] == "expired":
        _show_expired_page(user)
        st.stop()
    elif _sub["status"] == "trial" and _sub["days_left"] is not None and _sub["days_left"] <= 5:
        st.warning(
            f"Trial ends in **{_sub['days_left']} day(s)**. "
            "Contact deshmukha75@gmail.com to subscribe."
        )


# Admin/block_officer with no school assigned — let them pick one
if user["role"] in ("admin", "block_officer") and not user["school_id"]:
    from backend.supabase_client import get_supabase
    try:
        schools_resp = get_supabase().table("schools").select("id, school_code, name").eq("active", True).order("school_code").execute()
        all_schools  = schools_resp.data or []
    except Exception:
        all_schools = []

    if not all_schools:
        st.warning("No schools found in database. Run setup_schools.py first.")
        st.stop()

    school_options = {f"{s['school_code']} — {s['name']}": s for s in all_schools}
    sel_key = st.selectbox(
        f"Welcome, {user['full_name'] or 'Admin'} — select a school to view:",
        list(school_options.keys()),
    )
    chosen = school_options[sel_key]
    user = {**user, "school_id": chosen["id"], "school_name": chosen["name"], "school_code": chosen["school_code"]}

school_id   = user["school_id"]
school_name = user["school_name"]
school_code = user["school_code"]


def find_template() -> Path | None:
    if not TEMPLATE_DIR.exists():
        return None
    files = sorted(TEMPLATE_DIR.glob("*.xlsx"))
    return files[0] if files else None


# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    logo = BASE_DIR / "assets" / "logo.png"
    if logo.exists():
        st.image(str(logo))
    st.title("MDM Dashboard")
    st.caption("Maharashtra Mid-Day Meal Scheme")
    st.divider()

    # School info (from session — no dropdown, school is fixed per login)
    st.markdown(f"**{school_name}**")
    st.caption(f"Code: {school_code}  |  Role: {user['role'].title()}")

    # Subscription status badge
    if user["role"] not in ("admin", "block_officer") and user.get("school_id"):
        _si = get_subscription_info(user["school_id"])
        if _si["status"] == "active":
            days = f" · {_si['days_left']}d left" if _si["days_left"] is not None else ""
            st.success(f"Subscribed{days}")
        elif _si["status"] == "trial":
            days = _si["days_left"] if _si["days_left"] is not None else "?"
            st.info(f"Trial · {days} day(s) left")
        else:
            st.error("Subscription expired")

    st.divider()

    # Month / Year selector
    today       = date.today()
    month_names = [date(today.year, m, 1).strftime("%B") for m in range(1, 13)]
    month_map   = {name: i + 1 for i, name in enumerate(month_names)}

    sel_month_name = st.selectbox("Month", month_names, index=today.month - 1)
    sel_month      = month_map[sel_month_name]
    sel_year       = int(
        st.number_input("Year", value=today.year,
                        min_value=2020, max_value=2035, step=1)
    )
    month_label = date(sel_year, sel_month, 1).strftime("%B %Y")

    st.divider()

    # Download Excel button — generates in memory from Supabase data
    template = find_template()
    if template:
        records = get_attendance_records(school_id, sel_year, sel_month)
        try:
            xlsx_bytes = generate_excel_buffer(template, records, sel_year, sel_month)
            file_label = date(sel_year, sel_month, 1).strftime("%b").upper()
            st.download_button(
                label="Download Excel Bill",
                data=xlsx_bytes,
                file_name=f"{school_code}_{file_label}_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.caption("Open in Excel — formulas auto-calculate.")
        except Exception as exc:
            st.warning(f"Excel generation error: {exc}")
    else:
        st.warning("No template in `templates/` folder.")

    st.divider()
    st.page_link("pages/generate_bill.py", label="Bill Generator", icon="📋")
    st.page_link("pages/mobile_bill.py",  label="📱 Mobile Bill", icon="📋")
    st.divider()

    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1B5E20,#2E7D32);border-radius:16px;padding:1.2rem 1.8rem;margin-bottom:1rem;color:white;'>
    <div style='font-size:1.5rem;font-weight:800;'>🍱 {school_name}</div>
    <div style='font-size:0.95rem;opacity:0.85;margin-top:4px;'>Mid-Day Meal Dashboard &nbsp;·&nbsp; {month_label}</div>
</div>
""", unsafe_allow_html=True)

# ── Load data from Supabase ──────────────────────────────────────────────────
hm = HolidayManager(year=sel_year)
if HOLIDAY_FILE.exists():
    hm.load_school_holidays(HOLIDAY_FILE)

working_day_dates = hm.get_working_days(sel_month)
working_days      = len(working_day_dates)

month_df = get_month_attendance(school_id, sel_year, sel_month)


def _is_working(row_date) -> bool:
    try:
        return hm.is_working_day(row_date)
    except Exception:
        return True


if month_df.empty:
    working_df = month_df.copy()
    filled_df  = month_df.copy()
else:
    working_df = month_df[month_df["date"].apply(_is_working)]
    filled_df  = working_df[working_df["total"] > 0]

unfilled = working_days - len(filled_df)


# ── Metrics row ──────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("Working Days",    working_days)
m2.metric("Days Filled",     len(filled_df),
          delta=f"{-unfilled} unfilled" if unfilled else "All filled",
          delta_color="inverse" if unfilled else "normal")
m3.metric("Class 5 Total",   int(working_df["class5"].sum())  if not working_df.empty else 0)
m4.metric("Class 6-8 Total", int(working_df["class68"].sum()) if not working_df.empty else 0)

c5_days  = int(working_df["class5"].sum())  if not working_df.empty else 0
c68_days = int(working_df["class68"].sum()) if not working_df.empty else 0
m5.metric("Est. Bill Cl.5",   f"₹{round(c5_days  * 2.59, 0):,.0f}")
m6.metric("Est. Bill Cl.6-8", f"₹{round(c68_days * 3.88, 0):,.0f}")

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_entry, tab_overview, tab_bill = st.tabs([
    "Enter Attendance",
    "Monthly Overview",
    "Bill Preview",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — ATTENDANCE ENTRY
# ─────────────────────────────────────────────────────────────────────────────
with tab_entry:
    st.subheader("Daily Attendance Entry")

    days_in_month = calendar.monthrange(sel_year, sel_month)[1]
    min_date = date(sel_year, sel_month, 1)
    max_date = date(sel_year, sel_month, days_in_month)
    def_date = today if (min_date <= today <= max_date) else min_date

    col_date, col_status = st.columns([1, 2])
    with col_date:
        selected_date = st.date_input(
            "Date", value=def_date, min_value=min_date, max_value=max_date
        )

    holiday_rsn = hm.holiday_name(selected_date)

    with col_status:
        st.write("")
        if holiday_rsn:
            st.error(f"Non-working day: {holiday_rsn}")
        else:
            st.success("Working day")

    # Pre-fill from Supabase data
    match = month_df[month_df["date"] == selected_date] if not month_df.empty else pd.DataFrame()
    has_data = not match.empty
    d_c5 = int(match["class5"].values[0]) if has_data else 0
    d_c6 = int(match["class6"].values[0]) if has_data else 0
    d_c7 = int(match["class7"].values[0]) if has_data else 0
    d_c8 = int(match["class8"].values[0]) if has_data else 0
    if holiday_rsn:
        d_c5 = d_c6 = d_c7 = d_c8 = 0

    with st.form("attendance_form", clear_on_submit=False):
        a, b, c, d_ = st.columns(4)
        c5 = a.number_input("Class 5",  min_value=0, max_value=500, value=d_c5, step=1)
        c6 = b.number_input("Class 6",  min_value=0, max_value=500, value=d_c6, step=1)
        c7 = c.number_input("Class 7",  min_value=0, max_value=500, value=d_c7, step=1)
        c8 = d_.number_input("Class 8", min_value=0, max_value=500, value=d_c8, step=1)

        st.divider()
        p1, p2, p3 = st.columns(3)
        p1.metric("Class 5",     c5)
        p2.metric("Class 6-8",   c6 + c7 + c8)
        p3.metric("Grand Total", c5 + c6 + c7 + c8)

        save_btn = st.form_submit_button(
            "Save Attendance", use_container_width=True, type="primary"
        )

    if save_btn:
        if holiday_rsn and (c5 + c6 + c7 + c8) > 0:
            st.warning(f"Saving non-zero attendance on a holiday ({holiday_rsn}).")
        ok, msg = save_attendance(school_id, user["user_id"], selected_date, c5, c6, c7, c8)
        if ok:
            st.success(f"Saved — {selected_date.strftime('%d/%m/%Y')}  |  "
                       f"Cl5={c5}  Cl6={c6}  Cl7={c7}  Cl8={c8}")
            st.rerun()
        else:
            st.error(f"Save failed: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — MONTHLY OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab_overview:
    st.subheader(f"{month_label} — Attendance Overview")

    if month_df.empty:
        st.info("No attendance entered yet for this month.")
    else:
        def _status(row) -> str:
            try:
                rsn = hm.holiday_name(row["date"])
                return rsn if rsn else ("Filled" if row["total"] > 0 else "Missing")
            except Exception:
                return ""

        display = month_df.copy()
        display["Status"] = display.apply(_status, axis=1)
        display["Filled"] = display["total"].apply(lambda x: "Yes" if x > 0 else "—")
        display["Date"]   = display["date"].apply(lambda d: d.strftime("%d/%m/%Y"))

        def highlight_row(row):
            status = row["Status"]
            if status in ("Sunday", "Government Holiday", "School Holiday"):
                return ["background-color: #f5f5f5; color: #aaa"] * len(row)
            if status == "Missing":
                return ["background-color: #fff3cd"] * len(row)
            if status == "Filled":
                return ["background-color: #d4edda"] * len(row)
            return [""] * len(row)

        show_cols = ["Date", "Status", "class5", "class6", "class7", "class8", "class68", "total", "Filled"]
        styled = (
            display[show_cols]
            .rename(columns={
                "class5": "Class5", "class6": "Class6", "class7": "Class7",
                "class8": "Class8", "class68": "Cl.6-8", "total": "Total"
            })
            .style.apply(highlight_row, axis=1)
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=600)

        st.divider()
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Working Days",    working_days)
        s2.metric("Days Filled",     len(filled_df))
        s3.metric("Days Missing",    unfilled, delta_color="inverse")
        s4.metric("Class 5 Total",   int(working_df["class5"].sum())  if not working_df.empty else 0)
        s5.metric("Class 6-8 Total", int(working_df["class68"].sum()) if not working_df.empty else 0)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — BILL PREVIEW (pure Python, no Excel needed)
# ─────────────────────────────────────────────────────────────────────────────
with tab_bill:
    st.subheader(f"Bill Preview — {month_label}")
    st.caption("Calculated from attendance entered so far. Download Excel for the official government bill with food stock.")

    if working_df.empty or working_df["total"].sum() == 0:
        st.info("No attendance data found. Enter attendance first.")
    else:
        c5_bill, c68_bill = calculate_bill(
            attendance_df=working_df.rename(columns={"class5": "Class5", "class68": "Class68"}),
            working_days=working_days,
        )

        col5, col68 = st.columns(2)

        with col5:
            st.markdown("### इ.5 — Class 5")
            st.metric("Student-Days", c5_bill.total_student_days)
            for el in c5_bill.expense_lines:
                st.metric(el.label, f"₹{el.amount_inr:,.2f}")
            st.markdown(f"**Total: ₹{c5_bill.total_expense:,.2f}**")

        with col68:
            st.markdown("### इ.6 ते 8 — Class 6–8")
            st.metric("Student-Days", c68_bill.total_student_days)
            for el in c68_bill.expense_lines:
                st.metric(el.label, f"₹{el.amount_inr:,.2f}")
            st.markdown(f"**Total: ₹{c68_bill.total_expense:,.2f}**")

        st.divider()
        grand = c5_bill.total_expense + c68_bill.total_expense
        st.subheader(f"Grand Total: ₹{grand:,.2f}")

        st.markdown("#### Food Consumed This Month")
        food_rows = []
        for fl5, fl68 in zip(c5_bill.food_lines, c68_bill.food_lines):
            food_rows.append({
                "Food Item":      fl5.name_marathi,
                "Class 5 (kg)":   fl5.used_kg,
                "Class 6-8 (kg)": fl68.used_kg,
                "Total (kg)":     round(fl5.used_kg + fl68.used_kg, 3),
            })
        st.dataframe(pd.DataFrame(food_rows), use_container_width=True, hide_index=True)

        st.divider()
        st.page_link("pages/generate_bill.py", label="Open Full Bill Generator →", icon="📋")
