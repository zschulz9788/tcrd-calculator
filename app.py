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

# Super Bowl Sunday = SECOND Sunday of Feb
def super_bowl_sunday(year):
    d = date(year, 2, 1)
    while d.weekday() != 6:  # Sunday
        d += timedelta(days=1)
    return d + timedelta(days=7)

def is_holiday(d):
    year = d.year

    # Fixed-date holidays
    if (d.month, d.day) in [(1, 1), (7, 4), (12, 25)]:
        return True

    # Memorial Day: last Monday of May
    if d.month == 5 and d.weekday() == 0 and d + timedelta(days=7) > date(year, 5, 31):
        return True

    # Labor Day: first Monday of September
    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True

    # Thanksgiving: fourth Thursday of November
    if d.month == 11 and d.weekday() == 3:
        thursdays = [x for x in range(1, 31) if date(year, 11, x).weekday() == 3]
        if d.day == thursdays[3]:
            return True

    # Easter
    if d == easter_date(year):
        return True

    # Super Bowl Sunday
    if d == super_bowl_sunday(year):
        return True

    return False

def infer_year(text, default_year=2026):
    m = re.search(r'PERIOD\s+\d{2}(\d{2})', text, re.IGNORECASE)
    return 2000 + int(m.group(1)) if m else default_year

def split_columns(line):
    parts = re.split(r"\s{8,}", line.rstrip("\n"), maxsplit=1)
    left = parts[0] if len(parts) > 0 else ""
    right = parts[1] if len(parts) > 1 else ""
    return left, right

def build_day_blocks(lines, year):
    blocks = {}

    def push(d, s):
        blocks.setdefault(d, []).append(s)

    def process_column(col_lines):
        current_date = None
        for raw in col_lines:
            line = raw.strip()
            if not line:
                continue

            dm = re.search(r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', line)
            if dm:
                current_date = date(year, MONTHS[dm.group(2)], int(dm.group(1)))
                push(current_date, line)
                continue

            if current_date:
                push(current_date, line)

    left_lines, right_lines = [], []
    for ln in lines:
        l, r = split_columns(ln)
        if l.strip():
            left_lines.append(l)
        if r.strip():
            right_lines.append(r)

    process_column(left_lines)
    process_column(right_lines)

    return blocks

def pretty_blocks(blocks):
    out = []
    for d in sorted(blocks):
        out.append(d.strftime("%d %b").upper() + ":")
        for ln in blocks[d]:
            out.append(f"  {ln}")
        out.append("")
    return "\n".join(out).rstrip()

@app.route("/", methods=["GET", "POST"])
def index():
    schedule_text = request.form.get("schedule_text", "")
    action = request.form.get("action", "")

    base = holiday = total = normalized = ""

    if request.method == "POST" and schedule_text.strip():
        lines = schedule_text.splitlines()
        year = infer_year(schedule_text, default_year=2026)

        # Always normalize (so Normalize button shows something, and Calculate can show it too)
        blocks = build_day_blocks(lines, year)
        normalized = pretty_blocks(blocks)

        if action == "calculate":
            # Base TCRD (known-good, layout-agnostic)
            base_minutes = sum(
                int(t[:2]) * 60 + int(t[2:])
                for t in re.findall(r'TCRD\D*(\d{4})', schedule_text, re.IGNORECASE)
            )

            # Holiday bonus = holiday day block that contains any TCRD
            holiday_days = 0
            for d, blines in blocks.items():
                worked = any(re.search(r'TCRD\D*\d{4}', ln, re.IGNORECASE) for ln in blines)
                if worked and is_holiday(d):
                    holiday_days += 1

            holiday_minutes = holiday_days * HOLIDAY_BONUS_MINUTES
            total_minutes = base_minutes + holiday_minutes

            base = f"{base_minutes // 60}:{base_minutes % 60:02d}"
            holiday = f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}"
            total = f"{total_minutes // 60}:{total_minutes % 60:02d}"

    return render_template(
        "index.html",
        schedule_text=schedule_text,
        normalized=normalized,
        base=base,
        holiday=holiday,
        total=total
    )

if __name__ == "__main__":
    app.run()
