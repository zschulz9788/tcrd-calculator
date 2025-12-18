from flask import Flask, request, render_template
import re
from datetime import date, timedelta

app = Flask(__name__)

HOLIDAY_BONUS_MINUTES = 4 * 60 + 12  # 4:12 = 252 minutes

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

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

    # TODO: Easter, Super Bowl Sunday (can be added later)
    return False


@app.route("/", methods=["GET", "POST"])
def index():
    base_minutes = 0
    holiday_minutes = 0
    total_minutes = 0

    if request.method == "POST":
        text = request.form.get("schedule_text", "")
        lines = text.splitlines()

        current_date = None
        year = 2026  # from PERIOD 0126

        for line in lines:
            # Detect date lines like "01 JAN"
            date_match = re.search(
                r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',
                line
            )

            if date_match:
                day = int(date_match.group(1))
                month = MONTHS[date_match.group(2)]
                current_date = date(year, month, day)

            # OFF day = ignore
            if current_date and "OFF" in line:
                current_date = None

            # Detect TCRD
            tcrd_match = re.search(r'TCRD\D*(\d{4})', line, re.IGNORECASE)

            if tcrd_match and current_date:
                hrs = int(tcrd_match.group(1)[:2])
                mins = int(tcrd_match.group(1)[2:])
                minutes = hrs * 60 + mins

                base_minutes += minutes

                if is_holiday(current_date):
                    holiday_minutes += HOLIDAY_BONUS_MINUTES

                current_date = None  # prevent double counting per day

        total_minutes = base_minutes + holiday_minutes

    return render_template(
        "index.html",
        base=f"{base_minutes // 60}:{base_minutes % 60:02d}",
        holiday=f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}",
        total=f"{total_minutes // 60}:{total_minutes % 60:02d}"
    )


if __name__ == "__main__":
    app.run()
