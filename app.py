from flask import Flask, request, render_template
import re
from datetime import date, timedelta

app = Flask(__name__)

HOLIDAY_BONUS_MINUTES = 4 * 60 + 12

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

# -----------------------------
# Easter
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
# Super Bowl Sunday (2nd Sunday Feb)
# -----------------------------
def super_bowl_sunday(year):
    d = date(year, 2, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d + timedelta(days=7)

def is_holiday(d):
    year = d.year

    if (d.month, d.day) in [(1, 1), (7, 4), (12, 25)]:
        return True

    if d.month == 5 and d.weekday() == 0 and d + timedelta(days=7) > date(year, 5, 31):
        return True

    if d.month == 9 and d.weekday() == 0 and d.day <= 7:
        return True

    if d.month == 11 and d.weekday() == 3:
        thursdays = [x for x in range(1, 31) if date(year, 11, x).weekday() == 3]
        if d.day == thursdays[3]:
            return True

    if d == easter_date(year):
        return True

    if d == super_bowl_sunday(year):
        return True

    return False


def infer_year(text):
    m = re.search(r'PERIOD\s+\d{2}(\d{2})', text)
    return 2000 + int(m.group(1)) if m else 2026


def split_columns(line):
    parts = re.split(r"\s{8,}", line.rstrip(), maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def build_day_blocks(lines, year):
    blocks = {}

    def push(d, s):
        blocks.setdefault(d, []).append(s)

    def process_column(col_lines):
        current_date = None
        for line in col_lines:
            dm = re.search(r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', line)
            if dm:
                current_date = date(year, MONTHS[dm.group(2)], int(dm.group(1)))
                push(current_date, line.strip())
                continue
            if current_date:
                push(current_date, line.strip())

    left, right = [], []
    for ln in lines:
        l, r = split_columns(ln)
        if l.strip(): left.append(l)
        if r.strip(): right.append(r)

    process_column(left)
    process_column(right)
    return blocks


def pretty_blocks(blocks):
    out = []
    for d in sorted(blocks):
        out.append(d.strftime("%d %b").upper())
        for ln in blocks[d]:
            out.append(f"  {ln}")
        out.append("")
    return "\n".join(out).strip()


@app.route("/", methods=["GET", "POST"])
def index():
    text = request.form.get("schedule_text", "")
    action = request.form.get("action")

    base = holiday = total = normalized = ""

    if text:
        lines = text.splitlines()
        year = infer_year(text)

        blocks = build_day_blocks(lines, year)
        normalized = pretty_blocks(blocks)

        if action == "calculate":
            # Base TCRD
            base_minutes = sum(
                int(t[:2]) * 60 + int(t[2:])
                for t in re.findall(r'TCRD\D*(\d{4})', text, re.IGNORECASE)
            )

            # Holiday bonus
            holiday_days = 0
            for d, blines in blocks.items():
                worked = any("TCRD" in ln.upper() for ln in blines)
                if worked and is_holiday(d):
                    holiday_days += 1

            holiday_minutes = holiday_days * HOLIDAY_BONUS_MINUTES
            total_minutes = base_minutes + holiday_minutes

            base = f"{base_minutes // 60}:{base_minutes % 60:02d}"
            holiday = f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}"
            total = f"{total_minutes // 60}:{total_minutes % 60:02d}"

    return render_template(
        "index.html",
        base=base,
        holiday=holiday,
        total=total,
        normalized=normalized
    )


if __name__ == "__main__":
    app.run()
