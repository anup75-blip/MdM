"""
bill_calculator.py
Pure-Python MDM bill calculator.
Quantities and expense rates verified against April 2026.xlsx Sheet1 formulas.
No Excel dependency — takes attendance DataFrame, returns structured bill data.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

# ── Per-student-per-working-day food quantities (confirmed from Sheet1 formulas)
# IM5 = IL5 * 100  → Class5 rice 100g     JF5 = JE5 * 150 → Class68 rice 150g
# IN5 = IL5 * 20   → Class5 dal  20g      JG5 = JE5 * 30  → Class68 dal  30g
# IQ5 = IL5 * 0.3  → mohari 0.3g          JJ5 = JE5 * 0.25
# IR5 = IL5 * 0.4  → haldi  0.4g          JK5 = JE5 * 0.4
# IS5 = IL5 * 1.5  → mirchi 1.5g          JL5 = JE5 * 2.5
# IT5 = IL5 * 5    → oil    5ml            JM5 = JE5 * 7.5
# IU5 = IL5 * 2    → mith   2g             JN5 = JE5 * 4
# (name_en, name_marathi, class5_qty, class68_qty, unit)
FOOD_ITEMS: list[tuple] = [
    ("Tandul (Rice)",        "तांदूळ",              100.0,  150.0,  "g"),
    ("Masur Dal",            "मसूर डाळ",             20.0,   30.0,  "g"),
    ("Matki / Chavli",       "मटकी / चवळी",          20.0,   30.0,  "g"),
    ("Harbhara",             "हरभरा",                20.0,   30.0,  "g"),
    ("Mohari",               "मोहरी",                 0.3,    0.25,  "g"),
    ("Haldi",                "हळद",                   0.4,    0.4,   "g"),
    ("Kanda Lasun Masala",   "कांदा लसून मसाला",      2.0,    5.0,   "g"),
    ("Mith (Salt)",          "मीठ",                   2.0,    4.0,   "g"),
    ("Tel (Oil)",            "सोया. तेल",              5.0,    7.5,  "ml"),
]

# ── Expense rates ₹ per student-day (confirmed from Bill 5th and Bill 6 To 8 sheets)
# Class 5:   bhajipala=1.00  fuel=0.89  supp=0.70  total=2.59
# Class 6-8: bhajipala=1.64  fuel=1.14  supp=1.10  total=3.88
# Note: Sheet1 shows 2.08/3.11 which are STOCK calculation rates, not bill rates.
RATES: dict[str, dict[str, float]] = {
    "class5": {
        "भाजिपाला (Bhajipala)":      1.00,
        "इंधन (Fuel)":                0.89,
        "पूरक आहार (Supplementary)":  0.70,
    },
    "class68": {
        "भाजिपाला (Bhajipala)":      1.64,
        "इंधन (Fuel)":                1.14,
        "पूरक आहार (Supplementary)":  1.10,
    },
}


@dataclass
class FoodLine:
    serial: int
    name_marathi: str
    name_en: str
    unit: str
    opening_kg: float = 0.0   # previous month closing (teacher input)
    received_kg: float = 0.0  # received this month (teacher input)
    total_kg: float = 0.0     # opening + received
    used_kg: float = 0.0      # calculated: student_days × qty_per_student / 1000
    closing_kg: float = 0.0   # total - used
    demand_kg: float = 0.0    # next month estimate = used


@dataclass
class ExpenseLine:
    label: str
    student_days: int
    rate_inr: float
    amount_inr: float


@dataclass
class BillResult:
    class_label: str           # "इ.5 (Class 5)" or "इ.6 ते 8 (Class 6–8)"
    group: str                 # "class5" or "class68"
    students_enrolled: int
    working_days: int
    total_student_days: int
    food_lines: List[FoodLine] = field(default_factory=list)
    expense_lines: List[ExpenseLine] = field(default_factory=list)
    total_expense: float = 0.0


def calculate_bill(
    attendance_df,
    working_days: int,
    class5_enrolled: int = 0,
    class68_enrolled: int = 0,
    class5_opening: Dict[str, float] | None = None,
    class68_opening: Dict[str, float] | None = None,
    class5_received: Dict[str, float] | None = None,
    class68_received: Dict[str, float] | None = None,
) -> tuple[BillResult, BillResult]:
    """
    Calculate monthly MDM bill for Class 5 and Class 6-8.

    attendance_df must have columns: Class5 (int), Class68 (int).
    Returns (class5_bill, class68_bill).
    """
    c5_op  = class5_opening  or {}
    c68_op = class68_opening or {}
    c5_rx  = class5_received  or {}
    c68_rx = class68_received or {}

    c5_days  = int(attendance_df["Class5"].sum())
    c68_days = int(attendance_df["Class68"].sum())

    def make_food_lines(student_days: int, qty_idx: int, opening: dict, received: dict) -> list[FoodLine]:
        lines = []
        for i, (name_en, name_marathi, qty5, qty68, unit) in enumerate(FOOD_ITEMS, start=1):
            qty_per = qty5 if qty_idx == 0 else qty68
            used_kg = round(student_days * qty_per / 1000.0, 3)
            op      = round(opening.get(name_en, 0.0), 3)
            rx      = round(received.get(name_en, 0.0), 3)
            total   = round(op + rx, 3)
            closing = round(total - used_kg, 3)
            demand  = round(used_kg, 3)
            lines.append(FoodLine(
                serial=i, name_marathi=name_marathi, name_en=name_en, unit=unit,
                opening_kg=op, received_kg=rx, total_kg=total,
                used_kg=used_kg, closing_kg=closing, demand_kg=demand,
            ))
        return lines

    def make_expense_lines(group: str, student_days: int) -> tuple[list[ExpenseLine], float]:
        lines = []
        total = 0.0
        for label, rate in RATES[group].items():
            amt = round(rate * student_days, 2)
            total += amt
            lines.append(ExpenseLine(label=label, student_days=student_days, rate_inr=rate, amount_inr=amt))
        return lines, round(total, 2)

    c5_food  = make_food_lines(c5_days,  0, c5_op,  c5_rx)
    c68_food = make_food_lines(c68_days, 1, c68_op, c68_rx)

    c5_exp,  c5_total  = make_expense_lines("class5",  c5_days)
    c68_exp, c68_total = make_expense_lines("class68", c68_days)

    c5_bill = BillResult(
        class_label="इ.5 (Class 5)", group="class5",
        students_enrolled=class5_enrolled,
        working_days=working_days,
        total_student_days=c5_days,
        food_lines=c5_food,
        expense_lines=c5_exp,
        total_expense=c5_total,
    )
    c68_bill = BillResult(
        class_label="इ.6 ते 8 (Class 6–8)", group="class68",
        students_enrolled=class68_enrolled,
        working_days=working_days,
        total_student_days=c68_days,
        food_lines=c68_food,
        expense_lines=c68_exp,
        total_expense=c68_total,
    )
    return c5_bill, c68_bill
