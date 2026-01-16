from flask import Flask, request, render_template
import re
from datetime import date, timedelta

app = Flask(__name__)

HOLIDAY_BONUS_MINUTES = 4 * 60 + 12  # 252 minutes

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

TCRD_RE = re.compile(r"TCRD\D*(\d{4})", re.IGNORECASE)

# Detect a calendar date like "08 FEB"
DATE_RE = re.compile(
    r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b',
    re.IGNORECASE
)

# Detect an assigned pairing like "R7353"
PAIRING_RE = re.compile(r"\bR\d{4}\b", re.IGNORECASE)


def infer_year(text: str, default_year: int = 2026) -> int:
    # Parses "PERIOD 0226" -> 2026
    m = re.search(r"PERIOD\s+\d{2}(\d{2})", text, re.IGNORECASE)
    return 2000 + int(m.group(1)) if m else default_year


# -----------------------------
# Holiday helpers
# -----------------------------
def easter_date(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)

def super_bowl_sunday(year: int) -> date:
    # SECOND Sunday of February (per your contract)
    d = date(year, 2, 1)
    while d.weekday() != 6:  # Sunday
        d += timedelta(days=1)
    return d + timedelta(days=7)

def is_holiday(d: date) -> bool:
    y = d.year

    # Fixed-date holidays
    if (d.month, d.day) in [(1, 1), (7, 4), (12, 25)]:
        return True

    # Memorial Day: last Monday of May
    if d.month == 5 and d.weekday() == 0 and (d + timedelta(days=7) > date(y, 5, 31)):
        return True

    # Labor Day: first Monday of September
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True

    # Thanksgiving: fourth Thursday of November
    if d.month == 11 and d.weekday() == 3:
        thursdays = [x for x in range(1, 31) if date(y, 11, x).weekday() == 3]
        if d.day == thursdays[3]:
            return True

    # Easter
    if d == easter_date(y):
        return True

    # Super Bowl Sunday
    if d == super_bowl_sunday(y):
        return True

    return False


def fmt_hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60}:{total_minutes % 60:02d}"


def holiday_worked_days_from_text(text: str, year: int) -> set[date]:
    """
    Lightweight holiday worked-day detection:
    - Scan lines for a date token (DD MON)
    - If that same line contains OFF => not worked
    - If that same line contains an assigned pairing (R####) => worked
    This is robust for the day-list style where the assignment is on the date line.
    """
    worked_days = set()

    for line in text.splitlines():
        m = DATE_RE.search(line)
        if not m:
            continue

        dd = int(m.group(1))
        mon = MONTHS[m.group(2).upper()]
        d = date(year, mon, dd)

        upper = line.upper()
        if "OFF" in upper:
            continue

        if PAIRING_RE.search(upper):
            worked_days.add(d)

    return worked_days


@app.route("/", methods=["GET", "POST"])
def index():
    schedule_text = ""
    base_minutes = 0
    holiday_minutes = 0
    total_minutes = 0

    if request.method == "POST":
        schedule_text = request.form.get("schedule_text", "")
        year = infer_year(schedule_text, default_year=2026)

        # Base TCRD: global scan (this is why it always totals correctly)
        for t in TCRD_RE.findall(schedule_text):
            base_minutes += int(t[:2]) * 60 + int(t[2:])

        # Holiday bonus: determine which holiday dates were WORKED
        worked_days = holiday_worked_days_from_text(schedule_text, year)
        worked_holidays = {d for d in worked_days if is_holiday(d)}

        holiday_minutes = len(worked_holidays) * HOLIDAY_BONUS_MINUTES
        total_minutes = base_minutes + holiday_minutes

    return render_template(
        "index.html",
        schedule_text=schedule_text,
        base=fmt_hhmm(base_minutes) if request.method == "POST" else "",
        holiday=fmt_hhmm(holiday_minutes) if request.method == "POST" else "",
        total=fmt_hhmm(total_minutes) if request.method == "POST" else "",
    )


if __name__ == "__main__":
    app.run()
