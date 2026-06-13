"""
bill_header.py
Renders the government-style MDM bill header (State / District / Taluka / Kendra / School).
Also provides an inline edit form so teachers can update kendra/district/taluka/state.
"""
from __future__ import annotations

import streamlit as st


def render_bill_header(user: dict, bill_label: str, month_label: str) -> dict:
    """
    Render the full bill header with school location details.

    Shows an editable form if kendra is missing.
    Returns the (possibly updated) user info dict.
    """
    state    = user.get("state")    or "Maharashtra"
    district = user.get("district") or ""
    taluka   = user.get("taluka")   or ""
    kendra   = user.get("kendra")   or ""
    school   = user.get("school_name") or ""

    st.markdown(f"""
<div style="
    border: 2px solid #2e7d32;
    border-radius: 8px;
    padding: 14px 20px;
    background: #f9fbf9;
    margin-bottom: 12px;
">
<table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
<tr>
  <td style="width:50%; padding:3px 8px;">
    <b>राज्य (State):</b> {state}
  </td>
  <td style="width:50%; padding:3px 8px;">
    <b>जिल्हा (District):</b> {district or '<span style="color:#c62828">— not set —</span>'}
  </td>
</tr>
<tr>
  <td style="padding:3px 8px;">
    <b>तालुका (Taluka):</b> {taluka or '<span style="color:#c62828">— not set —</span>'}
  </td>
  <td style="padding:3px 8px;">
    <b>केंद्र (Kendra):</b> {kendra or '<span style="color:#c62828">— not set —</span>'}
  </td>
</tr>
<tr>
  <td colspan="2" style="padding:3px 8px; font-size:1.05rem;">
    <b>शाळेचे नाव (School):</b> {school}
  </td>
</tr>
<tr>
  <td colspan="2" style="padding:3px 8px;">
    <b>बिल (Bill):</b> {bill_label} &nbsp;&nbsp;|&nbsp;&nbsp; <b>महिना (Month):</b> {month_label}
  </td>
</tr>
</table>
</div>
""", unsafe_allow_html=True)

    # Show inline edit if any field is missing
    if not kendra or not district or not taluka:
        with st.expander("Update school details (kendra/district/taluka/state)", expanded=not kendra):
            _render_school_edit_form(user)

    return user


def _render_school_edit_form(user: dict) -> None:
    """Inline form to update kendra / district / taluka / state."""
    from supabase_client import get_supabase

    school_id = user.get("school_id")
    if not school_id:
        return

    with st.form("school_info_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        new_kendra   = c1.text_input("Kendra (केंद्र) *",      value=user.get("kendra")   or "", placeholder="Kendriya Shala, Shirala")
        new_district = c2.text_input("District (जिल्हा)",       value=user.get("district") or "", placeholder="Amravati")
        c3, c4 = st.columns(2)
        new_taluka   = c3.text_input("Taluka (तालुका)",         value=user.get("taluka")   or "", placeholder="Shirala")
        new_state    = c4.text_input("State (राज्य)",           value=user.get("state")    or "Maharashtra")
        save_btn = st.form_submit_button("Save School Info", type="primary", use_container_width=True)

    if save_btn:
        if not new_kendra.strip():
            st.error("Kendra name is required.")
            return
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
            # Update session_state so it reflects immediately without re-login
            st.session_state["mdm_user"]["kendra"]   = new_kendra.strip()
            st.session_state["mdm_user"]["district"]  = new_district.strip()
            st.session_state["mdm_user"]["taluka"]    = new_taluka.strip()
            st.session_state["mdm_user"]["state"]     = new_state.strip() or "Maharashtra"
            st.success("School details updated!")
            st.rerun()
        except Exception as exc:
            st.error(f"Save failed: {exc}")
