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
# Easter (Gregorian)
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

# -----------------------------
# Super Bowl Sunday (per your contract):
# SECOND Sunday of February
# -----------------------------
def super_bowl_sunday(year: int) -> date:
    d = date(year, 2, 1)
    while d.weekday() != 6:  # Sunday
        d += timedelta(days=1)
    return d + timedelta(days=7)  # second Sunday


def is_holiday(d: date) -> bool:
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


def infer_year_from_text(text: str, default_year: int = 2026) -> int:
    """
    Looks for 'PERIOD 0226' or similar and returns 2026.
    """
    m = re.search(r'PERIOD\s+(\d{2})(\d{2})', text, re.IGNORECASE)
    if m:
        yy = int(m.group(2))
        return 2000 + yy
    return default_year


def split_columns(line: str) -> tuple[str, str]:
    """
    Split a line into left/right columns using the big whitespace gap.
    Works fine for one-column too (right will be empty).
    """
    parts = re.split(r"\s{8,}", line.rstrip("\n"), maxsplit=1)
    left = parts[0] if len(parts) > 0 else ""
    right = parts[1] if len(parts) > 1 else ""
    return left, right


def build_day_blocks(lines: list[str], year: int) -> dict[date, list[str]]:
    """
    Build {date -> [lines]} by parsing each column independently, then merging.
    This is the 'foolproof' part: we no longer guess which date a TCRD belongs to.
    """
    blocks: dict[date, list[str]] = {}

    def push(d: date, s: str):
        blocks.setdefault(d, []).append(s)

    def process_column(col_lines: list[str]):
        current_date = None
        for raw in col_lines:
            line = raw.strip()
            if not line:
                continue

            dm = re.search(r'(\d{2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', line)
            if dm:
                day = int(dm.group(1))
                mon = MONTHS[dm.group(2)]
                current_date = date(year, mon, day)
                push(current_date, line)
                continue

            if current_date:
                push(current_date, line)

    # Separate the original pasted text into two streams (left and right)
    left_lines, right_lines = [], []
    for ln in lines:
        left, right = split_columns(ln)
        if left.strip():
            left_lines.append(left)
        if right.strip():
            right_lines.append(right)

    process_column(left_lines)
    process_column(right_lines)

    return blocks


def blocks_to_pretty_text(blocks: dict[date, list[str]]) -> str:
    """
    Human-readable normalized view (optional display).
    """
    out = []
    for d in sorted(blocks.keys()):
        out.append(f"{d.strftime('%d %b').upper()}:")
        for ln in blocks[d]:
            out.append(f"  {ln}")
        out.append("")
    return "\n".join(out).rstrip()


@app.route("/", methods=["GET", "POST"])
def index():
    base_minutes = 0
    holiday_minutes = 0
    normalized = ""

    if request.method == "POST":
        text = request.form.get("schedule_text", "")
        lines = text.splitlines()

        year = infer_year_from_text(text, default_year=2026)

        # -------------------------
        # Base TCRD (layout-agnostic, known-good)
        # -------------------------
        matches = re.findall(r'TCRD\D*(\d{4})', text, re.IGNORECASE)
        for t in matches:
            base_minutes += int(t[:2]) * 60 + int(t[2:])

        # -------------------------
        # Normalize into day blocks (foolproof)
        # -------------------------
        blocks = build_day_blocks(lines, year)
        normalized = blocks_to_pretty_text(blocks)

        # -------------------------
        # Holiday bonus: any holiday day block that contains a TCRD line
        # (OFF-only days won't have TCRD)
        # -------------------------
        holiday_worked_days = 0
        for d, blines in blocks.items():
            # "worked" if any TCRD appears in that day's block
            worked = any(re.search(r'TCRD\D*\d{4}', ln, re.IGNORECASE) for ln in blines)
            if worked and is_holiday(d):
                holiday_worked_days += 1

        holiday_minutes = holiday_worked_days * HOLIDAY_BONUS_MINUTES

    total_minutes = base_minutes + holiday_minutes

    return render_template(
        "index.html",
        base=f"{base_minutes // 60}:{base_minutes % 60:02d}",
        holiday=f"{holiday_minutes // 60}:{holiday_minutes % 60:02d}",
        total=f"{total_minutes // 60}:{total_minutes % 60:02d}",
        normalized=normalized
    )


if __name__ == "__main__":
    app.run()
