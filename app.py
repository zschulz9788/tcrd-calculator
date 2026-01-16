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

# -----------------------------
# Easter calculation (Gregorian)
# -----------------------------
def easter_date(year):
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

# -----------------------------
# Super Bowl Sunday
# First Sunday of February
# -----------------------------
def super_bowl_sunday(year):
    d = date(year, 2, 1)

    # Find first Sunday
    while d.weekday() != 6:
        d += timedelta(days=1)

    # Second Sunday = first Sunday + 7 days
    return d + timedelta(days=7)



def is_holiday(d):
    year = d.year

    # Fixed-date holidays
    if (d.month, d.day) in [
        (1, 1),    # New Year's Day
        (7, 4),    # Independence Day
        (12, 25),  # Christmas
    ]:
        return True

    # Memorial Day: last Monday of May
    if d.month == 5 and d.weekday() == 0:
        if d + timedelta(days=7) > date(year, 5, 31):
            return True

    # Labor Day: first Monday of September
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True

    # Thanksgiving: fourth Thursday of November
    if d.month == 11 and d.weekday() == 3:
        thursdays = [
            day for day in range(1, 31)
            if date(year, 11, day).weekday() == 3
        ]
        if d.day == thursdays[3]:
            return True

    # Easter
    if d == easter_date(year):
        return True

    # Super Bowl Sunday
    if d == super_bowl_sunday(year):
        return True

    return False


@app.route("/", methods=["GET", "POST"])
def index():
    base_minutes = 0
    holiday_minutes = 0

    if request.method == "POST":
        text = request.form.get("schedule_text", "")
        lines = text.splitlines()

        # -------------------------
        # Base TCRD (known-good)
        # -------------------------
        matches = re.findall(r'TCRD\D*(\d{4})', text, re.IGNORECASE)
        for t in matches:
            base_minutes += int(t[:2]) * 60 + int(t[2:])

        # -------------------------
        # Holiday bonus (separate)
        # -------------------------
        year = 2026  # PERIOD 0126
        holiday_dates = set()
        current_date = None
        saw_flying = False

        for line in lines:
            m = re.search(
                r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',
                line
            )
            if m:
                if current_date and saw_flying and is_holiday(current_date):
                    holiday_dates.add(current_date)

                current_date = date(year, MONTHS[m.group(2)], int(m.group(1)))
                saw_flying = False

            if "TCRD" in line.upper():
                saw_flying = True

        if current_date and saw_flying and is_holiday(current_date):
            holiday_dates.add(current_date)

        holiday_minutes = len(holiday_dates) * HOLIDAY_BONUS_MINUTES

    total_minutes = base_minutes + holiday_minutes

    return render_template(
        "index.html",
        base=f"{base_minutes // 60}:{base_minutes % 60:02d}",
        holiday=f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}",
        total=f"{total_minutes // 60}:{total_minutes % 60:02d}"
    )


if __name__ == "__main__":
    app.run()