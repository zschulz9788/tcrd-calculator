from flask import Flask, request, render_template
import fitz
import re

app = Flask(__name__)

def total_tcrd(pdf):
    doc = fitz.open(stream=pdf.read(), filetype="pdf")
    minutes = 0

    for page in doc:
        text = page.get_text()
        matches = re.findall(r'TCRD\s+(\d{4})', text)
        for t in matches:
            hours = int(t[:2])
            mins = int(t[2:])
            minutes += hours * 60 + mins

    return f"{minutes // 60}:{minutes % 60:02d}"

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        text = request.form.get("schedule_text", "")
        matches = re.findall(r'TCRD\D*(\d{4})', text, re.IGNORECASE)

        minutes = 0
        for t in matches:
            hours = int(t[:2])
            mins = int(t[2:])
            minutes += hours * 60 + mins

        result = f"{minutes // 60}:{minutes % 60:02d}"

    return render_template("index.html", result=result)

