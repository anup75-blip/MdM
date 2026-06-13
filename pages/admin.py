"""
pages/admin.py  —  MDM Admin Panel
Only accessible to users with role = 'admin'.

Tabs:
  1. Schools  — view all schools, add a new school
  2. Users    — view all teacher accounts, see who is unassigned
  3. Assign   — assign a teacher to a school (or change assignment)
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR    = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from auth            import get_current_user, logout
from supabase_client import get_supabase

st.set_page_config(page_title="MDM Admin", page_icon="🛠️", layout="wide")


# ── Auth guard ────────────────────────────────────────────────────────────────
user = get_current_user()
if not user:
    st.error("Please log in first.")
    st.page_link("../home.py", label="Go to Login")
    st.stop()

if user["role"] not in ("admin", "block_officer"):
    st.error("Access denied — admin only.")
    st.stop()


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_logout = st.columns([5, 1])
with col_title:
    st.title("MDM Admin Panel")
    st.caption(f"Logged in as: {user.get('full_name') or user.get('email') or 'Admin'}")
with col_logout:
    st.write("")
    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()

st.divider()

supabase = get_supabase()


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _load_schools() -> list[dict]:
    try:
        resp = supabase.table("schools").select("id, school_code, name, district, taluka, udise_code, principal, phone, active").order("school_code").execute()
        return resp.data or []
    except Exception as e:
        st.error(f"Could not load schools: {e}")
        return []


def _load_users() -> list[dict]:
    try:
        resp = (
            supabase.table("user_profiles")
            .select("id, full_name, role, school_id, school_code, schools(name)")
            .order("full_name")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.error(f"Could not load users: {e}")
        return []


# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════

tab_schools, tab_users, tab_assign, tab_backup = st.tabs(["🏫 Schools", "👤 Users", "🔗 Assign Teachers", "💾 Backup"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — SCHOOLS
# ─────────────────────────────────────────────────────────────────────────────
with tab_schools:
    st.subheader("All Schools")

    schools = _load_schools()
    if schools:
        import pandas as pd
        df = pd.DataFrame(schools).rename(columns={
            "school_code": "Code", "name": "Name", "district": "District",
            "taluka": "Taluka", "udise_code": "UDISE", "principal": "Principal",
            "phone": "Phone", "active": "Active",
        })
        st.dataframe(
            df[["Code", "Name", "District", "Taluka", "UDISE", "Principal", "Phone", "Active"]],
            use_container_width=True, hide_index=True,
        )
        st.caption(f"{len(schools)} school(s) in database.")
    else:
        st.info("No schools found. Add one below.")

    st.divider()
    st.subheader("Add New School")

    with st.form("add_school_form"):
        c1, c2 = st.columns(2)
        code       = c1.text_input("School Code *",   placeholder="SCH001")
        name       = c2.text_input("School Name *",   placeholder="Indirabaai Kanya Vidyalaya")
        c3, c4     = st.columns(2)
        district   = c3.text_input("District",        placeholder="Amravati")
        taluka     = c4.text_input("Taluka",          placeholder="Shirala")
        c5, c6     = st.columns(2)
        udise      = c5.text_input("UDISE Code",      placeholder="27XXXXXXXX")
        principal  = c6.text_input("Principal Name",  placeholder="Smt. Kavita Desai")
        phone      = st.text_input("Phone",           placeholder="9876543210")
        add_btn    = st.form_submit_button("Add School", use_container_width=True, type="primary")

    if add_btn:
        code = code.strip().upper()
        name = name.strip()
        if not code or not name:
            st.error("School Code and Name are required.")
        else:
            try:
                supabase.table("schools").insert({
                    "school_code": code,
                    "name":        name,
                    "district":    district.strip() or None,
                    "taluka":      taluka.strip() or None,
                    "udise_code":  udise.strip() or None,
                    "principal":   principal.strip() or None,
                    "phone":       phone.strip() or None,
                }).execute()
                st.success(f"School '{code} — {name}' added successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add school: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — USERS
# ─────────────────────────────────────────────────────────────────────────────
with tab_users:
    st.subheader("Teacher Accounts")

    users = _load_users()
    if users:
        import pandas as pd

        rows = []
        for u in users:
            school_name = (u.get("schools") or {}).get("name") or "—"
            rows.append({
                "Full Name":   u.get("full_name") or "(no name)",
                "Role":        u.get("role", "teacher").title(),
                "School Code": u.get("school_code") or "⚠ Unassigned",
                "School Name": school_name,
                "User ID":     u["id"][:8] + "...",
            })
        df = pd.DataFrame(rows)

        def _highlight(row):
            if row["School Code"].startswith("⚠"):
                return ["background-color: #fff3cd"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df.style.apply(_highlight, axis=1),
            use_container_width=True, hide_index=True,
        )

        unassigned = sum(1 for u in users if not u.get("school_id"))
        if unassigned:
            st.warning(f"{unassigned} teacher(s) not yet assigned to a school.")
        else:
            st.success("All teachers have been assigned to a school.")
    else:
        st.info("No teacher accounts found yet.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — ASSIGN TEACHERS
# ─────────────────────────────────────────────────────────────────────────────
with tab_assign:
    st.subheader("Assign Teacher to School")

    users   = _load_users()
    schools = _load_schools()

    if not users:
        st.info("No users to assign.")
    elif not schools:
        st.warning("No schools found. Add schools first.")
    else:
        # Build dropdowns
        user_options = {
            f"{u.get('full_name') or '(no name)'} — {'⚠ unassigned' if not u.get('school_id') else u.get('school_code', '')}": u
            for u in users
        }
        school_options = {
            f"{s['school_code']} — {s['name']}": s
            for s in schools if s.get("active", True)
        }

        with st.form("assign_form"):
            sel_user   = st.selectbox("Select Teacher", list(user_options.keys()))
            sel_school = st.selectbox("Assign to School", list(school_options.keys()))
            also_role  = st.selectbox(
                "Set Role",
                ["teacher", "principal", "block_officer", "admin"],
                index=0,
            )
            assign_btn = st.form_submit_button("Save Assignment", use_container_width=True, type="primary")

        if assign_btn:
            chosen_user   = user_options[sel_user]
            chosen_school = school_options[sel_school]
            try:
                supabase.table("user_profiles").update({
                    "school_id":   chosen_school["id"],
                    "school_code": chosen_school["school_code"],
                    "role":        also_role,
                }).eq("id", chosen_user["id"]).execute()
                st.success(
                    f"{chosen_user.get('full_name') or 'User'} assigned to "
                    f"{chosen_school['school_code']} — {chosen_school['name']} as {also_role}."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Assignment failed: {e}")

        st.divider()
        st.subheader("Remove School Assignment")
        st.caption("Use this to unassign a teacher from a school (e.g., transfer).")

        assigned_users = [u for u in users if u.get("school_id")]
        if assigned_users:
            unassign_options = {
                f"{u.get('full_name') or '(no name)'} — {u.get('school_code', '')}": u
                for u in assigned_users
            }
            with st.form("unassign_form"):
                sel_unassign = st.selectbox("Select Teacher to Unassign", list(unassign_options.keys()))
                unassign_btn = st.form_submit_button("Remove Assignment", use_container_width=True)
            if unassign_btn:
                chosen = unassign_options[sel_unassign]
                try:
                    supabase.table("user_profiles").update({
                        "school_id":   None,
                        "school_code": None,
                    }).eq("id", chosen["id"]).execute()
                    st.success(f"{chosen.get('full_name') or 'User'} unassigned.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
        else:
            st.info("No assigned teachers to unassign.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — BACKUP
# ─────────────────────────────────────────────────────────────────────────────
with tab_backup:
    st.subheader("Download Backup")
    st.info("Download all data as CSV files. Save these monthly to prevent data loss.")

    import pandas as pd
    import io
    from datetime import datetime

    col1, col2 = st.columns(2)

    # ── Attendance backup ──
    with col1:
        st.markdown("**Attendance Data**")
        st.caption("All attendance records from all schools.")
        if st.button("Prepare Attendance CSV", use_container_width=True):
            try:
                resp = supabase.table("attendance").select(
                    "date, class_5, class_6, class_7, class_8, school_id, schools(school_code, name)"
                ).order("date").execute()
                rows = []
                for r in (resp.data or []):
                    school = r.get("schools") or {}
                    rows.append({
                        "Date":        r["date"],
                        "School Code": school.get("school_code", ""),
                        "School Name": school.get("name", ""),
                        "Class 5":     r.get("class_5", 0),
                        "Class 6":     r.get("class_6", 0),
                        "Class 7":     r.get("class_7", 0),
                        "Class 8":     r.get("class_8", 0),
                    })
                if rows:
                    df = pd.DataFrame(rows)
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇ Download Attendance CSV",
                        data=csv,
                        file_name=f"mdm_attendance_backup_{datetime.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                    st.success(f"{len(rows)} records ready.")
                else:
                    st.warning("No attendance records found.")
            except Exception as e:
                st.error(f"Failed: {e}")

    # ── Schools backup ──
    with col2:
        st.markdown("**Schools List**")
        st.caption("All registered schools.")
        if st.button("Prepare Schools CSV", use_container_width=True):
            try:
                schools_data = _load_schools()
                if schools_data:
                    df = pd.DataFrame(schools_data).drop(columns=["id"], errors="ignore")
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇ Download Schools CSV",
                        data=csv,
                        file_name=f"mdm_schools_backup_{datetime.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                    st.success(f"{len(schools_data)} schools ready.")
                else:
                    st.warning("No schools found.")
            except Exception as e:
                st.error(f"Failed: {e}")
