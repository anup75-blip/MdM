"""
setup_schools.py
One-time script to bulk-import schools into Supabase.
Run ONCE from your local machine (never deploy this to cloud).

Usage:
    python scripts/setup_schools.py --csv data/schools_import.csv

CSV format (with header row):
    school_code, name, district, taluka, block_name, udise_code, principal, phone, email, password

Example row:
    SCH001, Indirabaai Kanya Vidyalaya, Amravati, Shirala, Shirala, 27XXXXXX, Smt. Sharma, 9876543210, teacher1@gmail.com, mypassword123

Requirements:
    pip install supabase python-dotenv
    Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (NOT in secrets.toml)
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

# Load .env for local use (service key should never go to cloud)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL         = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file.")
    print("       Never commit those keys — they are admin-level.")
    sys.exit(1)

from supabase import create_client

# Use SERVICE ROLE key here (admin access, only for this setup script)
admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_school_account(row: dict) -> tuple[bool, str]:
    """Create Supabase Auth user + school record + user_profile for one school."""
    code     = row["school_code"].strip().upper()
    email    = row["email"].strip()
    password = row["password"].strip()

    # ── 1. Insert school record ───────────────────────────────────────────────
    try:
        school_resp = admin.table("schools").upsert({
            "school_code": code,
            "name":        row["name"].strip(),
            "district":    row.get("district", "").strip(),
            "taluka":      row.get("taluka", "").strip(),
            "block_name":  row.get("block_name", "").strip(),
            "udise_code":  row.get("udise_code", "").strip(),
            "principal":   row.get("principal", "").strip(),
            "phone":       row.get("phone", "").strip(),
            "active":      True,
        }, on_conflict="school_code").execute()
        school_id = school_resp.data[0]["id"]
    except Exception as exc:
        return False, f"School insert failed: {exc}"

    # ── 2. Create Supabase Auth user ──────────────────────────────────────────
    try:
        auth_resp = admin.auth.admin.create_user({
            "email":          email,
            "password":       password,
            "email_confirm":  True,   # skip email confirmation
        })
        user_id = auth_resp.user.id
    except Exception as exc:
        # User already exists — try to get existing ID
        if "already" in str(exc).lower() or "duplicate" in str(exc).lower():
            try:
                # Update password
                users = admin.auth.admin.list_users()
                existing = next((u for u in users if u.email == email), None)
                if existing:
                    admin.auth.admin.update_user_by_id(
                        existing.id, {"password": pin}
                    )
                    user_id = existing.id
                else:
                    return False, f"Auth user conflict, could not resolve: {exc}"
            except Exception as exc2:
                return False, f"Auth user update failed: {exc2}"
        else:
            return False, f"Auth user creation failed: {exc}"

    # ── 3. Create user_profile linking auth user → school ─────────────────────
    try:
        admin.table("user_profiles").upsert({
            "id":          user_id,
            "school_id":   school_id,
            "school_code": code,
            "full_name":   row.get("principal", "").strip(),
            "role":        "teacher",
        }, on_conflict="id").execute()
    except Exception as exc:
        return False, f"Profile insert failed: {exc}"

    return True, f"OK  {code} → {email} (PIN set)"


def main():
    parser = argparse.ArgumentParser(description="Import schools into Supabase MDM database.")
    parser.add_argument("--csv", required=True, help="Path to CSV file with school data.")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Seconds between API calls (default 0.3 to avoid rate limits).")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader  = csv.DictReader(f)
        schools = list(reader)

    print(f"Importing {len(schools)} schools...\n")
    success = 0
    failed  = 0

    for i, row in enumerate(schools, 1):
        ok, msg = create_school_account(row)
        status  = "OK " if ok else "ERR"
        print(f"[{i:3}/{len(schools)}] {status}  {row.get('school_code','?'):<10} {msg}")
        if ok:
            success += 1
        else:
            failed += 1
        time.sleep(args.delay)

    print(f"\nDone. {success} succeeded, {failed} failed.")
    if failed:
        print("Re-run the script — failed rows will be retried (upsert is idempotent).")


if __name__ == "__main__":
    main()
