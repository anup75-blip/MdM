"""
attendance_db.py
Supabase CRUD for attendance records.
All queries are scoped to the logged-in school via Supabase RLS.
"""
from __future__ import annotations

import calendar
from datetime import date

import pandas as pd


def _supabase():
    from supabase_client import get_supabase
    import streamlit as st
    client = get_supabase()
    token = (st.session_state.get("mdm_user") or {}).get("access_token")
    if token:
        client.postgrest.session.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate_attendance(c5: int, c6: int, c7: int, c8: int) -> str | None:
    """Return error string if invalid, None if OK."""
    for label, val in [("Class 5", c5), ("Class 6", c6), ("Class 7", c7), ("Class 8", c8)]:
        if not isinstance(val, (int, float)):
            return f"{label} must be a number."
        if int(val) < 0 or int(val) > 500:
            return f"{label} must be between 0 and 500."
    return None


# ── Read ────────────────────────────────────────────────────────────────────────

def get_month_attendance(school_id: str, year: int, month: int) -> pd.DataFrame:
    """
    Fetch all attendance rows for a school in a given month.
    Returns DataFrame with columns: date, class5, class6, class7, class8, class68, total.
    """
    start = date(year, month, 1).isoformat()
    end   = date(year, month, calendar.monthrange(year, month)[1]).isoformat()

    resp = (
        _supabase()
        .table("attendance")
        .select("date, class5, class6, class7, class8")
        .eq("school_id", school_id)
        .gte("date", start)
        .lte("date", end)
        .order("date")
        .execute()
    )

    rows = resp.data or []
    if not rows:
        return pd.DataFrame(columns=["date", "class5", "class6", "class7", "class8", "class68", "total"])

    df = pd.DataFrame(rows)
    df["date"]    = pd.to_datetime(df["date"]).dt.date
    df["class68"] = df["class6"] + df["class7"] + df["class8"]
    df["total"]   = df["class5"] + df["class68"]
    return df


def get_attendance_records(school_id: str, year: int, month: int) -> list[dict]:
    """Return raw list of attendance dicts for Excel export."""
    start = date(year, month, 1).isoformat()
    end   = date(year, month, calendar.monthrange(year, month)[1]).isoformat()

    resp = (
        _supabase()
        .table("attendance")
        .select("date, class5, class6, class7, class8")
        .eq("school_id", school_id)
        .gte("date", start)
        .lte("date", end)
        .execute()
    )
    return resp.data or []


# ── Write ───────────────────────────────────────────────────────────────────────

def save_attendance(
    school_id: str,
    user_id:   str,
    att_date:  date,
    c5: int, c6: int, c7: int, c8: int,
) -> tuple[bool, str]:
    """
    Insert or update attendance for one day.
    Returns (success, message).
    """
    error = _validate_attendance(c5, c6, c7, c8)
    if error:
        return False, error

    supabase = _supabase()
    data = {
        "school_id":  school_id,
        "date":       att_date.isoformat(),
        "class5":     int(c5),
        "class6":     int(c6),
        "class7":     int(c7),
        "class8":     int(c8),
        "entered_by": user_id,
    }

    try:
        supabase.table("attendance").upsert(
            data, on_conflict="school_id,date"
        ).execute()

        supabase.table("audit_log").insert({
            "school_id": school_id,
            "user_id":   user_id,
            "action":    "attendance_save",
            "details":   {
                "date":   att_date.isoformat(),
                "class5": int(c5), "class6": int(c6),
                "class7": int(c7), "class8": int(c8),
            },
        }).execute()

        return True, "Saved."
    except Exception as exc:
        return False, f"Save failed: {exc}"
