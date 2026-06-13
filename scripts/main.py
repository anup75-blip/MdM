"""
main.py
Mid-Day Meal monthly report pipeline — single command entry point.

Usage:
    python scripts/main.py --month 4 --year 2026 --attendance data/attendance/apr2026.csv
    python scripts/main.py --month 4 --year 2026 --attendance data/attendance/apr2026.csv --template "C:/custom/template.xlsx"
"""

from __future__ import annotations

import argparse
import calendar
import json
import logging
import sys
from datetime import date
from pathlib import Path

# Make sibling scripts importable when run as: python scripts/main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from daily_entry import load_attendance
from holiday_manager import HolidayManager
from monthly_report import build_output_path, copy_template, generate_report, save_report

# ── Project paths ──────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).resolve().parent.parent
LOG_DIR          = BASE_DIR / "logs"
AUDIT_DIR        = BASE_DIR / "output" / "audit"
HOLIDAY_FILE     = BASE_DIR / "data" / "holidays" / "holiday_list.xlsx"
DEFAULT_TEMPLATE = Path(r"C:\Users\HP\Downloads\April 2026.xlsx")


# ── Logging ────────────────────────────────────────────────────────────────────
def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{date.today():%Y%m%d}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ── Audit ──────────────────────────────────────────────────────────────────────
def write_audit(
    df,
    hm: HolidayManager,
    month: int,
    year: int,
    output_path: Path,
) -> dict:
    """Write a JSON audit summary for this pipeline run."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    working_days = hm.get_working_days(month)
    non_working  = hm.get_non_working_days(month)
    total_days   = calendar.monthrange(year, month)[1]

    summary = {
        "year":             year,
        "month":            month,
        "total_days":       total_days,
        "working_days":     len(working_days),
        "non_working_days": [
            {"date": str(d), "reason": reason} for d, reason in non_working
        ],
        "records_loaded":   len(df),
        "total_class5":     int(df["Class5"].sum()),
        "total_class6":     int(df["Class6"].sum()),
        "total_class7":     int(df["Class7"].sum()),
        "total_class8":     int(df["Class8"].sum()),
        "total_class6_8":   int(df[["Class6", "Class7", "Class8"]].values.sum()),
        "total_attendance": int(df[["Class5", "Class6", "Class7", "Class8"]].values.sum()),
        "output_file":      str(output_path),
    }

    audit_path = AUDIT_DIR / f"audit_{year}_{month:02d}.json"
    with open(audit_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    logging.getLogger(__name__).info("Audit written → %s", audit_path)
    return summary


# ── Pipeline ───────────────────────────────────────────────────────────────────
def run_pipeline(
    month: int,
    year: int,
    attendance_csv: Path,
    template_path: Path,
) -> None:
    log = logging.getLogger(__name__)
    sep = "=" * 60
    month_label = date(year, month, 1).strftime("%B %Y")

    log.info(sep)
    log.info("Mid-Day Meal Pipeline  |  %s", month_label)
    log.info(sep)

    # 1 — Load attendance CSV
    log.info("[1/5] Loading attendance")
    df = load_attendance(attendance_csv)

    # 2 — Holiday manager
    log.info("[2/5] Initialising holiday manager")
    hm = HolidayManager(year=year)
    hm.load_school_holidays(HOLIDAY_FILE)

    # 3 — Resolve output path
    output_path = build_output_path(BASE_DIR, year, month)
    log.info("[3/5] Output file → %s", output_path)

    # 4 — Copy template, fill, save
    log.info("[4/5] Generating workbook")
    wb = copy_template(template_path, output_path)
    generate_report(wb, df, hm)
    save_report(wb, output_path)

    # 5 — Audit
    log.info("[5/5] Writing audit")
    summary = write_audit(df, hm, month, year, output_path)

    log.info(sep)
    log.info("Pipeline complete")
    log.info("  Output      : %s", output_path)
    log.info("  Class 5     : %d student-days", summary["total_class5"])
    log.info("  Class 6-8   : %d student-days", summary["total_class6_8"])
    log.info("  Working days: %d / %d", summary["working_days"], summary["total_days"])
    log.info(sep)


# ── CLI ────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mid-Day Meal Monthly Report Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--month",      type=int,  required=True,            help="Month number 1–12")
    p.add_argument("--year",       type=int,  required=True,            help="Year  e.g. 2026")
    p.add_argument("--attendance", type=Path, required=True,            help="Path to attendance CSV")
    p.add_argument("--template",   type=Path, default=DEFAULT_TEMPLATE, help="Path to Excel template")
    return p.parse_args()


def main() -> None:
    setup_logging(LOG_DIR)
    args = parse_args()

    try:
        run_pipeline(
            month=args.month,
            year=args.year,
            attendance_csv=args.attendance,
            template_path=args.template,
        )
    except FileNotFoundError as exc:
        logging.error("File not found: %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logging.error("Data error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
