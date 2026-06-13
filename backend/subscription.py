"""
subscription.py
Subscription status checker for MDM schools.

Statuses:
  trial   — within 30-day free trial window
  active  — paid subscription, still valid
  expired — trial ended and no active subscription
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def get_subscription_info(school_id: str) -> dict:
    """
    Returns:
        status       : 'trial' | 'active' | 'expired'
        days_left    : int (days remaining) or None if unlimited/unknown
        trial_ends_at: datetime or None
        sub_ends_at  : datetime or None
    """
    from supabase_client import get_supabase
    import streamlit as st
    try:
        client = get_supabase()
        token = (st.session_state.get("mdm_user") or {}).get("access_token")
        if token:
            client.postgrest.session.headers.update({"Authorization": f"Bearer {token}"})
        resp = (
            client
            .table("schools")
            .select("subscription_status, trial_ends_at, subscription_ends_at")
            .eq("id", school_id)
            .single()
            .execute()
        )
        data = resp.data or {}
    except Exception:
        # Can't fetch — default to trial so user isn't blocked unexpectedly
        return {"status": "trial", "days_left": 30, "trial_ends_at": None, "sub_ends_at": None}

    now           = datetime.now(timezone.utc)
    db_status     = data.get("subscription_status") or "trial"
    trial_ends_at = _parse_dt(data.get("trial_ends_at"))
    sub_ends_at   = _parse_dt(data.get("subscription_ends_at"))

    if db_status == "active":
        if sub_ends_at and sub_ends_at < now:
            return {"status": "expired", "days_left": 0,
                    "trial_ends_at": trial_ends_at, "sub_ends_at": sub_ends_at}
        days_left = int((sub_ends_at - now).days) if sub_ends_at else None
        return {"status": "active", "days_left": days_left,
                "trial_ends_at": trial_ends_at, "sub_ends_at": sub_ends_at}

    # trial (default)
    if trial_ends_at and trial_ends_at < now:
        return {"status": "expired", "days_left": 0,
                "trial_ends_at": trial_ends_at, "sub_ends_at": sub_ends_at}

    days_left = int((trial_ends_at - now).days) if trial_ends_at else 30
    return {"status": "trial", "days_left": max(days_left, 0),
            "trial_ends_at": trial_ends_at, "sub_ends_at": sub_ends_at}


def is_subscription_active(school_id: str) -> bool:
    """Quick check: returns True if school can use the system."""
    return get_subscription_info(school_id)["status"] in ("trial", "active")
