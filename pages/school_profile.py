"""
school_profile.py
School Profile — teachers update their school's kendra, district, taluka, state.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
sys.path.insert(0, str(BASE_DIR / "backend"))

from auth             import require_login, logout
from supabase_client  import get_supabase

st.set_page_config(page_title="School Profile", layout="centered", initial_sidebar_state="expanded")

user = require_login()

with st.sidebar:
    st.title("School Profile")
    st.markdown(f"**{user['school_name']}**")
    st.caption(f"Code: {user['school_code']}  |  Role: {user['role'].title()}")
    st.divider()
    if st.button("Logout", use_container_width=True):
        logout()
        st.rerun()

st.title("School Profile")
st.caption("Update your school's location details. These appear in all bill headers.")
st.divider()

school_id = user.get("school_id")
if not school_id:
    st.warning("No school associated with your account. Contact admin.")
    st.stop()

# ── Current info display ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)
col1.info(f"**School:** {user.get('school_name', '')}")
col2.info(f"**Code:** {user.get('school_code', '')}")

st.divider()

# ── Edit form ─────────────────────────────────────────────────────────────────
st.subheader("Edit School Details")

with st.form("school_profile_form"):
    new_kendra = st.text_input(
        "Kendra Name (केंद्राचे नाव) *",
        value=user.get("kendra") or "",
        placeholder="e.g. Kendriya Shala, Shirala",
        help="The cluster school name (केंद्र) that appears at the top of every government bill.",
    )

    c1, c2 = st.columns(2)
    new_district = c1.text_input(
        "District (जिल्हा)",
        value=user.get("district") or "",
        placeholder="e.g. Amravati",
    )
    new_taluka = c2.text_input(
        "Taluka (तालुका)",
        value=user.get("taluka") or "",
        placeholder="e.g. Shirala",
    )

    new_state = st.text_input(
        "State (राज्य)",
        value=user.get("state") or "Maharashtra",
    )

    save_btn = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

if save_btn:
    if not new_kendra.strip():
        st.error("Kendra name is required.")
    else:
        try:
            client = get_supabase()
            token  = (st.session_state.get("mdm_user") or {}).get("access_token")
            if token:
                client.postgrest.session.headers.update({"Authorization": f"Bearer {token}"})
            client.rpc("update_school_info", {
                "p_school_id": school_id,
                "p_kendra":    new_kendra.strip(),
                "p_district":  new_district.strip(),
                "p_taluka":    new_taluka.strip(),
                "p_state":     new_state.strip() or "Maharashtra",
            }).execute()
            # Reflect changes in session immediately
            st.session_state["mdm_user"]["kendra"]   = new_kendra.strip()
            st.session_state["mdm_user"]["district"]  = new_district.strip()
            st.session_state["mdm_user"]["taluka"]    = new_taluka.strip()
            st.session_state["mdm_user"]["state"]     = new_state.strip() or "Maharashtra"
            st.success("School details saved successfully!")
            st.rerun()
        except Exception as exc:
            st.error(f"Save failed: {exc}")

st.divider()

# ── Preview of bill header ────────────────────────────────────────────────────
st.subheader("Preview (how it will appear on bills)")

_kendra   = user.get("kendra")   or new_kendra or "—"
_district = user.get("district") or new_district or "—"
_taluka   = user.get("taluka")   or new_taluka or "—"
_state    = user.get("state")    or new_state or "Maharashtra"

st.markdown(f"""
<div style="
    border: 2px solid #2e7d32;
    border-radius: 8px;
    padding: 14px 20px;
    background: #f9fbf9;
">
<table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
<tr>
  <td style="width:50%; padding:4px 8px;"><b>राज्य (State):</b> {_state}</td>
  <td style="width:50%; padding:4px 8px;"><b>जिल्हा (District):</b> {_district}</td>
</tr>
<tr>
  <td style="padding:4px 8px;"><b>तालुका (Taluka):</b> {_taluka}</td>
  <td style="padding:4px 8px;"><b>केंद्र (Kendra):</b> {_kendra}</td>
</tr>
<tr>
  <td colspan="2" style="padding:4px 8px; font-size:1.05rem;">
    <b>शाळेचे नाव (School):</b> {user.get('school_name', '')}
  </td>
</tr>
</table>
</div>
""", unsafe_allow_html=True)
