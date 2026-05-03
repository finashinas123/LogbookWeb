from flask import Flask, render_template, request, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from weasyprint import HTML
from pathlib import Path
import base64
from datetime import datetime
import re
import os
from pathlib import Path
import platform

# ------------------ APP SETUP ------------------ #
app = Flask(__name__)
app.secret_key = "supersecretkey"
#basedir = Path("C:\OR Data\MCC USER FILES\CPAFORMS")#

#basedir = Path(__file__).resolve().parent#

# Detect environment
if platform.system() == "Windows":
    # Save to C drive
    basedir = Path("C:/CPAFORMS")
else:
    # Linux / Render
    basedir = Path("/tmp")

# Ensure folder exists
basedir.mkdir(parents=True, exist_ok=True)
# ------------------ DATABASE ------------------ #
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{basedir / 'logbook.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------ MODEL ------------------ #
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_type = db.Column(db.String(50))
    filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------ INIT DB ------------------ #
with app.app_context():
    db.create_all()

# ------------------ PDF FOLDER ------------------ #
PDF_ROOT = basedir / "generated_pdfs"
PDF_ROOT.mkdir(exist_ok=True)

# ------------------ IMAGE ENCODING ------------------ #
def encode(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = encode(basedir / "static/images/logo.png")
bg_base64 = encode(basedir / "static/images/opaclogo.png")
sign_base64 = encode(basedir / "static/images/sign.png")

# ------------------ SAFE FILENAME ------------------ #
def safe_filename(text):
    text = text or "procedure"
    text = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
    return text[:50]

# ------------------ FORMAT DATE ------------------ #
def format_date(date_str):
    """
    Converts YYYY-MM-DD → DD/MM/YYYY
    """
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return date_str.replace("/", "-")

# ------------------ HOME ------------------ #

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return cpbs()   # forward POST to your PDF logic
    return render_template("form1.html")
# ------------------ DOWNLOAD ------------------ #
@app.route('/download/<path:filepath>')
def download(filepath):
    return send_from_directory(PDF_ROOT, filepath, as_attachment=True)

# ------------------ PDF GENERATION ------------------ #
def generate_pdf(template, data, folder_name):
    folder = PDF_ROOT / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    MRN = safe_filename(data.get("MRN"))

    form_date_raw = data.get("date")
    formatted_date = format_date(form_date_raw)

    safe_date = formatted_date.replace("/", "-")

    filename = folder / f"{MRN}_{safe_date}.pdf"

    filename.parent.mkdir(parents=True, exist_ok=True)

    html = render_template(
        template,
        data=data,
        logo_base64=logo_base64,
        bg_base64=bg_base64,
        sign_base64=sign_base64
    )

    pdf = HTML(string=html).write_pdf()

    with open(filename, "wb") as f:
        f.write(pdf)

    db.session.add(Report(
        form_type=folder_name,
        filename=str(filename.relative_to(PDF_ROOT))
    ))
    db.session.commit()

    return filename, pdf

@app.route('/cpbs', methods=['GET', 'POST'])
def cpbs():
    if request.method == 'POST':
        data = request.form.to_dict()

        # ---------------- CALCULATIONS ---------------- #
        try:
            h = float(data.get("height", 0))
            w = float(data.get("weight", 0))
            ci = float(data.get("ci", 2.4))

            bsa = ((h * w) / 3600) ** 0.5 if h and w else 0
            flow = bsa * ci
        except:
            bsa, flow = 0, 0

        data["bsa"] = round(bsa, 2)
        data["flow"] = round(flow, 2)

        # ---------------- USE COMMON PDF FUNCTION ---------------- #
        filename, pdf = generate_pdf("pdf1.html", data, "cpa")

        # ---------------- DOWNLOAD ---------------- #
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename.name}"
            }
        )

    return render_template("form1.html")

# ------------------ RUN ------------------ #
if __name__ == "__main__":
    app.run(debug=True)
