"""
auth.py
Login / logout / session management using Supabase Auth.

Login methods:
  - Phone + Password  (teachers — phone number is their identity)
  - Email + Password  (admin — deshmukha75@gmail.com)
  - Google OAuth      (admin / testers)

Each teacher account = one school.
Phone number is stored as a synthetic email (e.g. 9876543210@mdm.app) in Supabase Auth
so we can use standard email+password auth without needing Twilio/SMS.
"""
from __future__ import annotations

import streamlit as st

SESSION_KEY  = "mdm_user"
_ADMIN_EMAIL = "deshmukha75@gmail.com"
_FAKE_DOMAIN = "mdm.app"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_auth_email(identifier: str) -> str:
    """
    Convert a phone number to a synthetic Supabase email.
    If identifier already looks like an email, return as-is.
    e.g. "9876543210" → "9876543210@mdm.app"
         "+919876543210" → "9876543210@mdm.app"
    """
    identifier = identifier.strip()
    if "@" in identifier:
        return identifier.lower()
    digits = "".join(c for c in identifier if c.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]   # strip country code
    return f"{digits}@{_FAKE_DOMAIN}"


def _is_phone_email(email: str) -> bool:
    return email.endswith(f"@{_FAKE_DOMAIN}")


# ── Google OAuth ───────────────────────────────────────────────────────────────

def google_login_url() -> str:
    from supabase_client import get_supabase
    site_url = st.secrets.get("supabase", {}).get("site_url", "http://localhost:8501")
    result = get_supabase().auth.sign_in_with_oauth({
        "provider": "google",
        "options":  {"redirect_to": site_url},
    })
    return result.url


def handle_oauth_callback() -> bool:
    from supabase_client import get_supabase
    code = st.query_params.get("code")
    if not code:
        return False
    try:
        result = get_supabase().auth.exchange_code_for_session({"auth_code": code})
    except Exception as exc:
        st.error(f"Google login error: {exc}")
        st.query_params.clear()
        return False
    if not result.user:
        st.query_params.clear()
        return False
    ok, _ = _load_profile_into_session(result.user)
    st.query_params.clear()
    return ok


# ── Login (phone or email + password) ─────────────────────────────────────────

def login(identifier: str, password: str) -> tuple[bool, str]:
    """
    Sign in with phone number OR email + password.
    Phone numbers are converted to synthetic emails internally.
    """
    from supabase_client import get_supabase
    if not identifier or not password:
        return False, "Phone/email and password are required."
    auth_email = _to_auth_email(identifier)
    try:
        result = get_supabase().auth.sign_in_with_password(
            {"email": auth_email, "password": password}
        )
    except Exception as e:
        return False, f"Login error: {e}"
    if not result.user:
        return False, "Incorrect phone number or password."
    return _load_profile_into_session(result.user)


# ── Sign-up (teacher self-registration) ───────────────────────────────────────

def signup(
    phone:       str,
    password:    str,
    school_name: str,
    district:    str = "",
    taluka:      str = "",
    udise:       str = "",
    kendra:      str = "",
    state:       str = "Maharashtra",
) -> tuple[bool, str]:
    """
    Create a new teacher account + their school in one step.
    Returns (True, "__logged_in__") if immediately logged in,
            (True, message)          if email confirmation needed,
            (False, error_message)   on failure.

    Requires email confirmation to be DISABLED in Supabase Auth settings.
    (Authentication → Providers → Email → Confirm email → OFF)
    """
    from supabase_client import get_supabase
    supabase    = get_supabase()
    phone       = phone.strip()
    school_name = school_name.strip()
    district    = district.strip()
    taluka      = taluka.strip()
    udise       = udise.strip()
    kendra      = kendra.strip()
    state       = state.strip() or "Maharashtra"

    if not phone or not password or not school_name:
        return False, "Phone number, password and school name are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    # Convert phone to synthetic email for Supabase Auth
    auth_email = _to_auth_email(phone)
    digits     = auth_email.split("@")[0]   # the 10-digit phone used as school code

    # Pass all school data in metadata — the DB trigger reads this
    # and creates the school + profile automatically (SECURITY DEFINER, bypasses RLS)
    try:
        result = supabase.auth.sign_up({
            "email":    auth_email,
            "password": password,
            "options":  {"data": {
                "phone":       phone,
                "school_name": school_name,
                "district":    district,
                "taluka":      taluka,
                "udise_code":  udise,
                "kendra":      kendra,
                "state":       state,
            }},
        })
    except Exception as e:
        err = str(e)
        if "already registered" in err.lower() or "already been registered" in err.lower():
            return False, "This phone number already has an account. Please log in."
        return False, f"Sign-up failed: {e}"

    if not result.user:
        return False, "Sign-up failed. Please try again."

    # Trigger has now created the school + profile in the DB.
    # Apply the JWT from sign_up directly to the PostgREST client so that
    # _load_profile_into_session can make RLS-authenticated queries immediately.
    if result.session:
        access_token = result.session.access_token
        supabase.postgrest.session.headers.update(
            {"Authorization": f"Bearer {access_token}"}
        )
        ok, _ = _load_profile_into_session(result.user)
        if ok:
            st.session_state[SESSION_KEY]["access_token"] = access_token
            return True, "__logged_in__"
        return False, "Account created but profile load failed. Please log in manually."

    return True, "Account created! Please log in now."


