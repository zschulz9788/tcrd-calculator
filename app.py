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

def is_holiday(d):
    year = d.year

    # Fixed holidays
    if (d.month, d.day) in [(1, 1), (7, 4), (12, 25)]:
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

    # (Easter & Super Bowl can be added later)
    return False


@app.route("/", methods=["GET", "POST"])
def index():
    base_minutes = 0
    holiday_minutes = 0

    if request.method == "POST":
        text = request.form.get("schedule_text", "")
        lines = text.splitlines()

        year = 2026  # PERIOD 0126
        last_date = None
        holiday_dates_used = set()

        for line in lines:
            # Find ALL dates in the line (because of 2-column layout)
            for m in re.finditer(
                r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',
                line
            ):
                day = int(m.group(1))
                month = MONTHS[m.group(2)]
                last_date = date(year, month, day)

            # Find TCRD
            tcrd_match = re.search(r'TCRD\D*(\d{4})', line, re.IGNORECASE)
            if tcrd_match and last_date:
                hrs = int(tcrd_match.group(1)[:2])
                mins = int(tcrd_match.group(1)[2:])
                minutes = hrs * 60 + mins

                base_minutes += minutes

                # Holiday bonus once per calendar day
                if is_holiday(last_date) and last_date not in holiday_dates_used:
                    holiday_minutes += HOLIDAY_BONUS_MINUTES
                    holiday_dates_used.add(last_date)

                last_date = None  # move on to next day

    total_minutes = base_minutes + holiday_minutes

    return render_template(
        "index.html",
        base=f"{base_minutes // 60}:{base_minutes % 60:02d}",
        holiday=f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}",
        total=f"{total_minutes // 60}:{total_minutes % 60:02d}"
    )


if __name__ == "__main__":
    app.run()