# ── Shared: load profile into session ─────────────────────────────────────────

def _load_profile_into_session(user) -> tuple[bool, str]:
    """Fetch the user_profiles row and write everything into st.session_state."""
    from supabase_client import get_supabase
    supabase = get_supabase()

    try:
        resp = (
            supabase.table("user_profiles")
            .select("school_id, school_code, role, full_name, schools(name, district, taluka, kendra, state)")
            .eq("id", user.id)
            .single()
            .execute()
        )
        profile     = resp.data
        school_info = profile.get("schools") or {}

        # Recover the display phone number from the synthetic email
        raw_email   = getattr(user, "email", "")
        display_id  = (
            raw_email.split("@")[0] if _is_phone_email(raw_email) else raw_email
        )

        # Get current access token and store it for subsequent RLS queries
        _token = None
        try:
            _sess = supabase.auth.get_session()
            if _sess:
                _token = _sess.access_token
                supabase.postgrest.session.headers.update(
                    {"Authorization": f"Bearer {_token}"}
                )
        except Exception:
            pass

        st.session_state[SESSION_KEY] = {
            "user_id":      user.id,
            "email":        raw_email,
            "display_id":   display_id,
            "school_id":    profile.get("school_id"),
            "school_code":  profile.get("school_code") or "",
            "school_name":  school_info.get("name", ""),
            "district":     school_info.get("district", ""),
            "taluka":       school_info.get("taluka", ""),
            "kendra":       school_info.get("kendra", ""),
            "state":        school_info.get("state", "Maharashtra"),
            "role":         profile.get("role", "teacher"),
            "full_name":    profile.get("full_name") or "",
            "access_token": _token,
        }

    except Exception:
        # No profile found — only expected for the known admin email
        raw_email = getattr(user, "email", "")
        role      = "admin" if raw_email == _ADMIN_EMAIL else "teacher"
        full_name = user.user_metadata.get("full_name") or raw_email
        if role == "admin":
            try:
                supabase.table("user_profiles").insert({
                    "id":        user.id,
                    "role":      "admin",
                    "full_name": full_name,
                }).execute()
            except Exception:
                pass
        st.session_state[SESSION_KEY] = {
            "user_id":     user.id,
            "email":       raw_email,
            "display_id":  raw_email,
            "school_id":   None,
            "school_code": "",
            "school_name": "Administrator" if role == "admin" else "",
            "district":    "",
            "taluka":      "",
            "kendra":      "",
            "state":       "Maharashtra",
            "role":        role,
            "full_name":   full_name,
        }

    # Audit log (best-effort — silent failure is fine here)
    try:
        school_id = st.session_state[SESSION_KEY].get("school_id")
        if school_id:
            supabase.table("audit_log").insert({
                "school_id": school_id,
                "user_id":   user.id,
                "action":    "login",
                "details":   {},
            }).execute()
    except Exception:
        pass

    return True, "Login successful."


# ── Session helpers ────────────────────────────────────────────────────────────

def logout() -> None:
    from supabase_client import get_supabase
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop(SESSION_KEY, None)


def get_current_user() -> dict | None:
    return st.session_state.get(SESSION_KEY)


def require_login() -> dict:
    user = get_current_user()
    if not user:
        st.error("Please log in to continue.")
        st.stop()
    return user
